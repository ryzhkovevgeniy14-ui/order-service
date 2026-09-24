from typing import Protocol
from uuid import UUID


class NotificationServiceError(Exception):
    """Ошибка при обращении к Notifications Service."""


class NotificationClient(Protocol):
    """Интерфейс клиента Notifications Service."""

    async def send_notification(
        self,
        message: str,
        reference_id: UUID,
        idempotency_key: str,
    ) -> None:
        """Отправить уведомление."""
