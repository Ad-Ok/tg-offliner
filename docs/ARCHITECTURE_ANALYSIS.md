# Архитектурный Анализ TG-Offliner

## 🔍 ТЕКУЩЕЕ СОСТОЯНИЕ

### Потоки данных: ЗАГРУЗКА ПОСТОВ

Сейчас существует **ТРИ независимых пути** загрузки постов:

```
┌─────────────────────────────────────────────────────────────────┐
│                      posts.vue                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ПУТЬ 1: /api/posts?channel_id=X                               │
│  ├── Используется когда: queryChunk === null                    │
│  ├── Источник: api/posts.py → get_posts()                      │
│  ├── Сортировка: НЕТ (возвращает в порядке из БД)              │
│  ├── Layouts: ✅ Добавлены (после моего фикса)                 │
│  ├── Hidden состояния: Загружаются ОТДЕЛЬНО на фронте          │
│  └── Проблема: ДУБЛИРОВАНИЕ загрузки layouts на фронте         │
│                                                                 │
│  ПУТЬ 2: /api/chunks/{channel_id}/{chunk}/posts                │
│  ├── Используется когда: queryChunk !== null                    │
│  ├── Источник: api/chunks.py → get_chunk_posts()               │
│  ├── Сортировка: ✅ Через sort_order параметр                  │
│  ├── Layouts: ✅ Добавлены (после моего фикса)                 │
│  ├── Hidden состояния: ✅ Уже учтены в chunking.py             │
│  └── Проблема: Конфликт параметров (URL vs сохранённые)        │
│                                                                 │
│  ПУТЬ 3: Повторная загрузка через watch(chunksInfo)            │
│  ├── Используется когда: total_chunks > 1                      │
│  ├── Источник: onChunkSelected() → getChunkPosts()             │
│  ├── Проблема: ПЕРЕЗАПИСЫВАЕТ SSR данные                       │
│  └── Проблема: Конфликт с сохранённой сортировкой              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Хранение настроек: ПОЛНАЯ НЕРАЗБЕРИХА

```
┌─────────────────────────────────────────────────────────────────┐
│                  ГДЕ ХРАНЯТСЯ НАСТРОЙКИ?                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Channel.changes (JSON) - СВАЛКА РАЗНЫХ ДАННЫХ:                │
│  ├── sortOrder: string ('asc'/'desc')                          │
│  ├── preview_pages: array (для freeze layout)                  │
│  └── ??? (неясно что ещё)                                      │
│                                                                 │
│  Channel.print_settings (JSON) - НАСТРОЙКИ ПЕЧАТИ:             │
│  ├── page_size: string ('A4')                                  │
│  ├── margins: array [top, left, bottom, right]                 │
│  ├── items_per_chunk: number (для chunking!)                   │
│  └── overflow_threshold: number (для chunking!)                │
│                                                                 │
│  ПРОБЛЕМА: items_per_chunk в print_settings,                   │
│            а sortOrder в changes - НЕЛОГИЧНО!                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Дублирование кода

```
┌─────────────────────────────────────────────────────────────────┐
│               ОДНА И ТА ЖЕ ЛОГИКА В РАЗНЫХ МЕСТАХ              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Сериализация поста:                                        │
│     - api/posts.py: ручной dict comprehension (строки 48-66)   │
│     - api/chunks.py: serialize_post() функция                  │
│     - РАЗНЫЕ поля! posts.py не имел layout до моего фикса      │
│                                                                 │
│  2. Загрузка layouts:                                          │
│     - api/posts.py: _get_layouts_map()                         │
│     - api/chunks.py: в get_chunk_posts()                       │
│     - posts.vue: ОТДЕЛЬНАЯ загрузка через api.get(/api/layouts)│
│     - Group.vue: syncLayoutFromProps()                         │
│                                                                 │
│  3. Получение discussion_group_id:                             │
│     - api/posts.py: Channel.query.filter_by().first()          │
│     - api/chunks.py: channel.discussion_group_id               │
│     - utils/chunking.py: channel.discussion_group_id           │
│                                                                 │
│  4. Определение скрытых постов:                                │
│     - utils/chunking.py: should_hide_post() ✅ правильно      │
│     - posts.vue: ОТДЕЛЬНАЯ загрузка edits для КАЖДОГО поста    │
│       (200+ запросов к /api/edits/{telegram_id}/{channel_id})  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 1. N+1 Query Problem на фронте

**Файл:** `posts.vue`, строки 180-195

```javascript
const editsPromises = allPosts.map(async (post) => {
  try {
    const response = await api.get(`/api/edits/${post.telegram_id}/${post.channel_id}`)
    // ...
  }
})
```

**Проблема:** Для канала с 200 постами делается 200 HTTP запросов!

**Решение:** Добавить batch endpoint `/api/edits/batch` или включить isHidden в ответ постов.

---

### 2. Конфликт источников сортировки

**Порядок приоритета НЕЯСЕН:**

1. URL параметр `?sort_order=asc`
2. `Channel.changes.sortOrder` (сохранённое)
3. Дефолт `'desc'`

**Текущее поведение:**
- Frontend: `querySortOrder || 'desc'`
- Backend (chunks): `request.args.get('sort_order', changes.get('sortOrder', 'desc'))`

**Проблема:** Frontend и backend могут иметь РАЗНЫЕ значения!

---

### 3. SSR vs Client Hydration Race Condition

**Сценарий:**
1. SSR рендерит страницу с `?chunk=0&sort_order=asc`
2. `initialChunkPosts` загружается с sort_order=asc
3. Client hydration начинается
4. `watch(chunksInfo, { immediate: true })` срабатывает
5. `onChunkSelected(0)` вызывается СНОВА
6. Данные перезаписываются (возможно с другой сортировкой)

---

### 4. Layout не синхронизирован с постами

**Проблема:** Layout хранится в отдельной таблице, но привязка через `grouped_id` — слабая.

```
Post.grouped_id (BigInteger) ← → Layout.grouped_id (BigInteger)
```

**Нет foreign key!** При удалении постов layouts остаются сиротами.

---

## 🎯 РЕКОМЕНДУЕМАЯ АРХИТЕКТУРА

### Принцип: Single Source of Truth

```
┌─────────────────────────────────────────────────────────────────┐
│                    ПРЕДЛАГАЕМАЯ АРХИТЕКТУРА                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. ОДИН API endpoint для постов:                              │
│     GET /api/channels/{channel_id}/posts                       │
│     Query params:                                              │
│       - sort_order: 'asc' | 'desc'                             │
│       - chunk: number (optional)                               │
│       - include_hidden: boolean (для edit mode)                │
│                                                                 │
│  2. Ответ ВСЕГДА включает ВСЁ:                                 │
│     {                                                          │
│       posts: [{                                                │
│         ...post_fields,                                        │
│         layout: {...} | null,    // если grouped_id            │
│         is_hidden: boolean,                                    │
│         comments: [{...}]        // вложенные комментарии      │
│       }],                                                      │
│       chunks_info: {             // метаданные пагинации       │
│         total_chunks: number,                                  │
│         current_chunk: number,                                 │
│         items_per_chunk: number                                │
│       },                                                       │
│       channel: {                 // настройки канала           │
│         sort_order: string,                                    │
│         ...                                                    │
│       }                                                        │
│     }                                                          │
│                                                                 │
│  3. Настройки хранятся в Channel.settings (новое поле JSON):   │
│     {                                                          │
│       "display": {                                             │
│         "sort_order": "desc",                                  │
│         "items_per_chunk": 50                                  │
│       },                                                       │
│       "print": {                                               │
│         "page_size": "A4",                                     │
│         "margins": [20,20,20,20]                               │
│       }                                                        │
│     }                                                          │
│                                                                 │
│  4. Frontend: ОДИН useAsyncData, БЕЗ повторных загрузок       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ❓ ВОПРОСЫ ДЛЯ УТОЧНЕНИЯ

### 1. Приоритеты параметров
**Вопрос:** Какой приоритет у источников настроек?
- URL параметр всегда главный?
- Или сохранённые настройки канала?
- Должен ли URL обновляться при изменении настроек?

### 2. Chunking для ленивой загрузки
**Вопрос:** Нужен ли chunking на фронте, если можно использовать:
- Виртуальный скроллинг (@tanstack/vue-virtual уже установлен!)
- Infinite scroll с подгрузкой

**Альтернатива:** Chunking ТОЛЬКО для экспорта (PDF/IDML), на фронте — виртуальный скроллинг всех постов.

### 3. Структура URL
**Вопрос:** Какой URL правильный?
- `/llamasass/posts` — без chunk
- `/llamasass/posts?chunk=0` — конкретный chunk
- `/llamasass/posts/chunk/0` — chunk как path segment

### 4. Сохранение vs Sharing
**Вопрос:** При отправке ссылки `/llamasass/posts?sort_order=asc`:
- Получатель должен видеть asc?
- Или его собственные сохранённые настройки?

### 5. Scoping настроек
**Вопрос:** Настройки глобальные или per-user?
- Сейчас: глобальные (Channel.changes)
- Должны ли быть per-session? per-user?

---

## 📋 ПЛАН РЕФАКТОРИНГА (если одобрен)

### Фаза 1: Унификация API (Backend)
1. [ ] Создать `/api/channels/{id}/posts` как единый endpoint
2. [ ] Включить layout, is_hidden, comments в ответ
3. [ ] Унифицировать serialize_post() в одном месте
4. [ ] Добавить batch endpoint для edits

### Фаза 2: Упрощение Frontend
1. [ ] Один useAsyncData для постов
2. [ ] Убрать отдельную загрузку layouts
3. [ ] Убрать отдельную загрузку edits
4. [ ] Убрать watch(chunksInfo) race condition

### Фаза 3: Настройки
1. [ ] Унифицировать хранение в Channel.settings
2. [ ] Определить приоритеты (URL vs saved)
3. [ ] Документировать поведение

### Фаза 4: Тесты
1. [ ] Unit тесты для chunking.py
2. [ ] Integration тесты для API
3. [ ] E2E тесты для критичных сценариев

---

## 🔧 БЫСТРЫЕ ФИКСЫ (можно сделать сейчас)

### Fix 1: Убрать N+1 запросы для edits
Добавить `is_hidden` в serialize_post() на бэкенде.

### Fix 2: Убрать race condition в watch
Изменить условие в watch(chunksInfo) — уже сделано частично.

### Fix 3: Унифицировать serialize_post
Создать общую функцию в utils/ и использовать везде.

