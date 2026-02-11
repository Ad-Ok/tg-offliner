# API v2 Спецификация

## 🎯 ЦЕЛИ

1. **Единый endpoint** для получения постов канала
2. **Предсказуемое поведение** параметров
3. **Нет дублирования** логики между бэкендом и фронтом
4. **Чистое разделение** уровней настроек
5. **Обратная совместимость** — старые endpoints работают

---

## 📊 УРОВНИ НАСТРОЕК

```
┌─────────────────────────────────────────────────────────────────┐
│                    ИЕРАРХИЯ НАСТРОЕК                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  УРОВЕНЬ ПОСТА (Post)                                          │
│  ├── is_hidden: boolean        → Edit.changes.hidden           │
│  ├── edited_message: string    → Edit.changes.message          │
│  └── print_settings: JSON      → Post.print_settings           │
│      ├── text_columns: number                                  │
│      ├── image_placement: string                               │
│      └── page_break_before: boolean                            │
│                                                                 │
│  УРОВЕНЬ ГАЛЕРЕИ (Layout)                                      │
│  ├── cells: array              → Layout.json_data.cells        │
│  ├── border_width: string      → Layout.json_data.border_width │
│  ├── columns: number           → Layout.json_data.columns      │
│  └── no_crop: boolean          → Layout.json_data.no_crop      │
│                                                                 │
│  УРОВЕНЬ КАНАЛА (Channel)                                      │
│  ├── DISPLAY настройки:                                        │
│  │   ├── sort_order: 'asc'|'desc'                              │
│  │   └── items_per_chunk: number                               │
│  ├── EXPORT настройки:                                         │
│  │   ├── page_size: 'A4'|'A3'|...                              │
│  │   ├── margins: [top, right, bottom, left]                   │
│  │   └── include_comments: boolean                             │
│  └── META (read-only):                                         │
│      ├── name, avatar, description                             │
│      └── discussion_group_id                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 ФЛОУ НАСТРОЕК: URL vs СОХРАНЁННЫЕ

### Принцип: "URL для sharing, DB для persistence"

```
┌─────────────────────────────────────────────────────────────────┐
│                    ПРИОРИТЕТ ПАРАМЕТРОВ                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. URL параметр (если есть)                                   │
│     └── Для sharing ссылок, временный override                 │
│                                                                 │
│  2. Сохранённые настройки канала (Channel.settings)            │
│     └── Персистентные настройки пользователя                   │
│                                                                 │
│  3. Дефолтные значения (константы)                             │
│     └── Fallback если ничего не задано                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Флоу сохранения настроек

```
┌─────────────────────────────────────────────────────────────────┐
│              ОТЛОЖЕННОЕ СОХРАНЕНИЕ (Deferred Save)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Frontend State:                                                │
│  ├── currentSettings: ref({...})  // текущие настройки         │
│  ├── savedSettings: ref({...})    // сохранённые в БД          │
│  └── hasUnsavedChanges: computed  // currentSettings !== saved │
│                                                                 │
│  Флоу:                                                          │
│  1. Загрузка страницы:                                          │
│     - Читаем URL параметры                                     │
│     - Загружаем savedSettings из API                           │
│     - currentSettings = URL params || savedSettings || defaults│
│                                                                 │
│  2. Изменение настройки (например, sort_order):                │
│     - currentSettings.sort_order = 'asc'                       │
│     - URL обновляется: ?sort_order=asc                         │
│     - hasUnsavedChanges = true                                 │
│     - Показываем индикатор "Несохранённые изменения"           │
│                                                                 │
│  3. Сохранение (явное действие):                               │
│     - PUT /api/v2/channels/{id}/settings                       │
│     - savedSettings = currentSettings                          │
│     - hasUnsavedChanges = false                                │
│     - URL очищается от параметров (теперь они сохранены)       │
│                                                                 │
│  4. Сброс изменений:                                           │
│     - currentSettings = savedSettings                          │
│     - URL очищается                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📡 API v2 ENDPOINTS

### 1. Получение постов канала (ГЛАВНЫЙ)

```
GET /api/v2/channels/{channel_id}/posts
```

**Query Parameters:**

| Параметр | Тип | Default | Описание |
|----------|-----|---------|----------|
| `sort_order` | `'asc'│'desc'` | saved или `'desc'` | Порядок сортировки |
| `chunk` | `number` | `null` | Номер chunk (null = все посты) |
| `items_per_chunk` | `number` | saved или `50` | Размер chunk |
| `include_hidden` | `boolean` | `false` | Включать скрытые посты |
| `include_comments` | `boolean` | `true` | Включать комментарии |

**Response:**

```json
{
  "channel": {
    "id": "llamasass",
    "name": "Llama Sass",
    "avatar": "/downloads/llamasass/avatars/channel.jpg",
    "discussion_group_id": 1234567890,
    "settings": {
      "display": {
        "sort_order": "desc",
        "items_per_chunk": 50
      },
      "export": {
        "page_size": "A4",
        "margins": [20, 20, 20, 20]
      }
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
    "include_hidden": false,
    "source": "saved"  // "url" | "saved" | "default"
  },
  
  "posts": [
    {
      "id": 1,
      "telegram_id": 123,
      "channel_id": "llamasass",
      "date": "2025-12-25T12:00:00",
      "message": "Hello world!",
      "media_url": "/downloads/llamasass/media/123_media.jpg",
      "thumb_url": "/downloads/llamasass/thumbs/123_thumb.jpg",
      "media_type": "MessageMediaPhoto",
      "mime_type": "image/jpeg",
      
      "author": {
        "name": "Llama",
        "avatar": "/downloads/llamasass/avatars/author.jpg",
        "link": "https://t.me/llamasass"
      },
      
      "repost_author": null,
      
      "reactions": {"❤️": 10, "👍": 5},
      
      "grouped_id": null,
      "reply_to": null,
      
      "is_hidden": false,
      "is_edited": false,
      
      "layout": null,
      
      "comments_count": 3,
      "comments": [
        {
          "id": 10,
          "telegram_id": 456,
          "channel_id": "1234567890",
          "message": "Great post!",
          "author": {...},
          "is_hidden": false
        }
      ]
    },
    
    {
      "id": 2,
      "telegram_id": 124,
      "grouped_id": 9876543210,
      
      "layout": {
        "cells": [...],
        "total_width": 100,
        "total_height": 75,
        "border_width": "2",
        "columns": 3
      },
      
      "group_posts": [
        {"telegram_id": 124, "media_url": "...", "is_hidden": false},
        {"telegram_id": 125, "media_url": "...", "is_hidden": false},
        {"telegram_id": 126, "media_url": "...", "is_hidden": true}
      ],
      
      "comments": [...]
    }
  ]
}
```

### 2. Обновление настроек канала

```
PUT /api/v2/channels/{channel_id}/settings
```

**Request Body:**

```json
{
  "display": {
    "sort_order": "asc",
    "items_per_chunk": 100
  },
  "export": {
    "page_size": "A3",
    "margins": [15, 15, 15, 15]
  }
}
```

**Response:**

```json
{
  "success": true,
  "settings": {...}
}
```

### 3. Скрытие/показ поста

```
POST /api/v2/posts/{channel_id}/{telegram_id}/visibility
```

**Request Body:**

```json
{
  "hidden": true
}
```

### 4. Обновление layout галереи

```
PUT /api/v2/layouts/{grouped_id}
```

**Request Body:**

```json
{
  "channel_id": "llamasass",
  "columns": 3,
  "border_width": "2",
  "no_crop": false,
  "regenerate": true  // пересчитать cells
}
```

### 5. Получение chunks metadata (для навигации)

```
GET /api/v2/channels/{channel_id}/chunks
```

**Response:**

```json
{
  "channel_id": "llamasass",
  "total_chunks": 5,
  "items_per_chunk": 50,
  "chunks": [
    {
      "index": 0,
      "posts_count": 48,
      "comments_count": 23,
      "date_from": "2025-12-25",
      "date_to": "2025-12-20"
    },
    ...
  ]
}
```

---

## 🗄️ ИЗМЕНЕНИЯ В МОДЕЛЯХ

### Channel Model (обновлённый)

```python
class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    avatar = db.Column(db.String, nullable=True)
    description = db.Column(db.Text, nullable=True)
    creation_date = db.Column(db.String, nullable=True)
    subscribers = db.Column(db.String, nullable=True)
    posts_count = db.Column(db.Integer, nullable=True)
    comments_count = db.Column(db.Integer, nullable=True)
    discussion_group_id = db.Column(db.BigInteger, nullable=True)
    
    # НОВОЕ: Унифицированные настройки
    settings = db.Column(JSON, nullable=False, default={
        "display": {
            "sort_order": "desc",
            "items_per_chunk": 50
        },
        "export": {
            "page_size": "A4",
            "margins": [20, 20, 20, 20],
            "include_comments": True
        }
    })
    
    # DEPRECATED: Будут удалены после миграции
    changes = db.Column(JSON, nullable=True)       # → settings.display
    print_settings = db.Column(JSON, nullable=True) # → settings.export
```

### Миграция данных

```python
def migrate_channel_settings():
    """Миграция старых настроек в новый формат"""
    channels = Channel.query.all()
    
    for channel in channels:
        new_settings = {
            "display": {
                "sort_order": (channel.changes or {}).get("sortOrder", "desc"),
                "items_per_chunk": (channel.print_settings or {}).get("items_per_chunk", 50)
            },
            "export": {
                "page_size": (channel.print_settings or {}).get("page_size", "A4"),
                "margins": (channel.print_settings or {}).get("margins", [20, 20, 20, 20]),
                "include_comments": True
            }
        }
        channel.settings = new_settings
    
    db.session.commit()
```

---

## 📁 СТРУКТУРА ФАЙЛОВ API v2

```
api/
├── __init__.py
├── posts.py           # Старый API (v1) - оставляем для совместимости
├── channels.py        # Старый API (v1)
├── chunks.py          # Старый API (v1)
├── layouts.py         # Старый API (v1)
├── edits.py           # Старый API (v1)
│
└── v2/
    ├── __init__.py
    ├── channels.py    # GET /api/v2/channels/{id}/posts
    │                  # PUT /api/v2/channels/{id}/settings
    │                  # GET /api/v2/channels/{id}/chunks
    │
    ├── posts.py       # POST /api/v2/posts/{channel}/{id}/visibility
    │
    ├── layouts.py     # PUT /api/v2/layouts/{grouped_id}
    │
    └── serializers.py # Общие функции сериализации
```

---

## 🔄 ПЛАН МИГРАЦИИ

### Фаза 1: Создание API v2 (параллельно с v1)

```
День 1-2:
├── [ ] Создать api/v2/__init__.py
├── [ ] Создать api/v2/serializers.py (общая сериализация)
├── [ ] Создать api/v2/channels.py с GET posts endpoint
├── [ ] Добавить тесты для v2 endpoints
└── [ ] Зарегистрировать blueprint в app.py

День 3:
├── [ ] Добавить PUT settings endpoint
├── [ ] Добавить POST visibility endpoint
├── [ ] Добавить PUT layouts endpoint
└── [ ] Тесты
```

### Фаза 2: Миграция Frontend

```
День 4-5:
├── [ ] Создать services/apiV2.js
├── [ ] Создать composables/useChannelPosts.js
├── [ ] Мигрировать posts.vue на API v2
├── [ ] Убрать отдельную загрузку layouts/edits
└── [ ] Тестирование

День 6:
├── [ ] Добавить UI для сохранения настроек
├── [ ] Индикатор "Несохранённые изменения"
└── [ ] Кнопки Save/Reset
```

### Фаза 3: Миграция данных и cleanup

```
День 7:
├── [ ] Скрипт миграции Channel.changes → Channel.settings
├── [ ] Скрипт миграции Channel.print_settings → Channel.settings
├── [ ] Проверка данных
└── [ ] Удаление старых полей (опционально)

День 8:
├── [ ] Deprecation warnings для v1 endpoints
├── [ ] Документация API v2
└── [ ] Release notes
```

---

## 🧪 ТЕСТЫ

### Unit тесты (api/v2/)

```python
# tests/test_api_v2_channels.py

def test_get_posts_default_params():
    """Посты возвращаются с дефолтными параметрами"""
    response = client.get('/api/v2/channels/llamasass/posts')
    assert response.status_code == 200
    data = response.json
    
    assert data['applied_params']['sort_order'] == 'desc'
    assert data['applied_params']['source'] == 'default'
    assert len(data['posts']) > 0

def test_get_posts_url_override():
    """URL параметр имеет приоритет"""
    # Сначала сохраняем sort_order = desc
    client.put('/api/v2/channels/llamasass/settings', json={
        'display': {'sort_order': 'desc'}
    })
    
    # Запрашиваем с URL параметром asc
    response = client.get('/api/v2/channels/llamasass/posts?sort_order=asc')
    data = response.json
    
    assert data['applied_params']['sort_order'] == 'asc'
    assert data['applied_params']['source'] == 'url'

def test_posts_include_layout():
    """Посты с grouped_id включают layout"""
    response = client.get('/api/v2/channels/llamasass/posts')
    
    grouped_posts = [p for p in response.json['posts'] if p.get('grouped_id')]
    for post in grouped_posts:
        assert 'layout' in post
        assert 'group_posts' in post

def test_posts_include_hidden_state():
    """Все посты имеют is_hidden"""
    response = client.get('/api/v2/channels/llamasass/posts')
    
    for post in response.json['posts']:
        assert 'is_hidden' in post
        assert isinstance(post['is_hidden'], bool)

def test_chunking():
    """Chunking работает корректно"""
    response = client.get('/api/v2/channels/llamasass/posts?chunk=0&items_per_chunk=10')
    data = response.json
    
    assert data['pagination']['current_chunk'] == 0
    assert len(data['posts']) <= 10
    assert data['pagination']['has_next'] == True
```

### Integration тесты

```python
# tests/test_api_v2_integration.py

def test_full_flow():
    """Полный флоу: загрузка → изменение → сохранение"""
    
    # 1. Загружаем посты
    response = client.get('/api/v2/channels/llamasass/posts')
    original_order = response.json['applied_params']['sort_order']
    
    # 2. Меняем сортировку через URL
    response = client.get('/api/v2/channels/llamasass/posts?sort_order=asc')
    assert response.json['applied_params']['source'] == 'url'
    
    # 3. Сохраняем настройку
    client.put('/api/v2/channels/llamasass/settings', json={
        'display': {'sort_order': 'asc'}
    })
    
    # 4. Проверяем что сохранилось
    response = client.get('/api/v2/channels/llamasass/posts')
    assert response.json['applied_params']['sort_order'] == 'asc'
    assert response.json['applied_params']['source'] == 'saved'
```

---

## ✅ ПРЕИМУЩЕСТВА API v2

1. **Один запрос вместо многих** — посты + layouts + hidden states
2. **Предсказуемое поведение** — чёткий приоритет параметров
3. **Нет дублирования** — одна функция сериализации
4. **Тестируемость** — чистые endpoints с ясными контрактами
5. **Обратная совместимость** — v1 продолжает работать
6. **Расширяемость** — легко добавить новые параметры

