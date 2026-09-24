from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from order_service.application.ports.inbox import InboxEvent
from order_service.application.ports.outbox import OutboxEvent
from order_service.domain.entities import Order, OrderStatus
from order_service.infrastructure.persistence.models import (
    InboxEventModel,
    OrderModel,
    OutboxEventModel,
)


class SqlAlchemyOrderRepository:
    """Репозиторий заказов на SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Получить заказ по идентификатору."""

        result = await self._session.execute(
            select(OrderModel).where(OrderModel.id == order_id),
        )
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Order | None:
        """Получить заказ по ключу идемпотентности."""

        result = await self._session.execute(
            select(OrderModel).where(
                OrderModel.idempotency_key == idempotency_key,
            ),
        )
        model = result.scalar_one_or_none()

        if model is None:
            return None

        return self._to_domain(model)

    async def add(self, order: Order) -> None:
        """Добавить заказ."""

        self._session.add(self._to_model(order))

    async def update(self, order: Order) -> None:
        """Обновить заказ."""

        await self._session.merge(self._to_model(order))

    @staticmethod
    def _to_domain(model: OrderModel) -> Order:
        """Преобразовать модель базы данных в доменную сущность."""

        return Order(
            id=model.id,
            user_id=model.user_id,
            quantity=model.quantity,
            item_id=model.item_id,
            status=OrderStatus(model.status),
            idempotency_key=model.idempotency_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _to_model(order: Order) -> OrderModel:
        """Преобразовать доменную сущность в модель базы данных."""

        return OrderModel(
            id=order.id,
            user_id=order.user_id,
            quantity=order.quantity,
            item_id=order.item_id,
            status=order.status.value,
            idempotency_key=order.idempotency_key,
            created_at=order.created_at,
            updated_at=order.updated_at,
        )


class SqlAlchemyOutboxRepository:
    """Репозиторий исходящих событий на SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: OutboxEvent) -> None:
        """Добавить событие в Outbox."""

        self._session.add(
            OutboxEventModel(
                id=event.id,
                order_id=event.order_id,
                event_type=event.event_type,
                payload=event.payload,
                published=event.published,
                created_at=event.created_at,
            ),
        )

    async def get_unpublished(self) -> list[OutboxEvent]:
        """Получить неопубликованные события."""

        result = await self._session.execute(
            select(OutboxEventModel)
            .where(OutboxEventModel.published.is_(False))
            .order_by(OutboxEventModel.created_at),
        )

        return [self._to_domain(model) for model in result.scalars()]

    async def mark_as_published(self, event_id: UUID) -> None:
        """Отметить событие как опубликованное."""

        result = await self._session.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.id == event_id,
            ),
        )
        model = result.scalar_one_or_none()

        if model is not None:
            model.published = True

    @staticmethod
    def _to_domain(model: OutboxEventModel) -> OutboxEvent:
        """Преобразовать модель базы данных в доменную модель события."""

        return OutboxEvent(
            id=model.id,
            order_id=model.order_id,
            event_type=model.event_type,
            payload=model.payload,
            published=model.published,
            created_at=model.created_at,
        )


class SqlAlchemyInboxRepository:
    """Репозиторий входящих событий на SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(
        self,
        order_id: UUID,
        event_type: str,
    ) -> bool:
        """Проверить, было ли событие обработано."""

        result = await self._session.execute(
            select(InboxEventModel.id).where(
                InboxEventModel.order_id == order_id,
                InboxEventModel.event_type == event_type,
            ),
        )

        return result.scalar_one_or_none() is not None

    async def add(self, event: InboxEvent) -> None:
        """Добавить обработанное событие."""

        self._session.add(
            InboxEventModel(
                id=event.id,
                order_id=event.order_id,
                event_type=event.event_type,
                created_at=event.created_at,
            ),
        )
