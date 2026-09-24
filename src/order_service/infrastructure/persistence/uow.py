from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from order_service.application.ports.uow import UnitOfWorkImplementation
from order_service.infrastructure.persistence.repositories import (
    SqlAlchemyInboxRepository,
    SqlAlchemyOrderRepository,
    SqlAlchemyOutboxRepository,
)


class SqlAlchemyUnitOfWork:
    """Фабрика единиц работы с базой данных."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def __call__(
        self,
    ) -> AsyncIterator[UnitOfWorkImplementation]:
        """Создать единицу работы в контексте транзакции."""

        async with self._session_factory() as session:
            try:
                yield _UnitOfWorkImplementation(session)
                await session.rollback()
            except Exception:
                await session.rollback()
                raise


class _UnitOfWorkImplementation:
    """Активная единица работы с базой данных."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._orders = SqlAlchemyOrderRepository(session)
        self._outbox = SqlAlchemyOutboxRepository(session)
        self._inbox = SqlAlchemyInboxRepository(session)

    @property
    def orders(self) -> SqlAlchemyOrderRepository:
        """Получить репозиторий заказов."""

        return self._orders

    @property
    def outbox(self) -> SqlAlchemyOutboxRepository:
        """Получить репозиторий исходящих событий."""

        return self._outbox

    @property
    def inbox(self) -> SqlAlchemyInboxRepository:
        """Получить репозиторий входящих событий."""

        return self._inbox

    async def commit(self) -> None:
        """Зафиксировать текущую транзакцию."""

        await self._session.commit()
