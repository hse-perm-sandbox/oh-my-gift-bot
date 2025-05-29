import logging
from src.logging_config import setup_logging

from src.config import settings


def start():
    """Создание экземпляра бота, настройка обработчиков и запуск бота."""

    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Запуск приложения")
    logger.info("Токен: %s", settings.TELEGRAM_TOKEN)


if __name__ == "__main__":
    start()
