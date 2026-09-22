from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CatalogItem:
    """Данные товара, необходимые Order Service."""

    item_id: UUID
    available_qty: int


class CatalogClient(Protocol):
    """Интерфейс клиента Catalog Service."""

    async def get_item(self, item_id: UUID) -> CatalogItem:
        """Получить товар из каталога."""
