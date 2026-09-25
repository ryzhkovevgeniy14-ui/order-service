from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from order_service.application.usecases.process_shipping_event import (
    ProcessShippingEvent,
)


@pytest.mark.asyncio
async def test_create_order_sends_new_notification(
    client: AsyncClient,
    item_id: UUID,
    notifications,
) -> None:
    """Проверить отправку уведомления при создании заказа."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-notification-new-key",
        },
    )

    assert response.status_code == 201

    order_id = UUID(response.json()["id"])

    assert notifications.notifications == [
        (
            "NEW: Ваш заказ создан и ожидает оплаты",
            order_id,
            "test-notification-new-key:NEW",
        ),
    ]


@pytest.mark.asyncio
async def test_payment_callback_sends_paid_notification(
    client: AsyncClient,
    item_id: UUID,
    notifications,
) -> None:
    """Проверить отправку уведомления после успешной оплаты."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-notification-paid-key",
        },
    )

    assert response.status_code == 201

    order_id = UUID(response.json()["id"])

    callback_response = await client.post(
        "/api/orders/payment-callback",
        json={
            "payment_id": str(uuid4()),
            "order_id": str(order_id),
            "status": "succeeded",
            "amount": "200.00",
            "error_message": None,
        },
    )

    assert callback_response.status_code == 200

    assert notifications.notifications == [
        (
            "NEW: Ваш заказ создан и ожидает оплаты",
            order_id,
            "test-notification-paid-key:NEW",
        ),
        (
            "PAID: Ваш заказ успешно оплачен и готов к отправке",
            order_id,
            "test-notification-paid-key:PAID",
        ),
    ]


@pytest.mark.asyncio
async def test_shipping_event_sends_shipped_notification(
    client: AsyncClient,
    item_id: UUID,
    uow,
    notifications,
) -> None:
    """Проверить отправку уведомления после отправки заказа."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-notification-shipped-key",
        },
    )

    assert response.status_code == 201

    order_id = UUID(response.json()["id"])

    use_case = ProcessShippingEvent(
        uow=uow,
        notifications=notifications,
    )

    await use_case.execute(
        order_id=order_id,
        event_type="order.shipped",
    )

    assert notifications.notifications == [
        (
            "NEW: Ваш заказ создан и ожидает оплаты",
            order_id,
            "test-notification-shipped-key:NEW",
        ),
        (
            "SHIPPED: Ваш заказ отправлен в доставку",
            order_id,
            "test-notification-shipped-key:SHIPPED",
        ),
    ]


@pytest.mark.asyncio
async def test_payment_callback_sends_cancelled_notification(
    client: AsyncClient,
    item_id: UUID,
    notifications,
) -> None:
    """Проверить отправку уведомления при отмене заказа."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-notification-cancelled-key",
        },
    )

    assert response.status_code == 201

    order_id = UUID(response.json()["id"])

    callback_response = await client.post(
        "/api/orders/payment-callback",
        json={
            "payment_id": str(uuid4()),
            "order_id": str(order_id),
            "status": "failed",
            "amount": "200.00",
            "error_message": "Payment failed",
        },
    )

    assert callback_response.status_code == 200

    assert notifications.notifications == [
        (
            "NEW: Ваш заказ создан и ожидает оплаты",
            order_id,
            "test-notification-cancelled-key:NEW",
        ),
        (
            "CANCELLED: Ваш заказ отменен. Причина: Payment failed",
            order_id,
            "test-notification-cancelled-key:CANCELLED",
        ),
    ]


@pytest.mark.asyncio
async def test_payment_callback_does_not_duplicate_notification(
    client: AsyncClient,
    item_id: UUID,
    notifications,
) -> None:
    """Проверить отсутствие дублирования уведомления."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-notification-idempotency-key",
        },
    )

    assert response.status_code == 201

    order_id = UUID(response.json()["id"])

    payload = {
        "payment_id": str(uuid4()),
        "order_id": str(order_id),
        "status": "succeeded",
        "amount": "200.00",
        "error_message": None,
    }

    first_response = await client.post(
        "/api/orders/payment-callback",
        json=payload,
    )
    second_response = await client.post(
        "/api/orders/payment-callback",
        json=payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    assert notifications.notifications == [
        (
            "NEW: Ваш заказ создан и ожидает оплаты",
            order_id,
            "test-notification-idempotency-key:NEW",
        ),
        (
            "PAID: Ваш заказ успешно оплачен и готов к отправке",
            order_id,
            "test-notification-idempotency-key:PAID",
        ),
    ]


@pytest.mark.asyncio
async def test_notification_error_does_not_block_order_creation(
    client: AsyncClient,
    item_id: UUID,
    notifications,
) -> None:
    """Проверить, что ошибка Notifications Service не блокирует создание заказа."""

    notifications.should_fail = True

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-notification-error-key",
        },
    )

    assert response.status_code == 201

    order_id = UUID(response.json()["id"])

    assert order_id is not None
    assert notifications.notifications == []


@pytest.mark.asyncio
async def test_shipping_event_sends_cancelled_notification_with_reason(
    client: AsyncClient,
    item_id: UUID,
    uow,
    notifications,
) -> None:
    """Проверить отправку уведомления об отмене заказа с причиной."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-notification-shipping-cancelled-key",
        },
    )

    assert response.status_code == 201

    order_id = UUID(response.json()["id"])

    use_case = ProcessShippingEvent(
        uow=uow,
        notifications=notifications,
    )

    await use_case.execute(
        order_id=order_id,
        event_type="order.cancelled",
        reason="Insufficient stock",
    )

    assert notifications.notifications == [
        (
            "NEW: Ваш заказ создан и ожидает оплаты",
            order_id,
            "test-notification-shipping-cancelled-key:NEW",
        ),
        (
            "CANCELLED: Ваш заказ отменен. Причина: Insufficient stock",
            order_id,
            "test-notification-shipping-cancelled-key:CANCELLED",
        ),
    ]
