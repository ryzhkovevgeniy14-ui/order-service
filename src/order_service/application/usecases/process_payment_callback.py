import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from order_service.application.ports.notifications import (
    NotificationClient,
    NotificationServiceError,
)
from order_service.application.ports.outbox import OutboxEvent
from order_service.application.ports.payments import (
    PaymentCallback,
    PaymentStatus,
)
from order_service.application.ports.uow import UnitOfWork
from order_service.domain.entities import Order, OrderStatus
from order_service.domain.exceptions import (
    InvalidStatusTransitionError,
    OrderNotFoundError,
)

logger = logging.getLogger(__name__)


class ProcessPaymentCallback:
    """Сценарий обработки callback от Payments Service."""

    def __init__(
        self,
        uow: UnitOfWork,
        notifications: NotificationClient,
    ) -> None:
        self._uow = uow
        self._notifications = notifications

    async def execute(self, callback: PaymentCallback) -> None:
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

                event_type = "order.paid"

            elif callback.status == PaymentStatus.FAILED:
                if order.status == OrderStatus.CANCELLED:
                    return

                if order.status != OrderStatus.NEW:
                    raise InvalidStatusTransitionError(
                        "Недопустимый переход статуса заказа.",
                    )

                event_type = "order.cancelled"

            else:
                return

            now = datetime.now(UTC)
            order.status = (
                OrderStatus.PAID
                if callback.status == PaymentStatus.SUCCEEDED
                else OrderStatus.CANCELLED
            )
            order.updated_at = now

            await uow.orders.update(order)
            await uow.outbox.add(
                self._create_outbox_event(
                    order=order,
                    event_type=event_type,
                    created_at=now,
                ),
            )
            await uow.commit()

        try:
            if order.status == OrderStatus.PAID:
                await self._notifications.send_notification(
                    message="Ваш заказ успешно оплачен и готов к отправке",
                    reference_id=order.id,
                    idempotency_key=f"{order.idempotency_key}:PAID",
                )
            elif order.status == OrderStatus.CANCELLED:
                await self._notifications.send_notification(
                    message="Ваш заказ отменен. Причина: Payment failed",
                    reference_id=order.id,
                    idempotency_key=f"{order.idempotency_key}:CANCELLED",
                )
        except NotificationServiceError:
            logger.exception(
                "Не удалось отправить уведомление об изменении статуса заказа.",
                extra={"order_id": str(order.id)},
            )

    @staticmethod
    def _create_outbox_event(
        order: Order,
        event_type: str,
        created_at: datetime,
    ) -> OutboxEvent:
        """Создать событие Outbox для изменения статуса заказа."""

        payload = {
            "event_type": event_type,
            "order_id": str(order.id),
            "item_id": str(order.item_id),
            "quantity": order.quantity,
        }

        if event_type == "order.paid":
            payload["idempotency_key"] = order.idempotency_key
        else:
            payload["reason"] = "Payment failed"

        return OutboxEvent(
            id=uuid4(),
            order_id=order.id,
            event_type=event_type,
            payload=json.dumps(payload),
            published=False,
            created_at=created_at,
        )
