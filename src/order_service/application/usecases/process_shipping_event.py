import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from order_service.application.ports.inbox import InboxEvent
from order_service.application.ports.notifications import (
    NotificationClient,
    NotificationServiceError,
)
from order_service.application.ports.uow import UnitOfWork
from order_service.domain.entities import OrderStatus
from order_service.domain.exceptions import (
    InvalidStatusTransitionError,
    OrderNotFoundError,
)

logger = logging.getLogger(__name__)


class ProcessShippingEvent:
    """Сценарий обработки события от Shipping Service."""

    def __init__(
        self,
        uow: UnitOfWork,
        notifications: NotificationClient,
    ) -> None:
        self._uow = uow
        self._notifications = notifications

    async def execute(
        self,
        order_id: UUID,
        event_type: str,
        reason: str | None = None,
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

        try:
            if order.status == OrderStatus.SHIPPED:
                await self._notifications.send_notification(
                    message="Ваш заказ отправлен в доставку",
                    reference_id=order.id,
                    idempotency_key=f"{order.idempotency_key}:SHIPPED",
                )
            elif order.status == OrderStatus.CANCELLED:
                await self._notifications.send_notification(
                    message=f"Ваш заказ отменен. Причина: {reason}",
                    reference_id=order.id,
                    idempotency_key=f"{order.idempotency_key}:CANCELLED",
                )
        except NotificationServiceError:
            logger.exception(
                "Не удалось отправить уведомление об изменении статуса заказа.",
                extra={"order_id": str(order.id)},
            )
