from datetime import UTC, datetime
from uuid import UUID, uuid4

from order_service.application.ports.inbox import InboxEvent
from order_service.application.ports.uow import UnitOfWork
from order_service.domain.entities import OrderStatus
from order_service.domain.exceptions import (
    InvalidStatusTransitionError,
    OrderNotFoundError,
)


class ProcessShippingEvent:
    """Сценарий обработки события от Shipping Service."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(
        self,
        order_id: UUID,
        event_type: str,
    ) -> None:
        async with self._uow() as uow:
            if await uow.inbox.exists(order_id, event_type):
                return

            order = await uow.orders.get_by_id(order_id)

            if order is None:
                raise OrderNotFoundError("Заказ не найден.")

            if event_type == "order.shipped":
                new_status = OrderStatus.SHIPPED
            elif event_type == "order.cancelled":
                new_status = OrderStatus.CANCELLED
            else:
                return

            if order.status in (
                OrderStatus.SHIPPED,
                OrderStatus.CANCELLED,
            ):
                raise InvalidStatusTransitionError(
                    "Недопустимый переход статуса заказа.",
                )

            now = datetime.now(UTC)
            order.status = new_status
            order.updated_at = now

            await uow.orders.update(order)
            await uow.inbox.add(
                InboxEvent(
                    id=uuid4(),
                    order_id=order_id,
                    event_type=event_type,
                    created_at=now,
                ),
            )
            await uow.commit()
