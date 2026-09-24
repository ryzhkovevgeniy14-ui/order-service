import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from order_service.application.ports.catalog import CatalogClient
from order_service.application.ports.notifications import (
    NotificationClient,
    NotificationServiceError,
)
from order_service.application.ports.payments import PaymentClient, PaymentServiceError
from order_service.application.ports.uow import UnitOfWork
from order_service.domain.entities import Order, OrderStatus
from order_service.domain.exceptions import InvalidOrderError

logger = logging.getLogger(__name__)


class CreateOrder:
    """Сценарий создания заказа."""

    def __init__(
        self,
        uow: UnitOfWork,
        catalog: CatalogClient,
        payments: PaymentClient,
        notifications: NotificationClient,
        callback_url: str,
    ) -> None:
        self._uow = uow
        self._catalog = catalog
        self._payments = payments
        self._notifications = notifications
        self._callback_url = callback_url

    async def execute(
        self,
        user_id: str,
        quantity: int,
        item_id: UUID,
        idempotency_key: str,
    ) -> Order:
        """Создать заказ."""

        if quantity <= 0:
            raise InvalidOrderError("Количество должно быть больше нуля.")

        async with self._uow() as uow:
            existing_order = await uow.orders.get_by_idempotency_key(
                idempotency_key,
            )

        if existing_order is not None:
            return existing_order

        item = await self._catalog.get_item(item_id)

        if item.available_qty < quantity:
            raise InvalidOrderError("Недостаточно товара на складе.")

        now = datetime.now(UTC)

        order = Order(
            id=uuid4(),
            user_id=user_id,
            quantity=quantity,
            item_id=item_id,
            status=OrderStatus.NEW,
            idempotency_key=idempotency_key,
            created_at=now,
            updated_at=now,
        )

        amount = item.price * quantity

        try:
            await self._payments.create_payment(
                order_id=order.id,
                amount=amount,
                callback_url=self._callback_url,
                idempotency_key=idempotency_key,
            )
        except PaymentServiceError:
            order.status = OrderStatus.CANCELLED

        async with self._uow() as uow:
            await uow.orders.add(order)
            await uow.commit()

        try:
            if order.status == OrderStatus.NEW:
                await self._notifications.send_notification(
                    message="Ваш заказ создан и ожидает оплаты",
                    reference_id=order.id,
                    idempotency_key=f"{order.idempotency_key}:NEW",
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

        return order
