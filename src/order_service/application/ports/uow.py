from contextlib import AbstractAsyncContextManager
from typing import Protocol

from order_service.application.ports.inbox import InboxRepository
from order_service.application.ports.outbox import OutboxRepository
from order_service.application.ports.repositories import OrderRepository


class UnitOfWorkImplementation(Protocol):
    """Интерфейс активной единицы работы."""

    @property
    def orders(self) -> OrderRepository:
        """Получить репозиторий заказов."""

    @property
    def outbox(self) -> OutboxRepository:
        """Получить репозиторий исходящих событий."""

    @property
    def inbox(self) -> InboxRepository:
        """Получить репозиторий входящих событий."""

    async def commit(self) -> None:
        """Зафиксировать текущую транзакцию."""


class UnitOfWork(Protocol):
    """Интерфейс фабрики единиц работы."""

    def __call__(self) -> AbstractAsyncContextManager[UnitOfWorkImplementation]:
        """Создать единицу работы в контексте транзакции."""
