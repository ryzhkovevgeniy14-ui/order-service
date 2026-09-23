from datetime import UTC, datetime

from order_service.application.ports.payments import PaymentCallback, PaymentStatus
from order_service.application.ports.uow import UnitOfWork
from order_service.domain.entities import OrderStatus
from order_service.domain.exceptions import (
    InvalidStatusTransitionError,
    OrderNotFoundError,
)


class ProcessPaymentCallback:
    """Сценарий обработки callback от Payments Service."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, callback: PaymentCallback) -> None:
        """Обработать результат платежа."""

        async with self._uow() as uow:
            order = await uow.orders.get_by_id(callback.order_id)

            if order is None:
                raise OrderNotFoundError("Заказ не найден.")

            if callback.status == PaymentStatus.SUCCEEDED:
                if order.status == OrderStatus.PAID:
                    return

                if order.status != OrderStatus.NEW:
                    raise InvalidStatusTransitionError(
                        "Недопустимый переход статуса заказа.",
                    )

                order.status = OrderStatus.PAID

            elif callback.status == PaymentStatus.FAILED:
                if order.status == OrderStatus.CANCELLED:
                    return

                if order.status != OrderStatus.NEW:
                    raise InvalidStatusTransitionError(
                        "Недопустимый переход статуса заказа.",
                    )

                order.status = OrderStatus.CANCELLED

            order.updated_at = datetime.now(UTC)

            await uow.orders.update(order)
            await uow.commit()
