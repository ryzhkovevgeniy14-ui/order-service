from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class PaymentServiceError(Exception):
    """Ошибка при обращении к Payments Service."""


class PaymentStatus(StrEnum):
    """Статус платежа."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True)
class Payment:
    """Данные созданного платежа."""

    id: UUID
    order_id: UUID
    amount: Decimal
    status: str
    idempotency_key: str
    created_at: str


@dataclass(frozen=True)
class PaymentCallback:
    """Данные callback от Payments Service."""

    payment_id: UUID
    order_id: UUID
    status: PaymentStatus
    amount: Decimal
    error_message: str | None


class PaymentClient(Protocol):
    """Интерфейс клиента Payments Service."""

    async def create_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        callback_url: str,
        idempotency_key: str,
    ) -> Payment:
        """Создать платеж."""
