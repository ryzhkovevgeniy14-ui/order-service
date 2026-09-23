from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID


class CatalogItemNotFoundError(Exception):
    """Товар не найден в каталоге."""


class CatalogServiceError(Exception):
    """Ошибка при обращении к Catalog Service."""


@dataclass(frozen=True)
class CatalogItem:
    """Данные товара, необходимые Order Service."""

    item_id: UUID
    available_qty: int
    price: Decimal


class CatalogClient(Protocol):
    """Интерфейс клиента Catalog Service."""

    async def get_item(self, item_id: UUID) -> CatalogItem:
        """Получить товар из каталога."""
