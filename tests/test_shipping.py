import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from order_service.application.ports.outbox import OutboxEvent
from order_service.application.usecases.process_shipping_event import (
    ProcessShippingEvent,
)
from order_service.application.usecases.publish_outbox_events import (
    PublishOutboxEvents,
)
from order_service.domain.entities import Order, OrderStatus
from order_service.infrastructure.messaging.kafka_consumer import KafkaConsumer


async def _create_order(
    client: AsyncClient,
    item_id: UUID,
    idempotency_key: str,
) -> UUID:
    """Создать тестовый заказ и вернуть его идентификатор."""

    response = await client.post(
        "/api/orders",
        json={
            "user_id": "user-123",
            "quantity": 2,
            "item_id": str(item_id),
            "idempotency_key": idempotency_key,
        },
    )

    assert response.status_code == 201

    return UUID(response.json()["id"])


@pytest.mark.asyncio
async def test_payment_callback_creates_paid_outbox_event(
    client: AsyncClient,
    item_id: UUID,
    uow,
) -> None:
    """Проверить создание события order.paid в Outbox."""

    order_id = await _create_order(
        client,
        item_id,
        "test-shipping-paid-key",
    )

    response = await client.post(
        "/api/orders/payment-callback",
        json={
            "payment_id": str(uuid4()),
            "order_id": str(order_id),
            "status": "succeeded",
            "amount": "200.00",
            "error_message": None,
        },
    )

    assert response.status_code == 200

    assert len(uow.outbox_repository.events) == 1

    event = uow.outbox_repository.events[0]

    assert event.order_id == order_id
    assert event.event_type == "order.paid"
    assert event.published is False

    payload = json.loads(event.payload)

    assert payload == {
        "event_type": "order.paid",
        "order_id": str(order_id),
        "item_id": str(item_id),
        "quantity": 2,
        "idempotency_key": "test-shipping-paid-key",
    }


@pytest.mark.asyncio
async def test_payment_callback_creates_cancelled_outbox_event(
    client: AsyncClient,
    item_id: UUID,
    uow,
) -> None:
    """Проверить создание события order.cancelled в Outbox."""

    order_id = await _create_order(
        client,
        item_id,
        "test-shipping-cancelled-key",
    )

    response = await client.post(
        "/api/orders/payment-callback",
        json={
            "payment_id": str(uuid4()),
            "order_id": str(order_id),
            "status": "failed",
            "amount": "200.00",
            "error_message": "Payment processing failed",
        },
    )

    assert response.status_code == 200

    assert len(uow.outbox_repository.events) == 1

    event = uow.outbox_repository.events[0]

    assert event.order_id == order_id
    assert event.event_type == "order.cancelled"
    assert event.published is False


@pytest.mark.asyncio
async def test_payment_callback_does_not_duplicate_paid_outbox_event(
    client: AsyncClient,
    item_id: UUID,
    uow,
) -> None:
    """Проверить идемпотентность события order.paid."""

    order_id = await _create_order(
        client,
        item_id,
        "test-shipping-paid-idempotency-key",
    )

    callback = {
        "payment_id": str(uuid4()),
        "order_id": str(order_id),
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

    assert len(uow.outbox_repository.events) == 1


@pytest.mark.asyncio
async def test_payment_callback_does_not_duplicate_cancelled_outbox_event(
    client: AsyncClient,
    item_id: UUID,
    uow,
) -> None:
    """Проверить идемпотентность события order.cancelled."""

    order_id = await _create_order(
        client,
        item_id,
        "test-shipping-cancelled-idempotency-key",
    )

    callback = {
        "payment_id": str(uuid4()),
        "order_id": str(order_id),
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

    assert len(uow.outbox_repository.events) == 1


@pytest.mark.asyncio
async def test_publish_outbox_event_marks_event_as_published(
    uow,
    message_broker,
) -> None:
    """Проверить публикацию Outbox-события и его отметку."""

    event = OutboxEvent(
        id=uuid4(),
        order_id=uuid4(),
        event_type="order.paid",
        payload='{"event_type": "order.paid"}',
        published=False,
        created_at=datetime.now(UTC),
    )

    await uow.outbox.add(event)

    use_case = PublishOutboxEvents(
        uow=uow,
        message_broker=message_broker,
        order_events_topic="student_system-order.events",
    )

    await use_case.execute()

    assert message_broker.messages == [
        ("student_system-order.events", event.payload),
    ]
    assert uow.outbox_repository.events[0].published is True


@pytest.mark.asyncio
async def test_publish_outbox_event_keeps_event_unpublished_when_broker_fails(
    uow,
    message_broker,
) -> None:
    """Проверить сохранение события в Outbox при ошибке брокера."""

    event = OutboxEvent(
        id=uuid4(),
        order_id=uuid4(),
        event_type="order.paid",
        payload='{"event_type": "order.paid"}',
        published=False,
        created_at=datetime.now(UTC),
    )

    await uow.outbox.add(event)
    message_broker.should_fail = True

    use_case = PublishOutboxEvents(
        uow=uow,
        message_broker=message_broker,
        order_events_topic="student_system-order.events",
    )

    with pytest.raises(RuntimeError, match="Kafka недоступна"):
        await use_case.execute()

    assert uow.outbox_repository.events[0].published is False


@pytest.mark.asyncio
async def test_shipping_event_shipped_updates_order_status(
    uow,
    notifications,
) -> None:
    """Проверить обработку события order.shipped."""

    order = Order(
        id=uuid4(),
        user_id="user-1",
        quantity=2,
        item_id=uuid4(),
        status=OrderStatus.PAID,
        idempotency_key="idempotency-key",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.orders.add(order)

    use_case = ProcessShippingEvent(
        uow=uow,
        notifications=notifications,
    )

    await use_case.execute(
        order_id=order.id,
        event_type="order.shipped",
    )

    updated_order = await uow.orders.get_by_id(order.id)

    assert updated_order is not None
    assert updated_order.status == OrderStatus.SHIPPED
    assert len(uow.inbox_repository.events) == 1
    assert uow.inbox_repository.events[0].event_type == "order.shipped"


@pytest.mark.asyncio
async def test_shipping_event_cancelled_updates_order_status(
    uow,
    notifications,
) -> None:
    """Проверить обработку события order.cancelled."""

    order = Order(
        id=uuid4(),
        user_id="user-1",
        quantity=2,
        item_id=uuid4(),
        status=OrderStatus.PAID,
        idempotency_key="idempotency-key",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.orders.add(order)

    use_case = ProcessShippingEvent(
        uow=uow,
        notifications=notifications,
    )

    await use_case.execute(
        order_id=order.id,
        event_type="order.cancelled",
    )

    updated_order = await uow.orders.get_by_id(order.id)

    assert updated_order is not None
    assert updated_order.status == OrderStatus.CANCELLED
    assert len(uow.inbox_repository.events) == 1
    assert uow.inbox_repository.events[0].event_type == "order.cancelled"


@pytest.mark.asyncio
async def test_shipping_event_shipped_is_idempotent(
    uow,
    notifications,
) -> None:
    """Проверить идемпотентность order.shipped."""

    order = Order(
        id=uuid4(),
        user_id="user-1",
        quantity=2,
        item_id=uuid4(),
        status=OrderStatus.PAID,
        idempotency_key="idempotency-key",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.orders.add(order)

    use_case = ProcessShippingEvent(
        uow=uow,
        notifications=notifications,
    )

    await use_case.execute(
        order_id=order.id,
        event_type="order.shipped",
    )
    await use_case.execute(
        order_id=order.id,
        event_type="order.shipped",
    )

    updated_order = await uow.orders.get_by_id(order.id)

    assert updated_order is not None
    assert updated_order.status == OrderStatus.SHIPPED
    assert len(uow.inbox_repository.events) == 1


@pytest.mark.asyncio
async def test_shipping_event_cancelled_is_idempotent(
    uow,
    notifications,
) -> None:
    """Проверить идемпотентность order.cancelled."""

    order = Order(
        id=uuid4(),
        user_id="user-1",
        quantity=2,
        item_id=uuid4(),
        status=OrderStatus.PAID,
        idempotency_key="idempotency-key",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    await uow.orders.add(order)

    use_case = ProcessShippingEvent(
        uow=uow,
        notifications=notifications,
    )

    await use_case.execute(
        order_id=order.id,
        event_type="order.cancelled",
    )
    await use_case.execute(
        order_id=order.id,
        event_type="order.cancelled",
    )

    updated_order = await uow.orders.get_by_id(order.id)

    assert updated_order is not None
    assert updated_order.status == OrderStatus.CANCELLED
    assert len(uow.inbox_repository.events) == 1


@pytest.mark.asyncio
async def test_kafka_consumer_processes_shipped_event(
    process_shipping_event,
) -> None:
    """Проверить обработку события order.shipped Consumer'ом."""

    consumer = KafkaConsumer(
        bootstrap_servers="localhost:9092",
        topic="student_system-shipment.events",
        group_id="order-service",
        process_shipping_event=process_shipping_event,
    )

    order_id = uuid4()
    message = json.dumps(
        {
            "event_type": "order.shipped",
            "order_id": str(order_id),
            "item_id": str(uuid4()),
            "quantity": 2,
            "shipment_id": str(uuid4()),
        },
    ).encode("utf-8")

    await consumer._process_message(message)

    assert process_shipping_event.events == [
        (order_id, "order.shipped"),
    ]


@pytest.mark.asyncio
async def test_kafka_consumer_processes_cancelled_event(
    process_shipping_event,
) -> None:
    """Проверить обработку события order.cancelled Consumer'ом."""

    consumer = KafkaConsumer(
        bootstrap_servers="localhost:9092",
        topic="student_system-shipment.events",
        group_id="order-service",
        process_shipping_event=process_shipping_event,
    )

    order_id = uuid4()
    message = json.dumps(
        {
            "event_type": "order.cancelled",
            "order_id": str(order_id),
            "item_id": str(uuid4()),
            "quantity": 2,
            "reason": "Insufficient stock",
        },
    ).encode("utf-8")

    await consumer._process_message(message)

    assert process_shipping_event.events == [
        (order_id, "order.cancelled"),
    ]


@pytest.mark.asyncio
async def test_kafka_consumer_handles_invalid_message(
    process_shipping_event,
) -> None:
    """Проверить обработку некорректного Kafka-сообщения."""

    consumer = KafkaConsumer(
        bootstrap_servers="localhost:9092",
        topic="student_system-shipment.events",
        group_id="order-service",
        process_shipping_event=process_shipping_event,
    )

    message = b"invalid json"

    await consumer._process_message(message)

    assert process_shipping_event.events == []
