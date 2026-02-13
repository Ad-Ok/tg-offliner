# Спецификация: Разбиение контента на части (Chunked Pagination)

## 📋 Обзор

Система разбиения больших каналов (1000+ постов) на управляемые части для:
- Оптимизации загрузки в ленте
- Экспорта в несколько файлов (PDF, IDML)
- Корректного отображения превью каждой части

> **Версия:** 2.2 (API v2)
> **Дата:** 13 февраля 2026
> **Статус:** Миграция завершена. Все страницы используют V2 API для данных. Pages CRUD остаётся на V1 (нет V2 аналога).

---

## 🔄 ТЕКУЩИЙ СТАТУС МИГРАЦИИ

| Компонент | API | Статус |
|-----------|-----|--------|
| **Backend: `utils/chunking.py`** | Shared | ✅ Готов (используется обеими API) |
| **Backend: `api/chunks.py` (v1)** | v1 | ⚠️ Legacy, можно удалить после финального аудита |
| **Backend: `api/v2/channels.py`** | v2 | ✅ Готов (chunking интегрирован в unified endpoint, real total_chunks) |
| **Frontend: `posts.vue`** | v2 | ✅ Мигрирован + ChunkNavigation |
| **Frontend: `preview/index.vue`** | v2 | ✅ Мигрирован + ChunkNavigation |
| **Frontend: `preview/frozen.vue`** | v2 | ✅ Мигрирован (динамические page sizes) |
| **Frontend: `pages.vue`** | v2+v1 | ✅ Посты/канал через V2, Pages CRUD через V1 |
| **Frontend: `GroupEditor.vue`** | v2 | ✅ Мигрирован (apiV2.updateLayout) |
| **Frontend: `usePostEdit.js`** | v2 | ✅ Мигрирован (apiV2.setPostVisibility) |
| **Frontend: `apiV2.js`** | v2 | ✅ Готов |
| **Frontend: `ChunkNavigation.vue`** | — | ✅ Работает в posts.vue и preview |
| ~~Frontend: `chunksService.js` (v1)~~ | v1 | 🗑️ Удалён |
| ~~Frontend: `useChannelPosts.js` (v1)~~ | v1 | 🗑️ Удалён |
| ~~Frontend: `editsService.js` (v1)~~ | v1 | 🗑️ Удалён |
| ~~Frontend: `layoutsService.js` (v1)~~ | v1 | 🗑️ Удалён |

---

## 🎯 Ключевые принципы

### 1. Атомарность контента

**Неделимые единицы:**
- Пост + все его комментарии = неделимая единица
- Медиа-группа (альбом) + все комментарии = неделимая единица
- **Никогда не разрываем пост и его комментарии между частями**

### 2. Подсчет веса

```
Вес единицы = 1 (пост/медиа в группе) + количество_комментариев

Примеры:
- Пост без комментариев: вес = 1
- Пост с 5 комментариями: вес = 6
- Альбом из 4 фото с 3 комментариями: вес = 4 + 3 = 7
```

### 3. Порог переполнения

- Хардкод: `overflow_threshold = 0.2` (20%) в `calculate_chunks()`
- Если chunk заполнен на 80%+ и следующая единица не влезает → начинаем новый chunk
- Если chunk почти пустой, а единица огромная → добавляем как есть (один огромный пост = отдельный chunk)
- **Не выносится как параметр API** — достаточно константы

### 4. Скрытые посты

- По умолчанию скрытые посты **пропускаются** при разбиении
- Параметр `include_hidden=true` включает скрытые посты (для режима редактирования)
- Не учитываются в весе chunk (когда скрыты)

---

## 📊 Архитектура (API v2)

### Backend API Endpoints

#### V2 (Основные — используются фронтом)

| Endpoint | Файл | Описание |
|----------|------|----------|
| `GET /api/v2/channels/{id}/posts` | `api/v2/channels.py` | **Главный endpoint.** Посты + layouts + hidden states + chunking. Query: `sort_order`, `chunk`, `items_per_chunk`, `include_hidden`, `include_comments` |
| `GET /api/v2/channels/{id}/chunks` | `api/v2/channels.py` | Метаданные chunks (для навигации) |
| `PUT /api/v2/channels/{id}/settings` | `api/v2/channels.py` | Обновление настроек (display + export) |
| `POST /api/v2/posts/{channel}/{id}/visibility` | `api/v2/posts.py` | Скрыть/показать пост |
| `GET /api/v2/layouts/{grouped_id}` | `api/v2/layouts.py` | Получить layout галереи |
| `PUT /api/v2/layouts/{grouped_id}` | `api/v2/layouts.py` | Обновить/пересоздать layout галереи |

#### V1 (Legacy — ещё используются preview и export)

| Endpoint | Файл | Описание | Замена в V2 |
|----------|------|----------|-------------|
| `GET /api/posts?channel_id=X` | `api/posts.py` | Все посты (плоский формат) | `GET /api/v2/channels/{id}/posts` |
| `GET /api/chunks/<id>` | `api/chunks.py` | Chunks metadata | `GET /api/v2/channels/{id}/chunks` |
| `GET /api/chunks/<id>/<idx>/posts` | `api/chunks.py` | Посты chunk'а (плоский формат) | `GET /api/v2/channels/{id}/posts?chunk=N` |
| `GET /api/channels/<id>` | `api/channels.py` | Информация о канале | Включена в response `GET .../posts` |
| `GET /api/edits/<tg_id>/<ch_id>` | `api/edits.py` | Edit поста (N+1 запросов!) | `is_hidden` в response, `POST .../visibility` |
| `GET /api/layouts/<grouped_id>` | `api/layouts.py` | Layout группы | `layout` в post response + `GET /api/v2/layouts/` |
| `GET /api/pages?channel_id=X` | `api/pages.py` | Страницы канала | Пока без V2 аналога |
| `POST /api/pages/<id>` | `api/pages.py` | Сохранить frozen layout | Пока без V2 аналога |

### Frontend: Текущее состояние

| Страница | API | Composable | Примечание |
|----------|-----|------------|------------|
| `pages/[channelId]/posts.vue` | **v2** | inline | ✅ Мигрировано + ChunkNavigation |
| `pages/preview/[channelId]/index.vue` | **v2** | inline | ✅ Мигрировано + ChunkNavigation |
| `pages/preview/[channelId]/frozen.vue` | **v2** | inline | ✅ Мигрировано (динамические page sizes) |
| `pages/[channelId]/pages.vue` | **v2+v1** | `usePages` | ✅ Посты/канал через V2, Pages CRUD через V1 |
| `components/system/GroupEditor.vue` | **v2** | inline | ✅ Мигрировано (apiV2.updateLayout) |

### Frontend Services и Composables

| Файл | API | Статус |
|------|-----|--------|
| `services/apiV2.js` | v2 | ✅ Основной клиент V2 |
| `utils/v2Adapter.js` | — | ✅ Трансформация V2 → flat формат для компонентов |
| `composables/usePostEdit.js` | v2 | ✅ Мигрирован (apiV2.setPostVisibility) |
| `composables/usePages.js` | v1 | ⚠️ Pages CRUD остаётся V1 (нет V2 pages endpoint) |
| ~~`services/chunksService.js`~~ | v1 | 🗑️ Удалён |
| ~~`composables/useChannelPosts.js`~~ | v1 | 🗑️ Удалён |
| ~~`services/editsService.js`~~ | v1 | 🗑️ Удалён |
| ~~`services/layoutsService.js`~~ | v1 | 🗑️ Удалён |

### Ключевое отличие V1 vs V2

```
V1 (Legacy):
  1. GET /api/posts?channel_id=X            → плоский список постов
  2. GET /api/chunks/X                       → chunks metadata
  3. GET /api/chunks/X/0/posts               → посты chunk'а (плоский список)
  4. GET /api/edits/:tg_id/:ch_id × N       → N+1 запросов на hidden states
  5. GET /api/layouts/:grouped_id × M        → M запросов на gallery layouts
  = 3 + N + M запросов

V2 (Unified):
  1. GET /api/v2/channels/X/posts?chunk=0    → посты + channel + layouts + hidden + pagination
  = 1 запрос (всё включено)
```

### Формат данных V2

**Response `GET /api/v2/channels/{id}/posts?chunk=0`:**

```json
{
  "channel": {
    "id": "llamasass",
    "name": "Llama Sass",
    "discussion_group_id": 1234567890,
    "settings": {
      "display": { "sort_order": "desc", "items_per_chunk": 50 },
      "export": { "page_size": "A4", "margins": [20, 20, 20, 20] }
    }
  },
  "pagination": {
    "current_chunk": 0,
    "total_chunks": 5,
    "total_posts": 234,
    "total_comments": 89,
    "items_per_chunk": 50,
    "has_next": true,
    "has_prev": false
  },
  "applied_params": {
    "sort_order": "desc",
    "chunk": 0,
    "items_per_chunk": 50,
    "include_hidden": false,
    "include_comments": true,
    "source": "saved"
  },
  "posts": [
    {
      "telegram_id": 123,
      "message": "Hello!",
      "is_hidden": false,
      "author": { "name": "Llama", "avatar": "...", "link": "..." },
      "repost_author": null,
      "layout": null,
      "group_posts": null,
      "comments": [
        { "telegram_id": 456, "message": "Great!", "is_hidden": false, ... }
      ],
      "comments_count": 1
    },
    {
      "telegram_id": 124,
      "grouped_id": 9876543210,
      "layout": { "cells": [...], "columns": 3 },
      "group_posts": [
        { "telegram_id": 124, "media_url": "...", "is_hidden": false },
        { "telegram_id": 125, "media_url": "...", "is_hidden": false }
      ],
      "comments": []
    }
  ]
}
```

**Трансформация на фронте:** `v2Adapter.js` → `transformV2PostsToFlat()` превращает вложенные объекты (author, group_posts, comments) в плоский массив совместимый с существующими компонентами.

### Модели данных (без изменений)

Модели `Post`, `Channel`, `Edit`, `Layout`, `Page` описаны в `models.py`. Chunking использует `Channel.print_settings.items_per_chunk` и `Channel.changes.sortOrder` (сериализуются через `get_channel_settings()` в `api/v2/serializers.py` в единый формат `settings`).

---

## 🔧 Уже реализовано

### 1. Backend: `utils/chunking.py` ✅

Ядро chunking логики. Используется обоими API (v1 и v2).

**Основные функции:**

| Функция | Описание |
|---------|----------|
| `get_visible_posts(channel_id, include_hidden)` | Посты канала (с фильтрацией скрытых) |
| `get_comments_for_post(telegram_id, discussion_id)` | Комментарии из discussion group |
| `build_content_units(channel_id, sort_order, include_hidden)` | Строит `ContentUnit[]` из постов |
| `calculate_chunks(channel_id, items_per_chunk, overflow_threshold, sort_order)` | Разбивает units на chunks |
| `get_chunk_posts_and_comments(chunk)` | Извлекает плоские списки из chunk |

**ContentUnit:**
```python
{
    'post': Post,              # Главный пост
    'group_posts': list[Post], # Все посты медиа-группы
    'comments': list[Post],    # Все комментарии
    'weight': int,             # len(group_posts или 1) + len(comments)
    'is_group': bool,
    'date': str
}
```

### 2. Backend: `api/v2/channels.py` ✅

Unified endpoint с встроенным chunking:

```python
# GET /api/v2/channels/{id}/posts?chunk=0&items_per_chunk=50&sort_order=desc
# → Один запрос возвращает посты + channel + layouts + hidden + pagination

# GET /api/v2/channels/{id}/chunks
# → Метаданные chunks для навигации

# PUT /api/v2/channels/{id}/settings
# → Сохранение items_per_chunk, sort_order, export настроек
```

### 3. Backend: `api/v2/serializers.py` ✅

Единая сериализация:
- `serialize_post_full()` / `serialize_post_basic()` — вложенный формат (author objects, inline comments)
- `get_hidden_posts_map()` — один запрос вместо N+1
- `get_layouts_map()` — один запрос вместо M
- `resolve_param(url, saved, default)` — приоритет параметров

### 4. Frontend: `services/apiV2.js` ✅

V2 клиент:
- `getChannelPosts(channelId, options)` — unified endpoint
- `getChannelChunks(channelId, options)` — chunks metadata
- `updateChannelSettings(channelId, settings)` — сохранение настроек
- `setPostVisibility(channelId, telegramId, hidden)` — скрытие поста
- `updateLayout(groupedId, options)` — gallery layouts

### 5. Frontend: `composables/useChannelPostsV2.js` ✅

Composable с полной поддержкой chunking:
- `fetchPosts()` — загрузка из URL query params
- `goToChunk(n)`, `nextChunk()`, `prevChunk()` — навигация
- `toggleSortOrder()`, `saveSettings()`, `resetToSaved()` — настройки
- `togglePostVisibility()`, `updatePostLayout()` — inline actions

### 6. Frontend: `pages/[channelId]/posts.vue` ✅

Мигрирован на V2:
- `useAsyncData` → `getChannelPosts()` с transform через `v2Adapter`
- URL query watcher для клиентской навигации
- `ChunkNavigation` component при `pagination.total_chunks > 1`

### 7. Backend V1: `api/chunks.py` ⚠️ Legacy

Отдельные endpoints — всё ещё используются preview:
- `GET /api/chunks/<channel_id>` → chunks metadata
- `GET /api/chunks/<channel_id>/<index>/posts` → посты chunk'а (плоский формат)

**Будет удалён** после миграции preview на V2.

---

## 🧪 Тестирование

### Существующие тесты ✅

| Файл | Что тестирует | API |
|------|---------------|-----|
| `tests/test_chunking.py` | Unit: `get_visible_posts`, `build_content_units`, `calculate_chunks` | Core |
| `tests/test_chunking.py` | API: `GET /api/chunks/{id}`, `GET /api/chunks/{id}/{idx}/posts` | v1 |
| `tests/test_api_v2.py` | API v2: posts endpoint, settings, visibility | v2 |

### Нужно добавить

| Что | Файл | Описание |
|-----|------|----------|
| V2 chunking API tests | `tests/test_api_v2.py` | Тесты `?chunk=N` в unified endpoint |
| V2 chunks metadata test | `tests/test_api_v2.py` | Тест `GET /api/v2/channels/{id}/chunks` |
| Preview V2 integration | Новый файл или `test_api_v2.py` | Тест загрузки постов для preview через V2 |

### Запуск тестов

```bash
# Backend тесты
cd /Users/adoknov/work/tg/tg-offliner
python -m pytest tests/test_chunking.py -v
python -m pytest tests/test_api_v2.py -v

# Все тесты
python -m pytest tests/ -v

# Frontend тесты
cd tg-offliner-frontend
npx vitest run
```

---

## 📱 Frontend: Текущая реализация и миграция

### Уже реализовано ✅

#### services/apiV2.js

```javascript
// Unified posts + chunking
getChannelPosts(channelId, { sortOrder, chunk, itemsPerChunk, includeHidden, includeComments })

// Chunks metadata для навигации
getChannelChunks(channelId, { sortOrder, itemsPerChunk })

// Настройки
updateChannelSettings(channelId, { display: { sort_order, items_per_chunk }, export: {...} })

// Actions
setPostVisibility(channelId, telegramId, hidden)
updateLayout(groupedId, { channelId, columns, borderWidth, noCrop, regenerate })
```

#### composables/useChannelPostsV2.js

```javascript
const {
  posts, channel, pagination, appliedParams, loading, error,
  currentChunk, currentSortOrder, hasNextChunk, hasPrevChunk, totalChunks,
  fetchPosts, toggleSortOrder, saveSettings, resetToSaved,
  goToChunk, nextChunk, prevChunk,
  togglePostVisibility, updatePostLayout
} = useChannelPostsV2(channelId)
```

#### pages/[channelId]/posts.vue

Полностью мигрирован: V2 API → `v2Adapter` transform → компоненты.

### Нужно мигрировать ❌

#### 1. `pages/preview/[channelId]/index.vue` — Flow Preview

**Текущий паттерн (V1):**
```javascript
// 1. Загрузка постов (V1 flat format)
const postsResponse = await api.get(`/api/posts?channel_id=${channelId}`)
const discussionResponse = await api.get(`/api/posts?channel_id=${discussionId}`)

// 2. N+1 запросов на hidden states
for (const post of allPosts) {
  const edit = await api.get(`/api/edits/${post.telegram_id}/${post.channel_id}`)
  if (edit?.changes?.hidden === 'true') post.isHidden = true
}

// 3. M запросов на gallery layouts
for (const groupedId of uniqueGroups) {
  const layout = await api.get(`/api/layouts/${groupedId}?channel_id=${channelId}`)
}
```

**Целевой паттерн (V2):**
```javascript
// 1 запрос — всё включено
const response = await getChannelPosts(channelId, {
  includeHidden: true,      // для preview нужны все посты
  includeComments: true,
  // chunk: null             // для preview загружаем ВСЕ посты (без chunking)
  // ... или chunk: N        // если preview с chunking
})

const posts = transformV2PostsToFlat(response.posts, response.channel.discussion_group_id)
const channel = response.channel
```

**Что меняется:**
- Удаляются N+1 запросов на edits → `is_hidden` уже в response
- Удаляются M запросов на layouts → `layout` уже в post
- Один `getChannelPosts()` вместо 3+ waterfall запросов
- Нужно решить: preview загружает все посты или по chunks?

#### 2. `pages/preview/[channelId]/frozen.vue` — Frozen Preview

**Текущий паттерн (V1):**
```javascript
const postsResponse = await api.get(`/api/posts?channel_id=${channelId}`)
const frozenData = await api.get(`/api/pages/${channelId}/frozen`)
```

**Целевой паттерн (V2):**
```javascript
// Для постов — V2
const response = await getChannelPosts(channelId, { includeHidden: true })
const posts = transformV2PostsToFlat(response.posts, response.channel.discussion_group_id)

// Для frozen layout — пока V1 (нет V2 аналога для pages)
const frozenData = await api.get(`/api/pages/${channelId}/frozen`)
```

#### 3. Chunking в Preview

**Решение:** Вариант **B** — Preview с chunking. Пользователь видит ту часть, которую экспортирует.

**Реализация в два этапа:**
1. **Этап 1 (текущий):** Миграция preview на V2 API без chunking (все посты одним запросом). Устранение N+1 запросов.
2. **Этап 2 (следующий):** Добавление chunk selector в preview. Каждый chunk = отдельный файл при экспорте.

#### 4. Frozen Preview: динамические настройки страницы

**Проблема:** `frozen.vue` использует хардкод A4 (`210mm × 297mm`, `20mm` padding) вместо `channel.print_settings`.

**Решение:** Читать `page_size` и `margins` из `channel.settings.export` (V2 response) и применять динамически.

#### 5. Preview: дублирование запроса channel info

**Проблема:** `preview/index.vue` загружает channel info **дважды** — один раз внутри `useAsyncData('preview-posts')`, второй раз отдельным `useAsyncData('preview-channelInfo')`. Это расточительно и не нужно.

**Решение:** При миграции на V2 channel info приходит в response `getChannelPosts()` — отдельный запрос не нужен.

#### 6. GroupEditor: миграция layoutsService → apiV2

**Проблема:** `GroupEditor.vue` использует `layoutsService.js` (V1: `POST /api/layouts/{id}/reload`, `PATCH /api/layouts/{id}/border`), а V2 объединяет всё в `PUT /api/v2/layouts/{id}` с параметрами `regenerate`, `border_width`, `columns`, `no_crop`.

**Решение:** Заменить `layoutsService` на `apiV2.updateLayout()` в `GroupEditor.vue`.

### Legacy код для удаления (после миграции)

| Файл | Причина удаления |
|------|-----------------|
| `services/chunksService.js` | Заменён `apiV2.getChannelPosts(?chunk=N)` |
| `composables/useChannelPosts.js` | Заменён `useChannelPostsV2.js` |
| Inline V1 код в `preview/index.vue` | Будет заменён на V2 вызовы |
| Inline V1 код в `preview/frozen.vue` | Будет заменён на V2 вызовы |

Backend V1 endpoints (`api/chunks.py`, `api/posts.py`) **НЕ удаляем** — они нужны для export endpoints на бэкенде.

---

## 📋 План миграции на API v2 (Frontend)

### Фаза 1: Preview → V2 (приоритет) ✅ ЗАВЕРШЕНО

**Цель:** Мигрировать `preview/[channelId]/index.vue` на API v2, убрать N+1 запросов.

> **Решение:** Используем `getChannelPosts()` напрямую в `useAsyncData`. N+1 запросов устранены.

**Выполнено:**
- [x] Заменить загрузку данных в `useAsyncData` — один V2 запрос вместо waterfall
- [x] Убрать inline цикл загрузки edits (N+1 → 0 запросов)
- [x] Убрать inline цикл загрузки layouts (M → 0 запросов)
- [x] Page break calculation работает с V2 данными
- [x] PrintSettingsSidebar работает (использует channel info из V2 response)
- [x] Добавлен ChunkNavigation компонент в preview
- [x] При выборе chunk — refresh данных + пересчёт page breaks

### Фаза 2: Frozen Preview → V2 ✅ ЗАВЕРШЕНО

**Выполнено:**
- [x] Заменена загрузка постов на V2 (`getChannelPosts()`)
- [x] Убрано дублирование channel info запроса
- [x] Динамические page size и margins из `PAGE_SIZES` (print-config.json)
- [x] Absolute positioning работает с V2 данными
- Frozen layout загружается через V1 `/api/pages/` — V2 аналога пока нет (опционально)

### Фаза 3: usePostEdit + GroupEditor → V2 ✅ ЗАВЕРШЕНО

**Выполнено:**
- [x] `usePostEdit.js` обновлён на V2 (`apiV2.setPostVisibility()`)
- [x] `GroupEditor.vue` обновлён на V2 (`apiV2.updateLayout()`)
- [x] Emit events работают с V2 response

### Фаза 4: Очистка legacy кода ✅ ЗАВЕРШЕНО

**Удалены все legacy файлы:**
- [x] `services/chunksService.js`
- [x] `composables/useChannelPosts.js`
- [x] `services/editsService.js`
- [x] `services/layoutsService.js`
- [x] `__tests__/layoutsService.test.js`

### Фаза 5: Backend cleanup (по желанию)

- [ ] Добавить deprecation headers в V1 endpoints
- [ ] Рассмотреть V2 endpoint для pages (`/api/v2/pages/`)
- [ ] Рассмотреть удаление `api/chunks.py` после полной миграции

---

## 📋 Чеклист (сводный)

### ✅ Готово

- [x] `utils/chunking.py` — ядро chunking
- [x] `api/v2/channels.py` — unified endpoint с chunking + real total_chunks
- [x] `api/v2/serializers.py` — единая сериализация + hidden/layouts maps
- [x] `api/v2/posts.py` — visibility endpoint
- [x] `api/v2/layouts.py` — layouts endpoint
- [x] `services/apiV2.js` — V2 клиент
- [x] `utils/v2Adapter.js` — трансформация V2 → flat
- [x] `pages/[channelId]/posts.vue` — мигрирован на V2 + ChunkNavigation
- [x] `pages/preview/[channelId]/index.vue` — мигрирован на V2 + ChunkNavigation
- [x] `pages/preview/[channelId]/frozen.vue` — мигрирован на V2 (динамические page sizes)
- [x] `pages/[channelId]/pages.vue` — посты/канал через V2 (Pages CRUD остаётся V1)
- [x] `composables/usePostEdit.js` — мигрирован на V2 (apiV2.setPostVisibility)
- [x] `components/system/GroupEditor.vue` — мигрирован на V2 (apiV2.updateLayout)
- [x] Удалён `services/chunksService.js` (legacy V1)
- [x] Удалён `composables/useChannelPosts.js` (legacy V1)
- [x] Удалён `services/editsService.js` (legacy V1)
- [x] Удалён `services/layoutsService.js` (legacy V1)
- [x] Удалён `__tests__/layoutsService.test.js`
- [x] `tests/test_chunking.py` — unit тесты chunking (27/27 pass)
- [x] `tests/test_api_v2.py` — тесты V2 endpoints (19/19 pass)

### ❌ Нужно сделать (Backend, опционально)

- [ ] V2 endpoint для pages (`/api/v2/pages/`)
- [ ] Deprecation warnings на V1 endpoints
- [ ] Рассмотреть удаление `api/chunks.py` после финального аудита

---

## 📚 Примеры использования (API v2)

### Frontend: Лента постов с chunking

```javascript
// pages/[channelId]/posts.vue — уже реализовано
import { getChannelPosts } from '~/services/apiV2'
import { transformV2PostsToFlat } from '~/utils/v2Adapter'

// Загрузка первого chunk'а
const response = await getChannelPosts('llamasass', {
  chunk: 0,
  itemsPerChunk: 50,
  sortOrder: 'desc',
  includeComments: true,
  includeHidden: true,
})

// response.pagination.total_chunks → 5
// response.pagination.has_next → true
// response.posts → 50 постов с inline comments, layouts, hidden states

const flatPosts = transformV2PostsToFlat(response.posts, response.channel.discussion_group_id)
```

### Frontend: Preview без chunking

```javascript
// Загрузка ВСЕХ постов для preview
const response = await getChannelPosts('llamasass', {
  // chunk: null — не указываем → все посты
  includeHidden: true,
  includeComments: true,
})

// response.pagination.total_chunks → 1
// response.pagination.total_posts → 234
// response.posts → все 234 поста
```

### Frontend: Preview с chunking (будущее)

```javascript
// Пользователь экспортирует часть 2 из 5
const response = await getChannelPosts('llamasass', {
  chunk: 1,              // часть 2 (0-indexed)
  itemsPerChunk: 50,
  includeHidden: false,  // для экспорта скрытые не нужны
  includeComments: true,
})

// Рендерим только эту часть для PDF
```

### Frontend: Навигация по chunks

```javascript
// Получить метаданные для навигации
import { getChannelChunks } from '~/services/apiV2'

const chunks = await getChannelChunks('llamasass', {
  sortOrder: 'desc',
  itemsPerChunk: 50,
})

// chunks.total_chunks → 5
// chunks.chunks → [{index: 0, posts_count: 48, date_from: "2025-12-25", date_to: "2025-12-20"}, ...]
```

### Сценарий 1: 100 постов без комментариев

```
items_per_chunk = 50

GET /api/v2/channels/X/posts?chunk=0  → 50 постов
GET /api/v2/channels/X/posts?chunk=1  → 50 постов

Экспорт:
- channel_part1.pdf (chunk 0)
- channel_part2.pdf (chunk 1)
```

### Сценарий 2: 50 постов, 2-3 комментария в каждом

```
items_per_chunk = 50

Пост 1 (вес 3) + Пост 2 (вес 4) + ... + Пост ~15 (вес ~3) = ~50
→ Chunk 0: ~15 постов + ~35 комментариев

GET /api/v2/channels/X/posts?chunk=0  → 15 постов с inline comments
GET /api/v2/channels/X/posts?chunk=1  → 15 постов с inline comments
...
```

### Сценарий 3: 2 поста по 100+ комментариев

```
items_per_chunk = 50, overflow = 0.2 → max = 60

Пост 1: вес = 151 (1 + 150 комментариев)
→ Chunk 0: только Пост 1 (вес 151, превышает, но chunk пустой)

Пост 2: вес = 121 (1 + 120 комментариев)
→ Chunk 1: только Пост 2 (вес 121)

GET /api/v2/channels/X/posts?chunk=0  → 1 пост + 150 inline comments
GET /api/v2/channels/X/posts?chunk=1  → 1 пост + 120 inline comments
```
