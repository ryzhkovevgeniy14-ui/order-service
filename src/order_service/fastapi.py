from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from order_service.application.ports.catalog import (
    CatalogItemNotFoundError,
    CatalogServiceError,
)
from order_service.domain.exceptions import (
    InvalidOrderError,
    OrderNotFoundError,
)
from order_service.infrastructure.http.catalog_client import HttpCatalogClient
from order_service.infrastructure.http.notifications_client import (
    HttpNotificationsClient,
)
from order_service.infrastructure.http.payments_client import HttpPaymentsClient
from order_service.infrastructure.persistence.database import Database
from order_service.presentation.api.routes.orders import router as orders_router
from order_service.settings import settings


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

    notifications = HttpNotificationsClient(
        base_url=settings.capashino_base_url,
        api_key=settings.capashino_api_key,
    )

    app.state.database = database
    app.state.catalog = catalog
    app.state.payments = payments
    app.state.notifications = notifications

    try:
        yield
    finally:
        await catalog.close()
        await payments.close()
        await notifications.close()
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
