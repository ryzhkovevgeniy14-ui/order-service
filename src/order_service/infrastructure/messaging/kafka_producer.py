from aiokafka import AIOKafkaProducer


class KafkaProducer:
    """Kafka Producer для публикации сообщений."""

    def __init__(self, bootstrap_servers: str) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
        )

    async def start(self) -> None:
        """Запустить Kafka Producer."""
        await self._producer.start()

    async def stop(self) -> None:
        """Остановить Kafka Producer."""
        await self._producer.stop()

    async def publish(
        self,
        topic: str,
        message: str,
    ) -> None:
        """Опубликовать сообщение в Kafka."""
        await self._producer.send_and_wait(
            topic,
            message.encode("utf-8"),
        )
