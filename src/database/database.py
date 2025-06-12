import sqlite3
import datetime
from typing import Dict, List, Optional, Tuple
from src.config import settings


class Database:
    """Класс для работы с базой данных бота"""
    def __init__(self):
        self.conn = self.get_db_connection()
        self.init_db()

    def get_db_connection(self):
        return sqlite3.connect(settings.DATABASE_PATH, check_same_thread=False)

    def init_db(self):
        cursor = self.conn.cursor()

        # Создание таблиц, если они не существуют
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS birthdays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            name TEXT,
            date TEXT,
            notes TEXT DEFAULT '',
            wishes TEXT DEFAULT '',
            gifts TEXT DEFAULT '',
            UNIQUE(chat_id, name)
        )''')

        # Добавление колонки gifts (для обратной совместимости)
        try:
            cursor.execute("ALTER TABLE birthdays ADD COLUMN gifts TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

        # Таблицы для праздников и глобальных праздников
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            name TEXT,
            date TEXT,
            notes TEXT DEFAULT '',
            UNIQUE(chat_id, name)
        )''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            description TEXT DEFAULT '',
            UNIQUE(name)
        )''')

        # Таблица для настроек уведомлений
        cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    event_type TEXT,
                    notify_on_day INTEGER DEFAULT 1,
                    notify_one_day_before INTEGER DEFAULT 1,
                    notify_one_week_before INTEGER DEFAULT 1,
                    UNIQUE(chat_id, event_type)
                )''')


        default_holidays = [
            ("Новый год", "01.01", "С Новым годом! 🎄✨"),
            ("Рождество Христово", "07.01", "С Рождеством Христовым! 🌟"),
            ("Старый Новый год", "14.01", "Со Старым Новым годом! 🎉"),
            ("Крещение Господне", "19.01", "С Крещением Господним! ❄️🙏"),
            ("День святого Валентина", "14.02", "С Днём святого Валентина! 💖"),
            ("День защитника Отечества", "23.02", "С Днём защитника Отечества! 🎖️"),
            ("Международный женский день", "08.03", "С 8 Марта! 💐"),
            ("Праздник Весны и Труда", "01.05", "С Праздником Весны и Труда! 🌸"),
            ("День Победы", "09.05", "С Днём Победы! 🇷🇺🎖️"),
            ("День России", "12.06", "С Днём России! 🇷🇺"),
            ("Международный день защиты детей", "01.06", "С Днём защиты детей! 👧👦"),
            ("День знаний", "01.09", "С Днём знаний! 📚✏️"),
            ("День учителя", "05.10", "С Днём учителя! 🍎📖"),
            ("День народного единства", "04.11", "С Днём народного единства! 🤝"),
        ]

        for name, date, desc in default_holidays:
            try:
                cursor.execute('''
                INSERT OR IGNORE INTO global_holidays (name, date, description)
                VALUES (?, ?, ?)''', (name, date, desc))
            except sqlite3.IntegrityError:
                pass

        self.conn.commit()

    def init_notification_settings(self, chat_id: int):
        """Инициализирует настройки уведомлений для нового чата"""
        cursor = self.conn.cursor()
        event_types = ['birthday', 'holiday', 'global_holiday']
        for event_type in event_types:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO notification_settings (chat_id, event_type, notify_on_day, notify_one_day_before, notify_one_week_before)
                    VALUES (?, ?, 1, 1, 1)
                ''', (chat_id, event_type))
            except sqlite3.Error:
                pass
        self.conn.commit()

    def get_notification_settings(self, chat_id: int, event_type: str) -> Optional[Dict]:
        """Получает настройки уведомлений для указанного чата и типа событий"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT notify_on_day, notify_one_day_before, notify_one_week_before
            FROM notification_settings
            WHERE chat_id = ? AND event_type = ?
        ''', (chat_id, event_type))
        result = cursor.fetchone()
        if result:
            return {
                'notify_on_day': result[0],
                'notify_one_day_before': result[1],
                'notify_one_week_before': result[2]
            }
        return None

    def update_notification_settings(self, chat_id: int, event_type: str, **kwargs) -> bool:
        """Обновляет настройки уведомлений для указанного чата и типа событий"""
        try:
            cursor = self.conn.cursor()

            # Получаем текущие настройки
            current_settings = self.get_notification_settings(chat_id, event_type)
            if not current_settings:
                current_settings = {
                    'notify_on_day': 1,
                    'notify_one_day_before': 1,
                    'notify_one_week_before': 1
                }

            # Обновляем только переданные настройки
            for key, value in kwargs.items():
                if key in current_settings:
                    current_settings[key] = value

            cursor.execute('''
                INSERT OR REPLACE INTO notification_settings 
                (chat_id, event_type, notify_on_day, notify_one_day_before, notify_one_week_before)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                chat_id,
                event_type,
                current_settings['notify_on_day'],
                current_settings['notify_one_day_before'],
                current_settings['notify_one_week_before']
            ))

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Ошибка при обновлении настроек уведомлений: {e}")
            return False

    def add_event(self, chat_id: int, name: str, date: datetime.date, notes: str = "",
                 wishes: str = "", event_type: str = 'birthday') -> bool:
        try:
            if event_type == 'birthday':
                self.conn.execute('''
                INSERT INTO birthdays (chat_id, name, date, notes, wishes) 
                VALUES (?, ?, ?, ?, ?)''', (chat_id, name, date.strftime('%Y-%m-%d'), notes, wishes))
            else:
                self.conn.execute('''
                INSERT INTO holidays (chat_id, name, date, notes) 
                VALUES (?, ?, ?, ?)''', (chat_id, name, date.strftime('%Y-%m-%d'), notes))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_event(self, chat_id: int, name: str, event_type: str = 'birthday') -> Optional[Dict]:
        table = 'birthdays' if event_type == 'birthday' else 'holidays'
        if event_type == 'birthday':
            cursor = self.conn.execute(f'''
            SELECT name, date, notes, wishes, gifts FROM {table} 
            WHERE chat_id = ? AND name = ?''', (chat_id, name))
            result = cursor.fetchone()
            if result:
                return {
                    "name": result[0],
                    "date": datetime.datetime.strptime(result[1], '%Y-%m-%d').date(),
                    "notes": result[2],
                    "wishes": result[3],
                    "gifts": result[4]
                }
        else:
            cursor = self.conn.execute(f'''
            SELECT name, date, notes FROM {table} 
            WHERE chat_id = ? AND name = ?''', (chat_id, name))
            result = cursor.fetchone()
            if result:
                return {
                    "name": result[0],
                    "date": datetime.datetime.strptime(result[1], '%Y-%m-%d').date(),
                    "notes": result[2]
                }
        return None

    def get_all_events(self, chat_id: int, event_type: str = 'birthday') -> Dict[str, datetime.date]:
        table = 'birthdays' if event_type == 'birthday' else 'holidays'
        cursor = self.conn.execute(f'SELECT name, date FROM {table} WHERE chat_id = ?', (chat_id,))
        return {name: datetime.datetime.strptime(date, '%Y-%m-%d').date()
                for name, date in cursor.fetchall()}

    def update_event(self, chat_id: int, name: str, date: datetime.date = None,
                     notes: str = None, wishes: str = None, gifts: str = None,
                     event_type: str = 'birthday') -> bool:
        """Обновляет данные события"""
        try:
            updates = []
            params = []

            # Формирование запроса на основе переданных параметров
            if date is not None:
                updates.append("date = ?")
                params.append(date.strftime('%Y-%m-%d'))

            if notes is not None:
                updates.append("notes = ?")
                params.append(notes)

            if wishes is not None and event_type == 'birthday':
                updates.append("wishes = ?")
                params.append(wishes)

            if gifts is not None and event_type == 'birthday':
                updates.append("gifts = ?")
                params.append(gifts)

            if not updates:
                return False

            params.extend([chat_id, name])
            table = 'birthdays' if event_type == 'birthday' else 'holidays'
            query = f"UPDATE {table} SET {', '.join(updates)} WHERE chat_id = ? AND name = ?"
            cursor = self.conn.execute(query, params)
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка при обновлении события: {e}")
            return False

    def delete_event(self, chat_id: int, name: str, event_type: str = 'birthday') -> bool:
        table = 'birthdays' if event_type == 'birthday' else 'holidays'
        cursor = self.conn.execute(f'DELETE FROM {table} WHERE chat_id = ? AND name = ?', (chat_id, name))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_global_holidays(self) -> List[Tuple[str, datetime.date, str]]:
        cursor = self.conn.execute('SELECT name, date, description FROM global_holidays')
        return [(name, datetime.datetime.strptime(date, '%d.%m').date(), desc)
                for name, date, desc in cursor.fetchall()]

    def __del__(self):
        self.conn.close()