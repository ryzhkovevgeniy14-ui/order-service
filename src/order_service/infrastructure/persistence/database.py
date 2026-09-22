from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class Database:
    """Подключение к базе данных."""

    def __init__(self, database_url: str) -> None:
        database_url = database_url.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1,
        )
        self.engine = create_async_engine(database_url)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        """Закрыть подключения к базе данных."""

        await self.engine.dispose()
