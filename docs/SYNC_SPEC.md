# Спецификация: Синхронизация (докачка) канала

**Версия:** 1.0  
**Дата:** 14 февраля 2026

---

## 📋 Цель

Добавить возможность докачки новых постов и комментариев из Telegram канала, который уже импортирован в систему. Вместо полного переимпорта — скачивать только то, что появилось после последнего импорта/синхронизации.

---

## 🎯 Scope

### Включено

| Функция | Описание |
|---------|----------|
| **Новые посты** | Посты с `telegram_id > max(telegram_id)` в БД |
| **Новые комментарии** | Комментарии из discussion group с `telegram_id > max` |
| **Метаданные канала** | Обновление подписчиков, описания, аватара и т.д. |
| **Медиа** | Полная загрузка фото/видео/документов для новых постов |
| **Gallery layouts** | Автогенерация для новых медиа-групп (без перезаписи существующих) |

### Не включено (v1)

- Обнаружение отредактированных постов
- Обнаружение удалённых постов
- Синхронизация реакций на старых постах

---

## 🔄 Пользовательский сценарий (UX Flow)

### Двухшаговый процесс: Check → Confirm → Sync

```
┌─────────────────────────────────────────────┐
│  Карточка канала (ChannelsList.vue)         │
│                                             │
│  llamatest  ·  17 постов  ·  24 комм.     │
│                                             │
│  [Экспорт ▼]  [🔄 Синхронизировать]  [🗑]  │
└──────────────────┬──────────────────────────┘
                   │ клик
                   ▼
┌─────────────────────────────────────────────┐
│  Проверка...  ⏳                            │
│  (GET /api/sync/check/{channel_id})         │
└──────────────────┬──────────────────────────┘
                   │ ответ
                   ▼
┌─────────────────────────────────────────────┐
│  Сводка синхронизации                       │
│                                             │
│  📊 Найдено:                               │
│  · 15 новых постов                          │
│  · ~30 новых комментариев (оценка)          │
│  · Метаданные: обновлены подписчики          │
│                                             │
│  [Отмена]  [▶ Синхронизировать]             │
└──────────────────┬──────────────────────────┘
                   │ подтверждение
                   ▼
┌─────────────────────────────────────────────┐
│  Синхронизация...  ████████░░░  12/15       │
│  (POST /api/sync/start/{channel_id})        │
│                                             │
│  Прогресс: 12 постов · 8 комментариев      │
│  [⏹ Остановить]                             │
└─────────────────────────────────────────────┘
```

### Повторный запуск после остановки

Если пользователь остановил синхронизацию — при следующем нажатии "Синхронизировать" процесс **начинается заново** (новый check → confirm → sync). Но поскольку уже скачанные посты сохранены в БД, `max(telegram_id)` будет выше → скачиваются только оставшиеся новые.

### Состояния кнопки

| Состояние | Кнопка | Действие |
|-----------|--------|----------|
| Idle | `🔄 Синхронизировать` | Запуск check |
| Checking | `⏳ Проверка...` (disabled) | — |
| Summary shown | `▶ Синхронизировать` (в модалке/dropdown) | Запуск sync |
| Syncing | `⏹ Остановить` | Stop sync |
| No new posts | `✅ Актуально` (fade out через 3 сек) | — |

---

## 🏗 Архитектура

### Новые backend endpoints

#### 1. `GET /api/sync/check/<channel_id>`

**Проверяет наличие новых данных без скачивания.**

Алгоритм:
1. Получить `max(telegram_id)` из таблицы `posts` для `channel_id`
2. Подключиться к Telegram, получить entity
3. Посчитать количество сообщений в канале с `id > max_telegram_id`  
   (используя Telethon: `client.get_messages(entity, min_id=max_id, limit=0)` → `.total`)
4. Если есть discussion group — аналогично для комментариев
5. Получить текущие метаданные канала, сравнить с БД

**Request:**
```
GET /api/sync/check/llamatest
```

**Response:**
```json
{
  "channel_id": "llamatest",
  "status": "has_updates",
  "local": {
    "posts_count": 17,
    "comments_count": 24,
    "max_post_id": 85,
    "max_comment_id": 1250,
    "last_import_date": "2026-02-12T15:30:00"
  },
  "remote": {
    "total_messages": 32,
    "new_posts_count": 15,
    "new_posts_estimate": true,
    "discussion_group_id": 2573960761,
    "new_comments_estimate": 30
  },
  "metadata_changes": {
    "subscribers": { "old": "1,234", "new": "1,456" },
    "description": { "changed": true }
  }
}
```

**Статусы:** `has_updates`, `up_to_date`, `error`

#### 2. `POST /api/sync/start/<channel_id>`

**Запускает докачку новых постов.**

Алгоритм:
1. Получить `max(telegram_id)` из таблицы `posts`
2. Итерировать `client.iter_messages(entity, min_id=max_id, reverse=True)`
3. Для каждого нового поста — `process_message_for_api()` + `_flush_batch()`
4. Обновить метаданные канала в БД
5. Если есть discussion group — аналогично для комментариев
6. Сгенерировать gallery layouts для новых медиа-групп
7. Прогресс через существующий `import_state`

**Request:**
```json
POST /api/sync/start/llamatest
{
  "export_settings": {
    "include_reposts": true,
    "include_polls": true,
    "include_discussion_comments": true
  }
}
```

**Response:**
```json
{
  "message": "Синхронизировано 15 новых постов и 28 комментариев",
  "processed_posts": 15,
  "processed_comments": 28,
  "metadata_updated": true,
  "success": true
}
```

#### 3. `POST /api/sync/stop/<channel_id>`

Реиспользует существующий `should_stop` / `set_status('stopped')`.

#### 4. `GET /api/download/status/<channel_id>`

Существующий endpoint — реиспользуется для прогресса синхронизации.  
Добавить поле `type: "sync" | "import"` для различения типов операций.

---

## 📊 Определение «нового поста»

### Стратегия: max(telegram_id)

```
БД:      [1] [2] [3] ... [85]     ← max_id = 85
Telegram: [1] [2] [3] ... [85] [86] [87] ... [100]
                                  ↑               ↑
                           min_id=85          новые
```

**Получение max telegram_id:**
```python
# В sync-функции
from models import Post
max_id = db.session.query(db.func.max(Post.telegram_id)) \
    .filter(Post.channel_id == channel_id) \
    .scalar() or 0
```

**Telethon запрос только новых:**
```python
# Получить количество новых (без скачивания)
messages = await client.get_messages(entity, min_id=max_id, limit=0)
new_count = messages.total

# Итерировать новые посты
for post in client.iter_messages(entity, min_id=max_id, reverse=True):
    # process...
```

### Для комментариев

Аналогично, но с `channel_id = str(discussion_group_id)`:
```python
max_comment_id = db.session.query(db.func.max(Post.telegram_id)) \
    .filter(Post.channel_id == str(discussion_group_id)) \
    .scalar() or 0
```

---

## 📂 Изменения в файлах

### Backend (Python)

| Файл | Изменения |
|------|-----------|
| `api/sync.py` | **НОВЫЙ** — Blueprint с endpoints check/start/stop |
| `telegram_export.py` | Новая функция `sync_channel()` (рефакторинг из `import_channel_direct`) |
| `telegram_export.py` | Новая функция `sync_discussion_comments()` |
| `telegram_export.py` | Новая вспомогательная `_get_max_telegram_id(channel_id)` |
| `app.py` | Регистрация `sync_bp` blueprint |
| `message_processing/channel_info.py` | Новая `compare_channel_metadata(old, new)` для diff метаданных |

### Frontend (Nuxt)

| Файл | Изменения |
|------|-----------|
| `services/apiV2.js` | Новые функции: `checkSync()`, `startSync()`, `stopSync()` |
| `components/system/ChannelsList.vue` | Кнопка «Синхронизировать» + сводка + подтверждение |
| `components/system/SyncStatus.vue` | **НОВЫЙ** — Компонент отображения прогресса sync |
| `components/system/DownloadStatus.vue` | Поддержка `type: "sync"` (или переиспользовать как есть) |

---

## 🔧 Детали реализации

### `sync_channel()` — основная функция

```python
def sync_channel(channel_id, export_settings=None):
    """
    Докачивает новые посты канала.
    Возвращает словарь с результатом.
    """
    # 1. Получить max telegram_id из БД
    max_id = _get_max_telegram_id(channel_id)
    
    # 2. Подключиться к Telegram
    client = connect_to_telegram()
    entity, error = get_entity_by_username_or_id(client, channel_id)
    
    # 3. Итерировать новые сообщения (min_id = max_id)
    new_posts = client.iter_messages(entity, min_id=max_id, reverse=True)
    
    # 4. process_message_for_api + _flush_batch (как в import)
    batch = []
    for post in new_posts:
        if should_stop_import(channel_id):
            break
        post_data = process_message_for_api(post, channel_id, client, folder_name)
        if post_data:
            batch.append(post_data)
        if len(batch) >= BATCH_SIZE:
            _flush_batch(batch)
            batch = []
    _flush_batch(batch)
    
    # 5. Обновить метаданные канала
    _update_channel_metadata(client, entity, channel_id)
    
    # 6. Синхронизировать комментарии
    if discussion_group_id and include_comments:
        sync_discussion_comments(client, channel_id, discussion_group_id)
    
    # 7. Сгенерировать gallery layouts для новых групп
    generate_gallery_layouts_for_channel(channel_id)
```

### `_update_channel_metadata()` — обновление метаданных

```python
def _update_channel_metadata(client, entity, channel_id):
    """Обновляет метаданные канала в БД (подписчики, описание, аватар)."""
    channel_info = get_channel_info(client, entity, output_dir="downloads", folder_name=folder_name)
    
    with app.app_context():
        channel = Channel.query.get(channel_id)
        if channel:
            channel.subscribers = channel_info.get('subscribers')
            channel.description = channel_info.get('description')
            channel.posts_count = channel_info.get('posts_count')
            # Аватар: скачать если изменился
            if channel_info.get('avatar') and channel_info['avatar'] != channel.avatar:
                channel.avatar = channel_info['avatar']
            db.session.commit()
```

### Важные моменты

1. **НЕ вызывать `clear_downloads()`** — при синхронизации медиа добавляются, а не перезаписываются
2. **НЕ удалять/пересоздавать канал в БД** — только обновлять
3. **`generate_gallery_layouts_for_channel()`** уже пропускает существующие layouts (код проверяет `Layout.query.filter_by(grouped_id=...).first()`)
4. **`_flush_batch()`** можно использовать as-is — он просто добавляет новые записи
5. **Прогресс** — переиспользовать `update_import_progress()` и `should_stop_import()`

### Обновление метаданных: что сравниваем

| Поле | Обновляем? | Примечание |
|------|-----------|------------|
| `name` | ❌ Нет | Пользователь мог переименовать в UI |
| `subscribers` | ✅ Да | Всегда актуальное значение |
| `description` | ✅ Да | Текст описания канала |
| `posts_count` | ✅ Да | Количество постов в Telegram |
| `avatar` | ✅ Да | Перекачать если изменился |
| `creation_date` | ❌ Нет | Не меняется |
| `print_settings` | ❌ Нет | Пользовательские настройки |
| `changes` | ❌ Нет | Пользовательские изменения |

---

## 🗓 Фазы разработки

### Фаза 1: Backend — Check endpoint

- [ ] Создать `api/sync.py` blueprint
- [ ] Реализовать `GET /api/sync/check/<channel_id>`
- [ ] Функция `_get_max_telegram_id(channel_id)`
- [ ] Функция `compare_channel_metadata()`
- [ ] Регистрация blueprint в `app.py`
- [ ] Тесты для check endpoint

### Фаза 2: Backend — Sync endpoint

- [ ] Реализовать `sync_channel()` в `telegram_export.py`
- [ ] Реализовать `sync_discussion_comments()` в `telegram_export.py`
- [ ] Реализовать `_update_channel_metadata()`
- [ ] Реализовать `POST /api/sync/start/<channel_id>` в `api/sync.py`
- [ ] Реализовать `POST /api/sync/stop/<channel_id>`
- [ ] Прогресс через `import_state` (поле `type: "sync"`)
- [ ] Тесты для sync endpoint

### Фаза 3: Frontend — UI

- [ ] API функции в `apiV2.js`: `checkSync()`, `startSync()`, `stopSync()`
- [ ] Кнопка «Синхронизировать» в `ChannelsList.vue`
- [ ] Сводка diff (модалка или dropdown) с кнопкой подтверждения
- [ ] `SyncStatus.vue` — прогресс синхронизации (или переиспользовать `DownloadStatus.vue`)
- [ ] Polling прогресса через `GET /api/download/status/<channel_id>`
- [ ] Обработка состояний: checking, summary, syncing, done, no updates

### Фаза 4: Тестирование

- [ ] `tests/test_sync.py` — unit тесты sync_channel, check, helpers
- [ ] `tests/test_api_sync.py` — API endpoint тесты (Flask test client)
- [ ] Ручной тест на `llamatest`: добавить пост → sync → проверить

---

## 🧪 Тесты

### Файловая структура

```
tests/
├── test_sync.py          # Unit тесты: sync_channel, helpers, edge cases
└── test_api_sync.py      # API endpoint тесты: check, start, stop
```

### `test_sync.py` — Unit тесты синхронизации

**Фреймворк:** `unittest.TestCase` + наследование от `TelegramExportUnitTestCase`  
**Паттерн:** `contextlib.ExitStack` для стека `mock.patch`, `SimpleNamespace` для Telethon объектов

#### Тест-кейсы: `_get_max_telegram_id()`

```python
class TestGetMaxTelegramId(unittest.TestCase):
    """Тесты для _get_max_telegram_id() — чистая DB-функция."""
    
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
```

| # | Тест | Что проверяет | Seed data | Ожидание |
|---|------|---------------|-----------|----------|
| 1 | `test_returns_max_id` | Корректный max по channel_id | Posts: id=10, 50, 85 для `ch1` | `85` |
| 2 | `test_returns_zero_for_empty` | Пустая таблица | Нет постов | `0` |
| 3 | `test_isolates_by_channel` | Не смешивает каналы | `ch1`: id=100, `ch2`: id=200 | ch1→`100`, ch2→`200` |
| 4 | `test_ignores_comments` | Комментарии не влияют на max поста | `ch1`: id=50; `disc_group`: id=999 | ch1→`50` |

#### Тест-кейсы: `sync_channel()`

```python
class TestSyncChannel(TelegramExportUnitTestCase):
    """
    Тесты sync_channel(). 
    Паттерн: ExitStack + mock всех внешних зависимостей.
    """
```

**Мокаемые зависимости (аналогично `import_channel_direct`):**

| Функция | Mock | Значение |
|---------|------|----------|
| `connect_to_telegram` | `mock.patch.object(telegram_export, ...)` | Mock client |
| `get_entity_by_username_or_id` | `mock.patch("utils.entity_validation....")` | `(entity, None)` |
| `_get_max_telegram_id` | `mock.patch.object(telegram_export, ...)` | `85` |
| `process_message_for_api` | `mock.patch.object(telegram_export, ...)` | `side_effect=[...]` |
| `_flush_batch` | `mock.patch.object(telegram_export, ...)` | — |
| `_update_channel_metadata` | `mock.patch.object(telegram_export, ...)` | — |
| `sync_discussion_comments` | `mock.patch.object(telegram_export, ...)` | `5` |
| `generate_gallery_layouts_for_channel` | `mock.patch.object(telegram_export, ...)` | — |
| `should_stop_import` | `mock.patch.object(telegram_export, ...)` | `False` |
| `update_import_progress` | `mock.patch.object(telegram_export, ...)` | — |

| # | Тест | Сценарий | Проверка |
|---|------|----------|----------|
| 1 | `test_sync_new_posts_success` | 3 новых поста, discussion group есть | `result["success"] == True`, `result["processed"] == 3`, `iter_messages` вызван с `min_id=85` |
| 2 | `test_sync_no_new_posts` | `iter_messages` возвращает `[]` | `result["success"] == True`, `result["processed"] == 0` |
| 3 | `test_sync_stops_on_request` | `should_stop_import` возвращает `True` после 1-го поста | `result["stopped"] == True`, `result["processed"] == 1` |
| 4 | `test_sync_entity_not_found` | `get_entity_by_username_or_id` → `(None, "error")` | `result["success"] == False` |
| 5 | `test_sync_calls_min_id` | Проверить что `iter_messages` вызван с `min_id=max_id` | `mock_client.iter_messages.assert_called_with(entity, min_id=85, reverse=True)` |
| 6 | `test_sync_skips_clear_downloads` | `clear_downloads` НЕ вызывается | `clear_mock.assert_not_called()` |
| 7 | `test_sync_updates_metadata` | Метаданные канала обновляются | `_update_channel_metadata.assert_called_once()` |
| 8 | `test_sync_handles_discussion_comments` | Discussion group ID есть | `sync_discussion_comments.assert_called_once_with(client, channel_id, disc_group_id)` |
| 9 | `test_sync_no_discussion_comments_when_disabled` | `include_discussion_comments=False` | `sync_discussion_comments.assert_not_called()` |
| 10 | `test_sync_generates_gallery_layouts` | Новые посты с grouped_id | `generate_gallery_layouts_for_channel.assert_called_once()` |
| 11 | `test_sync_with_max_id_zero` | `_get_max_telegram_id` → `0` (первый импорт) | `iter_messages` вызван с `min_id=0` — скачивает всё |
| 12 | `test_sync_batch_flush` | 60 новых постов (> BATCH_SIZE=50) | `_flush_batch` вызван минимум 2 раза |

#### Тест-кейсы: `sync_discussion_comments()`

| # | Тест | Сценарий | Проверка |
|---|------|----------|----------|
| 1 | `test_sync_comments_success` | 5 новых комментариев | Возвращает `5` |
| 2 | `test_sync_comments_uses_min_id` | max_comment_id=1000 | `iter_messages` вызван с `min_id=1000` |
| 3 | `test_sync_comments_empty` | Нет новых комментариев | Возвращает `0` |
| 4 | `test_sync_comments_entity_error` | Discussion group недоступна | Возвращает `0`, без исключений |

#### Тест-кейсы: `_update_channel_metadata()`

| # | Тест | Сценарий | Проверка |
|---|------|----------|----------|
| 1 | `test_updates_subscribers` | Подписчики изменились | `channel.subscribers == "200"` |
| 2 | `test_updates_description` | Описание изменилось | `channel.description == "new desc"` |
| 3 | `test_preserves_name` | Имя канала не перезаписывается | `channel.name == "old name"` (не из Telegram) |
| 4 | `test_preserves_print_settings` | print_settings не трогаются | `channel.print_settings` без изменений |
| 5 | `test_updates_avatar` | Аватар изменился | `channel.avatar == "new_path"` |

#### Тест-кейсы: `compare_channel_metadata()`

| # | Тест | Ожидание |
|---|------|----------|
| 1 | `test_detects_subscriber_change` | `{"subscribers": {"old": "100", "new": "200"}}` |
| 2 | `test_detects_description_change` | `{"description": {"changed": True}}` |
| 3 | `test_no_changes` | `{}` (пустой dict) |
| 4 | `test_ignores_unchanged_fields` | Только изменённые поля в результате |
| 5 | `test_handles_none_values` | old=None, new="value" → фиксируется как изменение |

### `test_api_sync.py` — API endpoint тесты

**Фреймворк:** `pytest` + fixtures  
**Паттерн:** Flask test client, in-memory SQLite, mock Telegram

#### Fixtures

```python
@pytest.fixture
def app():
    """Flask app с in-memory SQLite и sync blueprint."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    from api.sync import sync_bp
    app.register_blueprint(sync_bp, url_prefix='/api')
    
    with app.app_context():
        init_db(app)
        db.create_all()
        # Seed: канал + посты
        channel = Channel(id='llamatest', name='Test', subscribers='100',
                         description='Old desc', discussion_group_id=2573960761)
        db.session.add(channel)
        for i in [10, 20, 30, 40, 50]:
            db.session.add(Post(telegram_id=i, channel_id='llamatest',
                               date='2026-01-01', message=f'Post {i}'))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def mock_telegram():
    """Mock Telegram client + entity для всех sync тестов."""
    with ExitStack() as stack:
        entity = SimpleNamespace(username='llamatest', id=42, count=60)
        mock_client = mock.Mock()
        
        stack.enter_context(mock.patch(
            'api.sync.connect_to_telegram', return_value=mock_client))
        stack.enter_context(mock.patch(
            'api.sync.get_entity_by_username_or_id', return_value=(entity, None)))
        
        yield mock_client, entity
```

#### Тест-кейсы: `GET /api/sync/check/<channel_id>`

```python
class TestSyncCheck:
```

| # | Тест | Сценарий | Mock | Ожидание |
|---|------|----------|------|----------|
| 1 | `test_check_has_updates` | 10 новых постов | `get_messages(min_id=50, limit=0).total = 10` | 200, `status: "has_updates"`, `new_posts_count: 10` |
| 2 | `test_check_up_to_date` | Нет новых | `.total = 0` | 200, `status: "up_to_date"`, `new_posts_count: 0` |
| 3 | `test_check_channel_not_found` | channel_id не в БД | — | 404 |
| 4 | `test_check_telegram_error` | `get_entity_by_username_or_id` → `(None, "error")` | — | 503 |
| 5 | `test_check_returns_local_stats` | Проверяем `local` в response | — | `posts_count: 5`, `max_post_id: 50` |
| 6 | `test_check_metadata_changes` | Подписчики изменились | entity + full_chat mock | `metadata_changes.subscribers` present |
| 7 | `test_check_concurrent_operation` | `import_state` уже `downloading` | `set_status('llamatest', 'downloading')` | 409 |
| 8 | `test_check_comments_estimate` | Discussion group, 20 новых | `get_messages(disc_entity, min_id=...).total = 20` | `new_comments_estimate: 20` |

#### Тест-кейсы: `POST /api/sync/start/<channel_id>`

```python
class TestSyncStart:
```

| # | Тест | Сценарий | Mock | Ожидание |
|---|------|----------|------|----------|
| 1 | `test_start_success` | 3 новых поста | `sync_channel` → success dict | 200, `processed_posts: 3` |
| 2 | `test_start_channel_not_found` | Несуществующий канал | — | 404 |
| 3 | `test_start_concurrent` | Уже идёт sync/import | `set_status(downloading)` | 409 |
| 4 | `test_start_with_export_settings` | Кастомные настройки в body | — | `sync_channel` вызван с settings |
| 5 | `test_start_sets_status` | Проверка `import_state` | — | `get_status()["type"] == "sync"` |
| 6 | `test_start_telegram_error` | Telegram недоступен | `sync_channel` → error | 503 |

#### Тест-кейсы: `POST /api/sync/stop/<channel_id>`

```python
class TestSyncStop:
```

| # | Тест | Сценарий | Ожидание |
|---|------|----------|----------|
| 1 | `test_stop_active_sync` | Статус `downloading` с `type: sync` | 200, статус → `stopped` |
| 2 | `test_stop_no_active_sync` | Нет активного процесса | 404 |
| 3 | `test_stop_already_stopped` | Статус `stopped` | 400 |

### Примеры кода тестов

#### Unit тест: `sync_channel` success

```python
def test_sync_new_posts_success(self):
    """sync_channel скачивает только новые посты (min_id > max_id)."""
    entity = SimpleNamespace(username="llamatest", id=42, count=100)
    mock_client = mock.Mock()
    
    # 3 новых поста (telegram_id > 85)
    new_posts = [
        self._build_basic_post(id=86, message="New 1"),
        self._build_basic_post(id=87, message="New 2"),
        self._build_basic_post(id=88, message="New 3"),
    ]
    mock_client.iter_messages.return_value = new_posts
    
    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(
            telegram_export, "connect_to_telegram", return_value=mock_client))
        stack.enter_context(mock.patch(
            "utils.entity_validation.get_entity_by_username_or_id",
            return_value=(entity, None)))
        stack.enter_context(mock.patch.object(
            telegram_export, "_get_max_telegram_id", return_value=85))
        pma_mock = stack.enter_context(mock.patch.object(
            telegram_export, "process_message_for_api",
            side_effect=[
                {"telegram_id": 86, "channel_id": "llamatest", "date": "2026-02-15"},
                {"telegram_id": 87, "channel_id": "llamatest", "date": "2026-02-15"},
                {"telegram_id": 88, "channel_id": "llamatest", "date": "2026-02-15"},
            ]))
        flush_mock = stack.enter_context(mock.patch.object(
            telegram_export, "_flush_batch"))
        stack.enter_context(mock.patch.object(
            telegram_export, "_update_channel_metadata"))
        stack.enter_context(mock.patch.object(
            telegram_export, "sync_discussion_comments", return_value=5))
        stack.enter_context(mock.patch.object(
            telegram_export, "generate_gallery_layouts_for_channel"))
        stack.enter_context(mock.patch.object(
            telegram_export, "should_stop_import", return_value=False))
        stack.enter_context(mock.patch.object(
            telegram_export, "update_import_progress"))
        
        result = telegram_export.sync_channel("llamatest")
    
    self.assertTrue(result["success"])
    self.assertEqual(result["processed"], 3)
    # Проверяем что iter_messages вызван с min_id
    mock_client.iter_messages.assert_called_once_with(
        entity, min_id=85, reverse=True)
```

#### API тест: check endpoint

```python
class TestSyncCheck:
    def test_check_has_updates(self, client, mock_telegram):
        mock_client, entity = mock_telegram
        
        # Telegram говорит что 10 новых постов
        messages_result = mock.Mock()
        messages_result.total = 10
        mock_client.get_messages.return_value = messages_result
        
        response = client.get('/api/sync/check/llamatest')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'has_updates'
        assert data['remote']['new_posts_count'] == 10
        assert data['local']['max_post_id'] == 50
        assert data['local']['posts_count'] == 5

    def test_check_channel_not_in_db(self, client, mock_telegram):
        response = client.get('/api/sync/check/nonexistent')
        assert response.status_code == 404

    def test_check_up_to_date(self, client, mock_telegram):
        mock_client, _ = mock_telegram
        messages_result = mock.Mock()
        messages_result.total = 0
        mock_client.get_messages.return_value = messages_result
        
        response = client.get('/api/sync/check/llamatest')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'up_to_date'
```

### Сводная таблица тестов

| Файл | Класс | Кол-во тестов | Стиль |
|------|-------|---------------|-------|
| `test_sync.py` | `TestGetMaxTelegramId` | 4 | unittest + in-memory DB |
| `test_sync.py` | `TestSyncChannel` | 12 | unittest + ExitStack mocks |
| `test_sync.py` | `TestSyncDiscussionComments` | 4 | unittest + ExitStack mocks |
| `test_sync.py` | `TestUpdateChannelMetadata` | 5 | unittest + in-memory DB |
| `test_sync.py` | `TestCompareChannelMetadata` | 5 | unittest (чистая функция) |
| `test_api_sync.py` | `TestSyncCheck` | 8 | pytest + Flask test client |
| `test_api_sync.py` | `TestSyncStart` | 6 | pytest + Flask test client |
| `test_api_sync.py` | `TestSyncStop` | 3 | pytest + Flask test client |
| | | **Итого: 47** | |

---

## ⚠️ Edge cases

| Ситуация | Поведение |
|----------|----------|
| Канал не найден в БД | 404 — "Канал не импортирован" |
| Нет новых постов | `status: "up_to_date"` → кнопка "✅ Актуально" |
| Telegram недоступен | 503 — "Не удалось подключиться к Telegram" |
| Параллельный импорт/синхронизация | 409 — "Операция уже выполняется" (проверять `import_state`) |
| Канал стал приватным | 403 — "Нет доступа к каналу" |
| Discussion group изменилась | Обновить `discussion_group_id` в БД |
| Посты с `grouped_id` (альбомы) | Все части альбома попадут по `min_id`, layout генерируется автоматически |
| Пустой канал (0 постов в БД) | `max_id = 0` → скачать все (эквивалент полного импорта) |
| Sync после остановленного import | `max_id` учитывает уже скачанные посты → докачать остаток |

---

## 📚 Примеры API

### Проверка обновлений (нет новых данных)

```
GET /api/sync/check/llamatest

200 OK
{
  "channel_id": "llamatest",
  "status": "up_to_date",
  "local": {
    "posts_count": 17,
    "comments_count": 24,
    "max_post_id": 85
  },
  "remote": {
    "total_messages": 17,
    "new_posts_count": 0,
    "new_comments_estimate": 0
  },
  "metadata_changes": {}
}
```

### Проверка (есть обновления)

```
GET /api/sync/check/llamatest

200 OK
{
  "channel_id": "llamatest",
  "status": "has_updates",
  "local": {
    "posts_count": 17,
    "comments_count": 24,
    "max_post_id": 85
  },
  "remote": {
    "total_messages": 32,
    "new_posts_count": 15,
    "new_comments_estimate": 30
  },
  "metadata_changes": {
    "subscribers": { "old": "150", "new": "200" }
  }
}
```

### Запуск синхронизации

```
POST /api/sync/start/llamatest
Content-Type: application/json

{
  "export_settings": {
    "include_reposts": true,
    "include_polls": true,
    "include_discussion_comments": true
  }
}

200 OK
{
  "success": true,
  "processed_posts": 15,
  "processed_comments": 28,
  "metadata_updated": true,
  "message": "Синхронизировано 15 новых постов и 28 комментариев"
}
```

### Прогресс (через существующий endpoint)

```
GET /api/download/status/llamatest

200 OK
{
  "status": "downloading",
  "type": "sync",
  "details": {
    "processed_posts": 8,
    "total_posts": 15,
    "processed_comments": 3,
    "started_at": 1739520000
  }
}
```
