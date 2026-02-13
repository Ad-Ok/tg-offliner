# Спецификация: Разбиение контента на части (Chunked Pagination)

## 📋 Обзор

Система разбиения больших каналов (1000+ постов) на управляемые части для:
- Оптимизации загрузки в ленте
- Экспорта в несколько файлов (PDF, IDML)
- Корректного отображения превью каждой части

> **Версия:** 2.0 (API v2)
> **Дата:** 12 февраля 2026
> **Статус:** Частично реализовано. Posts page мигрирована на v2. Preview и Pages — ещё на v1.

---

## 🔄 ТЕКУЩИЙ СТАТУС МИГРАЦИИ

| Компонент | API | Статус |
|-----------|-----|--------|
| **Backend: `utils/chunking.py`** | Shared | ✅ Готов (используется обеими API) |
| **Backend: `api/chunks.py` (v1)** | v1 | ⚠️ Legacy, используется preview |
| **Backend: `api/v2/channels.py`** | v2 | ✅ Готов (chunking интегрирован в unified endpoint) |
| **Frontend: `posts.vue`** | v2 | ✅ Мигрирован |
| **Frontend: `useChannelPostsV2.js`** | v2 | ✅ Готов |
| **Frontend: `apiV2.js`** | v2 | ✅ Готов |
| **Frontend: `preview/index.vue`** | v1 | ❌ Нужна миграция |
| **Frontend: `preview/frozen.vue`** | v1 | ❌ Нужна миграция |
| **Frontend: `chunksService.js` (v1)** | v1 | ⚠️ Legacy, используется preview |
| **Frontend: `useChannelPosts.js` (v1)** | v1 | ⚠️ Legacy, используется preview |

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

- Настраиваемый порог: `overflow_threshold` (по умолчанию 0.2 = 20%)
- Если chunk заполнен на 80%+ и следующая единица не влезает → начинаем новый chunk
- Если chunk почти пустой, а единица огромная → добавляем как есть (один огромный пост = отдельный chunk)

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
| `pages/[channelId]/posts.vue` | **v2** | `useChannelPostsV2` | ✅ Мигрировано |
| `pages/preview/[channelId]/index.vue` | **v1** | Нет (inline) | ❌ N+1 запросов на edits/layouts |
| `pages/preview/[channelId]/frozen.vue` | **v1** | Нет (inline) | ❌ V1 API |
| `pages/[channelId]/pages.vue` | **v1** | `usePages` | ❌ V1 API |

### Frontend Services и Composables

| Файл | API | Статус |
|------|-----|--------|
| `services/apiV2.js` | v2 | ✅ Основной клиент V2 |
| `composables/useChannelPostsV2.js` | v2 | ✅ Composable для posts page |
| `utils/v2Adapter.js` | — | ✅ Трансформация V2 → flat формат для компонентов |
| `services/chunksService.js` | v1 | ⚠️ Legacy. Заменён `apiV2.getChannelPosts(?chunk=N)` |
| `composables/useChannelPosts.js` | v1 | ⚠️ Legacy. Заменён `useChannelPostsV2.js` |
| `services/editsService.js` | v1 | ⚠️ Legacy. Заменён `apiV2.setPostVisibility()` |
| `services/layoutsService.js` | v1 | ⚠️ Legacy. Заменён `apiV2.updateLayout()` |

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

**Вопрос:** Нужен ли chunking в preview?

**Варианты:**
- **A) Без chunking:** Preview загружает все посты одним запросом (`chunk=null`). Подходит для каналов < 500 постов.
- **B) С chunking:** Preview загружает по chunk'ам. Каждый chunk = отдельный файл при экспорте в PDF/IDML. Пользователь выбирает chunk для preview.
- **C) Гибридный:** По умолчанию без chunking, но при включении "Export mode" → chunking.

**Рекомендация:** Вариант **B** — Preview с chunking. Пользователь видит ту часть, которую экспортирует.

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

### Фаза 1: Preview → V2 (приоритет)

**Цель:** Мигрировать `preview/[channelId]/index.vue` на API v2, убрать N+1 запросов.

#### Шаг 1.1: Создать composable `usePreviewPostsV2.js`

```javascript
// composables/usePreviewPostsV2.js
// Специализированный composable для preview:
// - Загружает ВСЕ посты (без chunking) или по chunk'ам
// - include_hidden: true (для показа скрытых с маркером)
// - include_comments: true
// - Применяет usePostFiltering для фильтрации unsupported media
// - Предоставляет методы для работы с visibility

import { getChannelPosts } from '~/services/apiV2'
import { transformV2PostsToFlat } from '~/utils/v2Adapter'

export function usePreviewPostsV2(channelId, options = {}) {
  const posts = ref([])
  const channel = ref(null)
  const pagination = ref(null)
  const loading = ref(false)

  async function loadAllPosts() {
    loading.value = true
    const response = await getChannelPosts(channelId, {
      includeHidden: true,
      includeComments: true,
      // chunk: null → все посты
    })
    posts.value = transformV2PostsToFlat(
      response.posts, 
      response.channel.discussion_group_id
    )
    channel.value = response.channel
    pagination.value = response.pagination
    loading.value = false
    return response
  }

  async function loadChunk(chunkIndex) {
    loading.value = true
    const response = await getChannelPosts(channelId, {
      includeHidden: true,
      includeComments: true,
      chunk: chunkIndex,
    })
    posts.value = transformV2PostsToFlat(
      response.posts,
      response.channel.discussion_group_id
    )
    channel.value = response.channel
    pagination.value = response.pagination
    loading.value = false
    return response
  }

  return { posts, channel, pagination, loading, loadAllPosts, loadChunk }
}
```

**Задачи:**
- [ ] Создать `composables/usePreviewPostsV2.js`
- [ ] Интегрировать `usePostFiltering` в composable (или в preview page)
- [ ] Убедиться что `v2Adapter` правильно маппит `isHidden` для preview

#### Шаг 1.2: Мигрировать `preview/index.vue`

**Что менять:**
1. Заменить `useAsyncData('preview-posts', ...)` — убрать V1 waterfall (posts → edits × N → layouts × M)
2. Использовать `usePreviewPostsV2` или напрямую `getChannelPosts()`
3. Убрать inline загрузку edits/layouts — они уже в V2 response
4. Оставить всю остальную логику: page breaks, freeze, sidebar

```diff
- // V1: 3 + N + M запросов
- const postsResponse = await api.get(`/api/posts?channel_id=${channelId}`)
- for (const post of allPosts) {
-   const edit = await api.get(`/api/edits/${post.telegram_id}/${post.channel_id}`)
- }
- for (const gid of groups) {
-   const layout = await api.get(`/api/layouts/${gid}?channel_id=${channelId}`)
- }

+ // V2: 1 запрос
+ const response = await getChannelPosts(channelId, {
+   includeHidden: true,
+   includeComments: true,
+ })
+ const allPosts = transformV2PostsToFlat(response.posts, response.channel.discussion_group_id)
```

**Задачи:**
- [ ] Заменить загрузку данных в `useAsyncData`
- [ ] Убрать inline цикл загрузки edits (N+1 → 0 запросов)
- [ ] Убрать inline цикл загрузки layouts (M → 0 запросов)
- [ ] Проверить что page break calculation работает с V2 данными
- [ ] Проверить что freeze layout работает с V2 данными
- [ ] Проверить что PrintSettingsSidebar работает (использует channel info)

#### Шаг 1.3: Добавить chunking в Preview (опционально)

Если preview должен поддерживать chunking:

```vue
<!-- ChunkSelector для preview -->
<div v-if="pagination?.total_chunks > 1" class="print:hidden mb-4">
  <select v-model="selectedChunk" @change="loadChunkPosts">
    <option v-for="i in pagination.total_chunks" :key="i-1" :value="i-1">
      Часть {{ i }} ({{ chunkDateRange(i-1) }})
    </option>
  </select>
</div>
```

**Задачи:**
- [ ] Добавить UI для выбора chunk в preview
- [ ] При экспорте в PDF — экспортировать текущий выбранный chunk
- [ ] Обновить `freezeCurrentLayout()` для работы с chunk'ами

### Фаза 2: Frozen Preview → V2

#### Шаг 2.1: Мигрировать `preview/frozen.vue`

**Что менять:**
1. Заменить `api.get('/api/posts?...')` на `getChannelPosts()`
2. Оставить загрузку frozen layout через V1 (`/api/pages/{id}/frozen`) — V2 аналога пока нет

**Задачи:**
- [ ] Заменить загрузку постов на V2
- [ ] Проверить что absolute positioning работает с V2 данными
- [ ] Протестировать с реальными frozen layouts

### Фаза 3: Очистка legacy кода

#### Шаг 3.1: Удалить V1 frontend код

После того как ВСЕ страницы мигрированы:

- [ ] Удалить `services/chunksService.js`
- [ ] Удалить `composables/useChannelPosts.js`
- [ ] Проверить что `services/editsService.js` не используется нигде
- [ ] Проверить что `services/layoutsService.js` не используется нигде
- [ ] Удалить неиспользуемые сервисы

#### Шаг 3.2: Обновить `usePostEdit.js`

`usePostEdit.js` сейчас использует V1 `editsService`. Мигрировать на `apiV2.setPostVisibility()`:

```diff
- import('~/services/editsService').then(({ setPostHidden }) => {
-   setPostHidden(channelId, telegramId, hidden)
- })

+ import('~/services/apiV2').then(({ setPostVisibility }) => {
+   setPostVisibility(channelId, telegramId, hidden)
+ })
```

**Задачи:**
- [ ] Обновить `usePostEdit.js` на V2 API
- [ ] Убедиться что все компоненты используют V2 для visibility

### Фаза 4: Backend cleanup (по желанию)

- [ ] Добавить deprecation headers в V1 endpoints
- [ ] Рассмотреть V2 endpoint для pages (`/api/v2/pages/`)
- [ ] Рассмотреть удаление `api/chunks.py` после полной миграции

---

## 📋 Чеклист (сводный)

### ✅ Готово

- [x] `utils/chunking.py` — ядро chunking
- [x] `api/v2/channels.py` — unified endpoint с chunking
- [x] `api/v2/serializers.py` — единая сериализация + hidden/layouts maps
- [x] `api/v2/posts.py` — visibility endpoint
- [x] `api/v2/layouts.py` — layouts endpoint
- [x] `services/apiV2.js` — V2 клиент
- [x] `composables/useChannelPostsV2.js` — composable с chunking
- [x] `utils/v2Adapter.js` — трансформация V2 → flat
- [x] `pages/[channelId]/posts.vue` — мигрирован на V2
- [x] `tests/test_chunking.py` — unit тесты chunking
- [x] `tests/test_api_v2.py` — тесты V2 endpoints

### ❌ Нужно сделать (Frontend)

- [ ] Создать `composables/usePreviewPostsV2.js`
- [ ] Мигрировать `preview/[channelId]/index.vue` на V2
- [ ] Мигрировать `preview/[channelId]/frozen.vue` на V2
- [ ] Обновить `composables/usePostEdit.js` на V2
- [ ] Добавить chunking selector в preview (опционально)
- [ ] Удалить `services/chunksService.js` (legacy V1)
- [ ] Удалить `composables/useChannelPosts.js` (legacy V1)
- [ ] Добавить V2 тесты для chunking в unified endpoint

### ❌ Нужно сделать (Backend, опционально)

- [ ] V2 endpoint для pages (`/api/v2/pages/`)
- [ ] Deprecation warnings на V1 endpoints
- [ ] Тесты `?chunk=N` в V2 endpoints

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
