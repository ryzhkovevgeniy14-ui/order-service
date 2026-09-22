from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from order_service.domain.entities import OrderStatus


class CreateOrderRequest(BaseModel):
    """Данные для создания заказа."""

    user_id: str
    quantity: int = Field(gt=0)
    item_id: UUID
    idempotency_key: UUID


class OrderResponse(BaseModel):
    """Данные заказа в API."""

    id: UUID
    user_id: str
    quantity: int
    item_id: UUID
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
