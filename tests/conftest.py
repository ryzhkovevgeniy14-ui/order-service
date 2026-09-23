import os

os.environ.update(
    {
        "POSTGRES_CONNECTION_STRING": "postgresql+asyncpg://test:test@localhost:5432/test",
        "POSTGRES_DATABASE_NAME": "test",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USERNAME": "test",
        "POSTGRES_PASSWORD": "test",
        "CAPASHINO_BASE_URL": "http://test",
        "CAPASHINO_API_KEY": "test",
        "CALLBACK_URL": "http://test/api/orders/payment-callback",
    },
)

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from order_service.application.ports.catalog import (
    CatalogItem,
    CatalogItemNotFoundError,
)
from order_service.application.ports.payments import Payment, PaymentServiceError
from order_service.application.ports.repositories import OrderRepository
from order_service.application.usecases.create_order import CreateOrder
from order_service.domain.entities import Order
from order_service.fastapi import create_app
from order_service.presentation.api.dependencies import (
    get_catalog_client,
    get_create_order,
    get_payments_client,
    get_unit_of_work,
)

TEST_CALLBACK_URL = "http://order-service/api/orders/payment-callback"


class FakeOrderRepository:
    """In-memory репозиторий заказов для тестов."""

    def __init__(self) -> None:
        self._orders: dict[UUID, Order] = {}

    async def get_by_id(self, order_id: UUID) -> Order | None:
        """Получить заказ по идентификатору."""

        return self._orders.get(order_id)

    async def get_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Order | None:
        """Получить заказ по ключу идемпотентности."""

        return next(
            (
                order
                for order in self._orders.values()
                if order.idempotency_key == idempotency_key
            ),
            None,
        )

    async def add(self, order: Order) -> None:
        """Добавить заказ."""

        self._orders[order.id] = order

    async def update(self, order: Order) -> None:
        """Обновить заказ."""

        self._orders[order.id] = order


class FakeUnitOfWork:
    """In-memory фабрика единиц работы для тестов."""

    def __init__(self) -> None:
        self.repository = FakeOrderRepository()

    @asynccontextmanager
    async def __call__(
        self,
    ) -> AsyncIterator["FakeUnitOfWork"]:
        """Создать единицу работы в контексте транзакции."""

        yield self

    @property
    def orders(self) -> OrderRepository:
        """Получить репозиторий заказов."""

        return self.repository

    async def commit(self) -> None:
        """Зафиксировать изменения."""


class FakeCatalogClient:
    """In-memory клиент Catalog Service для тестов."""

    def __init__(self, item: CatalogItem) -> None:
        self.item = item

    async def get_item(self, item_id: UUID) -> CatalogItem:
        """Получить тестовый товар."""

        if item_id != self.item.item_id:
            raise CatalogItemNotFoundError("Товар не найден в каталоге.")

        return self.item


class FakePaymentsClient:
    """In-memory клиент Payments Service для тестов."""

    def __init__(self) -> None:
        self.created_payments: list[Payment] = []
        self.should_fail = False

    async def create_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        callback_url: str,
        idempotency_key: str,
    ) -> Payment:
        """Создать тестовый платёж."""

        if self.should_fail:
            raise PaymentServiceError("Ошибка Payments Service.")

        payment = Payment(
            id=uuid4(),
            order_id=order_id,
            amount=amount,
            status="pending",
            idempotency_key=idempotency_key,
            created_at=datetime.now(UTC).isoformat(),
        )

        self.created_payments.append(payment)

        return payment


@pytest.fixture
def app() -> FastAPI:
    """Создать FastAPI-приложение для тестов."""

    return create_app()


@pytest.fixture
def uow() -> FakeUnitOfWork:
    """Предоставить тестовую единицу работы."""

    return FakeUnitOfWork()


@pytest.fixture
def item_id() -> UUID:
    """Предоставить идентификатор тестового товара."""

    return uuid4()


@pytest.fixture
def catalog(item_id: UUID) -> FakeCatalogClient:
    """Предоставить тестовый клиент Catalog Service."""

    return FakeCatalogClient(
        CatalogItem(
            item_id=item_id,
            available_qty=10,
            price=Decimal("100.00"),
        ),
    )


@pytest.fixture
def payments() -> FakePaymentsClient:
    """Предоставить тестовый клиент Payments Service."""

    return FakePaymentsClient()


@pytest.fixture
def configured_app(
    app: FastAPI,
    uow: FakeUnitOfWork,
    catalog: FakeCatalogClient,
    payments: FakePaymentsClient,
) -> FastAPI:
    """Настроить приложение с тестовыми зависимостями."""

    app.dependency_overrides[get_unit_of_work] = lambda: uow
    app.dependency_overrides[get_catalog_client] = lambda: catalog
    app.dependency_overrides[get_payments_client] = lambda: payments
    app.dependency_overrides[get_create_order] = lambda: CreateOrder(
        uow=uow,
        catalog=catalog,
        payments=payments,
        callback_url=TEST_CALLBACK_URL,
    )

    return app


@pytest_asyncio.fixture
async def client(
    configured_app: FastAPI,
) -> AsyncIterator[AsyncClient]:
    """Предоставить HTTP-клиент для тестирования API."""

    transport = ASGITransport(app=configured_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
