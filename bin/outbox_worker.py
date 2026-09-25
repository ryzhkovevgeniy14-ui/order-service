import asyncio
import logging

from order_service.application.usecases.publish_outbox_events import (
    PublishOutboxEvents,
)
from order_service.infrastructure.messaging.kafka_producer import KafkaProducer
from order_service.infrastructure.persistence.database import Database
from order_service.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from order_service.settings import settings

logger = logging.getLogger(__name__)


async def main() -> None:
    """Запустить Outbox-воркер."""

    database = Database(settings.postgres_connection_string)
    producer = KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
    )
    uow = SqlAlchemyUnitOfWork(database.session_factory)

    publisher = PublishOutboxEvents(
        uow=uow,
        message_broker=producer,
        order_events_topic=settings.order_events_topic,
    )

    await producer.start()

    try:
        while True:
            try:
                await publisher.execute()
            except Exception:
                logger.exception("Ошибка публикации событий Outbox.")

            await asyncio.sleep(1)
    finally:
        await producer.stop()
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
