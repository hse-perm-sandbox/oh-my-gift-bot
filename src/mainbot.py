import telebot
from telebot import types
import datetime
import sqlite3
import time
import requests
import html
import threading
from src.config import settings


class EventProfile:
    def __init__(self, name, date, notes="", wishes="", gifts=""):
        self.name = name
        self.date = date
        self.notes = notes
        self.wishes = wishes
        self.gifts = gifts


class BirthdayBot:
    def __init__(self):
        self.bot = telebot.TeleBot(settings.TELEGRAM_TOKEN)
        self.user_data = {}
        self.init_db()
        self.setup_handlers()
        self.start_reminder_thread()

    def escape_html(self, text):
        if text is None:
            return ""
        return html.escape(text)

    def init_db(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()

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

        try:
            cursor.execute("ALTER TABLE birthdays ADD COLUMN gifts TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass

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

        default_holidays = [
            ("Новый год", "01.01", "С Новым годом! 🎄✨"),
            ("Рождество", "07.01", "С Рождеством Христовым! 🌟"),
            ("День святого Валентина", "14.02", "С Днём святого Валентина! 💖"),
            ("Международный женский день", "08.03", "С 8 Марта! 💐"),
            ("День Победы", "09.05", "С Днём Победы! 🎖️"),
            ("День России", "12.06", "С Днём России! 🇷🇺"),
            ("День народного единства", "04.11", "С Днём народного единства!"),
        ]

        for name, date, desc in default_holidays:
            try:
                cursor.execute('''
                INSERT OR IGNORE INTO global_holidays (name, date, description)
                VALUES (?, ?, ?)''', (name, date, desc))
            except sqlite3.IntegrityError:
                pass

        conn.commit()
        conn.close()

    def get_db_connection(self):
        return sqlite3.connect(settings.DATABASE_PATH, check_same_thread=False)

    def start_reminder_thread(self):
        reminder_thread = threading.Thread(target=self.check_reminders)
        reminder_thread.daemon = True
        reminder_thread.start()

    def add_event(self, chat_id, name, date, notes="", wishes="", event_type='birthday'):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            if event_type == 'birthday':
                cursor.execute('''
                INSERT INTO birthdays (chat_id, name, date, notes, wishes) 
                VALUES (?, ?, ?, ?, ?)''', (chat_id, name, date.strftime('%Y-%m-%d'), notes, wishes))
            else:
                cursor.execute('''
                INSERT INTO holidays (chat_id, name, date, notes) 
                VALUES (?, ?, ?, ?)''', (chat_id, name, date.strftime('%Y-%m-%d'), notes))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def update_event(self, chat_id, name, date=None, notes=None, wishes=None, gifts=None, event_type='birthday'):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            updates = []
            params = []

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
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_event(self, chat_id, name, event_type='birthday'):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            table = 'birthdays' if event_type == 'birthday' else 'holidays'
            if event_type == 'birthday':
                cursor.execute(f'''
                SELECT name, date, notes, wishes, gifts FROM {table} 
                WHERE chat_id = ? AND name = ?''', (chat_id, name))
                result = cursor.fetchone()
                if result:
                    return EventProfile(
                        name=result[0],
                        date=datetime.datetime.strptime(result[1], '%Y-%m-%d').date(),
                        notes=result[2],
                        wishes=result[3],
                        gifts=result[4]
                    )
            else:
                cursor.execute(f'''
                SELECT name, date, notes FROM {table} 
                WHERE chat_id = ? AND name = ?''', (chat_id, name))
                result = cursor.fetchone()
                if result:
                    return EventProfile(
                        name=result[0],
                        date=datetime.datetime.strptime(result[1], '%Y-%m-%d').date(),
                        notes=result[2]
                    )
            return None
        finally:
            conn.close()

    def get_all_events(self, chat_id, event_type='birthday'):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            table = 'birthdays' if event_type == 'birthday' else 'holidays'
            cursor.execute(f'SELECT name, date FROM {table} WHERE chat_id = ?', (chat_id,))
            return {name: datetime.datetime.strptime(date, '%Y-%m-%d').date() for name, date in cursor.fetchall()}
        finally:
            conn.close()

    def delete_event(self, chat_id, name, event_type='birthday'):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            table = 'birthdays' if event_type == 'birthday' else 'holidays'
            cursor.execute(f'DELETE FROM {table} WHERE chat_id = ? AND name = ?', (chat_id, name))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_global_holidays(self):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT name, date, description FROM global_holidays')
            return [(name, datetime.datetime.strptime(date, '%d.%m').date(), desc)
                    for name, date, desc in cursor.fetchall()]
        finally:
            conn.close()

    def add_global_holiday(self, name, date, description=""):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT OR IGNORE INTO global_holidays (name, date, description)
            VALUES (?, ?, ?)''', (name, date.strftime('%d.%m'), description))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def check_reminders(self):
        while True:
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            week_later = today + datetime.timedelta(days=7)
            conn = self.get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT chat_id FROM birthdays UNION SELECT DISTINCT chat_id FROM holidays')
                chat_ids = [row[0] for row in cursor.fetchall()]

                for name, date, desc in self.get_global_holidays():
                    holiday_date = datetime.date(today.year, date.month, date.day)

                    if holiday_date == today:
                        for chat_id in chat_ids:
                            try:
                                self.bot.send_message(chat_id, f"🎉 Сегодня праздник: {name}!\n\n{desc}")
                            except Exception as e:
                                print(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
                    elif holiday_date == tomorrow:
                        for chat_id in chat_ids:
                            try:
                                self.bot.send_message(chat_id, f"Напоминание: завтра праздник - {name}! 🎉")
                            except Exception as e:
                                print(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")
                    elif holiday_date == week_later:
                        for chat_id in chat_ids:
                            try:
                                self.bot.send_message(chat_id, f"Напоминание: через 7 дней праздник - {name}! 🎉")
                            except Exception as e:
                                print(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")

                for event_type in ['birthday', 'holiday']:
                    for chat_id in chat_ids:
                        if event_type == 'birthday':
                            cursor.execute('SELECT name, date, wishes, notes FROM birthdays WHERE chat_id = ?',
                                           (chat_id,))
                        else:
                            cursor.execute('SELECT name, date, notes FROM holidays WHERE chat_id = ?', (chat_id,))

                        for row in cursor.fetchall():
                            if event_type == 'birthday':
                                name, date_str, wishes, notes = row
                            else:
                                name, date_str, notes = row
                                wishes = ""

                            event_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                            event_date_this_year = datetime.date(today.year, event_date.month, event_date.day)

                            if event_date_this_year == today:
                                message = f"🎉 Сегодня {'день рождения у' if event_type == 'birthday' else 'праздник:'} {name}!\n"
                                if wishes: message += f"\nПоздравление: {wishes}"
                                if notes: message += f"\nЗаметка: {notes}"
                                try:
                                    self.bot.send_message(chat_id, message)
                                except Exception as e:
                                    print(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
                            elif event_date_this_year == tomorrow:
                                try:
                                    self.bot.send_message(chat_id,
                                                          f"Напоминание: завтра {'день рождения у' if event_type == 'birthday' else 'праздник:'} {name}! 🎉")
                                except Exception as e:
                                    print(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")
                            elif event_date_this_year == week_later:
                                try:
                                    self.bot.send_message(chat_id,
                                                          f"Напоминание: через 7 дней {'день рождения у' if event_type == 'birthday' else 'праздник:'} {name}! 🎉")
                                except Exception as e:
                                    print(f"Ошибка при отправке напоминания в чат {chat_id}: {e}")

            except Exception as e:
                print(f"Ошибка при проверке напоминаний: {e}")
            finally:
                conn.close()

            time.sleep(3600)

    def process_add_event(self, message, event_type='birthday'):
        try:
            parts = message.text.rsplit(' ', 1)
            if len(parts) != 2:
                raise ValueError

            name = parts[0]
            date = datetime.datetime.strptime(parts[1] + ".2000", "%d.%m.%Y").date()

            if self.add_event(message.chat.id, name, date, event_type=event_type):
                event_name = "День рождения" if event_type == 'birthday' else "Праздник"
                self.bot.send_message(message.chat.id, f"{event_name} {name} добавлен!")
            else:
                self.bot.send_message(message.chat.id, f"{name} уже существует в списке.")
        except ValueError:
            event_name = "день рождения" if event_type == 'birthday' else "праздник"
            msg = self.bot.send_message(
                message.chat.id,
                f"Неверный формат. Пожалуйста, используйте: Имя ДД.ММ для {event_name}"
            )
            self.bot.register_next_step_handler(msg, lambda m: self.process_add_event(m, event_type))

    def edit_event_start(self, call, event_type='birthday'):
        name = call.data.replace(f'edit_{event_type}_', '')
        self.user_data[call.from_user.id] = {'action': f'edit_{event_type}', 'name': name}

        msg = self.bot.send_message(
            call.message.chat.id,
            f"Введите новую дату в формате ДД.ММ:"
        )
        self.bot.register_next_step_handler(msg, lambda m: self.process_edit_event(m, event_type))

    def process_edit_event(self, message, event_type='birthday'):
        try:
            date = datetime.datetime.strptime(message.text + ".2000", "%d.%m.%Y").date()
            user_id = message.from_user.id
            data = self.user_data.get(user_id, {})

            if self.update_event(message.chat.id, data['name'], date=date, event_type=event_type):
                self.bot.send_message(message.chat.id, "Дата успешно обновлена!")
            else:
                self.bot.send_message(message.chat.id, "Ошибка при обновлении даты.")

            if user_id in self.user_data:
                del self.user_data[user_id]
        except ValueError:
            msg = self.bot.send_message(message.chat.id, "Неверный формат даты. Попробуйте еще раз (ДД.ММ):")
            self.bot.register_next_step_handler(msg, lambda m: self.process_edit_event(m, event_type))

    def add_note_start(self, call, event_type='birthday'):
        name = call.data.replace(f'add_note_{event_type}_', '')
        self.user_data[call.from_user.id] = {'action': f'add_note_{event_type}', 'name': name}

        msg = self.bot.send_message(
            call.message.chat.id,
            f"Введите заметку:"
        )
        self.bot.register_next_step_handler(msg, lambda m: self.process_add_note(m, event_type))

    def process_add_note(self, message, event_type='birthday'):
        user_id = message.from_user.id
        data = self.user_data.get(user_id, {})

        if self.update_event(message.chat.id, data['name'], notes=message.text, event_type=event_type):
            self.bot.send_message(message.chat.id, "Заметка успешно добавлена!")
        else:
            self.bot.send_message(message.chat.id, "Ошибка при добавлении заметки.")

        if user_id in self.user_data:
            del self.user_data[user_id]

    def delete_event_confirm(self, call, event_type='birthday'):
        name = call.data.replace(f'delete_{event_type}_', '')
        event_name = "день рождения" if event_type == 'birthday' else "праздник"

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Да", callback_data=f"confirm_delete_{event_type}_{name}"),
            types.InlineKeyboardButton("❌ Нет", callback_data=f"{event_type}_{name}")
        )

        self.bot.edit_message_text(
            f"Вы уверены, что хотите удалить {event_name} {name}?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )

    def delete_event_execute(self, call, event_type='birthday'):
        name = call.data.replace(f'confirm_delete_{event_type}_', '')
        if self.delete_event(call.message.chat.id, name, event_type):
            self.bot.answer_callback_query(call.id, "Удалено")
            self.back_to_event_list(call, event_type)
        else:
            self.bot.answer_callback_query(call.id, "Ошибка при удалении")

    def back_to_event_list(self, call, event_type='birthday'):
        events = self.get_all_events(call.message.chat.id, event_type)
        event_name = "дней рождения" if event_type == 'birthday' else "праздников"

        if not events:
            self.bot.answer_callback_query(call.id, f"Нет {event_name}")
            return

        markup = types.InlineKeyboardMarkup()
        for name in events.keys():
            markup.add(types.InlineKeyboardButton(name, callback_data=f"{event_type}_{name}"))

        try:
            self.bot.edit_message_text(
                f"Выберите {event_name[:-1]}:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )
        except Exception as e:
            print(f"Ошибка при редактировании сообщения: {e}")

    def show_event_list(self, message_or_call, event_type='birthday'):
        if isinstance(message_or_call, types.Message):
            chat_id = message_or_call.chat.id
        else:
            chat_id = message_or_call.message.chat.id

        events = self.get_all_events(chat_id, event_type)
        event_name = "дней рождения" if event_type == 'birthday' else "праздников"

        if not events:
            if isinstance(message_or_call, types.Message):
                self.bot.send_message(chat_id, f"У вас пока нет добавленных {event_name}.")
            else:
                self.bot.edit_message_text(
                    f"У вас пока нет добавленных {event_name}.",
                    chat_id,
                    message_or_call.message.message_id
                )
            return

        markup = types.InlineKeyboardMarkup()
        for name in events.keys():
            markup.add(types.InlineKeyboardButton(name, callback_data=f"{event_type}_{name}"))

        if event_type == 'birthday':
            if isinstance(message_or_call, types.Message):
                self.bot.send_message(chat_id, f"Выберите день рождения:", reply_markup=markup)
            else:
                self.bot.edit_message_text(
                    f"Выберите день рождения:",
                    chat_id,
                    message_or_call.message.message_id,
                    reply_markup=markup
                )
        else:
            if isinstance(message_or_call, types.Message):
                self.bot.send_message(chat_id, f"Выберите праздник:", reply_markup=markup)
            else:
                self.bot.edit_message_text(
                    f"Выберите праздник:",
                    chat_id,
                    message_or_call.message.message_id,
                    reply_markup=markup
                )

    def show_event_profile(self, call, event_type='birthday'):
        name = call.data.replace(f'{event_type}_', '')
        profile = self.get_event(call.message.chat.id, name, event_type)
        event_name = "дня рождения" if event_type == 'birthday' else "праздника"

        if not profile:
            self.bot.answer_callback_query(call.id, "Профиль не найден")
            return

        safe_name = self.escape_html(profile.name)
        safe_notes = self.escape_html(profile.notes) if profile.notes else "нет"
        safe_wishes = self.escape_html(profile.wishes) if profile.wishes and event_type == 'birthday' else "нет"
        safe_gifts = self.escape_html(profile.gifts) if profile.gifts and event_type == 'birthday' else "нет"

        text = f"""
<b>Профиль {event_name}</b>

{"👤" if event_type == 'birthday' else "🎉"} Имя: {safe_name}
📅 Дата: {profile.date.strftime('%d.%m')}

📝 Заметки: {safe_notes}
"""
        if event_type == 'birthday':
            text += f"\n💝 Поздравление: {safe_wishes}"
            text += f"\n🎁 Идеи подарков: {safe_gifts}"

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{event_type}_{name}"),
            types.InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_{event_type}_{name}")
        )
        markup.row(
            types.InlineKeyboardButton("📝 Добавить заметку", callback_data=f"add_note_{event_type}_{name}"),
        )
        if event_type == 'birthday':
            markup.row(
                types.InlineKeyboardButton("💝 Добавить поздравление", callback_data=f"add_wish_{event_type}_{name}"),
                types.InlineKeyboardButton("🎁 Добавить подарок", callback_data=f"add_gift_{event_type}_{name}")
            )

        markup.row(types.InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_{event_type}_list"))

        try:
            self.bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
            plain_text = f"Профиль {event_name}\n\n"
            plain_text += f"Имя: {profile.name}\n"
            plain_text += f"Дата: {profile.date.strftime('%d.%m')}\n"
            plain_text += f"Заметки: {profile.notes if profile.notes else 'нет'}\n"
            if event_type == 'birthday':
                plain_text += f"Поздравление: {profile.wishes if profile.wishes else 'нет'}\n"
                plain_text += f"Идеи подарков: {profile.gifts if profile.gifts else 'нет'}\n"

            self.bot.edit_message_text(
                plain_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )

    def generate_gift_ideas(self, name, info):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.API_KEY}"
        }

        prompt = f"Не задавай вопросов, выведи только идеи подарков. Придумай 5 оригинальных идей подарков на день рождения для {name}." \
                 f"Учти следующую информацию: {info}. " \
                 f"Сделай текст не слишком длинным, перечисли идеи списком."

        data = {
            "model": "deepseek-ai/DeepSeek-R1",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты помогаешь с выбором подарков."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            response = requests.post(settings.API_URL, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].split('</think>')[-1].strip()
            else:
                print(f"Ошибка API: {response.status_code}, {response.text}")
                return f"Идеи подарков для {name}: книга, подарочный сертификат, цветы"
        except Exception as e:
            print(f"Ошибка при генерации идей подарков: {e}")
            return f"Идеи подарков для {name}: парфюм, билеты на мероприятие, гаджет"

    def process_gift_info(self, message):
        user_id = message.from_user.id
        if user_id not in self.user_data or self.user_data[user_id]['action'] != 'generate_gift':
            self.bot.send_message(message.chat.id, "Что-то пошло не так. Пожалуйста, попробуйте снова.")
            return

        name = self.user_data[user_id]['name']
        info = message.text

        self.bot.send_chat_action(message.chat.id, 'typing')

        try:
            gift_ideas = self.generate_gift_ideas(name, info)

            self.user_data[user_id] = {
                'action': 'add_gift_birthday',
                'name': name,
                'generated_gifts': gift_ideas
            }

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ Использовать эти идеи", callback_data=f"use_generated_gift_{name}"),
            )
            markup.row(
                types.InlineKeyboardButton("🔄 Сгенерировать другие", callback_data=f"generate_gift_{name}"),
                types.InlineKeyboardButton("📝 Ввести вручную", callback_data=f"manual_gift_{name}")
            )

            self.bot.send_message(
                message.chat.id,
                f"Сгенерированные идеи подарков для {name}:\n\n{gift_ideas}\n\nХотите использовать их или сгенерировать другие?",
                reply_markup=markup
            )

            try:
                self.bot.delete_message(message.chat.id, message.message_id - 1)
            except:
                pass

        except Exception as e:
            print(f"Ошибка при генерации идей подарков: {e}")
            self.bot.send_message(message.chat.id,
                                  "Произошла ошибка при генерации идей подарков. Пожалуйста, попробуйте снова.")

    def generate_congratulation(self, name, info):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.API_KEY}"
        }

        prompt = f"Не задавай вопросов, выведи только поздравление. Придумай оригинальное и теплое поздравление с днем рождения для {name}. Информация о человеке: {info}. " \
                 f"Сделай текст не слишком длинным (4-5 предложений)."

        data = {
            "model": "deepseek-ai/DeepSeek-R1",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты пишешь поздравления."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        try:
            response = requests.post(settings.API_URL, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].split('</think>')[-1].strip()
            else:
                print(f"Ошибка API: {response.status_code}, {response.text}")
                return f"Дорогой(ая) {name}! От всей души поздравляю с Днём рождения! 🎉 Желаю счастья, здоровья и успехов во всех начинаниях! 🎂🎁"
        except Exception as e:
            print(f"Ошибка при генерации поздравления: {e}")
            return f"Дорогой(ая) {name}! Сердечно поздравляю с Днём рождения! 🌟 Пусть этот год принесёт много радости и приятных моментов! 🎈"

    def process_wish_info(self, message):
        user_id = message.from_user.id
        if user_id not in self.user_data or self.user_data[user_id]['action'] != 'generate_wish':
            self.bot.send_message(message.chat.id, "Что-то пошло не так. Пожалуйста, попробуйте снова.")
            return

        name = self.user_data[user_id]['name']
        info = message.text

        self.bot.send_chat_action(message.chat.id, 'typing')

        try:
            congratulation = self.generate_congratulation(name, info)

            self.user_data[user_id] = {
                'action': 'add_wish_birthday',
                'name': name,
                'generated_wish': congratulation
            }

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ Использовать это поздравление",
                                           callback_data=f"use_generated_wish_{name}"),
            )
            markup.row(
                types.InlineKeyboardButton("🔄 Сгенерировать другое", callback_data=f"generate_wish_{name}"),
                types.InlineKeyboardButton("📝 Ввести вручную", callback_data=f"manual_wish_{name}")
            )

            self.bot.send_message(
                message.chat.id,
                f"Сгенерированное поздравление для {name}:\n\n{congratulation}\n\nХотите использовать его или сгенерировать другое?",
                reply_markup=markup
            )

            try:
                self.bot.delete_message(message.chat.id, message.message_id - 1)
            except:
                pass

        except Exception as e:
            print(f"Ошибка при генерации поздравления: {e}")
            self.bot.send_message(message.chat.id,
                                  "Произошла ошибка при генерации поздравления. Пожалуйста, попробуйте снова.")

    def setup_handlers(self):
        @self.bot.message_handler(func=lambda message: message.text == 'Добавить праздник')
        def add_holiday_start(message):
            msg = self.bot.send_message(
                message.chat.id,
                "Введите название и дату праздника в формате: Название ДД.ММ"
            )
            self.bot.register_next_step_handler(msg, lambda m: self.process_add_event(m, 'holiday'))

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_gift_birthday_'))
        def add_gift_start(call):
            name = call.data.replace('add_gift_birthday_', '')
            self.user_data[call.from_user.id] = {'action': 'add_gift_birthday', 'name': name}

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✨ Сгенерировать идеи", callback_data=f"generate_gift_{name}"),
            )
            markup.row(
                types.InlineKeyboardButton("📝 Ввести вручную", callback_data=f"manual_gift_{name}")
            )
            markup.row(
                types.InlineKeyboardButton("🔙 Назад", callback_data=f"birthday_{name}")
            )

            self.bot.edit_message_text(
                f"Хотите сгенерировать идеи подарков для {name} или ввести вручную?",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('generate_gift_'))
        def generate_gift(call):
            name = call.data.replace('generate_gift_', '')
            self.user_data[call.from_user.id] = {'action': 'generate_gift', 'name': name}

            msg = self.bot.send_message(
                call.message.chat.id,
                f"Введите информацию о {name} (возраст, хобби, увлечения и т.д.), чтобы я мог предложить персонализированные идеи подарков:"
            )
            self.bot.register_next_step_handler(msg, self.process_gift_info)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('use_generated_gift_'))
        def use_generated_gift(call):
            name = call.data.replace('use_generated_gift_', '')
            user_id = call.from_user.id
            data = self.user_data.get(user_id, {})

            if 'generated_gifts' in data:
                if self.update_event(call.message.chat.id, data['name'], gifts=data['generated_gifts'],
                                     event_type='birthday'):
                    self.bot.answer_callback_query(call.id, "Идеи подарков сохранены!")
                    self.show_event_profile(call, 'birthday')
                else:
                    self.bot.answer_callback_query(call.id, "Ошибка при сохранении идей подарков")
            else:
                self.bot.answer_callback_query(call.id, "Идеи подарков не найдены")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('manual_gift_'))
        def manual_gift_input(call):
            name = call.data.replace('manual_gift_', '')
            self.user_data[call.from_user.id] = {'action': 'add_gift_birthday', 'name': name}

            msg = self.bot.send_message(
                call.message.chat.id,
                f"Введите ваши идеи подарков для {name}:"
            )
            self.bot.register_next_step_handler(msg, self.process_add_gift)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_wish_birthday_'))
        def add_wish_start(call):
            name = call.data.replace('add_wish_birthday_', '')
            self.user_data[call.from_user.id] = {'action': 'add_wish_birthday', 'name': name}

            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✨ Сгенерировать поздравление", callback_data=f"generate_wish_{name}"),
            )
            markup.row(
                types.InlineKeyboardButton("📝 Ввести вручную", callback_data=f"manual_wish_{name}")
            )
            markup.row(
                types.InlineKeyboardButton("🔙 Назад", callback_data=f"birthday_{name}")
            )

            self.bot.edit_message_text(
                f"Хотите сгенерировать поздравление для {name} или ввести вручную?",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('generate_wish_'))
        def generate_wish(call):
            name = call.data.replace('generate_wish_', '')
            self.user_data[call.from_user.id] = {'action': 'generate_wish', 'name': name}

            msg = self.bot.send_message(
                call.message.chat.id,
                f"Введите информацию о {name} (возраст, хобби, увлечения и т.д.), чтобы я мог создать персонализированное поздравление:"
            )
            self.bot.register_next_step_handler(msg, self.process_wish_info)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('use_generated_wish_'))
        def use_generated_wish(call):
            name = call.data.replace('use_generated_wish_', '')
            user_id = call.from_user.id
            data = self.user_data.get(user_id, {})

            if 'generated_wish' in data:
                if self.update_event(call.message.chat.id, data['name'], wishes=data['generated_wish'],
                                     event_type='birthday'):
                    self.bot.answer_callback_query(call.id, "Поздравление сохранено!")
                    self.show_event_profile(call, 'birthday')
                else:
                    self.bot.answer_callback_query(call.id, "Ошибка при сохранении поздравления")
            else:
                self.bot.answer_callback_query(call.id, "Поздравление не найдено")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('manual_wish_'))
        def manual_wish_input(call):
            name = call.data.replace('manual_wish_', '')
            self.user_data[call.from_user.id] = {'action': 'add_wish_birthday', 'name': name}

            msg = self.bot.send_message(
                call.message.chat.id,
                f"Введите ваше поздравление для {name}:"
            )
            self.bot.register_next_step_handler(msg, self.process_add_wish)

            try:
                self.bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass

        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Дни рождения")
            button2 = types.KeyboardButton('Праздники')
            button3 = types.KeyboardButton('Информация о боте')
            markup.row(button1, button2)
            markup.row(button3)
            self.bot.send_message(message.chat.id,
                                  f'Привет, {message.from_user.first_name}! Я бот для отслеживания дней рождения и праздников.',
                                  reply_markup=markup)

        @self.bot.message_handler(func=lambda message: message.text == 'Дни рождения')
        def show_birthdays_menu(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Добавить день рождения")
            button2 = types.KeyboardButton('Список дней рождения')
            button3 = types.KeyboardButton('Назад')
            markup.row(button1, button2)
            markup.row(button3)
            self.bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

        @self.bot.message_handler(func=lambda message: message.text == 'Праздники')
        def show_holidays_menu(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Добавить праздник")
            button2 = types.KeyboardButton('Список личных праздников')
            button3 = types.KeyboardButton('Список глобальных праздников')
            button4 = types.KeyboardButton('Назад')
            markup.row(button1, button2)
            markup.row(button3, button4)
            self.bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

        @self.bot.message_handler(func=lambda message: message.text == 'Список дней рождения')
        def show_birthdays_list(message):
            self.show_event_list(message, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('birthday_'))
        def show_birthday_profile(call):
            self.show_event_profile(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data == 'back_to_birthday_list')
        def back_to_birthday_list(call):
            self.back_to_event_list(call, 'birthday')

        @self.bot.message_handler(func=lambda message: message.text == 'Добавить день рождения')
        def add_birthday_start(message):
            msg = self.bot.send_message(
                message.chat.id,
                "Введите имя и дату рождения в формате: Имя ДД.ММ"
            )
            self.bot.register_next_step_handler(msg, lambda m: self.process_add_event(m, 'birthday'))

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('edit_birthday_'))
        def edit_birthday_start(call):
            self.edit_event_start(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_note_birthday_'))
        def add_birthday_note_start(call):
            self.add_note_start(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_wish_birthday_'))
        def add_birthday_wish_start(call):
            self.add_wish_start(call)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_birthday_'))
        def delete_birthday_confirm(call):
            self.delete_event_confirm(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_birthday_'))
        def delete_birthday_execute(call):
            self.delete_event_execute(call, 'birthday')

        @self.bot.message_handler(func=lambda message: message.text == 'Список личных праздников')
        def show_holidays_list(message):
            self.show_event_list(message, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('holiday_'))
        def show_holiday_profile(call):
            self.show_event_profile(call, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data == 'back_to_holiday_list')
        def back_to_holiday_list(call):
            self.back_to_event_list(call, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('edit_holiday_'))
        def edit_holiday_start(call):
            self.edit_event_start(call, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_note_holiday_'))
        def add_holiday_note_start(call):
            self.add_note_start(call, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_holiday_'))
        def delete_holiday_confirm(call):
            self.delete_event_confirm(call, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_holiday_'))
        def delete_holiday_execute(call):
            self.delete_event_execute(call, 'holiday')

        @self.bot.message_handler(func=lambda message: message.text == 'Список глобальных праздников')
        def show_global_holidays(message):
            holidays = self.get_global_holidays()
            if not holidays:
                self.bot.send_message(message.chat.id, "Список глобальных праздников пуст.")
                return

            text = "📅 <b>Глобальные праздники:</b>\n\n"
            for name, date, desc in sorted(holidays, key=lambda x: (x[1].month, x[1].day)):
                safe_name = self.escape_html(name)
                safe_desc = self.escape_html(desc) if desc else ""
                text += f"🎉 <b>{safe_name}</b> - {date.strftime('%d.%m')}\n"
                if safe_desc:
                    text += f"   {safe_desc}\n"
                text += "\n"

            self.bot.send_message(message.chat.id, text, parse_mode='HTML')

        @self.bot.message_handler(func=lambda message: message.text == 'Информация о боте')
        def send_help(message):
            help_text = """
📌 <b>Информация о боте</b>

Я помогаю отслеживать дни рождения и праздники, а также напоминаю о них заранее.

<b>Основные функции:</b>
- Добавление дней рождений и праздников
- Просмотр списка предстоящих событий
- Напоминания за 1, 7 дней и в день события
- Профили с дополнительной информацией
- Возможность добавлять заметки, поздравления и подарки
- Генерация поздравлений и идей для подарков на основе информации об имениннике

Используйте кнопки меню для навигации.

Ссылка на руководство пользователя:
https://drive.google.com/file/d/1vWW2xOe9dFCfBCGBaMvCsvZBe01v6gQ7/view?usp=sharing
Ссылка на канал технической поддержки:
https://t.me/holidaysarewaiting
"""
            self.bot.send_message(message.chat.id, help_text, parse_mode='HTML', disable_web_page_preview=True)

        @self.bot.message_handler(func=lambda message: message.text == 'Назад')
        def back_to_main(message):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Дни рождения")
            button2 = types.KeyboardButton('Праздники')
            button3 = types.KeyboardButton('Информация о боте')
            markup.row(button1, button2)
            markup.row(button3)
            self.bot.send_message(message.chat.id, "Главное меню:", reply_markup=markup)

    def run(self):
        print("Бот запущен...")
        self.bot.polling(none_stop=True, interval=0)