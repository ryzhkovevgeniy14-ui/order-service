from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class OutboxEvent:
    """Событие, ожидающее публикации."""

    id: UUID
    order_id: UUID
    event_type: str
    payload: str
    published: bool
    created_at: datetime


class OutboxRepository(Protocol):
    """Интерфейс репозитория исходящих событий."""

    async def add(self, event: OutboxEvent) -> None:
        """Добавить событие в Outbox."""

    async def get_unpublished(self) -> list[OutboxEvent]:
        """Получить неопубликованные события."""

    async def mark_as_published(self, event_id: UUID) -> None:
        """Отметить событие как опубликованное."""
