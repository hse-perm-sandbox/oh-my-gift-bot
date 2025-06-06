from telebot import TeleBot
from src.config import settings
from src.database.database import Database
from src.services.api_services import AIService
from src.services.reminder_services import ReminderService
from src.handlers.handlers import Handlers
from src.logging_config import setup_logging


class BirthdayBot:
    def __init__(self):
        self.bot = TeleBot(settings.TELEGRAM_TOKEN)
        self.db = Database()
        self.ai_service = AIService()
        self.reminder_service = ReminderService(self.bot, self.db)
        self.handlers = Handlers(self.bot, self.db, self.ai_service)

    def run(self):
        self.handlers.setup_handlers()
        self.reminder_service.start()
        print("Бот запущен...")
        self.bot.polling(none_stop=True, interval=0)


def start():
    """Точка входа в приложение"""
    setup_logging()
    bot = BirthdayBot()
    bot.run()


if __name__ == "__main__":
    start()