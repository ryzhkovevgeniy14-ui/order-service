import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from order_service.application.ports.catalog import (
    CatalogItemNotFoundError,
    CatalogServiceError,
)
from order_service.application.usecases.process_shipping_event import (
    ProcessShippingEvent,
)
from order_service.application.usecases.publish_outbox_events import (
    PublishOutboxEvents,
)
from order_service.domain.exceptions import (
    InvalidOrderError,
    OrderNotFoundError,
)
from order_service.infrastructure.http.catalog_client import HttpCatalogClient
from order_service.infrastructure.http.payments_client import HttpPaymentsClient
from order_service.infrastructure.messaging.kafka_consumer import KafkaConsumer
from order_service.infrastructure.messaging.kafka_producer import KafkaProducer
from order_service.infrastructure.persistence.database import Database
from order_service.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from order_service.presentation.api.routes.orders import router as orders_router
from order_service.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управлять ресурсами приложения."""

    database = Database(settings.postgres_connection_string)
    catalog = HttpCatalogClient(
        base_url=settings.capashino_base_url,
        api_key=settings.capashino_api_key,
    )

    payments = HttpPaymentsClient(
        base_url=settings.capashino_base_url,
        api_key=settings.capashino_api_key,
    )

    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )

    uow = SqlAlchemyUnitOfWork(database.session_factory)

    publisher = PublishOutboxEvents(
        uow=uow,
        message_broker=producer,
        order_events_topic=settings.order_events_topic,
    )

    process_shipping_event = ProcessShippingEvent(uow=uow)

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.shipment_events_topic,
        group_id="order-service",
        process_shipping_event=process_shipping_event,
    )

    async def publish_outbox_loop() -> None:
        while True:
            try:
                await publisher.execute()
            except Exception:
                logger.exception("Ошибка публикации событий Outbox.")

            await asyncio.sleep(1)

    app.state.database = database
    app.state.catalog = catalog
    app.state.payments = payments
    app.state.producer = producer

    publisher_task: asyncio.Task[None] | None = None
    consumer_task: asyncio.Task[None] | None = None

    try:
        await producer.start()
        await consumer.start()

        publisher_task = asyncio.create_task(publish_outbox_loop())
        consumer_task = asyncio.create_task(consumer.consume())

        yield
    finally:
        if publisher_task is not None:
            publisher_task.cancel()

        if consumer_task is not None:
            consumer_task.cancel()

        if publisher_task is not None:
            try:
                await publisher_task
            except asyncio.CancelledError:
                pass

        if consumer_task is not None:
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

        await consumer.stop()
        await producer.stop()

        await catalog.close()
        await payments.close()
        await database.dispose()


async def invalid_order_handler(
    request: Request,
    exc: InvalidOrderError,
) -> JSONResponse:
    """Обработать ошибку валидации заказа."""

    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


async def order_not_found_handler(
    request: Request,
    exc: OrderNotFoundError,
) -> JSONResponse:
    """Обработать отсутствие заказа."""

    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


async def catalog_service_error_handler(
    request: Request,
    exc: CatalogServiceError,
) -> JSONResponse:
    """Обработать ошибку Catalog Service."""

    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
    )


async def catalog_item_not_found_handler(
    request: Request,
    exc: CatalogItemNotFoundError,
) -> JSONResponse:
    """Обработать отсутствие товара в каталоге."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def create_app() -> FastAPI:
    """Создать приложение FastAPI."""

    app = FastAPI(
        title="Order Service",
        lifespan=lifespan,
    )

    app.include_router(orders_router)

    app.add_exception_handler(InvalidOrderError, invalid_order_handler)
    app.add_exception_handler(OrderNotFoundError, order_not_found_handler)
    app.add_exception_handler(
        CatalogItemNotFoundError,
        catalog_item_not_found_handler,
    )
    app.add_exception_handler(
        CatalogServiceError,
        catalog_service_error_handler,
    )

    return app
