from typing import Protocol
from uuid import UUID

from order_service.domain.entities import Order


class OrderRepository(Protocol):
    """Интерфейс репозитория заказов."""

    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Получить заказ по идентификатору."""

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Order | None:
        """Получить заказ по ключу идемпотентности."""

    async def add(self, order: Order) -> None:
        """Добавить заказ."""
