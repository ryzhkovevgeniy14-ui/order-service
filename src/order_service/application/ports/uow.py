from contextlib import AbstractAsyncContextManager
from typing import Protocol

from order_service.application.ports.repositories import OrderRepository


class UnitOfWorkImplementation(Protocol):
    """Интерфейс активной единицы работы."""

    @property
    def orders(self) -> OrderRepository:
        """Получить репозиторий заказов."""

    async def commit(self) -> None:
        """Зафиксировать текущую транзакцию."""


class UnitOfWork(Protocol):
    """Интерфейс фабрики единиц работы."""

    def __call__(self) -> AbstractAsyncContextManager[UnitOfWorkImplementation]:
        """Создать единицу работы в контексте транзакции."""
