import asyncio
from urllib.parse import urljoin
from uuid import UUID

import httpx

from order_service.application.ports.notifications import (
    NotificationServiceError,
)


class HttpNotificationsClient:
    """Клиент для Notifications Service."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._client = httpx.AsyncClient()

    async def send_notification(
        self,
        message: str,
        reference_id: UUID,
        idempotency_key: str,
    ) -> None:
        """Отправить уведомление."""

        url = urljoin(
            self._base_url.rstrip("/") + "/",
            "api/notifications",
        )

        for attempt in range(3):
            try:
                response = await self._client.post(
                    url,
                    headers={"X-API-Key": self._api_key},
                    json={
                        "message": message,
                        "reference_id": str(reference_id),
                        "idempotency_key": idempotency_key,
                    },
                )
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise NotificationServiceError(
                        "Ошибка при обращении к Notifications Service.",
                    ) from exc
            else:
                if response.status_code < 400:
                    return

                if response.status_code < 500:
                    raise NotificationServiceError(
                        f"Notifications Service: "
                        f"{response.status_code} {response.text}",
                    )

                if attempt == 2:
                    raise NotificationServiceError(
                        f"Notifications Service: "
                        f"{response.status_code} {response.text}",
                    )

            if attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))

    async def close(self) -> None:
        """Закрыть HTTP-клиент."""

        await self._client.aclose()
