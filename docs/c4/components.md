# Диаграмма компонентов
Диаграмма компонентов показывает внутреннюю структуру контейнера, разбивая его на логические компоненты (модули, классы, сервисы) и связи между ними.

```mermaid
C4Component
    title Диаграмма компонентов Telegram-бота OhMyGift!

    System_Boundary(ext, "Внешние системы") {
        System_Ext(AiApi, "IO.NET", "Предоставляет доступ <br> к GPU через API-ключ")
        System_Ext(telegram, "Telegram API", "Официальное API Telegram")
    UpdateLayoutConfig($c4BoundaryInRow="1")
    }
    
    System_Boundary(boundary, "Система OhMyGiftBot") {
        Container_Boundary(bot_container, "Контейнер: Telegram-бот") {

            Boundary(services, "Сервисы") {
                Component(api_services, "ApiServices", "Python", "Создание запросов через API-ключ")
                Component(reminder_services, "ReminderServices", "Python", "Проверяет и формирует напоминания")
            }

            Boundary(handlers, "Обработчики сообщений") {
                Component(handlers, "Handlers", "Python", "Обрабатывает команды пользователей <br> и формирует интерфейс")
            }

            Boundary(repos, "Репозитории для работы с БД") {
                Component(database, "Database", "Python", "Обрабатывает данные пользователей")
            }
        }
        Container_Boundary(database, "Контейнер: База данных") {
            ContainerDb(db, "База данных", "MySQL3", "Хранит пользователей и их информацию")
        }
    }

    Rel(api_services, AiApi, "Отправляет промпт через API-ключ в сервис IO.NET")
    UpdateRelStyle(api_services, AiApi, $offsetX="-60", $offsetY="-40")
    Rel(database, db, "Работает с данными пользователей")
    UpdateRelStyle(database, db, $offsetX="-110", $offsetY="-30")
    Rel(handlers, database, "Обрабатывает данные из базы данных")
    UpdateRelStyle(handlers, database, $offsetX="-100", $offsetY="-30")
    Rel(handlers, reminder_services, "Обрабатывает данных об уведомлениях")
    UpdateRelStyle(handlers, reminder_services, $offsetX="0", $offsetY="20")
    Rel(handlers, api_services, "Обрабатывает данные о запросах")
    UpdateRelStyle(handlers, api_services, $offsetX="-90", $offsetY="-30")
    Rel(handlers, telegram, "Обрабатывает команды пользователей")
    UpdateRelStyle(handlers, telegram, $offsetX="-80", $offsetY="30")

    UpdateLayoutConfig($c4ShapeInRow="1", $c4BoundaryInRow="3")
```

Диаграмма отображает внутреннюю структуру системы на уровне компонентов. Система разделена на два основных контейнера:
1. Контейнер Telegram-бота содержит логические блоки:

    - Обработчики — принимают callback-запросы и маршрутизируют их:
        - Handler: реагирует на вопросы пользователей;

    - Репозитории — получают и сохраняют данные в базу:
        - Database: сохраняет и извлекает информацию о пользователях Telegram;

    - Сервисы — вспомогательные компоненты, реализующие бизнес-логику:
        - ApiServices: Отвечает за обработку данных для отправления через API-ключ в сервис IO.NET.
        - ReminderServices: Отвечает за проверку и создание напоминаний, уведомлений о событиях.



2. Контейнер базы данных
    - MySQL3 — централизованное хранилище всех личных и глобальных данных пользователей.

Взаимодействие с внешними системами
- Telegram API — для отправки/получения сообщений и callback-запросов.
- IO.NET — предоставляет GPU для обработки промптов через API-ключ.