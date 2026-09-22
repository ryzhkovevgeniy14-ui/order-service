from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from order_service.domain.entities import Order, OrderStatus
from order_service.infrastructure.persistence.models import OrderModel


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
        idempotency_key: UUID,
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
