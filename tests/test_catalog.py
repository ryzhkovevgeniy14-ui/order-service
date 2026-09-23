from uuid import UUID

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_order(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить успешное создание заказа."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-idempotency-key",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == "user-123"
    assert data["quantity"] == 2
    assert data["item_id"] == str(item_id)
    assert data["status"] == "NEW"
    assert data["id"]
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.asyncio
async def test_get_order(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить получение существующего заказа."""

    create_response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": "test-get-order-key",
        },
    )

    order_id = create_response.json()["id"]

    response = await client.get(f"/api/orders/{order_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == order_id
    assert data["user_id"] == "user-123"
    assert data["quantity"] == 2
    assert data["item_id"] == str(item_id)
    assert data["status"] == "NEW"
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.asyncio
async def test_create_order_item_not_found(
    client: AsyncClient,
) -> None:
    """Проверить ошибку создания заказа при отсутствии товара в каталоге."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(UUID(int=0)),
            "idempotency_key": "test-item-not-found-key",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Товар не найден в каталоге."


@pytest.mark.asyncio
async def test_create_order_insufficient_quantity(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить ошибку создания заказа при недостаточном количестве товара."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 11,
            "item_id": str(item_id),
            "idempotency_key": "test-insufficient-quantity-key",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Недостаточно товара на складе."


@pytest.mark.asyncio
async def test_create_order_invalid_quantity(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить ошибку создания заказа при некорректном количестве."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 0,
            "item_id": str(item_id),
            "idempotency_key": "test-invalid-quantity-key",
        },
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(error["loc"] == ["body", "quantity"] for error in errors)


@pytest.mark.asyncio
async def test_create_order_idempotency(
    client: AsyncClient,
    item_id: UUID,
) -> None:
    """Проверить идемпотентность создания заказа."""

    payload = {
        "user_id": "user-123",
        "quantity": 2,
        "item_id": str(item_id),
        "idempotency_key": "test-idempotency-key",
    }

    first_response = await client.post("/api/orders", json=payload)
    second_response = await client.post("/api/orders", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_order = first_response.json()
    second_order = second_response.json()

    assert second_order["id"] == first_order["id"]


@pytest.mark.asyncio
async def test_get_order_not_found(
    client: AsyncClient,
) -> None:
    """Проверить ошибку получения несуществующего заказа."""

    order_id = UUID(int=0)

    response = await client.get(f"/api/orders/{order_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Заказ не найден."
