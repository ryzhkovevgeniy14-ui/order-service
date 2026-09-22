from uuid import UUID

from order_service.application.ports.uow import UnitOfWork
from order_service.domain.entities import Order
from order_service.domain.exceptions import OrderNotFoundError


class GetOrder:
    """Сценарий получения заказа."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, order_id: UUID) -> Order:
        """Получить заказ по идентификатору."""

        async with self._uow() as uow:
            order = await uow.orders.get_by_id(order_id)

        if order is None:
            raise OrderNotFoundError("Заказ не найден.")

        return order
