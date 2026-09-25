import asyncio

from order_service.application.usecases.process_shipping_event import (
    ProcessShippingEvent,
)
from order_service.infrastructure.http.notifications_client import (
    HttpNotificationsClient,
)
from order_service.infrastructure.messaging.kafka_consumer import KafkaConsumer
from order_service.infrastructure.persistence.database import Database
from order_service.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from order_service.settings import settings


async def main() -> None:
    """Запустить Kafka Consumer."""

    database = Database(settings.postgres_connection_string)

    notifications = HttpNotificationsClient(
        base_url=settings.capashino_base_url,
        api_key=settings.capashino_api_key,
    )

    uow = SqlAlchemyUnitOfWork(database.session_factory)

    process_shipping_event = ProcessShippingEvent(
        uow=uow,
        notifications=notifications,
    )

    consumer = KafkaConsumer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic=settings.shipment_events_topic,
        group_id="order-service",
        process_shipping_event=process_shipping_event,
    )

    await consumer.start()

    try:
        await consumer.consume()
    finally:
        await consumer.stop()
        await notifications.close()
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
