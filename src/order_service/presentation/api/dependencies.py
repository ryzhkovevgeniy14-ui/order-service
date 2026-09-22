from fastapi import Depends, Request

from order_service.application.ports.uow import UnitOfWork
from order_service.application.usecases.create_order import CreateOrder
from order_service.application.usecases.get_order import GetOrder
from order_service.infrastructure.http.catalog_client import HttpCatalogClient
from order_service.infrastructure.persistence.database import Database
from order_service.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


def get_database(request: Request) -> Database:
    """Получить подключение к базе данных."""

    return request.app.state.database


def get_catalog_client(request: Request) -> HttpCatalogClient:
    """Получить клиент Catalog Service."""

    return request.app.state.catalog


def get_unit_of_work(request: Request) -> SqlAlchemyUnitOfWork:
    """Получить единицу работы с базой данных."""

    database = get_database(request)

    return SqlAlchemyUnitOfWork(database.session_factory)


def get_create_order(
    uow: UnitOfWork = Depends(get_unit_of_work),  # noqa: B008
    catalog: HttpCatalogClient = Depends(get_catalog_client),  # noqa: B008
) -> CreateOrder:
    """Получить сценарий создания заказа."""

    return CreateOrder(
        uow=uow,
        catalog=catalog,
    )


def get_get_order(
    uow: UnitOfWork = Depends(get_unit_of_work),  # noqa: B008
) -> GetOrder:
    """Получить сценарий получения заказа."""

    return GetOrder(uow=uow)
