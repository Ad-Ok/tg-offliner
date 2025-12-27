# GitHub Copilot Instructions для проекта TG-Offliner

## ⚠️ КРИТИЧЕСКИ ВАЖНО: ЧИТАЙ ИНСТРУКЦИЮ В ПЕРВУЮ ОЧЕРЕДЬ!!!

**ПЕРЕД любым действием:**
1. 🔍 НАЙДИ инструкцию в этом файле для своей задачи
2. 📖 ПРОЧИТАЙ её полностью
3. ✅ ВЫПОЛНЯЙ точно по инструкции
4. 🚫 НЕ придумывай свои решения, если есть готовая инструкция!

**Примеры:**
- Работа с Docker → используй `docker compose`, НЕ `docker-compose`
- Подключение к Telegram → используй `telegram_client.py`, НЕ создавай новые клиенты
- API endpoints → смотри существующие blueprints в `api/`

---

## 🎯 О ПРОЕКТЕ

TG-Offliner — веб-приложение для загрузки и экспорта контента из Telegram каналов в HTML, PDF и IDML (InDesign).

**Основные возможности:**
- Загрузка сообщений из публичных/приватных каналов
- Экспорт в HTML/PDF/IDML форматы
- Управление медиа-файлами (фото, видео, аудио, документы)
- Отслеживание изменений постов (edit history)
- Галерейные макеты для медиа-контента
- Система скрытия постов без удаления
- Поддержка комментариев из discussion groups

---

## 📁 СТРУКТУРА ПРОЕКТА (КРИТИЧЕСКИ ВАЖНО!)

### Основная структура

```
tg-offliner/
├── app.py                      # Flask приложение, главный entry point
├── config.py                   # Конфигурация из .env
├── database.py                 # Инициализация SQLAlchemy
├── models.py                   # SQLAlchemy модели (Post, Channel, Edit, Layout, Page)
├── telegram_client.py          # Singleton клиент Telethon
├── telegram_export.py          # Логика импорта из Telegram
├── authorize_telegram.py       # Первичная авторизация
├── check_auth.py              # Проверка авторизации
├── .env                        # Credentials (НЕ в Git!)
├── session_name.session        # Telegram сессия (НЕ в Git!)
├── instance/                   # SQLite база данных
│   └── posts.db
├── downloads/                  # Скачанные медиа по каналам
│   └── {channel_id}/
│       ├── avatars/
│       ├── media/
│       └── thumbs/
├── api/                        # Flask blueprints
│   ├── channels.py            # Управление каналами
│   ├── posts.py               # CRUD постов
│   ├── downloads.py           # Загрузка из Telegram
│   ├── media.py               # Статика медиа-файлов
│   ├── edits.py               # История изменений
│   ├── layouts.py             # Gallery layouts
│   └── pages.py               # Управление страницами
├── message_processing/        # Обработка Telegram сообщений
│   ├── channel_info.py        # Метаданные канала
│   ├── message_transform.py   # Трансформация сообщений для API
│   ├── author.py              # Обработка авторов
│   └── polls.py               # Обработка опросов
├── utils/                     # Утилиты
│   ├── gallery_layout.py      # Генерация gallery макетов
│   ├── entity_validation.py   # Валидация Telegram entities
│   ├── text_format.py         # Форматирование текста
│   ├── date_utils.py          # Работа с датами
│   └── time_utils.py          # Работа со временем
├── idml_export/               # Экспорт в InDesign
│   ├── builder.py             # IDMLBuilder класс
│   ├── constants.py           # Размеры страниц, стили
│   ├── coordinates.py         # Координаты элементов
│   ├── styles.py              # XML стили
│   ├── resources.py           # Ресурсы (шрифты, графика)
│   └── templates/             # XML шаблоны
├── tests/                     # Тесты
└── tg-offliner-frontend/      # Nuxt.js фронтенд
    ├── nuxt.config.ts
    ├── package.json
    ├── app/
    │   ├── components/        # Vue компоненты
    │   ├── pages/             # Nuxt страницы
    │   ├── stores/            # Pinia хранилища
    │   ├── services/          # API клиенты
    │   └── composables/       # Vue composables
    └── public/                # Статика
```

---

## 🐳 DOCKER (КРИТИЧЕСКИ ВАЖНО!)

### Версии и команды

**ВСЕГДА используй `docker compose`, НЕ `docker-compose`!**
- Версия: Docker Compose v2
- ❌ НЕПРАВИЛЬНО: `docker-compose up`
- ✅ ПРАВИЛЬНО: `docker compose up`

### Сервисы

**`docker-compose.yml` определяет два сервиса:**

1. **app** (Flask backend):
   - Порт: `5000`
   - Volume: `.:/app`
   - Зависит от: `ssr`
   - Команда: `./start.sh` → `python app.py`

2. **ssr** (Nuxt.js frontend):
   - Порт: `3000`
   - Working dir: `/app`
   - Команда: `npm run dev`
   - Volume: `./tg-offliner-frontend:/app`

### Работа с Docker

```bash
# Запуск всех сервисов
cd /Users/adoknov/work/tg/tg-offliner
docker compose up --build

# Остановка
docker compose down

# Перезапуск одного сервиса
docker compose restart app
docker compose restart ssr

# Логи
docker compose logs -f app
docker compose logs -f ssr

# Exec в контейнер
docker compose exec app bash
docker compose exec ssr sh

# Авторизация Telegram (интерактивно)
docker compose run --rm app python authorize_telegram.py
```

**ВАЖНО:** Flask backend работает на порту 5000, Nuxt frontend на порту 3000. Frontend проксирует API запросы на backend через Nitro devProxy.

---

## 🗄️ БАЗА ДАННЫХ (КРИТИЧЕСКИ ВАЖНО!)

### SQLite

**База:** `instance/posts.db`  
**Engine:** SQLAlchemy + Flask-SQLAlchemy

### Credentials

**НЕ ВЫДУМЫВАЙ credentials!** База SQLite не требует пользователя/пароля.

```python
# database.py
SQLALCHEMY_DATABASE_URI = 'sqlite:///posts.db?check_same_thread=False'
```

### Модели (models.py)

#### Post (таблица: posts)
- `id` (Integer, PK, autoincrement)
- `telegram_id` (Integer, NOT NULL) - ID сообщения в Telegram
- `channel_id` (String, NOT NULL) - ID канала
- `date` (String, NOT NULL) - Дата публикации
- `message` (Text, nullable) - Текст сообщения
- `media_url` (String, nullable) - Путь к медиа
- `thumb_url` (String, nullable) - Путь к миниатюре
- `media_type` (String, nullable) - Тип медиа (photo, video, audio, document)
- `mime_type` (String, nullable) - MIME тип файла
- `author_name` (String, nullable) - Имя автора
- `author_avatar` (String, nullable) - Аватар автора
- `author_link` (String, nullable) - Ссылка на автора
- `repost_author_name`, `repost_author_avatar`, `repost_author_link` - Для репостов
- `reactions` (JSON, nullable) - Реакции на пост
- `grouped_id` (BigInteger, nullable) - ID медиа-группы (альбом)
- `reply_to` (Integer, nullable) - ID сообщения для ответа
- `print_settings` (JSON, nullable) - Настройки печати для поста

#### Channel (таблица: channels)
- `id` (String, PK) - ID канала (username или числовой ID)
- `name` (String, NOT NULL) - Название канала
- `avatar` (String, nullable) - Путь к аватару
- `description` (Text, nullable) - Описание
- `creation_date` (String, nullable) - Дата создания
- `subscribers` (String, nullable) - Количество подписчиков
- `posts_count` (Integer, nullable) - Количество постов
- `comments_count` (Integer, nullable) - Количество комментариев
- `discussion_group_id` (BigInteger, nullable) - ID discussion group
- `changes` (JSON, NOT NULL, default={}) - Изменения канала
- `print_settings` (JSON, nullable) - Глобальные настройки печати

#### Edit (таблица: edits)
- `id` (Integer, PK, autoincrement)
- `telegram_id` (Integer, NOT NULL) - ID сообщения
- `channel_id` (String, NOT NULL) - ID канала
- `date` (String, NOT NULL) - Дата редактирования
- `changes` (JSON, NOT NULL) - Изменения: `{"message": "...", "reactions": {...}, "hidden": "true"}`

#### Layout (таблица: layouts)
- `id` (Integer, PK, autoincrement)
- `grouped_id` (BigInteger, NOT NULL, unique) - ID медиа-группы
- `channel_id` (String, NOT NULL) - ID канала
- `json_data` (JSON, NOT NULL) - Данные layout

#### Page (таблица: pages)
- `id` (Integer, PK, autoincrement)
- `channel_id` (String, NOT NULL) - ID канала
- `json_data` (JSON, NOT NULL) - Данные сетки и содержимого

### Работа с базой

```python
# Подключение к базе
from models import db, Post, Channel, Edit, Layout, Page
from database import create_app, init_db

app = create_app()
init_db(app)

# Запросы
with app.app_context():
    # Получить все посты канала
    posts = Post.query.filter_by(channel_id='channel_id').all()
    
    # Получить канал
    channel = Channel.query.get('channel_id')
    
    # Получить историю изменений
    edits = Edit.query.filter_by(telegram_id=123, channel_id='channel_id').all()
    
    # Создать запись
    new_post = Post(telegram_id=123, channel_id='test', date='2025-12-25')
    db.session.add(new_post)
    db.session.commit()
```

---

## 📡 TELEGRAM API (КРИТИЧЕСКИ ВАЖНО!)

### Credentials

**НЕ ВЫДУМЫВАЙ credentials! Всегда бери из `.env`:**

```bash
# .env
API_ID=1234567
API_HASH=your_api_hash
PHONE=+1234567890
```

### Авторизация

**Первичная авторизация (один раз):**
```bash
docker compose run --rm app python authorize_telegram.py
```

После авторизации создается `session_name.session` - **НЕ коммитить в Git!**

**Проверка авторизации:**
```bash
python check_auth.py
```

### Telethon клиент

**ВСЕГДА используй `telegram_client.py`, НЕ создавай новые клиенты!**

```python
from telegram_client import connect_to_telegram

# Получить существующий клиент (singleton)
client = connect_to_telegram()

# Использовать для запросов
entity = await client.get_entity('channel_username')
messages = await client.get_messages(entity, limit=100)
```

**НЕ делай так:**
```python
# ❌ НЕПРАВИЛЬНО - создание нового клиента
client = TelegramClient('new_session', api_id, api_hash)
```

---

## 🌐 API ENDPOINTS

### Blueprints

API разбит на blueprints в папке `api/`:

#### channels.py (`/api/*`)
- `GET /api/channels` - Список каналов
- `POST /api/channels` - Добавить канал в БД
- `GET /api/channels/<channel_id>` - Получить канал
- `PUT /api/channels/<channel_id>` - Обновить канал
- `DELETE /api/channels/<channel_id>` - Удалить канал
- `GET /api/channels/<channel_id>/preview` - Предпросмотр канала
- `GET /api/channels/<channel_id>/export` - Экспорт в HTML
- `GET /api/channels/<channel_id>/export-pdf` - Экспорт в PDF
- `GET /api/channels/<channel_id>/export-idml` - Экспорт в IDML

#### posts.py (`/api/*`)
- `GET /api/posts/<channel_id>` - Посты канала
- `GET /api/posts/<channel_id>/<telegram_id>` - Получить пост
- `PUT /api/posts/<channel_id>/<telegram_id>` - Обновить пост
- `DELETE /api/posts/<channel_id>/<telegram_id>` - Удалить пост
- `POST /api/posts/<channel_id>/<telegram_id>/hide` - Скрыть пост
- `POST /api/posts/<channel_id>/<telegram_id>/unhide` - Показать пост

#### downloads.py (`/api/*`)
- `POST /api/download/import` - Импорт канала
- `POST /api/download/stop/<channel_id>` - Остановить загрузку
- `GET /api/download/status/<channel_id>` - Статус загрузки
- `POST /api/download/progress/<channel_id>` - Обновить прогресс

#### edits.py (`/api/*`)
- `GET /api/edits/<channel_id>/<telegram_id>` - История изменений поста
- `GET /api/edits/all` - Все изменения

#### layouts.py (`/api/*`)
- `GET /api/layouts/<grouped_id>` - Получить layout
- `POST /api/layouts/<grouped_id>` - Сохранить layout
- `PUT /api/layouts/<grouped_id>` - Обновить layout
- `DELETE /api/layouts/<grouped_id>` - Удалить layout

#### pages.py (`/api/*`)
- `GET /api/pages/<channel_id>` - Получить страницы канала
- `POST /api/pages/<channel_id>` - Создать страницу
- `PUT /api/pages/<channel_id>/<page_id>` - Обновить страницу
- `DELETE /api/pages/<channel_id>/<page_id>` - Удалить страницу

#### media.py (без префикса)
- `GET /media/<path:filename>` - Статика медиа
- `GET /downloads/<path:filepath>` - Статика downloads

---

## 📦 КОНФИГУРАЦИЯ (config.py)

### Переменные окружения

**Файл:** `.env` (НЕ в Git!)

```bash
# Telegram API
API_ID=1234567
API_HASH=your_api_hash
PHONE=+1234567890

# Настройки экспорта (опционально)
OUTPUT_DIR=telegram_export
```

### EXPORT_SETTINGS

```python
EXPORT_SETTINGS = {
    "include_system_messages": False,      # Системные сообщения
    "include_reposts": True,               # Репосты/форварды
    "include_polls": True,                 # Опросы
    "include_discussion_comments": True,   # Комментарии из discussion group
    "message_limit": None,                 # None = без лимита, или число
    "comments_search_limit": 1000,         # Лимит поиска комментариев
    "comments_forward_search_limit": 500   # Лимит поиска форвардов
}
```

---

## 📂 МЕДИА-ФАЙЛЫ

### Структура папок

```
downloads/
└── {channel_id}/          # ID канала (username или channel_123456)
    ├── avatars/           # Аватары пользователей/канала
    ├── media/             # Медиа-файлы (фото, видео, аудио, документы)
    │   └── {telegram_id}_media.{ext}
    └── thumbs/            # Миниатюры
        └── {telegram_id}_thumb.{ext}
```

**Примеры:**
- Фото: `downloads/llamasass/media/15_media.jpg`
- Аудио: `downloads/channel_2030815660/media/1749_media.oga`
- Миниатюра: `downloads/llamasass/thumbs/15_thumb.jpg`

### Типы медиа

**media_type:**
- `photo` - Фотографии
- `video` - Видео
- `audio` - Аудио файлы
- `voice` - Голосовые сообщения
- `document` - Документы, файлы

**mime_type:**
- `image/jpeg`, `image/png`, `image/webp`
- `video/mp4`, `video/webm`
- `audio/mpeg`, `audio/ogg`
- `application/pdf`, `application/zip`, и т.д.

---

## 🎨 FRONTEND (Nuxt.js)

### Структура

**Папка:** `tg-offliner-frontend/`

**Технологии:**
- **Nuxt 4.0** (Vue 3.5 + Vite)
- **Pinia** (state management)
- **Tailwind CSS** + **DaisyUI**
- **@fancyapps/ui** (lightbox для галерей)
- **vue-grid-layout-v3** (drag & drop сетки)
- **@tanstack/vue-virtual** (виртуализация длинных списков)

### Основные компоненты

- `ChannelCover.vue` - Обложка канала
- `Group.vue` - Группа постов
- Другие компоненты в `app/components/`

### Stores (Pinia)

**НЕ создавай дубликаты stores!** Используй существующие в `app/stores/`.

### Services

API клиенты в `app/services/` - используй их для запросов к backend.

### Tailwind конфигурация

**ДВА конфига:**
1. `tailwind.config.js` - Для основного UI
2. `tailwind.pdf.config.js` - Для PDF экспорта

**ДВА CSS файла:**
1. `public/styles.css` - Из основного конфига
2. `public/styles-pdf.css` - Из PDF конфига

**Команды:**
```bash
npm run watch:tailwindcss    # Следить за изменениями основного CSS
npm run watch:pdf-css        # Следить за изменениями PDF CSS
npm run build:tailwindcss    # Собрать основной CSS
npm run build:pdf-css        # Собрать PDF CSS
```

---

## 📄 IDML ЭКСПОРТ (InDesign)

### Модуль idml_export/

**Основной класс:** `IDMLBuilder` в `builder.py`

### Архитектура экспорта (ВАЖНО!)

**Новый подход: HTML → Layout → IDML**

```
1. Генерация HTML preview для печати (с PDF CSS)
   ↓
2. WeasyPrint рендерит документ и извлекает координаты элементов
   ↓
3. Сохранение layout.json с координатами всех блоков
   ↓
4. IDMLBuilder создает IDML на основе точных координат
```

**Почему так:**
- ✅ Переиспользуем существующую HTML структуру
- ✅ Автоматическая пагинация через CSS (@page, page-break)
- ✅ Точные координаты из браузерного рендера
- ✅ Один источник правды для preview/PDF/IDML

### API Endpoints

- `GET /api/channels/<channel_id>/extract-layout` - Извлечь координаты элементов
- `GET /api/channels/<channel_id>/export-idml` - Экспорт в IDML
- `GET /api/channels/<channel_id>/print` - Экспорт в PDF (с извлечением layout)

### Извлечение Layout

**Функция:** `extract_layout_from_document(document, channel_id)` в `api/channels.py`

**Что делает:**
1. Обходит все boxes в WeasyPrint Document
2. Извлекает координаты (x, y, width, height)
3. Определяет номер страницы
4. Группирует элементы по постам (data-telegram-id)
5. Сохраняет в JSON формате

**Формат layout.json:**
```json
{
  "channel_id": "llamasass",
  "pages": [
    {
      "number": 0,
      "width": 595.28,
      "height": 841.89,
      "elements": [
        {
          "tag": "div",
          "classes": ["post"],
          "data-telegram-id": "123",
          "x": 50.0,
          "y": 100.0,
          "width": 495.28,
          "height": 200.0,
          "page": 0
        }
      ]
    }
  ],
  "posts": [
    {
      "telegram_id": "123",
      "elements": [...]
    }
  ]
}
```

### Использование

**Вариант 1: Через API (с автоматическим извлечением)**
```bash
# Извлечь layout
GET /api/channels/llamasass/extract-layout

# Экспортировать IDML (использует layout)
GET /api/channels/llamasass/export-idml
```

**Вариант 2: Программно**

```python
from idml_export.builder import IDMLBuilder
from models import Channel, Post

# Получаем канал
channel = Channel.query.get('channel_id')
print_settings = channel.print_settings or {}

# Создаем builder
builder = IDMLBuilder(channel, print_settings)
builder.create_document()

# Добавляем посты
posts = Post.query.filter_by(channel_id=channel.id).all()
for post in posts:
    builder.add_post(post, downloads_dir='downloads')

# Сохраняем
builder.save('output.idml')
```

### Настройки печати

**Channel.print_settings (глобальные):**
```json
{
  "page_size": "A4",
  "margins": [56.69, 56.69, 56.69, 56.69],
  "text_columns": 1,
  "column_gutter": 14.17,
  "master_page_enabled": true,
  "include_headers_footers": true
}
```

**Post.print_settings (индивидуальные):**
```json
{
  "text_columns": 2,
  "image_placement": "above_text",
  "page_break_before": false,
  "keep_with_next": false
}
```

### Размеры страниц

**constants.py:**
```python
PAGE_SIZES = {
    'A4': (595.28, 841.89),          # 210 × 297 мм
    'A3': (841.89, 1190.55),         # 297 × 420 мм
    'USLetter': (612, 792),          # 8.5 × 11 дюймов
    'Tabloid': (792, 1224)           # 11 × 17 дюймов
}
```

### Стили параграфов

- `PostHeader` - Автор и дата
- `PostBody` - Основной текст
- `PostCaption` - Подписи к медиа
- `PostQuote` - Цитаты

---

## 🧪 ТЕСТЫ

### Структура tests/

```
tests/
├── test_telegram_export_unit.py        # Unit тесты
├── test_telegram_export_integration.py # Integration тесты
├── test_telegram_export_gallery.py     # Тесты gallery layout
├── test_message_transform_helpers.py   # Тесты обработки сообщений
├── test_api_layouts.py                 # Тесты API layouts
├── test_api_edits.py                   # Тесты API edits
└── _telegram_export_base.py            # Базовый класс для тестов
```

### Запуск тестов

```bash
# Все тесты
python -m pytest tests/

# Конкретный файл
python -m pytest tests/test_telegram_export_unit.py

# С выводом
python -m pytest tests/ -v

# Из run_tests.py
cd tests
python run_tests.py
```

---

## 🔧 УТИЛИТЫ (utils/)

### gallery_layout.py
**Функция:** `generate_gallery_layout(images)`
- Генерирует оптимальные layout'ы для галерей
- Вход: список изображений с размерами
- Выход: JSON с координатами и размерами

### entity_validation.py
**Функции:**
- `get_entity_by_username_or_id(client, identifier)` - Получить Telegram entity
- `validate_entity_for_download(entity, identifier)` - Валидация для загрузки

### text_format.py
- Форматирование Telegram текста (жирный, курсив, код, ссылки)

### date_utils.py, time_utils.py
- Работа с датами и временем
- Форматирование в разных форматах

---

## 📥 ИМПОРТ ИЗ TELEGRAM

### Основной модуль: telegram_export.py

**Главная функция:** `import_channel_direct(channel_username, channel_id=None, export_settings=None)`

**Что делает:**
1. Подключается к Telegram через `telegram_client.py`
2. Получает entity (канал или пользователь)
3. Валидирует entity
4. Скачивает сообщения и медиа
5. Сохраняет в БД через `process_message_for_api()`
6. Обновляет прогресс через API

**Прогресс-трекинг:**
```python
def update_import_progress(channel_id, processed_posts, processed_comments, total_posts=None):
    """Обновляет прогресс импорта через POST /api/download/progress/{channel_id}"""
    
def should_stop_import(channel_id):
    """Проверяет через GET /api/download/status/{channel_id} нужно ли остановить"""
```

### message_processing/

#### message_transform.py
**Функция:** `process_message_for_api(client, message, channel_id, entity, ...)`
- Преобразует Telethon Message в структуру для БД
- Скачивает медиа
- Извлекает metadata (автор, реакции, и т.д.)
- Возвращает словарь для Post модели

#### author.py
- Извлечение информации об авторе сообщения
- Обработка репостов/форвардов

#### channel_info.py
**Функция:** `get_channel_info(client, entity)`
- Получает метаданные канала (название, описание, подписчики, и т.д.)
- Возвращает словарь для Channel модели

#### polls.py
- Обработка опросов из Telegram

---

## ⚡ ЧАСТЫЕ ОШИБКИ И КАК ИХ ИЗБЕЖАТЬ

### ❌ НЕ делай так:

1. **Docker:**
   - ❌ `docker-compose up` → ✅ `docker compose up`

2. **Telegram клиент:**
   - ❌ Создавать новый TelegramClient → ✅ Использовать `connect_to_telegram()`
   - ❌ Выдумывать API_ID/API_HASH → ✅ Читать из `.env`

3. **База данных:**
   - ❌ Выдумывать имена таблиц → ✅ Использовать модели из `models.py`
   - ❌ Прямые SQL запросы → ✅ Использовать SQLAlchemy ORM

4. **API:**
   - ❌ Создавать дубликаты endpoints → ✅ Проверять существующие blueprints
   - ❌ Выдумывать URL схемы → ✅ Смотреть в `api/*.py`

5. **Пути:**
   - ❌ Хардкодить пути → ✅ Использовать `DOWNLOADS_DIR`, `os.path.join()`
   - ❌ Выдумывать структуру папок → ✅ Следовать `downloads/{channel_id}/{avatars|media|thumbs}/`

6. **Frontend:**
   - ❌ Создавать дубликаты stores/services → ✅ Использовать существующие
   - ❌ Забывать про два Tailwind конфига → ✅ Помнить о `tailwind.config.js` и `tailwind.pdf.config.js`

### ✅ ВСЕГДА делай так:

1. **Перед работой с Docker:**
   ```bash
   cd /Users/adoknov/work/tg/tg-offliner
   docker compose up
   ```

2. **Для Telegram клиента:**
   ```python
   from telegram_client import connect_to_telegram
   client = connect_to_telegram()
   ```

3. **Для работы с БД:**
   ```python
   from models import db, Post, Channel, Edit, Layout, Page
   from database import create_app
   
   app = create_app()
   with app.app_context():
       posts = Post.query.filter_by(channel_id='id').all()
   ```

4. **Для API endpoints:**
   - Проверь существующие blueprints в `api/`
   - Используй те же URL схемы и форматы ответов

5. **Для путей к медиа:**
   ```python
   from message_processing.message_transform import DOWNLOADS_DIR, get_channel_folder
   
   channel_folder = get_channel_folder(channel_id)
   media_path = os.path.join(channel_folder, 'media', f'{telegram_id}_media.jpg')
   ```

---

## 🚀 БЫСТРЫЙ СТАРТ

### Первый запуск

```bash
# 1. Клонировать и перейти в папку
cd /Users/adoknov/work/tg/tg-offliner

# 2. Создать .env из примера
cp example.env .env
# Заполнить API_ID, API_HASH, PHONE

# 3. Авторизоваться в Telegram
docker compose run --rm app python authorize_telegram.py

# 4. Запустить приложение
docker compose up --build

# 5. Открыть браузер
# Frontend: http://localhost:3000
# Backend: http://localhost:5000
```

### Разработка

```bash
# Запуск в dev режиме
docker compose up

# Логи
docker compose logs -f app
docker compose logs -f ssr

# Перезапуск после изменений
docker compose restart app

# Остановка
docker compose down
```

### Frontend разработка

```bash
cd tg-offliner-frontend

# Установка зависимостей
npm install

# Dev режим (с watch CSS)
npm run dev

# Только watch Tailwind
npm run watch:tailwindcss
npm run watch:pdf-css

# Build
npm run build
```

---

## 📚 ДОКУМЕНТАЦИЯ

### Python зависимости (requirements.txt)

**Ключевые:**
- `flask` - Web framework
- `flask-sqlalchemy` - ORM
- `flask-cors` - CORS поддержка
- `Telethon==1.42.0` - Telegram client
- `weasyprint==66.0` - PDF generation
- `beautifulsoup4==4.13.3` - HTML parsing
- `Pillow==10.0.1` - Image processing
- `python-dotenv==1.1.0` - .env файлы
- `requests` - HTTP запросы

### Node.js зависимости (package.json)

**Ключевые:**
- `nuxt: ^4.0.0` - Framework
- `vue: ^3.5.17` - UI library
- `pinia: ^3.0.3` - State management
- `@fancyapps/ui: ^6.0.34` - Lightbox
- `vue-grid-layout-v3: ^3.1.2` - Drag & drop сетки
- `tailwindcss: ^3.4.17` - CSS framework
- `daisyui: ^5.0.50` - UI компоненты

---

## 🔐 БЕЗОПАСНОСТЬ

### Что НЕ должно попасть в Git

- `.env` файл с credentials
- `session_name.session` - Telegram сессия
- `instance/posts.db` - База данных
- `downloads/` - Медиа-файлы
- `server.log` - Логи
- `__pycache__/`, `*.pyc` - Python cache
- `node_modules/` - Node зависимости

### Что коммитить

- Код Python/JavaScript/Vue
- Docker конфигурация
- Примеры (example.env)
- Документация (README.md)
- Тесты

---

## 📞 КОНТАКТЫ И ВОПРОСЫ

Если что-то непонятно или не уверен в правильности действий:
1. Проверь этот файл инструкций
2. Проверь README.md в корне и idml_export/README.md
3. Проверь существующий код в соответствующих модулях
4. Спроси у разработчика

**НЕ ИМПРОВИЗИРУЙ с критическими компонентами (Docker, Telegram API, база данных)!**

---

## 🎯 ПРАВИЛА РАБОТЫ

1. **НЕ ВЫДУМЫВАЙ:**
   - Credentials (читай из .env)
   - API endpoints (проверяй blueprints)
   - Структуру БД (используй models.py)
   - Пути к файлам (используй константы)

2. **ВСЕГДА ПРОВЕРЯЙ:**
   - Существующие модули перед созданием новых
   - Документацию (README.md)
   - Существующий код как примеры

3. **ИСПОЛЬЗУЙ ПРАВИЛЬНЫЕ КОМАНДЫ:**
   - `docker compose` вместо `docker-compose`
   - `connect_to_telegram()` вместо нового клиента
   - SQLAlchemy ORM вместо прямого SQL

4. **ПОМНИ О СТРУКТУРЕ:**
   - Backend (Flask) на порту 5000
   - Frontend (Nuxt) на порту 3000
   - Два Tailwind конфига для UI и PDF
   - Медиа в `downloads/{channel_id}/`

5. **БЕЗОПАСНОСТЬ:**
   - Никогда не коммить credentials
   - Никогда не коммить session файлы
   - Всегда проверять .gitignore

---

## ❓ ЧАСТЫЕ ВОПРОСЫ (FAQ)

### Как добавить новый API endpoint?

1. Открой соответствующий blueprint в `api/`
2. Добавь новый route декоратор
3. Регистрация blueprint уже есть в `app.py`
4. Не забудь обновить frontend service

### Как изменить настройки экспорта?

Открой `config.py` и измени `EXPORT_SETTINGS`.

### Как добавить новое поле в модель?

1. Открой `models.py`
2. Добавь поле в соответствующий класс
3. Удали `instance/posts.db`
4. Перезапусти app - база пересоздастся

### Почему не работает авторизация Telegram?

1. Проверь `.env` файл (API_ID, API_HASH, PHONE)
2. Запусти `docker compose run --rm app python authorize_telegram.py`
3. Введи код из Telegram
4. Проверь создался ли `session_name.session`

### Как очистить кеш и пересобрать?

```bash
docker compose down
docker compose build --no-cache
docker compose up
```

### Как обновить frontend зависимости?

```bash
cd tg-offliner-frontend
npm install
docker compose restart ssr
```

---

**Версия инструкций:** 1.0  
**Дата:** 25 декабря 2025
