from urllib.parse import urljoin
from uuid import UUID

import httpx

from order_service.application.ports.catalog import CatalogItem


class HttpCatalogClient:
    """Клиент для Catalog Service."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._client = httpx.AsyncClient()

    async def get_item(self, item_id: UUID) -> CatalogItem:
        """Получить товар из каталога."""

        url = urljoin(
            self._base_url.rstrip("/") + "/",
            f"api/catalog/items/{item_id}",
        )

        response = await self._client.get(
            url,
            headers={"X-API-Key": self._api_key},
        )
        response.raise_for_status()

        return CatalogItem(**response.json())

    async def close(self) -> None:
        """Закрыть HTTP-клиент."""

        await self._client.aclose()
