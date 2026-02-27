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
- **Изменил Python код → ПЕРЕЗАПУСТИ Flask: `docker compose restart app`**

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
├── database.py                 # Инициализация SQLAlchemy (принимает database_uri)
├── models.py                   # SQLAlchemy модели (Post, Channel, Edit, Layout, Page)
├── telegram_client.py          # Singleton клиент Telethon
├── telegram_export.py          # Логика импорта из Telegram
├── authorize_telegram.py       # Первичная авторизация
├── check_auth.py              # Проверка авторизации
├── start.sh                    # Entrypoint: автобэкап → авторизация → запуск Flask
├── print-config.json           # ⭐ ЕДИНЫЙ ИСТОЧНИК настроек печати (Python + JS)
├── .env                        # Credentials (НЕ в Git!)
├── session_name.session        # Telegram сессия (НЕ в Git!)
├── instance/                   # SQLite база данных
│   ├── posts.db
│   └── backups/               # 💾 Бэкапы БД (автоматические и ручные)
├── downloads/                  # Скачанные медиа по каналам
│   └── {channel_id}/
│       ├── avatars/
│       ├── media/
│       └── thumbs/
├── api/                        # Flask blueprints (v1)
│   ├── channels.py            # Управление каналами + экспорт
│   ├── posts.py               # CRUD постов
│   ├── downloads.py           # Импорт из Telegram, статусы
│   ├── media.py               # Статика медиа-файлов
│   ├── edits.py               # История изменений
│   ├── layouts.py             # Gallery layouts
│   ├── pages.py               # Управление страницами
│   ├── chunks.py              # Чанки/пагинация контента
│   ├── backup.py              # 💾 Бэкапы базы данных
│   └── v2/                    # ⭐ API v2 — унифицированные endpoints
│       ├── __init__.py        # Регистрация v2 blueprint
│       ├── channels.py        # Посты, настройки, чанки
│       ├── posts.py           # Видимость постов
│       ├── layouts.py         # Gallery layouts
│       └── serializers.py     # Сериализация, настройки, resolve_param
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
│   ├── time_utils.py          # Работа со временем
│   ├── chunking.py            # ⭐ Система чанков: build_content_units, calculate_chunks
│   ├── import_state.py        # Потокобезопасное состояние импорта
│   ├── post_filtering.py      # Фильтрация постов (скрытие медиа/постов)
│   └── backup.py              # 💾 Утилиты бэкапов БД
├── idml_export/               # Экспорт в InDesign
│   ├── builder.py             # IDMLBuilder класс
│   ├── constants.py           # Загружает из print-config.json
│   ├── coordinates.py         # Координаты элементов
│   ├── styles.py              # XML стили
│   ├── resources.py           # Ресурсы (шрифты, графика)
│   └── templates/             # XML шаблоны
├── tests/                     # Тесты (pytest)
└── tg-offliner-frontend/      # Nuxt.js фронтенд
    ├── nuxt.config.ts
    ├── package.json
    ├── tailwind.config.js     # Tailwind для основного UI
    ├── tailwind.pdf.config.js # Tailwind для PDF экспорта
    ├── app/
    │   ├── components/        # Vue компоненты
    │   ├── pages/             # Nuxt страницы (file-based routing)
    │   ├── stores/            # Pinia хранилища
    │   ├── services/          # ⭐ API клиенты (api.js, apiV2.js, dateService.js)
    │   ├── utils/
    │   │   └── units.js       # ⭐ Загружает из print-config.json
    │   └── composables/       # Vue composables
    ├── assets/
    │   └── tailwind.css       # ⭐ ИСХОДНЫЙ файл стилей (редактировать ТОЛЬКО его!)
    └── public/                # Статика (styles.css, styles-pdf.css — НЕ ТРОГАТЬ!)
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

### ⚠️ КРИТИЧЕСКИ ВАЖНО: Перезагрузка после изменений кода

**После изменения Python кода (backend) ВСЕГДА перезапускай Flask контейнер!**

```bash
# После изменения любых Python файлов
docker compose restart app

# Проверь, что контейнер запустился
docker compose ps

# Проверь логи на ошибки
docker compose logs app
```

**Почему это важно:**
- Flask не перезагружается автоматически в Docker (нет hot-reload)
- Старый код остается в памяти контейнера
- Импорт канала будет использовать старую версию кода
- Изменения в `utils/`, `message_processing/`, `api/` не применятся без перезапуска

**Симптомы, что нужна перезагрузка:**
- ❌ Новые функции не работают
- ❌ Изменения в логике обработки не применяются
- ❌ Debug логи не появляются
- ❌ Исправленные баги все еще воспроизводятся

**Frontend (Nuxt) имеет hot-reload** - изменения применяются автоматически, перезагрузка не нужна.

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

**`create_app(database_uri=None)`** — принимает опциональный URI. Если передан — использует его, иначе подключается к реальной `instance/posts.db`. Это критично для тестов: **ВСЕГДА передавай `database_uri='sqlite:///:memory:'` в тестах!**

### ⚠️ Доступ к БД из терминала (КРИТИЧЕСКИ ВАЖНО!)

**НЕ используй `create_app()` / `init_db()` для чтения данных!** Это может создать пустую БД или перезаписать данные.

**✅ ПРАВИЛЬНО — прямой доступ через sqlite3:**
```bash
# С хоста (macOS)
python3 -c '
import sqlite3
conn = sqlite3.connect("instance/posts.db")
c = conn.cursor()
c.execute("SELECT id, name FROM channels")
print(c.fetchall())
'

# Из Docker контейнера
docker compose exec app python3 -c '
import sqlite3
conn = sqlite3.connect("instance/posts.db")
c = conn.cursor()
c.execute("SELECT id, name FROM channels")
print(c.fetchall())
'
```

**❌ НЕПРАВИЛЬНО — Flask app context для простых запросов:**
```python
# НЕ ДЕЛАЙ ТАК для проверки данных!
app = create_app()
init_db(app)  # ← может создать пустые таблицы!
with app.app_context():
    channels = Channel.query.all()  # ← может смотреть не туда
```

Flask `create_app()` + `init_db()` нужны только в коде приложения, НЕ для ad-hoc запросов из терминала.

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

### 🧪 Тестовый канал

**Канал для тестирования:** `llamatest` (username в Telegram)
- Discussion group ID: `2573960761`
- Содержит ~80 постов с комментариями, медиа-группами (альбомами), gallery layouts
- Медиа скачано в `downloads/llamatest/`
- **Используй для тестирования функциональности без импорта новых каналов**

**Проверка наличия данных:**
```bash
# Быстрая проверка БД
python3 -c 'import sqlite3; c = sqlite3.connect("instance/posts.db").cursor(); c.execute("SELECT id, name FROM channels"); print(c.fetchall())'
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

### Регистрация blueprints (app.py)

```python
app.register_blueprint(posts_bp,      url_prefix='/api')
app.register_blueprint(channels_bp,   url_prefix='/api')
app.register_blueprint(downloads_bp,  url_prefix='/api')
app.register_blueprint(media_bp)                         # без префикса
app.register_blueprint(edits_bp)                         # без префикса (routes содержат /api)
app.register_blueprint(layouts_bp,    url_prefix='/api')
app.register_blueprint(pages_bp,      url_prefix='/api')
app.register_blueprint(chunks_bp,     url_prefix='/api')
app.register_blueprint(backup_bp,     url_prefix='/api')
app.register_blueprint(api_v2_bp)                        # /api/v2 (в __init__.py)
```

### API v1 Blueprints

#### channels.py (`url_prefix='/api'`)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/channels` | Список каналов |
| `POST` | `/api/channels` | Добавить канал в БД |
| `POST` | `/api/add_channel` | Импорт канала из Telegram (202 Accepted, 409 если уже идёт, auto-resume) |
| `GET` | `/api/channels/<channel_id>` | Получить канал |
| `PUT` | `/api/channels/<channel_id>` | Обновить канал |
| `DELETE` | `/api/channels/<channel_id>` | Удалить канал |
| `GET` | `/api/channel_preview` | SSR HTML preview |
| `GET` | `/api/channels/<channel_id>/export-html` | Экспорт в HTML |
| `GET` | `/api/channels/<channel_id>/print` | Экспорт в PDF |
| `GET` | `/api/channels/<channel_id>/export-idml` | Экспорт в IDML |
| `GET` | `/api/channels/<channel_id>/extract-layout` | Извлечь координаты |

#### posts.py (`url_prefix='/api'`)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/posts` | Посты канала (query: `channel_id`) |
| `GET` | `/api/posts/check` | Проверка существования поста |
| `POST` | `/api/posts` | Создать пост |
| `DELETE` | `/api/posts` | Удалить пост |

#### downloads.py (`url_prefix='/api'`)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/download/status` | Все статусы загрузок |
| `GET` | `/api/download/status/<channel_id>` | Статус загрузки канала |
| `POST` | `/api/download/progress/<channel_id>` | Обновить прогресс |
| `POST` | `/api/download/stop/<channel_id>` | Остановить загрузку |
| `POST` | `/api/download/cancel/<channel_id>` | Отменить и очистить |
| `POST` | `/api/download/clear/<channel_id>` | Очистить статус |

#### edits.py (без `url_prefix`, пути содержат `/api`)
| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/api/edits` | Создать/обновить редакцию |
| `GET` | `/api/edits/<telegram_id>/<channel_id>` | История изменений поста |
| `GET` | `/api/edits` | Все изменения |
| `GET` | `/api/edits/<channel_id>` | Изменения канала |
| `DELETE` | `/api/edits/<channel_id>` | Удалить изменения канала |

#### layouts.py (`url_prefix='/api'`)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/layouts/<grouped_id>` | Получить layout |
| `POST` | `/api/layouts/<grouped_id>/reload` | Перегенерировать layout |
| `PATCH` | `/api/layouts/<grouped_id>/border` | Обновить толщину рамки |

#### pages.py (`url_prefix='/api'`)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/pages` | Страницы (query: `channel_id`) |
| `GET` | `/api/pages/<page_id>` | Получить страницу |
| `POST` | `/api/pages` | Создать страницу |
| `PUT` | `/api/pages/<page_id>` | Обновить страницу |
| `DELETE` | `/api/pages/<page_id>` | Удалить страницу |
| `POST` | `/api/pages/<channel_id>` | Создать frozen layout |
| `GET` | `/api/pages/<channel_id>/frozen` | Получить frozen страницы |

#### chunks.py (`url_prefix='/api'`)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/chunks/<channel_id>` | Метаданные чанков |
| `GET` | `/api/chunks/<channel_id>/<chunk_index>/posts` | Посты в чанке |

#### backup.py (`url_prefix='/api'`)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/backups` | Список бэкапов |
| `POST` | `/api/backups` | Создать бэкап |
| `POST` | `/api/backups/<name>/restore` | Восстановить из бэкапа |
| `DELETE` | `/api/backups/<name>` | Удалить бэкап |

#### media.py (без префикса)
| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/media/<path:filename>` | Статика медиа |
| `GET` | `/downloads/<path:filename>` | Статика downloads |

### ⭐ API v2 (`/api/v2`)

**Новые унифицированные endpoints** — используют сериализаторы, include_hidden, встроенные layouts.

| Метод | Путь | Описание |
|-------|------|----------|
| `GET` | `/api/v2/channels/<channel_id>/posts` | Посты с полной информацией (layouts, hidden, comments) |
| `PUT` | `/api/v2/channels/<channel_id>/settings` | Обновить display/export настройки |
| `GET` | `/api/v2/channels/<channel_id>/chunks` | Метаданные чанков для навигации |
| `POST` | `/api/v2/posts/<channel_id>/<telegram_id>/visibility` | Скрыть/показать пост |
| `GET` | `/api/v2/layouts/<grouped_id>` | Получить gallery layout |
| `PUT` | `/api/v2/layouts/<grouped_id>` | Обновить/перегенерировать layout |

**V2 сериализаторы** (`api/v2/serializers.py`):
- `serialize_post_full()` — пост с `is_hidden`, `layout`, `group_posts`, `comments`
- `serialize_channel()` — канал с merged `settings`
- `get_channel_settings(channel)` — читает из `settings` / fallback `changes` + `print_settings`
- `resolve_param(url, saved, default)` → `(value, source)` — приоритет: URL > Saved > Default
- `get_hidden_posts_map(channel_id)` — единый запрос для скрытых постов
- `get_layouts_map(channel_id)` — единый запрос для всех layouts

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

### ⭐ API сервисы (КРИТИЧЕСКИ ВАЖНО!)

**Файлы:** `app/services/api.js`, `app/services/apiV2.js`, `app/services/dateService.js`

#### apiBase / mediaBase — разные URL для SSR и браузера

```javascript
// app/services/api.js

// apiBase: используется для всех fetch() запросов к Flask
export const apiBase =
  typeof window === 'undefined'
    ? 'http://app:5000'       // SSR: Docker-внутренний hostname контейнера app
    : 'http://localhost:5000'; // Браузер: пробрасываемый порт

// mediaBase: используется для <img src>, <video src> и т.д.
export const mediaBase =
  typeof window !== 'undefined'
    ? 'http://localhost:5000'  // Браузер: всегда localhost
    : isPdfSsr()
      ? 'http://app:5000'     // SSR + PDF: WeasyPrint ходит внутри Docker
      : 'http://localhost:5000'; // SSR обычный: img загружаются браузером
```

**Почему:**
- Nuxt SSR-сервер (`ssr` контейнер) при серверном рендере ходит к Flask по Docker-сети → `http://app:5000`
- Браузер пользователя ходит к Flask через проброс порта → `http://localhost:5000`
- medialBase для PDF-рендера (WeasyPrint) использует Docker-сеть, т.к. он тоже внутри Docker

#### api — HTTP клиент (v1)

```javascript
import { api, apiBase, mediaBase } from '~/services/api'

// Методы: get, post, put, patch, delete
// Возвращают Promise<{ data }>
const { data } = await api.get('/api/channels')
await api.post('/api/posts', { channel_id: 'test', ... })
await api.put('/api/channels/test', { name: 'New Name' })
await api.delete('/api/posts', { body: ... })
```

#### apiV2 — клиент для v2 endpoints

```javascript
import apiV2 from '~/services/apiV2'
// или импорт отдельных функций:
import { getChannelPosts, getChannelChunks, updateChannelSettings, setPostVisibility, updateLayout } from '~/services/apiV2'

// Посты с полной информацией (layouts, hidden, comments)
const data = await getChannelPosts(channelId, { chunk, sort_order, include_hidden })

// Метаданные чанков для навигации
const chunks = await getChannelChunks(channelId, { sort_order, include_hidden })

// Обновить настройки отображения/экспорта
await updateChannelSettings(channelId, { display: { sort_order: 'asc' } })

// Скрыть/показать пост
await setPostVisibility(channelId, telegramId, true)

// Обновить gallery layout
await updateLayout(groupedId, { action: 'regenerate' })
```

**❌ НЕ создавай новых fetch-обёрток!** Используй `api` из `api.js` или `apiV2` из `apiV2.js`.
**❌ НЕ хардкодь URL!** Используй `apiBase` / `mediaBase`.

### Страницы (file-based routing)

| Файл | Маршрут | Описание |
|------|---------|----------|
| `pages/index.vue` | `/` | Главная — список каналов |
| `pages/backups.vue` | `/backups` | 💾 Управление бэкапами |
| `pages/[channelId]/posts.vue` | `/:channelId/posts` | Стена постов канала |
| `pages/[channelId]/pages.vue` | `/:channelId/pages` | Grid-страницы канала |
| `pages/preview/[channelId]/index.vue` | `/preview/:channelId` | Preview для экспорта |
| `pages/preview/[channelId]/frozen.vue` | `/preview/:channelId/frozen` | Frozen layout preview |

### Composables

| Файл | Экспорт | Описание |
|------|---------|----------|
| `useChannelPostsV2.js` | `useChannelPostsV2(channelId)` | **Основной**: посты, чанки, сортировка, навигация. Использует V2 API |
| `useConfirmDialog.js` | `useConfirmDialog()` | Модальные подтверждения |
| `useDisplayMode.js` | `useDisplayMode()` | `'default'` или `'minimal'` (preview) |
| `usePages.js` | `usePages()` | CRUD grid-страниц, blocksToLayout/layoutToBlocks |
| `usePostEdit.js` | `usePostEdit(post)` | Скрытие/показ постов через V2 API |
| `usePostFiltering.js` | `usePostFiltering()` | Фильтрация неподдерживаемых медиа |

### Компоненты

**Контент:**
`ChannelCover`, `ChunkNavigation`, `Group`, `PageBlock`, `Post`, `PostAuthor`, `PostBody`, `PostFooter`, `PostHeader`, `PostMedia`, `PostQuote`, `PostReactions`, `PrintUtilities`, `Wall`

**Системные** (`components/system/`):
`ChannelExports`, `ChannelsList`, `ConfirmDialog`, `DownloadStatus`, `GroupEditor`, `Navbar`, `Page`, `PageSkeleton`, `PostEditor`, `PrintSettingsSidebar`, `SystemAlert`

### Stores (Pinia)

**`editMode.ts`** — управление режимами редактирования, экспорта, preview.
- State: `isEditMode`, `isExportMode`, `isPreviewEditMode`
- Getters: `showDeleteButtons`, `isPostsPage`, `isPreviewPage`

**НЕ создавай дубликаты stores!** Используй существующие в `app/stores/`.

### Tailwind конфигурация (КРИТИЧЕСКИ ВАЖНО!)

**ДВА конфига:**
1. `tailwind.config.js` - Для основного UI
2. `tailwind.pdf.config.js` - Для PDF экспорта

**ИСХОДНЫЙ файл:** `assets/tailwind.css`
- Содержит `@tailwind` директивы и кастомные стили
- Содержит `@page` настройки для PDF
- **ТОЛЬКО ЭТОТ ФАЙЛ НУЖНО РЕДАКТИРОВАТЬ!**

**СГЕНЕРИРОВАННЫЕ файлы (НЕ ТРОГАТЬ!):**
1. `public/styles.css` - Генерируется из `assets/tailwind.css` + `tailwind.config.js`
2. `public/styles-pdf.css` - Генерируется из `assets/tailwind.css` + `tailwind.pdf.config.js`

**❌ НИКОГДА НЕ РЕДАКТИРУЙ:**
- `public/styles.css`
- `public/styles-pdf.css`

**✅ ВСЕГДА РЕДАКТИРУЙ:**
- `assets/tailwind.css` (исходник)
- Затем запускай сборку

**Команды сборки:**
```bash
# Локально (если есть node_modules)
npm run watch:tailwindcss    # Следить за изменениями основного CSS
npm run watch:pdf-css        # Следить за изменениями PDF CSS
npm run build:tailwindcss    # Собрать основной CSS
npm run build:pdf-css        # Собрать PDF CSS

# Внутри Docker контейнера (всегда работает)
docker compose exec ssr sh -c "cd /app && npm run build:pdf-css"
docker compose exec ssr sh -c "cd /app && npm run build:tailwindcss"
```

**Пример добавления кастомных стилов:**
```css
/* В assets/tailwind.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Кастомные стили для PDF */
@page {
  size: A4;
  margin: 20mm;
}

.custom-class {
  /* твои стили */
}
```

Затем:
```bash
docker compose exec ssr sh -c "cd /app && npm run build:pdf-css"
```

---

## 📄 IDML ЭКСПОРТ (InDesign)

**Основной класс:** `IDMLBuilder` в `builder.py`

### ⭐ ЕДИНИЦЫ ИЗМЕРЕНИЯ И КОНСТАНТЫ (КРИТИЧЕСКИ ВАЖНО!)

**ЕДИНЫЙ ИСТОЧНИК ПРАВДЫ:** `print-config.json` в корне проекта

```json
{
  "pageSizes": {
    "A4": { "width": 210, "height": 297 },  // в миллиметрах
    "A3": { "width": 297, "height": 420 }
  },
  "conversion": {
    "mmToPoints": 2.83465,      // 1mm = 2.83465 points (InDesign)
    "mmToPx": 3.7795275591      // 1mm = 3.7795... px (96 DPI)
  },
  "defaultPrintSettings": {
    "pageSize": "A4",
    "margins": [20, 20, 20, 20] // в миллиметрах
  }
}
```

**Кто читает:**
- **Python:** `idml_export/constants.py` → `json.load('print-config.json')`
- **JavaScript:** `app/utils/units.js` → `import config from 'print-config.json'`

**Единицы измерения в разных местах:**

| Компонент | Единица | Источник |
|-----------|---------|----------|
| **БД (Channel.print_settings)** | миллиметры (mm) | Пользователь |
| **Frontend (CSS variables)** | миллиметры (mm) | `PAGE_SIZES` из config |
| **PDF (WeasyPrint)** | миллиметры (mm) | Напрямую: `@page { size: A4; margin: 20mm; }` |
| **IDML (InDesign)** | points (pt) | Конвертируется: `mm_to_points(mm)` |

**Функции конвертации:**

Python (`idml_export/constants.py`):
```python
mm_to_points(mm)   # 210mm → 595.28pt
points_to_mm(pt)   # 595.28pt → 210mm
mm_to_px(mm)       # 210mm → 793.7px
px_to_mm(px)       # 793.7px → 210mm
points_to_px(pt)   # 595.28pt → 793.7px
px_to_points(px)   # 793.7px → 595.28pt
```

JavaScript (`app/utils/units.js`):
```javascript
mmToPoints(mm)     // 210mm → 595.28pt
pointsToMm(pt)     // 595.28pt → 210mm
mmToPx(mm)         // 210mm → 793.7px
pxToMm(px)         // 793.7px → 210mm
pointsToPx(pt)     // 595.28pt → 793.7px
pxToPoints(px)     // 793.7px → 595.28pt
```

**❌ НЕ ХАРДКОДЬ константы!** Всегда используй:
- `PAGE_SIZES` из constants.py или units.js
- Функции конвертации из тех же модулей
- Для изменения - редактируй **ТОЛЬКО** `print-config.json`

### Архитектура экспорта

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
  "margins": [20, 20, 20, 20],  // в миллиметрах [top, left, bottom, right]
  "text_columns": 1,
  "column_gutter": 5,           // в миллиметрах
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

**Из print-config.json:**
```json
{
  "pageSizes": {
    "A4": { "width": 210, "height": 297 },
    "A3": { "width": 297, "height": 420 },
    "USLetter": { "width": 215.9, "height": 279.4 },
    "Tabloid": { "width": 279.4, "height": 431.8 }
  }
}
```

**В PDF:**
- WeasyPrint понимает строковые константы: `@page { size: A4; }`
- Margins в миллиметрах: `margin: 20mm;`

**В IDML:**
- InDesign требует размеры в points
- Конвертация: `mm_to_points(210)` → `595.28pt`

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
├── test_async_import.py                # ⭐ Async import, resume, retry, FloodWait (23 теста)
├── test_api_v2.py                      # ⭐ Тесты V2 API + чанки (36 тестов)
├── test_chunking.py                    # Тесты системы чанков (27 тестов)
├── test_backup.py                      # 💾 Тесты бэкапов (29 тестов)
├── test_api_layouts.py                 # Тесты API layouts
├── test_api_edits.py                   # Тесты API edits
├── test_gallery_layout.py             # Тесты gallery layout
├── test_message_transform_helpers.py  # Тесты обработки сообщений
├── test_telegram_export_unit.py       # Unit тесты экспорта
├── test_telegram_export_integration.py # Integration тесты
├── test_telegram_export_gallery.py    # Тесты gallery экспорта
├── test_telegram_export_discussion.py # Тесты discussion groups
├── test_telegram_export_*.py          # Другие тесты экспорта
├── _telegram_export_base.py           # Базовый класс для тестов
└── run_tests.py                       # Скрипт запуска
```

### ⚠️ Безопасность тестов (КРИТИЧЕСКИ ВАЖНО!)

**ВСЕГДА используй in-memory БД в тестах!** Иначе `db.drop_all()` в teardown
уничтожит production данные в `instance/posts.db`.

```python
# ✅ ПРАВИЛЬНО — in-memory БД:
from database import create_app
app = create_app(database_uri='sqlite:///:memory:')

# ❌ НЕПРАВИЛЬНО — без database_uri (затрёт production БД!):
app = create_app()
```

`create_app()` принимает параметр `database_uri`. Если передан — использует его,
иначе подключается к реальной `instance/posts.db`.

### Запуск тестов

```bash
# Все тесты (из Docker)
docker compose exec app python -m pytest tests/ -v

# Конкретный файл
docker compose exec app python -m pytest tests/test_backup.py -v

# Конкретный тест
docker compose exec app python -m pytest tests/test_api_v2.py::TestGetChannelChunks -v

# С коротким выводом ошибок
docker compose exec app python -m pytest tests/ --tb=short
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

### chunking.py
**Система чанков для пагинации контента:**
- `build_content_units(channel_id, include_hidden=False)` — собирает посты в логические единицы (пост + комментарии + медиа-группы)
- `calculate_chunks(channel_id, items_per_chunk=50, ..., include_hidden=False)` — разбивает content units на чанки с учётом overflow threshold

### import_state.py
**Потокобезопасное состояние импорта (threading.Lock):**
- `set_status(channel_id, status, details)` — установить статус (`'downloading'`, `'completed'`, `'error'`, `'stopped'`)
- `get_status(channel_id)` — получить текущий статус
- `get_all_statuses()` — все статусы каналов
- `update_progress(channel_id, posts, total, comments)` — обновить прогресс
- `should_stop(channel_id)` — проверить нужна ли остановка
- `clear_status(channel_id)` — удалить запись статуса

### post_filtering.py
**Фильтрация постов (Python-side):**
- `should_hide_media(post)` — скрывает WebPage, non-image Documents, .webp
- `should_hide_post(post, edits)` — скрывает если пост hidden через edits или содержит только неподдерживаемый медиа без текста

### backup.py
**💾 Утилиты бэкапов базы данных:**
- `create_backup(label=None)` — атомарный бэкап через `sqlite3.Connection.backup()`
- `restore_backup(backup_name)` — восстановление с автоматическим safety-бэкапом
- `list_backups()` — список бэкапов (новые первыми) со статистикой таблиц
- `delete_backup(backup_name)` — удаление бэкапа
- `rotate_backups(max_count=10)` — ротация, сохраняет safety-бэкапы (`before-restore`)
- `auto_backup()` — автобэкап при старте (вызывается из `start.sh`)

**Бэкапы хранятся в:** `instance/backups/posts_YYYY-MM-DD_HH-MM-SS_{label}.db`

---

## 📥 ИМПОРТ ИЗ TELEGRAM

### Основной модуль: telegram_export.py

**Главная функция:** `import_channel_direct(channel_username, channel_id=None, export_settings=None, resume=False)`

**Что делает:**
1. Подключается к Telegram через `telegram_client.py`
2. Получает entity (канал или пользователь)
3. Валидирует entity
4. **resume=True**: загружает существующие ID из БД и пропускает уже скачанные посты
5. Скачивает сообщения и медиа с retry и FloodWait handling
6. Сохраняет в БД через батчевый `_flush_batch()`
7. Обновляет прогресс через shared state (без HTTP)

**Ключевые функции:**
```python
def _get_existing_telegram_ids(channel_id):
    """Возвращает set telegram_id постов уже в БД"""

def _process_message_with_retry(post, real_id, client, folder_name, max_retries=3):
    """Обрабатывает сообщение с retry, FloodWaitError → ждёт seconds+1, generic → exponential backoff"""

def _flush_batch(batch):
    """Сохраняет батч постов в БД (BATCH_SIZE=50)"""
```

**Прогресс-трекинг (shared state, без HTTP):**
```python
def update_import_progress(channel_id, processed_posts, processed_comments, total_posts=None):
    """Обновляет прогресс через utils.import_state (shared state)"""
    
def should_stop_import(channel_id):
    """Проверяет через utils.import_state нужно ли остановить"""
```

**Константы:**
- `MAX_RETRIES = 3` — максимум попыток обработки сообщения
- `RETRY_BASE_DELAY = 2` — базовая задержка (секунды), удваивается с каждой попыткой
- `BATCH_SIZE = 50` — размер батча для записи в БД

**API endpoint `/api/add_channel`:**
- Запускает импорт в `threading.Thread` и возвращает `202 Accepted` мгновенно
- Автоматически определяет `resume=True` если канал уже есть в БД
- Возвращает `409` если канал уже загружается
- Прогресс доступен через `GET /api/download/status/<channel_id>`

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
   - ❌ Забывать перезапускать Flask после изменений Python кода → ✅ `docker compose restart app`

2. **Перезагрузка после изменений:**
   - ❌ Изменил код → сразу тестируешь импорт канала → не работает → "Баг!"
   - ✅ Изменил код → `docker compose restart app` → проверил логи → тестируешь

3. **Tailwind CSS:**
   - ❌ Редактировать `public/styles.css` → ✅ Редактировать `assets/tailwind.css` и пересобрать
   - ❌ Редактировать `public/styles-pdf.css` → ✅ Редактировать `assets/tailwind.css` и пересобрать
   - ❌ Забывать пересобирать CSS → ✅ `docker compose exec ssr sh -c "cd /app && npm run build:pdf-css"`

4. **Telegram клиент:**
   - ❌ Создавать новый TelegramClient → ✅ Использовать `connect_to_telegram()`
   - ❌ Выдумывать API_ID/API_HASH → ✅ Читать из `.env`

5. **База данных:**
   - ❌ Выдумывать имена таблиц → ✅ Использовать модели из `models.py`
   - ❌ Прямые SQL запросы → ✅ Использовать SQLAlchemy ORM

6. **API:**
   - ❌ Создавать дубликаты endpoints → ✅ Проверять существующие blueprints
   - ❌ Выдумывать URL схемы → ✅ Смотреть в `api/*.py`

7. **Пути:**
   - ❌ Хардкодить пути → ✅ Использовать `DOWNLOADS_DIR`, `os.path.join()`
   - ❌ Выдумывать структуру папок → ✅ Следовать `downloads/{channel_id}/{avatars|media|thumbs}/`

8. **Frontend:**
   - ❌ Создавать дубликаты stores/services → ✅ Использовать существующие
   - ❌ Забывать про два Tailwind конфига → ✅ Помнить о `tailwind.config.js` и `tailwind.pdf.config.js`
   - ❌ Хардкодить URL в fetch-запросах → ✅ Использовать `apiBase` / `mediaBase` из `~/services/api`
   - ❌ Создавать новые fetch-обёртки → ✅ Использовать `api` из `api.js` или функции из `apiV2.js`

9. **Тесты:**
   - ❌ `create_app()` без `database_uri` → ✅ `create_app(database_uri='sqlite:///:memory:')`
   - ❌ Использовать production БД в тестах → ✅ Всегда in-memory
   - ❌ `db.drop_all()` без проверки URI → ✅ Передавать `database_uri` в `create_app()`

### ✅ ВСЕГДА делай так:

1. **После изменения Python кода (САМОЕ ВАЖНОЕ!):**
   ```bash
   # Изменил любой .py файл в проекте?
   docker compose restart app
   
   # Убедись что контейнер запустился
   docker compose ps
   
   # Проверь логи если что-то не работает
   docker compose logs -f app
   ```

2. **Перед работой с Docker:**
   ```bash
   cd /Users/adoknov/work/tg/tg-offliner
   docker compose up
   ```

3. **Для Telegram клиента:**
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
- `nuxt: ^4.0.0` - Framework (ESM modules, НЕ CommonJS)
- `vue: ^3.5.17` - UI library
- `pinia: ^3.0.3` - State management
- `@fancyapps/ui: ^6.0.34` - Lightbox
- `vue-grid-layout-v3: ^3.1.2` - Drag & drop сетки
- `tailwindcss: ^3.4.17` - CSS framework
- `daisyui: ^5.0.50` - UI компоненты

**ВАЖНО:** Nuxt 4 использует ESM (ES Modules):
- ✅ ПРАВИЛЬНО: `import Wall from '~/components/Wall.vue'` или `const Wall = (await import('~/components/Wall.vue')).default`
- ❌ НЕПРАВИЛЬНО: `const Wall = require('~/components/Wall.vue')` - это CommonJS, не работает!

### ⚠️ ЧАСТЫЕ СИНТАКСИЧЕСКИЕ ОШИБКИ

**При редактировании кода ВСЕГДА проверяй:**

1. **Пропущенные точки с запятой или переводы строк:**
   ```javascript
   // ❌ НЕПРАВИЛЬНО:
   function foo() {
     return 42
   }const bar = 123  // Missing semicolon or newline!
   
   // ✅ ПРАВИЛЬНО:
   function foo() {
     return 42
   }
   const bar = 123
   ```

2. **Незакрытые скобки в computed/watch:**
   ```javascript
   // ❌ НЕПРАВИЛЬНО:
   const computed1 = computed(() => {
     return value
   }
   const computed2 = computed(() => {  // Missing closing paren!
   
   // ✅ ПРАВИЛЬНО:
   const computed1 = computed(() => {
     return value
   })
   const computed2 = computed(() => {
     return value2
   })
   ```
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

### Как создать бэкап базы данных?

1. Через веб-интерфейс: http://localhost:3000/backups → кнопка «Создать бэкап»
2. Через API: `POST http://localhost:5000/api/backups`
3. Автоматически при каждом запуске контейнера (`start.sh`)
4. Программно: `from utils.backup import create_backup; create_backup(label='manual')`

Бэкапы хранятся в `instance/backups/` и автоматически ротируются (макс. 10).

### Как восстановить базу из бэкапа?

1. Через веб-интерфейс: http://localhost:3000/backups → кнопка «Восстановить»
2. Через API: `POST http://localhost:5000/api/backups/<name>/restore`
3. При восстановлении автоматически создаётся safety-бэкап (метка `before-restore`)
4. **После восстановления** нужно перезапустить Flask: `docker compose restart app`

---

**Версия инструкций:** 2.0  
**Дата:** 26 февраля 2026
