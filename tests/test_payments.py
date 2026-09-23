from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_order_creates_payment(
    client: AsyncClient,
    item_id: UUID,
    payments,
) -> None:
    """Проверить создание платежа при создании заказа."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-payment-key",
        },
    )

    assert response.status_code == 201

    order = response.json()

    assert len(payments.created_payments) == 1

    payment = payments.created_payments[0]

    assert str(payment.order_id) == order["id"]
    assert payment.amount == 200
    assert payment.idempotency_key == "test-payment-key"


@pytest.mark.asyncio
async def test_create_order_payment_failed(
    client: AsyncClient,
    item_id: UUID,
    payments,
) -> None:
    """Проверить отмену заказа при ошибке создания платежа."""

    payments.should_fail = True

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-payment-failed-key",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_payment_callback_succeeded(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить перевод заказа в PAID после успешного callback."""

    create_response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-callback-success-key",
        },
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    callback_response = await client.post(
        "/api/orders/payment-callback",
        json={
            "payment_id": str(uuid4()),
            "order_id": order_id,
            "status": "succeeded",
            "amount": "200.00",
            "error_message": None,
        },
    )

    assert callback_response.status_code == 200

    order_response = await client.get(f"/api/orders/{order_id}")

    assert order_response.status_code == 200
    assert order_response.json()["status"] == "PAID"


@pytest.mark.asyncio
async def test_payment_callback_failed(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить перевод заказа в CANCELLED после неуспешного callback."""

    create_response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-callback-failed-key",
        },
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    callback_response = await client.post(
        "/api/orders/payment-callback",
        json={
            "payment_id": str(uuid4()),
            "order_id": order_id,
            "status": "failed",
            "amount": "200.00",
            "error_message": "Payment processing failed",
        },
    )

    assert callback_response.status_code == 200

    order_response = await client.get(f"/api/orders/{order_id}")

    assert order_response.status_code == 200
    assert order_response.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_payment_callback_succeeded_idempotency(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить идемпотентность успешного callback."""

    create_response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-callback-success-idempotency-key",
        },
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    callback = {
        "payment_id": str(uuid4()),
        "order_id": order_id,
        "status": "succeeded",
        "amount": "200.00",
        "error_message": None,
    }

    first_response = await client.post(
        "/api/orders/payment-callback",
        json=callback,
    )
    second_response = await client.post(
        "/api/orders/payment-callback",
        json=callback,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    order_response = await client.get(f"/api/orders/{order_id}")

    assert order_response.json()["status"] == "PAID"


@pytest.mark.asyncio
async def test_payment_callback_failed_idempotency(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить идемпотентность неуспешного callback."""

    create_response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-callback-failed-idempotency-key",
        },
    )

    assert create_response.status_code == 201

    order_id = create_response.json()["id"]

    callback = {
        "payment_id": str(uuid4()),
        "order_id": order_id,
        "status": "failed",
        "amount": "200.00",
        "error_message": "Payment processing failed",
    }

    first_response = await client.post(
        "/api/orders/payment-callback",
        json=callback,
    )
    second_response = await client.post(
        "/api/orders/payment-callback",
        json=callback,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    order_response = await client.get(f"/api/orders/{order_id}")

    assert order_response.json()["status"] == "CANCELLED"
