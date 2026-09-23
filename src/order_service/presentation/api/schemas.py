from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from order_service.application.ports.payments import PaymentStatus
from order_service.domain.entities import OrderStatus


class CreateOrderRequest(BaseModel):
    """Данные для создания заказа."""

    user_id: str
    quantity: int = Field(gt=0)
    item_id: UUID
    idempotency_key: str


class OrderResponse(BaseModel):
    """Данные заказа в API."""

    id: UUID
    user_id: str
    quantity: int
    item_id: UUID
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class PaymentCallbackRequest(BaseModel):
    """Данные callback от Payments Service."""

    payment_id: UUID
    order_id: UUID
    status: PaymentStatus
    amount: Decimal
    error_message: str | None
