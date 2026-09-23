from decimal import Decimal
from urllib.parse import urljoin
from uuid import UUID

import httpx

from order_service.application.ports.payments import (
    Payment,
    PaymentServiceError,
)


class HttpPaymentsClient:
    """Клиент для Payments Service."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._client = httpx.AsyncClient()

    async def create_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        callback_url: str,
        idempotency_key: str,
    ) -> Payment:
        """Создать платеж."""

        url = urljoin(
            self._base_url.rstrip("/") + "/",
            "api/payments",
        )

        try:
            response = await self._client.post(
                url,
                headers={"X-API-Key": self._api_key},
                json={
                    "order_id": str(order_id),
                    "amount": str(amount),
                    "callback_url": callback_url,
                    "idempotency_key": idempotency_key,
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise PaymentServiceError(
                "Ошибка при обращении к Payments Service.",
            ) from exc

        data = response.json()

        return Payment(
            id=UUID(data["id"]),
            order_id=UUID(data["order_id"]),
            amount=Decimal(data["amount"]),
            status=data["status"],
            idempotency_key=data["idempotency_key"],
            created_at=data["created_at"],
        )

    async def close(self) -> None:
        """Закрыть HTTP-клиент."""

        await self._client.aclose()
