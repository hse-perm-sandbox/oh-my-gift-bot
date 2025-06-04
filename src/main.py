from src.mainbot import BirthdayBot
from src.logging_config import setup_logging


def start():
    """Точка входа в приложение"""
    setup_logging()
    bot = BirthdayBot()
    bot.run()


if __name__ == "__main__":
    start()