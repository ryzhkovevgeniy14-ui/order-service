from uuid import UUID

from fastapi import APIRouter, Depends, status

from order_service.application.usecases.create_order import CreateOrder
from order_service.application.usecases.get_order import GetOrder
from order_service.presentation.api.dependencies import (
    get_create_order,
    get_get_order,
)
from order_service.presentation.api.schemas import (
    CreateOrderRequest,
    OrderResponse,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order(
    request: CreateOrderRequest,
    use_case: CreateOrder = Depends(get_create_order),  # noqa: B008
) -> OrderResponse:
    """Создать заказ."""

    order = await use_case.execute(
        user_id=request.user_id,
        quantity=request.quantity,
        item_id=request.item_id,
        idempotency_key=request.idempotency_key,
    )

    return OrderResponse.model_validate(order, from_attributes=True)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
async def get_order(
    order_id: UUID,
    use_case: GetOrder = Depends(get_get_order),  # noqa: B008
) -> OrderResponse:
    """Получить заказ."""

    order = await use_case.execute(order_id)

    return OrderResponse.model_validate(order, from_attributes=True)
