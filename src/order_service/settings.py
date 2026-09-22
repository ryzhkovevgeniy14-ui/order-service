from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения."""

    postgres_connection_string: str
    postgres_database_name: str
    postgres_host: str
    postgres_port: int
    postgres_username: str
    postgres_password: str
    capashino_base_url: str
    capashino_api_key: str

    model_config = SettingsConfigDict(
        extra="ignore",
    )


settings = Settings()
