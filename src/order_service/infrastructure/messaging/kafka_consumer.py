import json
import logging
from uuid import UUID

from aiokafka import AIOKafkaConsumer

from order_service.application.usecases.process_shipping_event import (
    ProcessShippingEvent,
)

logger = logging.getLogger(__name__)


class KafkaConsumer:
    """Kafka Consumer для обработки событий Shipping Service."""

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        process_shipping_event: ProcessShippingEvent,
    ) -> None:
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
        )
        self._process_shipping_event = process_shipping_event

    async def start(self) -> None:
        """Запустить Kafka Consumer."""
        await self._consumer.start()

    async def stop(self) -> None:
        """Остановить Kafka Consumer."""
        await self._consumer.stop()

    async def consume(self) -> None:
        """Получать и обрабатывать события из Kafka."""

        async for message in self._consumer:
            try:
                await self._process_message(message.value)
            except Exception:
                logger.exception("Ошибка обработки Kafka-сообщения.")

    async def _process_message(self, message: bytes) -> None:
        """Разобрать сообщение и передать его в use case."""
        try:
            payload = json.loads(message.decode("utf-8"))

            await self._process_shipping_event.execute(
                order_id=UUID(payload["order_id"]),
                event_type=payload["event_type"],
            )
        except (json.JSONDecodeError, KeyError, ValueError) as error:
            logger.error("Ошибка обработки Kafka-сообщения: %s", error)
