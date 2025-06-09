import html
from typing import Dict, Any, Optional
from telebot import types, TeleBot
import datetime
from src.database.database import Database
from src.services.api_services import AIService


class Handlers:
    """Основной класс обработчиков бота, отвечающий за взаимодействие с пользователем"""
    def __init__(self, bot: TeleBot, db: Database, ai_service: AIService):
        """Инициализация обработчиков с зависимостями"""
        self.bot = bot
        self.db = db
        self.ai_service = ai_service
        self.user_data: Dict[int, Dict[str, Any]] = {}

    def escape_html(self, text: Optional[str]) -> str:
        """Экранирование HTML-символов для безопасного отображения"""
        if text is None:
            return ""
        return html.escape(text)

    # Основной метод для настройки всех обработчиков
    def setup_handlers(self):
        """Регистрация всех обработчиков команд и обратных запросов"""

        # Обработчик команды /start - главное меню
        @self.bot.message_handler(commands=['start'])
        def send_welcome(message):
            """Показывает главное меню с основными кнопками"""
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Дни рождения")
            button2 = types.KeyboardButton('Праздники')
            button3 = types.KeyboardButton('Информация о боте')
            button4 = types.KeyboardButton('Настройка уведомлений')
            markup.row(button1, button2)
            markup.row(button3, button4)
            self.bot.send_message(
                message.chat.id,
                f'Привет, {message.from_user.first_name}! Я бот для отслеживания дней рождения и праздников.',
                reply_markup=markup
            )

        # Обработчики меню "Дни рождения"
        @self.bot.message_handler(func=lambda message: message.text == 'Дни рождения')
        def show_birthdays_menu(message):
            """Показывает меню управления днями рождения"""
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Добавить день рождения")
            button2 = types.KeyboardButton('Список дней рождения')
            button3 = types.KeyboardButton('Назад')
            markup.row(button1, button2)
            markup.row(button3)
            self.bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

        # Обработчики меню "Праздники"
        @self.bot.message_handler(func=lambda message: message.text == 'Праздники')
        def show_holidays_menu(message):
            """Показывает меню управления праздниками"""
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Добавить праздник")
            button2 = types.KeyboardButton('Список личных праздников')
            button3 = types.KeyboardButton('Список глобальных праздников')
            button4 = types.KeyboardButton('Назад')
            markup.row(button1, button2)
            markup.row(button3, button4)
            self.bot.send_message(message.chat.id, "Выберите действие:", reply_markup=markup)

        # Обработчики меню "Настройки уведомлений"
        @self.bot.message_handler(func=lambda message: message.text == 'Настройка уведомлений')
        def show_settings_menu(message):
            """Показывает меню управления уведомлениями"""
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton('Уведомления о днях рождения')
            button2 = types.KeyboardButton('Уведомления о личных праздниках')
            button3 = types.KeyboardButton('Уведомления о глобальных праздниках')
            button4 = types.KeyboardButton('Назад')
            markup.row(button1, button2)
            markup.row(button3, button4)
            self.bot.send_message(message.chat.id, "Выберите событие для настройки уведомлений:", reply_markup=markup)


        # Обработчики списков событий
        @self.bot.message_handler(func=lambda message: message.text == 'Список дней рождения')
        def show_birthdays_list(message):
            """Показывает список дней рождения"""
            self.show_event_list(message, 'birthday')

        # Обработчики добавления событий
        @self.bot.message_handler(func=lambda message: message.text == 'Добавить день рождения')
        def add_birthday_start(message):
            """Начинает процесс добавления дня рождения"""
            msg = self.bot.send_message(
                message.chat.id,
                "Введите имя и дату рождения в формате: Имя ДД.ММ"
            )
            self.bot.register_next_step_handler(msg, lambda m: self.process_add_event(m, 'birthday'))

        @self.bot.message_handler(func=lambda message: message.text == 'Добавить праздник')
        def add_holiday_start(message):
            """Начинает процесс добавления праздника"""
            msg = self.bot.send_message(
                message.chat.id,
                "Введите название и дату праздника в формате: Название ДД.ММ"
            )
            self.bot.register_next_step_handler(msg, lambda m: self.process_add_event(m, 'holiday'))

        @self.bot.message_handler(func=lambda message: message.text == 'Список личных праздников')
        def show_holidays_list(message):
            """Показывает список личных праздников"""
            self.show_event_list(message, 'holiday')

        @self.bot.message_handler(func=lambda message: message.text == 'Список глобальных праздников')
        def show_global_holidays(message):
            """Показывает список глобальных праздников"""
            holidays = self.db.get_global_holidays()
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

        # Обработчик информации о боте
        @self.bot.message_handler(func=lambda message: message.text == 'Информация о боте')
        def send_help(message):
            """Показывает информацию о возможностях бота"""
            help_text = """
📌 <b>Информация о боте</b>

Я помогаю отслеживать дни рождения и праздники, а также напоминаю о них заранее.

<b>Основные функции:</b>
- Добавление дней рождений и праздников
- Просмотр списка предстоящих событий
- Напоминания за 1, 7 дней и в день события
- Настройка параметров уведомлений
- Профили с дополнительной информацией
- Возможность добавлять заметки, поздравления и подарки
- Генерация поздравлений и идей для подарков на основе информации об имениннике

Используйте кнопки меню для навигации.

Ссылка на руководство пользователя:
https://drive.google.com/file/d/1vWW2xOe9dFCfBCGBaMvCsvZBe01v6gQ7/view?usp=sharing
Ссылка на канал технической поддержки:
https://t.me/holidaysarewaiting
"""
            self.bot.send_message(
                message.chat.id,
                help_text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )


        # Обработчик кнопки "Уведомления о днях рождения"
        @self.bot.message_handler(func=lambda message: message.text == 'Уведомления о днях рождения')
        def show_settings_birthday_menu(message):
            """Показывает меню настроек уведомлений для дней рождения"""
            self.show_notification_settings_menu(message, 'birthday')

        # Обработчик кнопки "Уведомления о личных праздниках"
        @self.bot.message_handler(func=lambda message: message.text == 'Уведомления о личных праздниках')
        def show_settings_personal_holidays_menu(message):
            """Показывает меню настроек уведомлений для личных праздников"""
            self.show_notification_settings_menu(message, 'holiday')

        # Обработчик кнопки "Уведомления о глобальных праздниках"
        @self.bot.message_handler(func=lambda message: message.text == 'Уведомления о глобальных праздниках')
        def show_settings_global_holidays_menu(message):
            """Показывает меню настроек уведомлений для глобальных праздников"""
            self.show_notification_settings_menu(message, 'global_holiday')

        # Обработчик кнопки "Назад"
        @self.bot.message_handler(func=lambda message: message.text == 'Назад')
        def back_to_main(message):
            """Возвращает в главное меню"""
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Дни рождения")
            button2 = types.KeyboardButton('Праздники')
            button3 = types.KeyboardButton('Информация о боте')
            button4 = types.KeyboardButton('Настройка уведомлений')
            markup.row(button1, button2)
            markup.row(button3, button4)
            self.bot.send_message(message.chat.id, "Главное меню:", reply_markup=markup)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_notification_'))
        def toggle_notification(call):
            """Переключает статус уведомления (вкл/выкл) и обновляет существующее сообщение"""
            try:
                print(f"Получены callback_data: {call.data}")

                parts = call.data.split('_')
                print(f"Разделенные части: {parts}")

                if len(parts) < 4 or parts[0] != 'toggle' or parts[1] != 'notification':
                    print(f"Неверный формат callback_data или префикс: {call.data}")
                    self.bot.answer_callback_query(call.id, "Ошибка в формате команды")
                    return

                if parts[2] == 'global' and len(parts) >= 5:
                    event_type = 'global_holiday'
                    setting = '_'.join(parts[4:])
                else:
                    event_type = parts[2]
                    setting = '_'.join(parts[3:])
                print(f"event_type: {event_type}, setting: {setting}")

                # Проверка event_type и setting
                valid_event_types = ['birthday', 'holiday', 'global_holiday']
                valid_settings = ['notify_on_day', 'notify_one_day_before', 'notify_one_week_before']
                if event_type not in valid_event_types:
                    print(f"Недопустимый event_type: {event_type}, callback_data: {call.data}")
                    self.bot.answer_callback_query(call.id, "Недопустимый тип события")
                    return
                if setting not in valid_settings:
                    print(f"Недопустимая настройка: {setting}, callback_data: {call.data}")
                    self.bot.answer_callback_query(call.id, "Недопустимая настройка")
                    return

                chat_id = call.message.chat.id

                # Получение текущих настроек
                settings = self.db.get_notification_settings(chat_id, event_type)
                if not settings:
                    settings = {'notify_on_day': 1, 'notify_one_day_before': 1, 'notify_one_week_before': 1}
                    self.db.update_notification_settings(chat_id, event_type, **settings)
                print(f"Текущие настройки: {settings}")

                # Переключение настроек
                new_value = 1 if settings.get(setting, 0) == 0 else 0
                update_data = {setting: new_value}
                success = self.db.update_notification_settings(chat_id, event_type, **update_data)

                if not success:
                    print(
                        f"Не удалось обновить настройки: chat_id={chat_id}, event_type={event_type}, setting={setting}")
                    self.bot.answer_callback_query(call.id, "Ошибка при обновлении настроек")
                    return

                # Получение обновленных настроек
                updated_settings = self.db.get_notification_settings(chat_id, event_type)
                if not updated_settings:
                    print(f"Настройки не найдены после обновления: chat_id={chat_id}, event_type={event_type}")
                    self.bot.answer_callback_query(call.id, "Ошибка: настройки не найдены")
                    return
                print(f"Обновленные настройки: {updated_settings}")

                # Создание нового меню
                event_name = {
                    'birthday': 'Дней рождения',
                    'holiday': 'Личных праздников',
                    'global_holiday': 'Глобальных праздников'
                }[event_type]

                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton(
                        f"В день события {'✅' if updated_settings['notify_on_day'] else '❌'}",
                        callback_data=f"toggle_notification_{event_type}_notify_on_day"
                    )
                )
                markup.row(
                    types.InlineKeyboardButton(
                        f"За 1 день {'✅' if updated_settings['notify_one_day_before'] else '❌'}",
                        callback_data=f"toggle_notification_{event_type}_notify_one_day_before"
                    )
                )
                markup.row(
                    types.InlineKeyboardButton(
                        f"За неделю {'✅' if updated_settings['notify_one_week_before'] else '❌'}",
                        callback_data=f"toggle_notification_{event_type}_notify_one_week_before"
                    )
                )

                text = f"Настройки уведомлений для {event_name}:"

                # Редактирование существующего сообщения
                try:
                    self.bot.edit_message_text(
                        text,
                        chat_id=chat_id,
                        message_id=call.message.message_id,
                        reply_markup=markup
                    )
                    self.bot.answer_callback_query(call.id, "Настройка обновлена")
                except Exception as e:
                    print(f"Ошибка при редактировании сообщения: {e}, callback_data={call.data}")
                    self.bot.answer_callback_query(call.id, "Ошибка при обновлении меню")
            except Exception as e:
                print(f"Общая ошибка в toggle_notification: {e}, callback_data={call.data}")
                self.bot.answer_callback_query(call.id, "Произошла ошибка")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('birthday_'))
        def show_birthday_profile(call):
            """Показывает профиль дня рождения"""
            self.show_event_profile(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('holiday_'))
        def show_holiday_profile(call):
            """Показывает профиль праздника"""
            self.show_event_profile(call, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data == 'back_to_birthday_list')
        def back_to_birthday_list(call):
            """Возвращает к списку дней рождения"""
            self.back_to_event_list(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data == 'back_to_holiday_list')
        def back_to_holiday_list(call):
            """Возвращает к списку праздника"""
            self.back_to_event_list(call, 'holiday')

        # Обработчики редактирования событий
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('edit_birthday_'))
        def edit_birthday_start(call):
            """Начинает процесс редактирования дня рождения"""
            self.edit_event_start(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('edit_holiday_'))
        def edit_holiday_start(call):
            """Начинает процесс редактирования праздника"""
            self.edit_event_start(call, 'holiday')

        # Обработчики добавления заметок
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_note_birthday_'))
        def add_birthday_note_start(call):
            """Начинает процесс добавления заметки к дню рождения"""
            self.add_note_start(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_note_holiday_'))
        def add_holiday_note_start(call):
            """Начинает процесс добавления заметки к празднику"""
            self.add_note_start(call, 'holiday')

        # Обработчики работы с поздравлениями (только для дней рождения)
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_wish_birthday_'))
        def add_wish_start(call):
            """Начинает процесс добавления/генерации поздравления"""
            self.add_wish_start(call)

        # Обработчики работы с подарками (только для дней рождения)
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('add_gift_birthday_'))
        def add_gift_start(call):
            """Начинает процесс добавления/генерации идей подарков"""
            self.add_gift_start(call)

        # Обработчики удаления событий
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_birthday_'))
        def delete_birthday_confirm(call):
            """Запрашивает подтверждение удаления дня рождения"""
            self.delete_event_confirm(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('delete_holiday_'))
        def delete_holiday_confirm(call):
            """Запрашивает подтверждение удаления праздника"""
            self.delete_event_confirm(call, 'holiday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_birthday_'))
        def delete_birthday_execute(call):
            """Выполняет удаление дня рождения после подтверждения"""
            self.delete_event_execute(call, 'birthday')

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_delete_holiday_'))
        def delete_holiday_execute(call):
            """Выполняет удаление праздника после подтверждения"""
            self.delete_event_execute(call, 'holiday')

        # Обработчики генерации идей подарков через AI
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('generate_gift_'))
        def generate_gift(call):
            """Запрашивает информацию для генерации идей подарков"""
            name = call.data.replace('generate_gift_', '')
            self.user_data[call.from_user.id] = {'action': 'generate_gift', 'name': name}

            msg = self.bot.send_message(
                call.message.chat.id,
                f"Введите информацию о {name} (возраст, хобби, увлечения и т.д.), "
                "чтобы я мог предложить персонализированные идеи подарков:"
            )
            self.bot.register_next_step_handler(msg, self.process_gift_info)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('use_generated_gift_'))
        def use_generated_gift(call):
            """Сохраняет сгенерированные идеи подарков"""
            name = call.data.replace('use_generated_gift_', '')
            user_id = call.from_user.id
            data = self.user_data.get(user_id, {})

            if 'generated_gifts' in data:
                if self.db.update_event(
                    call.message.chat.id,
                    data['name'],
                    gifts=data['generated_gifts'],
                    event_type='birthday'
                ):
                    self.bot.answer_callback_query(call.id, "Идеи подарков сохранены!")
                    self.show_event_profile(call, 'birthday')
                else:
                    self.bot.answer_callback_query(call.id, "Ошибка при сохранении идей подарков")
            else:
                self.bot.answer_callback_query(call.id, "Идеи подарков не найдены")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('manual_gift_'))
        def manual_gift_input(call):
            """Запрашивает ручной ввод идей подарков"""
            name = call.data.replace('manual_gift_', '')
            self.user_data[call.from_user.id] = {'action': 'add_gift_birthday', 'name': name}

            msg = self.bot.send_message(
                call.message.chat.id,
                f"Введите ваши идеи подарков для {name}:"
            )
            self.bot.register_next_step_handler(msg, self.process_add_gift)

        # Обработчики генерации поздравлений через AI
        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('generate_wish_'))
        def generate_wish(call):
            """Запрашивает информацию для генерации поздравления"""
            name = call.data.replace('generate_wish_', '')
            self.user_data[call.from_user.id] = {'action': 'generate_wish', 'name': name}

            msg = self.bot.send_message(
                call.message.chat.id,
                f"Введите информацию о {name} (возраст, хобби, увлечения и т.д.), "
                "чтобы я мог создать персонализированное поздравление:"
            )
            self.bot.register_next_step_handler(msg, self.process_wish_info)


        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('use_generated_wish_'))
        def use_generated_wish(call):
            """Сохраняет сгенерированное поздравление"""
            name = call.data.replace('use_generated_wish_', '')
            user_id = call.from_user.id
            data = self.user_data.get(user_id, {})

            if 'generated_wish' in data:
                if self.db.update_event(
                    call.message.chat.id,
                    data['name'],
                    wishes=data['generated_wish'],
                    event_type='birthday'
                ):
                    self.bot.answer_callback_query(call.id, "Поздравление сохранено!")
                    self.show_event_profile(call, 'birthday')
                else:
                    self.bot.answer_callback_query(call.id, "Ошибка при сохранении поздравления")
            else:
                self.bot.answer_callback_query(call.id, "Поздравление не найдено")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('manual_wish_'))
        def manual_wish_input(call):
            """Запрашивает ручной ввод поздравления"""
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

    # Основные методы обработки данных
    def process_add_event(self, message, event_type='birthday'):
        """Обрабатывает добавление нового события (дня рождения/праздника)"""
        try:
            parts = message.text.rsplit(' ', 1)
            if len(parts) != 2:
                raise ValueError

            name = parts[0]
            date = datetime.datetime.strptime(parts[1] + ".2000", "%d.%m.%Y").date()

            if self.db.add_event(message.chat.id, name, date, event_type=event_type):
                event_name = "День рождения" if event_type == 'birthday' else "Праздник"
                self.bot.send_message(message.chat.id, f"{event_name} {name} добавлен!")
                self.db.init_notification_settings(message.chat.id)  # Инициализация настроек уведомлений
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
        """Обрабатывает изменение даты события"""
        try:
            date = datetime.datetime.strptime(message.text + ".2000", "%d.%m.%Y").date()
            user_id = message.from_user.id
            data = self.user_data.get(user_id, {})

            if self.db.update_event(message.chat.id, data['name'], date=date, event_type=event_type):
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
        """Обрабатывает добавление заметки к событию"""
        user_id = message.from_user.id
        data = self.user_data.get(user_id, {})

        if self.db.update_event(message.chat.id, data['name'], notes=message.text, event_type=event_type):
            self.bot.send_message(message.chat.id, "Заметка успешно добавлена!")
        else:
            self.bot.send_message(message.chat.id, "Ошибка при добавлении заметки.")

        if user_id in self.user_data:
            del self.user_data[user_id]

    def add_wish_start(self, call):
        """Показывает меню выбора способа добавления поздравления"""
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

    def show_notification_settings_menu(self, message, event_type, message_id=None):
        """Показывает меню настроек уведомлений для указанного типа событий"""
        chat_id = message.chat.id
        settings = self.db.get_notification_settings(chat_id, event_type)
        if not settings:
            settings = {'notify_on_day': 1, 'notify_one_day_before': 1, 'notify_one_week_before': 1}
            self.db.update_notification_settings(chat_id, event_type, **settings)

        event_name = {
            'birthday': 'Дней рождения',
            'holiday': 'Личных праздников',
            'global_holiday': 'Глобальных праздников'
        }[event_type]

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton(
                f"В день события {'✅' if settings['notify_on_day'] else '❌'}",
                callback_data=f"toggle_notification_{event_type}_notify_on_day"
            )
        )
        markup.row(
            types.InlineKeyboardButton(
                f"За 1 день {'✅' if settings['notify_one_day_before'] else '❌'}",
                callback_data=f"toggle_notification_{event_type}_notify_one_day_before"
            )
        )
        markup.row(
            types.InlineKeyboardButton(
                f"За неделю {'✅' if settings['notify_one_week_before'] else '❌'}",
                callback_data=f"toggle_notification_{event_type}_notify_one_week_before"
            )
        )

        text = f"Настройки уведомлений для {event_name}:"

        try:
            if message_id:
                self.bot.edit_message_text(
                    text,
                    chat_id,
                    message_id,
                    reply_markup=markup
                )
            else:
                self.bot.send_message(chat_id, text, reply_markup=markup)
        except Exception as e:
            print(f"Error in show_notification_settings: {e}")
            self.bot.send_message(chat_id, text, reply_markup=markup)

    def add_gift_start(self, call):
        """Показывает меню выбора способа добавления идей подарков"""
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

    def process_gift_info(self, message):
        """Обрабатывает информацию для генерации идей подарков"""
        user_id = message.from_user.id
        if user_id not in self.user_data or self.user_data[user_id]['action'] != 'generate_gift':
            self.bot.send_message(message.chat.id, "Что-то пошло не так. Пожалуйста, попробуйте снова.")
            return

        name = self.user_data[user_id]['name']
        info = message.text

        self.bot.send_chat_action(message.chat.id, 'typing')

        try:
            gift_ideas = self.ai_service.generate_gift_ideas(name, info)

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
                f"Сгенерированные идеи подарков для {name}:\n\n{gift_ideas}\n\n"
                "Хотите использовать их или сгенерировать другие?",
                reply_markup=markup
            )

            try:
                self.bot.delete_message(message.chat.id, message.message_id - 1)
            except:
                pass

        except Exception as e:
            print(f"Ошибка при генерации идей подарков: {e}")
            self.bot.send_message(
                message.chat.id,
                "Произошла ошибка при генерации идей подарков. Пожалуйста, попробуйте снова."
            )

    def process_wish_info(self, message):
        """Обрабатывает информацию для генерации поздравления"""
        user_id = message.from_user.id
        if user_id not in self.user_data or self.user_data[user_id]['action'] != 'generate_wish':
            self.bot.send_message(message.chat.id, "Что-то пошло не так. Пожалуйста, попробуйте снова.")
            return

        name = self.user_data[user_id]['name']
        info = message.text

        self.bot.send_chat_action(message.chat.id, 'typing')

        try:
            congratulation = self.ai_service.generate_congratulation(name, info)

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
                f"Сгенерированное поздравление для {name}:\n\n{congratulation}\n\n"
                "Хотите использовать его или сгенерировать другое?",
                reply_markup=markup
            )

            try:
                self.bot.delete_message(message.chat.id, message.message_id - 1)
            except:
                pass

        except Exception as e:
            print(f"Ошибка при генерации поздравления: {e}")
            self.bot.send_message(
                message.chat.id,
                "Произошла ошибка при генерации поздравления. Пожалуйста, попробуйте снова."
            )

    def process_add_gift(self, message):
        """Обрабатывает ручной ввод идей подарков"""
        user_id = message.from_user.id
        data = self.user_data.get(user_id, {})

        if self.db.update_event(message.chat.id, data['name'], gifts=message.text, event_type='birthday'):
            self.bot.send_message(message.chat.id, "Идеи подарков успешно добавлены!")
        else:
            self.bot.send_message(message.chat.id, "Ошибка при добавлении идей подарков.")

        if user_id in self.user_data:
            del self.user_data[user_id]

    def process_add_wish(self, message):
        """Обрабатывает ручной ввод поздравления"""
        user_id = message.from_user.id
        data = self.user_data.get(user_id, {})

        if self.db.update_event(message.chat.id, data['name'], wishes=message.text, event_type='birthday'):
            self.bot.send_message(message.chat.id, "Поздравление успешно добавлено!")
        else:
            self.bot.send_message(message.chat.id, "Ошибка при добавлении поздравления.")

        if user_id in self.user_data:
            del self.user_data[user_id]

    def delete_event_confirm(self, call, event_type='birthday'):
        """Показывает подтверждение удаления события"""
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
        """Выполняет удаление события"""
        name = call.data.replace(f'confirm_delete_{event_type}_', '')
        if self.db.delete_event(call.message.chat.id, name, event_type):
            self.bot.answer_callback_query(call.id, "Удалено")
            self.back_to_event_list(call, event_type)
        else:
            self.bot.answer_callback_query(call.id, "Ошибка при удалении")

    def back_to_event_list(self, call, event_type='birthday'):
        """Возвращает к списку событий"""
        events = self.db.get_all_events(call.message.chat.id, event_type)
        event_name = "дней рождения" if event_type == 'birthday' else "праздников"

        if not events:
            self.bot.answer_callback_query(call.id, f"Нет {event_name}")
            return

        markup = types.InlineKeyboardMarkup()
        for name in events.keys():
            markup.add(types.InlineKeyboardButton(name, callback_data=f"{event_type}_{name}"))

        try:
            if event_name == "дней рождения":
                self.bot.edit_message_text(
                    f"Выберите день рождения:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
            )
            else:
                self.bot.edit_message_text(
                    f"Выберите праздник:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=markup
            )
        except Exception as e:
            print(f"Ошибка при редактировании сообщения: {e}")

    def show_event_list(self, message_or_call, event_type='birthday'):
        """Показывает список событий (дней рождения/праздников)"""
        if isinstance(message_or_call, types.Message):
            chat_id = message_or_call.chat.id
        else:
            chat_id = message_or_call.message.chat.id

        events = self.db.get_all_events(chat_id, event_type)
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
        """Показывает профиль события с детальной информацией"""
        name = call.data.replace(f'{event_type}_', '')
        profile = self.db.get_event(call.message.chat.id, name, event_type)
        event_name = "дня рождения" if event_type == 'birthday' else "праздника"

        if not profile:
            self.bot.answer_callback_query(call.id, "Профиль не найден")
            return

        safe_name = self.escape_html(profile['name'])
        safe_notes = self.escape_html(profile['notes']) if profile['notes'] else "нет"
        safe_wishes = self.escape_html(profile.get('wishes', '')) if profile.get('wishes') and event_type == 'birthday' else "нет"
        safe_gifts = self.escape_html(profile.get('gifts', '')) if profile.get('gifts') and event_type == 'birthday' else "нет"

        text = f"""
<b>Профиль {event_name}</b>

{"👤" if event_type == 'birthday' else "🎉"} Имя: {safe_name}
📅 Дата: {profile['date'].strftime('%d.%m')}

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
            plain_text += f"Имя: {profile['name']}\n"
            plain_text += f"Дата: {profile['date'].strftime('%d.%m')}\n"
            plain_text += f"Заметки: {profile['notes'] if profile['notes'] else 'нет'}\n"
            if event_type == 'birthday':
                plain_text += f"Поздравление: {profile.get('wishes', 'нет')}\n"
                plain_text += f"Идеи подарков: {profile.get('gifts', 'нет')}\n"

            self.bot.edit_message_text(
                plain_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )