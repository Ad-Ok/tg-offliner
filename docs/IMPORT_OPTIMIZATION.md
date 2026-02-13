# Оптимизация импорта каналов

> **Дата:** 13 февраля 2026
> **Статус:** Анализ завершён, реализация не начата

---

## 📋 Текущая архитектура импорта

### Общий флоу

```
Frontend → POST /api/download/import → background thread → telegram_export.py
```

Импорт использует **Telethon** для загрузки из Telegram и **V1 REST API** (`localhost:5000`) для записи в БД.

### Последовательность операций

```
1. connect_to_telegram()                          — singleton Telethon client
2. get_channel_info() → POST /api/channels        — сохранение канала (V1 HTTP)
3. client.iter_messages(entity, reverse=True)      — итерация постов последовательно
4. На КАЖДЫЙ пост:
   ├── process_message_for_api()                   — скачивание медиа, thumbnail, парсинг
   ├── requests.post("/api/posts", json=post_data) — HTTP запрос на КАЖДЫЙ пост
   ├── time.sleep(0.1)                             — искусственная задержка 100ms
   ├── should_stop_import() → GET /api/download/status  — HTTP проверка на КАЖДЫЙ пост
   └── update_import_progress() → POST /api/download/progress  — HTTP каждые 5 постов
5. import_all_discussion_comments()                — отдельный проход по discussion group
6. generate_gallery_layouts_for_channel()           — генерация layouts
```

### Как работают комментарии

Функция `import_all_discussion_comments()` в `telegram_export.py`:

**Шаг 1 — Полное сканирование discussion group (все сообщения в память):**
```python
for message in client.iter_messages(discussion_entity):  # ВСЕ сообщения, без лимита
    all_messages.append(message)                          # Всё в RAM
    if message.fwd_from and message.fwd_from.saved_from_msg_id:
        forward_mapping[saved_id] = message.id            # Маппинг: пост канала → forwarded msg
```

**Шаг 2 — Второй проход по тем же сообщениям + линейный поиск:**
```python
for message in all_messages:
    if message.reply_to:
        # Линейный поиск O(K) на каждый комментарий!
        for saved_id, fwd_id in forward_mapping.items():
            if top_id == fwd_id:
                original_post_id = saved_id
                break
        # process_message_for_api() + requests.post("/api/posts")
```

### Ключевые файлы

| Файл | Роль |
|------|------|
| `telegram_export.py` | Основная логика импорта |
| `message_processing/message_transform.py` | Обработка каждого сообщения: скачивание медиа, thumbnail, парсинг |
| `message_processing/author.py` | Извлечение автора (может скачивать аватар) |
| `api/downloads.py` | Endpoints для статуса/прогресса/остановки (V1) |
| `api/posts.py` | `POST /api/posts` — сохранение одного поста (V1) |
| `config.py` | `EXPORT_SETTINGS` — параметры импорта |

---

## 🐢 Узкие места (bottlenecks)

| # | Проблема | Влияние | Где |
|---|----------|---------|-----|
| **1** | **`time.sleep(0.1)` на каждый пост** | 100ms × N постов = **50s на 500 постов** | `telegram_export.py:207` |
| **2** | **HTTP POST на каждый пост** | ~5-15ms × N постов | `telegram_export.py:193` → `api/posts.py:80` |
| **3** | **HTTP POST на каждый комментарий** | ~5-15ms × M комментариев | `telegram_export.py:316` |
| **4** | **Медиа скачивается синхронно** | 0.5-5s × количество медиа = **основной bottleneck** | `message_transform.py:131`: `client.download_media()` |
| **5** | **Thumbnail создаётся синхронно** | ~50ms × фото | `message_transform.py:142`: Pillow resize |
| **6** | **Линейный поиск в `forward_mapping`** | O(K) × M комментариев | `telegram_export.py:296-305` |
| **7** | **Все сообщения discussion group в RAM** | Память, 2 прохода | `telegram_export.py:264`: `all_messages.append()` |
| **8** | **`should_stop_import()` — HTTP на каждый пост** | ~5ms × N | `telegram_export.py:163` |
| **9** | **`update_import_progress()` — HTTP каждые 5 постов** | ~5ms × N/5 | `telegram_export.py:204` |

### Расчёт для типичного канала

**500 постов, 200 комментариев, 100 фото, discussion group 5000 сообщений:**

```
ПОСТЫ:
  500 × 0.1s  (sleep)              = 50.0s
  500 × 0.01s (HTTP POST /api/posts) = 5.0s
  100 × 2.0s  (media download)     = 200.0s
  100 × 0.05s (thumbnail)          = 5.0s
  500 × 0.005s (HTTP stop check)   = 2.5s
  100 × 0.005s (HTTP progress)     = 0.5s
                              ИТОГО ≈ 263s (4.4 мин)

КОММЕНТАРИИ:
  5000 сообщений × Telegram API    ≈ 30-60s (iter_messages)
  200 × 0.01s (HTTP POST)          = 2.0s
  200 × O(K) линейный поиск        ≈ 1.0s
                              ИТОГО ≈ 33-63s

LAYOUTS:
  Генерация                        ≈ 2-5s

ОБЩЕЕ ВРЕМЯ: ~5-6 минут
```

---

## 🚀 План оптимизации

### P0 — Мгновенный эффект (30 минут работы, ×2 ускорение)

#### 1. Убрать `time.sleep(0.1)`

**Экономия:** ~50s на 500 постов

Задержка не нужна. Telethon сам управляет rate limiting через `FloodWaitError`. `iter_messages` получает сообщения пачками — между обработкой уже полученных сообщений задержка бессмысленна.

```diff
  # telegram_export.py, строка ~207
  # Небольшая задержка между постами, чтобы избежать rate limits
- time.sleep(0.1)
+ # Убрано: Telethon сам управляет rate limiting через FloodWaitError
```

#### 2. Batch INSERT вместо HTTP POST на каждый пост

**Экономия:** ~5s → ~0.05s (×100)

Вместо HTTP запроса `requests.post("/api/posts")` на каждый пост — прямая запись в БД пачками:

```python
from app import app
from models import db, Post

BATCH_SIZE = 50

def _flush_batch(batch):
    """Записывает пачку постов в БД за один commit."""
    with app.app_context():
        for data in batch:
            new_post = Post(
                telegram_id=data['telegram_id'],
                channel_id=data['channel_id'],
                date=data['date'],
                message=data.get('message', ''),
                media_url=data.get('media_url'),
                thumb_url=data.get('thumb_url'),
                media_type=data.get('media_type'),
                mime_type=data.get('mime_type'),
                author_name=data.get('author_name'),
                author_avatar=data.get('author_avatar'),
                author_link=data.get('author_link'),
                repost_author_name=data.get('repost_author_name'),
                repost_author_avatar=data.get('repost_author_avatar'),
                repost_author_link=data.get('repost_author_link'),
                reactions=data.get('reactions'),
                grouped_id=data.get('grouped_id'),
                reply_to=data.get('reply_to'),
            )
            db.session.add(new_post)
        db.session.commit()

# В import_channel_direct():
batch = []
for post in all_posts:
    post_data = process_message_for_api(post, real_id, client, folder_name)
    if post_data:
        batch.append(post_data)
        processed_count += 1
    
    if len(batch) >= BATCH_SIZE:
        _flush_batch(batch)
        batch = []
        update_import_progress(channel_id, processed_count, comments_count, total_posts)

if batch:
    _flush_batch(batch)
```

Аналогично для комментариев в `import_all_discussion_comments()`.

---

### P1 — Существенное ускорение (2-3 часа работы, ещё ×2-3)

#### 3. Reverse mapping для комментариев — O(1) вместо O(K)

**Экономия:** незначительная для малых K, существенная для групп с 10k+ сообщений.

```python
# Шаг 1: строим ОБА маппинга
forward_mapping = {}   # saved_from_msg_id → forwarded_msg_id
reverse_mapping = {}   # forwarded_msg_id → saved_from_msg_id

for message in client.iter_messages(discussion_entity):
    if message.fwd_from and hasattr(message.fwd_from, 'saved_from_msg_id'):
        saved_id = message.fwd_from.saved_from_msg_id
        forward_mapping[saved_id] = message.id
        reverse_mapping[message.id] = saved_id  # ← O(1) lookup

# Шаг 2: вместо линейного поиска
- for saved_id, fwd_id in forward_mapping.items():
-     if top_id == fwd_id:
-         original_post_id = saved_id
-         break

+ original_post_id = reverse_mapping.get(top_id)
+ if original_post_id is None:
+     original_post_id = reverse_mapping.get(reply_to_msg_id)
```

#### 4. Streaming вместо 2 проходов по discussion group

**Экономия:** -RAM, -1 проход по Telegram API.

Проблема: сообщения от `iter_messages` идут от новых к старым. Forwards (оригинальные посты канала) хронологически раньше комментариев к ним. Поэтому при стриминге нового→старому мы встречаем комментарии раньше, чем forwards.

Решение: pending queue для комментариев, которые ещё не могут быть привязаны:

```python
def import_all_discussion_comments_streaming(client, channel_id, discussion_group_id):
    """Один проход по discussion group."""
    discussion_entity, _ = get_entity_by_username_or_id(client, str(discussion_group_id))
    if not discussion_entity:
        return 0
    
    folder_name = f"channel_{discussion_group_id}"
    reverse_mapping = {}   # fwd_msg_id → original_post_id
    pending = []           # Комментарии, для которых forward ещё не встретился
    batch = []
    comments_imported = 0
    
    for message in client.iter_messages(discussion_entity):
        # Forward из канала — запоминаем маппинг
        if message.fwd_from and hasattr(message.fwd_from, 'saved_from_msg_id'):
            reverse_mapping[message.id] = message.fwd_from.saved_from_msg_id
            continue
        
        # Пропускаем не-ответы
        if not (message.reply_to and hasattr(message.reply_to, 'reply_to_msg_id')):
            continue
        
        # Пропускаем сами forwards
        if message.fwd_from:
            continue
        
        # Ищем оригинальный пост
        top_id = getattr(message.reply_to, 'reply_to_top_id', None)
        original_post_id = reverse_mapping.get(top_id) if top_id else None
        if original_post_id is None:
            original_post_id = reverse_mapping.get(message.reply_to.reply_to_msg_id)
        
        if original_post_id is None:
            pending.append(message)  # Forward позже в итерации
            continue
        
        comment_data = process_message_for_api(message, str(discussion_group_id), client, folder_name)
        if comment_data:
            comment_data['reply_to'] = original_post_id
            batch.append(comment_data)
            comments_imported += 1
        
        if len(batch) >= 50:
            _flush_batch(batch)
            batch = []
    
    # Обрабатываем pending — теперь все forwards собраны
    for message in pending:
        top_id = getattr(message.reply_to, 'reply_to_top_id', None)
        original_post_id = reverse_mapping.get(top_id) if top_id else None
        if original_post_id is None:
            original_post_id = reverse_mapping.get(message.reply_to.reply_to_msg_id)
        if original_post_id:
            comment_data = process_message_for_api(message, str(discussion_group_id), client, folder_name)
            if comment_data:
                comment_data['reply_to'] = original_post_id
                batch.append(comment_data)
                comments_imported += 1
    
    if batch:
        _flush_batch(batch)
    
    return comments_imported
```

#### 5. Параллельное скачивание медиа (самый большой эффект)

**Экономия:** 200s → 30-50s (×4-6)

Медиа — **главный** bottleneck. Скачивание одного файла 0.5-5 секунд (сетевой I/O). Текущий код скачивает последовательно.

**Вариант A: Двухфазный импорт (проще)**

```python
# Фаза 1: Получаем все посты, сохраняем текст в БД
# Фаза 2: Скачиваем медиа параллельно, обновляем записи

import asyncio

async def download_media_batch(client, posts_with_media, channel_folder):
    """Скачивает медиа для пачки постов параллельно."""
    semaphore = asyncio.Semaphore(4)  # Максимум 4 одновременных загрузки
    
    async def download_one(post):
        async with semaphore:
            target = os.path.join(channel_folder, "media", f"{post.id}_media")
            path = await client.download_media(post.media, file=target)
            return post.id, path
    
    tasks = [download_one(post) for post in posts_with_media]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

**Вариант B: Async Telethon (нативный подход)**

Telethon — async библиотека. Текущий код использует `telethon.sync` обёртку, которая делает его синхронным. Переход на нативный async даст максимальную производительность:

```python
# Вместо telethon.sync — нативный async
from telethon import TelegramClient

async def import_channel_async(channel_username, ...):
    client = connect_to_telegram()  # async client
    
    # Скачиваем сообщения и медиа параллельно
    async for message in client.iter_messages(entity):
        # Текст обрабатываем сразу
        post_data = build_post_data_without_media(message, ...)
        batch.append(post_data)
        
        # Медиа добавляем в очередь на скачивание
        if message.media:
            media_queue.append((message, post_data))
    
    # Скачиваем медиа пачками по 4
    for chunk in batched(media_queue, 4):
        results = await asyncio.gather(*[
            download_and_thumbnail(client, msg, data, channel_folder)
            for msg, data in chunk
        ])
```

**Осторожно:** `telethon.sync` client не thread-safe. Для параллельного скачивания нужен либо полный переход на async, либо пул Telethon клиентов (сложно).

**Рекомендация:** Вариант A (двухфазный) — проще в реализации, не требует переписывания всего на async.

---

### P2 — Чистка (1 час, небольшой эффект)

#### 6. Shared state вместо HTTP для stop/progress

**Экономия:** ~3s, чистота архитектуры.

```python
# utils/import_state.py
import threading

_state = {}
_lock = threading.Lock()

def set_stop_flag(channel_id):
    with _lock:
        _state.setdefault(channel_id, {})['stop'] = True

def should_stop(channel_id):
    with _lock:
        return _state.get(channel_id, {}).get('stop', False)

def update_progress(channel_id, posts, comments, total):
    with _lock:
        _state.setdefault(channel_id, {}).update({
            'posts_processed': posts,
            'comments_processed': comments,
            'total_posts': total,
        })

def get_progress(channel_id):
    with _lock:
        return _state.get(channel_id, {}).copy()
```

Вместо:
```python
# Было: HTTP на каждый пост
requests.get(f"http://localhost:5000/api/download/status/{channel_id}")

# Стало: чтение из памяти
from utils.import_state import should_stop
should_stop(channel_id)
```

---

## 📊 Сводная таблица

| # | Оптимизация | Строк кода | Эффект | Приоритет |
|---|-------------|-----------|--------|-----------|
| 1 | Убрать `sleep(0.1)` | 1 | **-50s / 500 постов** | **P0** |
| 2 | Batch INSERT в БД | ~30 | **-5s**, стабильность | **P0** |
| 3 | Reverse mapping (O(1) lookup) | ~10 | O(1) вместо O(K) | **P1** |
| 4 | Streaming комментариев (1 проход) | ~50 | **-RAM**, -1 проход | **P1** |
| 5 | Параллельное скачивание медиа | ~50 | **-150s / 100 фото** | **P1** |
| 6 | Shared state вместо HTTP | ~20 | -3s, чистота | **P2** |

### Ожидаемый эффект

```
СЕЙЧАС (500 постов, 100 фото, 200 комментариев):  ~5-6 минут

ПОСЛЕ P0 (sleep + batch):                          ~3-4 минуты  (×1.5)
ПОСЛЕ P0 + P1 (+ параллельное медиа + streaming):  ~1-1.5 минуты (×4-6)
ПОСЛЕ ВСЕГО:                                        ~50-80 секунд (×5-7)
```

---

## 📋 Порядок реализации

### Этап 1: P0 — Quick wins

- [ ] Убрать `time.sleep(0.1)` в `telegram_export.py`
- [ ] Создать `_flush_batch()` для записи постов в БД
- [ ] Заменить `requests.post("/api/posts")` на `_flush_batch()` в цикле постов
- [ ] Заменить `requests.post("/api/posts")` на `_flush_batch()` в цикле комментариев
- [ ] `docker compose restart app`
- [ ] Тест: импорт тестового канала, замер времени

### Этап 2: P1 — Основные оптимизации

- [ ] Добавить `reverse_mapping` в `import_all_discussion_comments()`
- [ ] Заменить линейный поиск на `reverse_mapping.get()`
- [ ] Реализовать streaming вариант `import_all_discussion_comments_streaming()`
- [ ] Реализовать параллельное скачивание медиа (двухфазный подход)
- [ ] Тест: импорт канала с 500+ постами и комментариями

### Этап 3: P2 — Cleanup

- [ ] Создать `utils/import_state.py`
- [ ] Заменить HTTP проверки stop/progress на shared state
- [ ] Обновить `api/downloads.py` для чтения из shared state
- [ ] Рассмотреть переход на нативный async Telethon (большой рефакторинг)
