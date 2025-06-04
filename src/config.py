from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Класс конфигурируемые параметры приложения. Параметры могут быть переопределены
    в файле .env в корне проекта или через переменные окружения."""

    LOG_LEVEL: str = "INFO"
    TELEGRAM_TOKEN: str = ""
    DATABASE_PATH: str = ""
    API_URL: str = ""
    API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )


settings = Settings()
