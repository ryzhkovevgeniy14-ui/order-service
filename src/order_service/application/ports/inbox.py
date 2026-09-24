from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class InboxEvent:
    """Обработанное входящее событие."""

    id: UUID
    order_id: UUID
    event_type: str
    created_at: datetime


class InboxRepository(Protocol):
    """Интерфейс репозитория входящих событий."""

    async def exists(
        self,
        order_id: UUID,
        event_type: str,
    ) -> bool:
        """Проверить, было ли событие обработано."""

    async def add(self, event: InboxEvent) -> None:
        """Добавить обработанное событие."""
