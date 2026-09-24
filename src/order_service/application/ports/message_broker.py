from typing import Protocol


class MessageBroker(Protocol):
    """Интерфейс брокера сообщений."""

    async def publish(
        self,
        topic: str,
        message: str,
    ) -> None:
        """Опубликовать сообщение в топик."""
