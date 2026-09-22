from contextlib import asynccontextmanager

from fastapi import FastAPI

from order_service.infrastructure.http.catalog_client import HttpCatalogClient
from order_service.infrastructure.persistence.database import Database
from order_service.presentation.api.routes.orders import router as orders_router
from order_service.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управлять ресурсами приложения."""

    database = Database(settings.postgres_connection_string)
    catalog = HttpCatalogClient(
        base_url=settings.capashino_base_url,
        api_key=settings.capashino_api_key,
    )

    app.state.database = database
    app.state.catalog = catalog

    try:
        yield
    finally:
        await catalog.close()
        await database.dispose()


def create_app() -> FastAPI:
    """Создать приложение FastAPI."""

    app = FastAPI(
        title="Order Service",
        lifespan=lifespan,
    )

    app.include_router(orders_router)

    return app
