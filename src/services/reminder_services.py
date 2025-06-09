import datetime
import time
import threading
import logging
from typing import Dict, List, Tuple
from telebot import TeleBot
from src.database.database import Database


class ReminderService:
    """Сервис для отправки напоминаний о событиях"""
    def __init__(self, bot: TeleBot, db: Database):
        """Инициализация с ботом и базой данных"""
        self.bot = bot
        self.db = db
        self.running = True
        self.thread = threading.Thread(target=self.check_reminders)
        self.thread.daemon = True

    def start(self):
        self.thread.start()

    def stop(self):
        self.running = False

    def check_reminders(self):
        """Основной цикл проверки событий"""
        while self.running:
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            week_later = today + datetime.timedelta(days=7)

            try:
                self.check_global_holidays(today, tomorrow, week_later)
                self.check_personal_events(today, tomorrow, week_later)
            except Exception as e:
                logging.error(f"Ошибка при проверке напоминаний: {e}")

            time.sleep(3600) # Проверка каждый час

    def check_global_holidays(self, today: datetime.date, tomorrow: datetime.date, week_later: datetime.date):
        """Проверяет и отправляет уведомления о глобальных праздниках"""
        holidays = self.db.get_global_holidays()
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT DISTINCT chat_id FROM birthdays UNION SELECT DISTINCT chat_id FROM holidays')
        chat_ids = [row[0] for row in cursor.fetchall()]

        for chat_id in chat_ids:
            settings = self.db.get_notification_settings(chat_id, 'global_holiday')
            if not settings:
                continue

            for name, date, desc in holidays:
                holiday_date = datetime.date(today.year, date.month, date.day)

                if holiday_date == today and settings['notify_on_day']:
                    try:
                        self.bot.send_message(chat_id, f"🎉 Сегодня праздник: {name}!\n\n{desc}")
                    except Exception as e:
                        logging.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
                elif holiday_date == tomorrow and settings['notify_one_day_before']:
                    try:
                        self.bot.send_message(chat_id, f"Напоминание: завтра праздник - {name}! 🎉")
                    except Exception as e:
                        logging.error(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")
                elif holiday_date == week_later and settings['notify_one_week_before']:
                    try:
                        self.bot.send_message(chat_id, f"Напоминание: через 7 дней праздник - {name}! 🎉")
                    except Exception as e:
                        logging.error(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")

    def check_personal_events(self, today: datetime.date, tomorrow: datetime.date, week_later: datetime.date):
        """Проверяет и отправляет уведомления о личных событиях"""
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT DISTINCT chat_id FROM birthdays UNION SELECT DISTINCT chat_id FROM holidays')
        chat_ids = [row[0] for row in cursor.fetchall()]

        for event_type in ['birthday', 'holiday']:
            for chat_id in chat_ids:
                settings = self.db.get_notification_settings(chat_id, event_type)
                if not settings:
                    continue

                if event_type == 'birthday':
                    cursor.execute('SELECT name, date, wishes, notes FROM birthdays WHERE chat_id = ?', (chat_id,))
                else:
                    cursor.execute('SELECT name, date, notes FROM holidays WHERE chat_id = ?', (chat_id,))

                for row in cursor.fetchall():
                    if event_type == 'birthday':
                        name, date_str, wishes, notes = row
                    else:
                        name, date_str, notes = row
                        wishes = ''

                    event_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                    event_date_by_year = datetime.date(today.year, event_date.month, event_date.day)

                    if event_date_by_year == today and settings['notify_on_day']:
                        message = f"🎉 Сегодня {'день рождения у' if event_type == 'birthday' else 'праздник:'} {name}!\n"
                        if wishes:
                            message += f"\nПоздравление: {wishes}\n"
                        if notes:
                            message += f"\nЗаметка: {notes}"
                        try:
                            self.bot.send_message(chat_id, message)
                        except Exception as e:
                            logging.error(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
                    elif event_date_by_year == tomorrow and settings['notify_one_day_before']:
                        try:
                            self.bot.send_message(chat_id,
                                                 f"Напоминание: завтра {'день рождения у' if event_type == 'birthday' else 'праздник'} {name}! 🎉")
                        except Exception as e:
                            logging.error(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")
                    elif event_date_by_year == week_later and settings['notify_one_week_before']:
                        try:
                            self.bot.send_message(chat_id,
                                                 f"Напоминание: через 7 дней {'день рождения у' if event_type == 'birthday' else 'праздник'} {name}! 🎉")
                        except Exception as e:
                            logging.error(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")