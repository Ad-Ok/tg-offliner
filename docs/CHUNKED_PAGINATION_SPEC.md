# Спецификация: Разбиение контента на части (Chunked Pagination)

## 📋 Обзор

Система разбиения больших каналов (1000+ постов) на управляемые части для:
- Оптимизации загрузки в ленте
- Экспорта в несколько файлов (PDF, IDML)
- Корректного отображения превью каждой части

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

- Посты с `hidden: 'true'` в Edit **пропускаются** при разбиении
- Не учитываются в весе chunk

---

## 📊 Существующая архитектура (ВАЖНО!)

### Backend API Endpoints

| Endpoint | Файл | Описание |
|----------|------|----------|
| `GET /api/posts?channel_id=X` | `api/posts.py` | Все посты + комментарии из discussion_group |
| `GET /api/channels` | `api/channels.py` | Список каналов |
| `GET /api/channels/<id>` | `api/channels.py` | Информация о канале |
| `PUT /api/channels/<id>` | `api/channels.py` | Обновление канала (включая print_settings) |
| `GET /api/edits/<telegram_id>/<channel_id>` | `api/edits.py` | Получить edit для поста |
| `POST /api/edits` | `api/edits.py` | Создать/обновить edit |
| `GET /api/layouts/<grouped_id>?channel_id=X` | `api/layouts.py` | Layout для медиа-группы |
| `GET /api/pages?channel_id=X` | `api/pages.py` | Страницы канала (grid layout) |
| `POST /api/pages/<channel_id>` | `api/pages.py` | Сохранить frozen layout |
| `GET /api/pages/<channel_id>/frozen` | `api/pages.py` | Получить frozen layout |
| `GET /api/channels/<id>/print` | `api/channels.py` | Экспорт в PDF |
| `GET /api/channels/<id>/export-idml` | `api/channels.py` | Экспорт в IDML |
| `GET /api/channels/<id>/export-html` | `api/channels.py` | Экспорт в HTML |

### Frontend Pages

| Страница | Файл | Описание |
|----------|------|----------|
| `/` | `pages/index.vue` | Список каналов |
| `/:channelId/posts` | `pages/[channelId]/posts.vue` | Лента постов |
| `/:channelId/pages` | `pages/[channelId]/pages.vue` | Grid редактор |
| `/preview/:channelId` | `pages/preview/[channelId]/index.vue` | Preview |
| `/preview/:channelId/frozen` | `pages/preview/[channelId]/frozen.vue` | Frozen preview |

### Frontend Services

| Сервис | Файл | Методы |
|--------|------|--------|
| `api` | `services/api.js` | `get`, `post`, `put`, `patch`, `delete` |
| `editsService` | `services/editsService.js` | `createOrUpdateEdit`, `getEditForPost`, `setPostHidden` |
| `layoutsService` | `services/layoutsService.js` | `reloadLayout`, `updateBorder` |

### Модели данных

```python
# models.py

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.Integer, nullable=False)
    channel_id = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String, nullable=True)
    thumb_url = db.Column(db.String, nullable=True)
    media_type = db.Column(db.String, nullable=True)
    grouped_id = db.Column(db.BigInteger, nullable=True)  # Для медиа-групп
    reply_to = db.Column(db.Integer, nullable=True)       # Для комментариев
    reactions = db.Column(JSON, nullable=True)
    # ... остальные поля

class Channel(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    discussion_group_id = db.Column(db.BigInteger, nullable=True)
    changes = db.Column(JSON, nullable=False, default='{}')
    print_settings = db.Column(JSON, nullable=True)
    # ... остальные поля

class Edit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.Integer, nullable=False)
    channel_id = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)
    changes = db.Column(JSON, nullable=False)  # {"hidden": "true", ...}

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String, nullable=False)
    json_data = db.Column(JSON, nullable=False)  # Frozen layout или grid layout
```

### Конфигурация

```python
# idml_export/constants.py - загружает из print-config.json

DEFAULT_PRINT_SETTINGS = {
    'page_size': 'A4',
    'margins': [20, 20, 20, 20],
    'text_columns': 1,
    'column_gutter': 5,
    'master_page_enabled': True,
    'include_headers_footers': True,
}
```

### Фильтрация постов

```python
# utils/post_filtering.py

def should_hide_post(post, edits):
    """Проверяет, должен ли пост быть скрыт"""
    # 1. Проверка hidden в edits
    # 2. Проверка unsupported media без текста
    
def should_hide_media(post):
    """Проверяет, должно ли медиа быть скрыто"""
    # webp, MessageMediaWebPage, non-image documents
```

---

## 🔧 Изменения для реализации

### 1. Расширение print_settings

**Файл:** `print-config.json`

```json
{
  "defaultPrintSettings": {
    "pageSize": "A4",
    "margins": [20, 20, 20, 20],
    "textColumns": 1,
    "columnGutter": 5,
    "masterPageEnabled": true,
    "includeHeadersFooters": true,
    "itemsPerChunk": 50,
    "overflowThreshold": 0.2
  }
}
```

**Файл:** `idml_export/constants.py`

```python
DEFAULT_PRINT_SETTINGS = {
    # ... существующие поля ...
    'items_per_chunk': _config['defaultPrintSettings'].get('itemsPerChunk', 50),
    'overflow_threshold': _config['defaultPrintSettings'].get('overflowThreshold', 0.2),
}
```

### 2. Новый модуль: utils/chunking.py

```python
"""
Модуль для разбиения канала на chunks (части)
"""
from models import Post, Channel, Edit
from utils.post_filtering import should_hide_post


def get_visible_posts(channel_id):
    """
    Получает все видимые посты канала (не скрытые)
    
    Args:
        channel_id: ID канала
        
    Returns:
        list[Post]: Список видимых постов, отсортированных по дате (новые первыми)
    """
    posts = Post.query.filter_by(channel_id=channel_id).all()
    edits = Edit.query.filter_by(channel_id=channel_id).all()
    
    visible = [p for p in posts if not should_hide_post(p, edits)]
    visible.sort(key=lambda p: p.date, reverse=True)
    
    return visible


def get_comments_for_post(telegram_id, discussion_channel_id):
    """
    Получает комментарии для поста из дискуссионной группы
    
    Args:
        telegram_id: ID поста в канале
        discussion_channel_id: ID дискуссионной группы (str или None)
        
    Returns:
        list[Post]: Список комментариев
    """
    if not discussion_channel_id:
        return []
    
    return Post.query.filter_by(
        channel_id=discussion_channel_id,
        reply_to=telegram_id
    ).all()


def build_content_units(channel_id):
    """
    Строит список ContentUnit из постов канала
    
    ContentUnit = {
        'post': Post,              # Главный пост (или первый в группе)
        'group_posts': list[Post], # Все посты медиа-группы (если is_group=True)
        'comments': list[Post],    # Все комментарии
        'weight': int,             # Сумма: len(group_posts или 1) + len(comments)
        'is_group': bool,          # Это медиа-группа?
        'date': str                # Дата для сортировки
    }
    
    Args:
        channel_id: ID канала
        
    Returns:
        list[ContentUnit]: Список единиц контента, отсортированных по дате
    """
    channel = Channel.query.get(channel_id)
    if not channel:
        return []
    
    discussion_id = str(channel.discussion_group_id) if channel.discussion_group_id else None
    
    # Получаем видимые посты
    visible_posts = get_visible_posts(channel_id)
    
    # Группируем по grouped_id
    groups = {}  # grouped_id -> list[Post]
    singles = []  # Одиночные посты
    
    for post in visible_posts:
        if post.grouped_id:
            if post.grouped_id not in groups:
                groups[post.grouped_id] = []
            groups[post.grouped_id].append(post)
        else:
            singles.append(post)
    
    units = []
    
    # Обрабатываем одиночные посты
    for post in singles:
        comments = get_comments_for_post(post.telegram_id, discussion_id)
        units.append({
            'post': post,
            'group_posts': [],
            'comments': comments,
            'weight': 1 + len(comments),
            'is_group': False,
            'date': post.date
        })
    
    # Обрабатываем медиа-группы
    for grouped_id, group_posts in groups.items():
        # Сортируем по telegram_id (порядок в альбоме)
        group_posts.sort(key=lambda p: p.telegram_id)
        first_post = group_posts[0]
        
        # Комментарии привязаны к первому посту группы
        comments = get_comments_for_post(first_post.telegram_id, discussion_id)
        
        units.append({
            'post': first_post,
            'group_posts': group_posts,
            'comments': comments,
            'weight': len(group_posts) + len(comments),
            'is_group': True,
            'date': first_post.date
        })
    
    # Сортируем по дате (новые первыми)
    units.sort(key=lambda u: u['date'], reverse=True)
    
    return units


def calculate_chunks(channel_id, items_per_chunk=50, overflow_threshold=0.2):
    """
    Разбивает канал на chunks
    
    Args:
        channel_id: ID канала
        items_per_chunk: Целевое количество единиц на chunk (по умолчанию 50)
        overflow_threshold: Допустимое превышение (по умолчанию 0.2 = 20%)
        
    Returns:
        list[Chunk]: Список chunks
        
    Chunk = {
        'index': int,              # Индекс chunk (0, 1, 2...)
        'units': list[ContentUnit],# Единицы контента
        'total_weight': int,       # Сумма весов
        'posts_count': int,        # Количество постов (без комментариев)
        'comments_count': int,     # Количество комментариев
        'date_from': str,          # Дата первого поста
        'date_to': str             # Дата последнего поста
    }
    """
    units = build_content_units(channel_id)
    
    if not units:
        return []
    
    max_weight = items_per_chunk * (1 + overflow_threshold)
    threshold_weight = items_per_chunk * 0.8  # 80% заполнения
    
    chunks = []
    current_chunk = _new_chunk(0)
    
    for unit in units:
        can_fit = current_chunk['total_weight'] + unit['weight'] <= max_weight
        chunk_almost_full = current_chunk['total_weight'] >= threshold_weight
        
        if can_fit:
            # Влезает - добавляем
            _add_unit_to_chunk(current_chunk, unit)
        elif chunk_almost_full and current_chunk['units']:
            # Chunk почти полный - начинаем новый
            chunks.append(current_chunk)
            current_chunk = _new_chunk(len(chunks))
            _add_unit_to_chunk(current_chunk, unit)
        else:
            # Chunk не полный, но unit огромный - добавляем как есть
            _add_unit_to_chunk(current_chunk, unit)
    
    # Не забываем последний chunk
    if current_chunk['units']:
        chunks.append(current_chunk)
    
    return chunks


def _new_chunk(index):
    """Создает пустой chunk"""
    return {
        'index': index,
        'units': [],
        'total_weight': 0,
        'posts_count': 0,
        'comments_count': 0,
        'date_from': None,
        'date_to': None
    }


def _add_unit_to_chunk(chunk, unit):
    """Добавляет unit в chunk"""
    chunk['units'].append(unit)
    chunk['total_weight'] += unit['weight']
    
    if unit['is_group']:
        chunk['posts_count'] += len(unit['group_posts'])
    else:
        chunk['posts_count'] += 1
    
    chunk['comments_count'] += len(unit['comments'])
    
    # Обновляем даты
    if chunk['date_from'] is None or unit['date'] > chunk['date_from']:
        chunk['date_from'] = unit['date']
    if chunk['date_to'] is None or unit['date'] < chunk['date_to']:
        chunk['date_to'] = unit['date']


def get_chunk_posts_and_comments(chunk):
    """
    Извлекает плоские списки постов и комментариев из chunk
    
    Args:
        chunk: Chunk объект
        
    Returns:
        tuple[list[Post], list[Post]]: (посты, комментарии)
    """
    posts = []
    comments = []
    
    for unit in chunk['units']:
        if unit['is_group']:
            posts.extend(unit['group_posts'])
        else:
            posts.append(unit['post'])
        comments.extend(unit['comments'])
    
    return posts, comments
```

### 3. Новые API Endpoints

**Файл:** `api/chunks.py` (новый файл)

```python
"""
API endpoints для работы с chunks (частями контента)
"""
from flask import Blueprint, jsonify, request
from models import Channel
from utils.chunking import calculate_chunks, get_chunk_posts_and_comments
from idml_export.constants import DEFAULT_PRINT_SETTINGS

chunks_bp = Blueprint('chunks', __name__)


def serialize_post(post):
    """Сериализация Post для JSON"""
    return {
        "id": post.id,
        "telegram_id": post.telegram_id,
        "channel_id": post.channel_id,
        "date": post.date,
        "message": post.message,
        "media_url": post.media_url,
        "thumb_url": post.thumb_url,
        "media_type": post.media_type,
        "mime_type": post.mime_type,
        "author_name": post.author_name,
        "author_avatar": post.author_avatar,
        "author_link": post.author_link,
        "repost_author_name": post.repost_author_name,
        "repost_author_avatar": post.repost_author_avatar,
        "repost_author_link": post.repost_author_link,
        "reactions": post.reactions,
        "grouped_id": post.grouped_id,
        "reply_to": post.reply_to
    }


@chunks_bp.route('/chunks/<channel_id>', methods=['GET'])
def get_channel_chunks(channel_id):
    """
    Получить информацию о разбиении канала на chunks
    
    Query params:
        items_per_chunk: int (опционально, переопределяет настройки канала)
    
    Returns:
        {
            "channel_id": "str",
            "items_per_chunk": int,
            "overflow_threshold": float,
            "total_chunks": int,
            "total_posts": int,
            "total_comments": int,
            "chunks": [
                {
                    "index": 0,
                    "posts_count": int,
                    "comments_count": int,
                    "total_weight": int,
                    "date_from": "str",
                    "date_to": "str"
                }
            ]
        }
    """
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    
    # Получаем настройки
    print_settings = channel.print_settings or {}
    items_per_chunk = request.args.get(
        'items_per_chunk',
        print_settings.get('items_per_chunk', DEFAULT_PRINT_SETTINGS['items_per_chunk']),
        type=int
    )
    overflow_threshold = print_settings.get(
        'overflow_threshold',
        DEFAULT_PRINT_SETTINGS['overflow_threshold']
    )
    
    # Вычисляем chunks
    chunks = calculate_chunks(channel_id, items_per_chunk, overflow_threshold)
    
    # Подсчитываем общие статистики
    total_posts = sum(c['posts_count'] for c in chunks)
    total_comments = sum(c['comments_count'] for c in chunks)
    
    return jsonify({
        "channel_id": channel_id,
        "items_per_chunk": items_per_chunk,
        "overflow_threshold": overflow_threshold,
        "total_chunks": len(chunks),
        "total_posts": total_posts,
        "total_comments": total_comments,
        "chunks": [{
            "index": c['index'],
            "posts_count": c['posts_count'],
            "comments_count": c['comments_count'],
            "total_weight": c['total_weight'],
            "date_from": c['date_from'],
            "date_to": c['date_to']
        } for c in chunks]
    })


@chunks_bp.route('/chunks/<channel_id>/<int:chunk_index>/posts', methods=['GET'])
def get_chunk_posts(channel_id, chunk_index):
    """
    Получить посты и комментарии конкретного chunk
    
    Returns:
        {
            "channel_id": "str",
            "chunk_index": int,
            "posts": [...],
            "comments": [...]
        }
    """
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    
    # Получаем настройки
    print_settings = channel.print_settings or {}
    items_per_chunk = print_settings.get('items_per_chunk', DEFAULT_PRINT_SETTINGS['items_per_chunk'])
    overflow_threshold = print_settings.get('overflow_threshold', DEFAULT_PRINT_SETTINGS['overflow_threshold'])
    
    # Вычисляем chunks
    chunks = calculate_chunks(channel_id, items_per_chunk, overflow_threshold)
    
    if chunk_index >= len(chunks):
        return jsonify({"error": f"Chunk {chunk_index} not found. Total chunks: {len(chunks)}"}), 404
    
    chunk = chunks[chunk_index]
    posts, comments = get_chunk_posts_and_comments(chunk)
    
    return jsonify({
        "channel_id": channel_id,
        "chunk_index": chunk_index,
        "posts_count": len(posts),
        "comments_count": len(comments),
        "posts": [serialize_post(p) for p in posts],
        "comments": [serialize_post(c) for c in comments]
    })
```

### 4. Регистрация Blueprint

**Файл:** `app.py` (добавить)

```python
from api.chunks import chunks_bp
app.register_blueprint(chunks_bp, url_prefix='/api')
```

---

## 🧪 Тестирование

### Существующая инфраструктура тестов

```
tests/
├── run_tests.py                    # Запуск тестов с HTML отчетом
├── _telegram_export_base.py        # Базовый класс для тестов
├── test_api_edits.py               # Тесты API edits ✓
├── test_api_layouts.py             # Тесты API layouts ✓
├── test_gallery_layout.py          # Тесты gallery layout
├── test_message_transform_helpers.py
├── test_telegram_export_*.py       # Множество тестов telegram_export
```

### Новые тесты: tests/test_chunking.py

```python
"""
Тесты для модуля разбиения на chunks
"""
import os
import sys
import unittest
from datetime import datetime

os.environ.setdefault("API_ID", "123456")
os.environ.setdefault("API_HASH", "testhash")
os.environ.setdefault("PHONE", "+10000000000")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask
from models import db, Post, Channel, Edit


class ChunkingTests(unittest.TestCase):
    """Тесты для utils/chunking.py"""
    
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
    
    def _create_channel(self, channel_id='test_channel', discussion_id=None):
        """Создает тестовый канал"""
        channel = Channel(
            id=channel_id,
            name='Test Channel',
            discussion_group_id=discussion_id,
            changes={}
        )
        db.session.add(channel)
        db.session.commit()
        return channel
    
    def _create_post(self, telegram_id, channel_id='test_channel', 
                     date='2025-01-01', grouped_id=None, reply_to=None):
        """Создает тестовый пост"""
        post = Post(
            telegram_id=telegram_id,
            channel_id=channel_id,
            date=date,
            message=f'Post {telegram_id}',
            grouped_id=grouped_id,
            reply_to=reply_to
        )
        db.session.add(post)
        db.session.commit()
        return post
    
    def _create_hidden_edit(self, telegram_id, channel_id='test_channel'):
        """Создает edit со скрытием поста"""
        edit = Edit(
            telegram_id=telegram_id,
            channel_id=channel_id,
            date=datetime.now().isoformat(),
            changes={'hidden': 'true'}
        )
        db.session.add(edit)
        db.session.commit()
        return edit
    
    # ============ UNIT TESTS ============
    
    def test_get_visible_posts_excludes_hidden(self):
        """Скрытые посты не попадают в visible"""
        with self.app.app_context():
            from utils.chunking import get_visible_posts
            
            self._create_channel()
            self._create_post(1)
            self._create_post(2)
            self._create_post(3)
            self._create_hidden_edit(2)  # Скрываем пост 2
            
            visible = get_visible_posts('test_channel')
            
            self.assertEqual(len(visible), 2)
            visible_ids = [p.telegram_id for p in visible]
            self.assertIn(1, visible_ids)
            self.assertIn(3, visible_ids)
            self.assertNotIn(2, visible_ids)
    
    def test_get_comments_for_post(self):
        """Комментарии привязываются к посту через reply_to"""
        with self.app.app_context():
            from utils.chunking import get_comments_for_post
            
            self._create_channel('channel', discussion_id=12345)
            self._create_post(100, 'channel')
            
            # Создаем комментарии в дискуссионной группе
            self._create_post(1, '12345', reply_to=100)
            self._create_post(2, '12345', reply_to=100)
            self._create_post(3, '12345', reply_to=999)  # К другому посту
            
            comments = get_comments_for_post(100, '12345')
            
            self.assertEqual(len(comments), 2)
    
    def test_build_content_units_single_posts(self):
        """Одиночные посты становятся отдельными units"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel()
            self._create_post(1, date='2025-01-01')
            self._create_post(2, date='2025-01-02')
            self._create_post(3, date='2025-01-03')
            
            units = build_content_units('test_channel')
            
            self.assertEqual(len(units), 3)
            # Проверяем сортировку (новые первыми)
            self.assertEqual(units[0]['post'].telegram_id, 3)
            self.assertEqual(units[1]['post'].telegram_id, 2)
            self.assertEqual(units[2]['post'].telegram_id, 1)
    
    def test_build_content_units_media_group(self):
        """Медиа-группа объединяется в один unit"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel()
            # Медиа-группа из 4 фото
            self._create_post(1, grouped_id=12345)
            self._create_post(2, grouped_id=12345)
            self._create_post(3, grouped_id=12345)
            self._create_post(4, grouped_id=12345)
            # Одиночный пост
            self._create_post(5)
            
            units = build_content_units('test_channel')
            
            self.assertEqual(len(units), 2)  # 1 группа + 1 одиночный
            
            group_unit = next(u for u in units if u['is_group'])
            self.assertEqual(len(group_unit['group_posts']), 4)
            self.assertEqual(group_unit['weight'], 4)  # 4 фото, 0 комментариев
    
    def test_build_content_units_with_comments(self):
        """Комментарии добавляются к weight"""
        with self.app.app_context():
            from utils.chunking import build_content_units
            
            self._create_channel('channel', discussion_id=99999)
            self._create_post(100, 'channel')
            
            # 3 комментария
            self._create_post(1, '99999', reply_to=100)
            self._create_post(2, '99999', reply_to=100)
            self._create_post(3, '99999', reply_to=100)
            
            units = build_content_units('channel')
            
            self.assertEqual(len(units), 1)
            self.assertEqual(units[0]['weight'], 4)  # 1 пост + 3 комментария
            self.assertEqual(len(units[0]['comments']), 3)
    
    def test_calculate_chunks_simple(self):
        """Простое разбиение без комментариев"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel()
            # 10 постов
            for i in range(10):
                self._create_post(i, date=f'2025-01-{i+1:02d}')
            
            chunks = calculate_chunks('test_channel', items_per_chunk=3)
            
            self.assertEqual(len(chunks), 4)  # 10 постов / 3 = 4 chunks (3+3+3+1)
            self.assertEqual(chunks[0]['posts_count'], 3)
            self.assertEqual(chunks[1]['posts_count'], 3)
            self.assertEqual(chunks[2]['posts_count'], 3)
            self.assertEqual(chunks[3]['posts_count'], 1)
    
    def test_calculate_chunks_respects_atomic_unit(self):
        """Пост с комментариями не разрывается"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel('channel', discussion_id=99999)
            
            # Пост 1: вес = 1
            self._create_post(1, 'channel', date='2025-01-01')
            
            # Пост 2: вес = 6 (1 + 5 комментариев)
            self._create_post(2, 'channel', date='2025-01-02')
            for i in range(5):
                self._create_post(100+i, '99999', reply_to=2)
            
            # items_per_chunk=5, overflow=0.2 → max=6
            # Пост 1 (вес 1) влезает
            # Пост 2 (вес 6) → 1+6=7 > 6, но chunk почти пустой → добавляем
            chunks = calculate_chunks('channel', items_per_chunk=5, overflow_threshold=0.2)
            
            # Проверяем, что пост 2 целиком попал в chunk
            self.assertEqual(len(chunks), 1)  # Все в одном chunk
            self.assertEqual(chunks[0]['total_weight'], 7)
    
    def test_calculate_chunks_overflow_starts_new_chunk(self):
        """При переполнении создается новый chunk"""
        with self.app.app_context():
            from utils.chunking import calculate_chunks
            
            self._create_channel('channel', discussion_id=99999)
            
            # Создаем 4 поста по 2 комментария каждый (вес = 3)
            for i in range(4):
                self._create_post(i+1, 'channel', date=f'2025-01-{i+1:02d}')
                self._create_post(100+i*2, '99999', reply_to=i+1)
                self._create_post(101+i*2, '99999', reply_to=i+1)
            
            # items_per_chunk=5, overflow=0.2 → max=6
            # Пост 1 (3) → chunk 0 = 3
            # Пост 2 (3) → chunk 0 = 6 (== max, влезает)
            # Пост 3 (3) → chunk 0 = 9 > 6, chunk 0 full (6 >= 4) → новый chunk
            # Пост 3 → chunk 1 = 3
            # Пост 4 (3) → chunk 1 = 6
            chunks = calculate_chunks('channel', items_per_chunk=5, overflow_threshold=0.2)
            
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0]['total_weight'], 6)  # 2 поста по 3
            self.assertEqual(chunks[1]['total_weight'], 6)  # 2 поста по 3


class ChunksAPITests(unittest.TestCase):
    """Тесты для API chunks"""
    
    def setUp(self):
        from app import app
        
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            
            # Создаем тестовый канал
            channel = Channel(
                id='test_channel',
                name='Test Channel',
                changes={},
                print_settings={'items_per_chunk': 10}
            )
            db.session.add(channel)
            
            # Создаем 25 постов
            for i in range(25):
                post = Post(
                    telegram_id=i+1,
                    channel_id='test_channel',
                    date=f'2025-01-{i+1:02d}',
                    message=f'Post {i+1}'
                )
                db.session.add(post)
            
            db.session.commit()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_get_channel_chunks(self):
        """GET /api/chunks/<channel_id> возвращает информацию о chunks"""
        response = self.client.get('/api/chunks/test_channel')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['channel_id'], 'test_channel')
        self.assertEqual(data['items_per_chunk'], 10)
        self.assertEqual(data['total_chunks'], 3)  # 25 постов / 10 = 3 chunks
        self.assertEqual(data['total_posts'], 25)
    
    def test_get_channel_chunks_not_found(self):
        """GET /api/chunks/<channel_id> для несуществующего канала"""
        response = self.client.get('/api/chunks/nonexistent')
        
        self.assertEqual(response.status_code, 404)
    
    def test_get_chunk_posts(self):
        """GET /api/chunks/<channel_id>/<index>/posts возвращает посты chunk"""
        response = self.client.get('/api/chunks/test_channel/0/posts')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['chunk_index'], 0)
        self.assertIn('posts', data)
        self.assertIn('comments', data)
        self.assertGreater(len(data['posts']), 0)
    
    def test_get_chunk_posts_invalid_index(self):
        """GET /api/chunks/<channel_id>/<index>/posts для несуществующего chunk"""
        response = self.client.get('/api/chunks/test_channel/999/posts')
        
        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
```

### Запуск тестов

```bash
# Все тесты
cd /Users/adoknov/work/tg/tg-offliner
python -m pytest tests/test_chunking.py -v

# С HTML отчетом
python tests/run_tests.py --pattern "test_chunking.py" --html

# Все тесты проекта
python tests/run_tests.py --html
```

---

## 📱 Frontend изменения

### Новый сервис: services/chunksService.js

```javascript
import { api } from './api.js'

export const chunksService = {
  /**
   * Получить информацию о разбиении канала на chunks
   */
  async getChannelChunks(channelId, itemsPerChunk = null) {
    const params = itemsPerChunk ? `?items_per_chunk=${itemsPerChunk}` : ''
    const response = await api.get(`/api/chunks/${channelId}${params}`)
    return response.data
  },

  /**
   * Получить посты и комментарии конкретного chunk
   */
  async getChunkPosts(channelId, chunkIndex) {
    const response = await api.get(`/api/chunks/${channelId}/${chunkIndex}/posts`)
    return response.data
  }
}
```

### Изменения в pages/[channelId]/posts.vue

```vue
<template>
  <div class="max-w-xl mx-auto print:max-w-none" :class="pageFormatClass">
    <!-- Информация о канале -->
    <ChannelCover ... />
    
    <!-- Навигация по chunks (если больше 1) -->
    <ChunkNavigation 
      v-if="chunksInfo && chunksInfo.total_chunks > 1"
      :chunks-info="chunksInfo"
      :current-chunk="currentChunk"
      @select-chunk="onChunkSelect"
    />
    
    <!-- Кнопка сортировки -->
    <div v-if="!pending" class="mb-4 flex justify-end print:hidden">
      ...
    </div>
    
    <!-- Лента постов текущего chunk -->
    <Wall 
      :channelId="channelId" 
      :posts="currentChunkPosts" 
      :loading="pending"
      :sort-order="sortOrder"
      :discussion-group-id="..."
    />
    
    <!-- Infinite scroll для следующего chunk -->
    <div 
      v-if="hasMoreChunks" 
      ref="loadMoreTrigger"
      class="py-8 flex justify-center"
    >
      <button @click="loadNextChunk" class="btn btn-outline">
        Загрузить еще
      </button>
    </div>
  </div>
</template>

<script setup>
import { chunksService } from '~/services/chunksService'

// Состояние chunks
const chunksInfo = ref(null)
const currentChunk = ref(0)
const loadedChunks = ref([])  // Загруженные посты из всех chunks

// Загрузка информации о chunks
const loadChunksInfo = async () => {
  chunksInfo.value = await chunksService.getChannelChunks(channelId)
}

// Загрузка постов chunk
const loadChunk = async (index) => {
  const data = await chunksService.getChunkPosts(channelId, index)
  return [...data.posts, ...data.comments]
}

// Обработчик выбора chunk
const onChunkSelect = async (index) => {
  currentChunk.value = index
  const posts = await loadChunk(index)
  loadedChunks.value = posts
}

// Infinite scroll
const loadNextChunk = async () => {
  if (currentChunk.value + 1 < chunksInfo.value.total_chunks) {
    currentChunk.value++
    const newPosts = await loadChunk(currentChunk.value)
    loadedChunks.value = [...loadedChunks.value, ...newPosts]
  }
}

const hasMoreChunks = computed(() => 
  chunksInfo.value && currentChunk.value + 1 < chunksInfo.value.total_chunks
)

// Текущие посты для отображения
const currentChunkPosts = computed(() => loadedChunks.value)

// Инициализация
onMounted(async () => {
  await loadChunksInfo()
  if (chunksInfo.value.total_chunks > 0) {
    loadedChunks.value = await loadChunk(0)
  }
})
</script>
```

---

## 📋 Чеклист реализации

### Backend

- [ ] Добавить `itemsPerChunk`, `overflowThreshold` в `print-config.json`
- [ ] Обновить `idml_export/constants.py` для загрузки новых настроек
- [ ] Создать `utils/chunking.py` с функциями разбиения
- [ ] Создать `api/chunks.py` с endpoints
- [ ] Зарегистрировать `chunks_bp` в `app.py`
- [ ] Написать тесты `tests/test_chunking.py`
- [ ] Добавить экспорт chunks в PDF/IDML (`/api/chunks/<id>/<index>/export-pdf`)

### Frontend

- [ ] Создать `services/chunksService.js`
- [ ] Создать компонент `ChunkNavigation.vue`
- [ ] Обновить `pages/[channelId]/posts.vue` для работы с chunks
- [ ] Добавить настройку `items_per_chunk` в UI экспорта
- [ ] Обновить preview для отображения chunks
- [ ] Добавить тесты для `chunksService`

### Тестирование

- [ ] Unit тесты: `get_visible_posts`, `get_comments_for_post`
- [ ] Unit тесты: `build_content_units` (одиночные, группы, комментарии)
- [ ] Unit тесты: `calculate_chunks` (разные сценарии)
- [ ] API тесты: `/api/chunks/<channel_id>`
- [ ] API тесты: `/api/chunks/<channel_id>/<index>/posts`
- [ ] Integration тесты: полный цикл с реальными данными
- [ ] E2E тесты: навигация по chunks в UI

---

## 📚 Примеры использования

### Сценарий 1: 100 постов без комментариев

```
items_per_chunk = 50

Chunk 0: посты 1-50, вес = 50
Chunk 1: посты 51-100, вес = 50

Файлы:
- channel_part1.pdf (посты 1-50)
- channel_part2.pdf (посты 51-100)
```

### Сценарий 2: 50 постов, 2-3 комментария в каждом

```
items_per_chunk = 50

Пост 1 (вес 3) + Пост 2 (вес 4) + ... + Пост ~15 (вес ~3) = ~50
→ Chunk 0: ~15 постов + ~35 комментариев

Пост 16 + ... + Пост ~30 = ~50
→ Chunk 1: ~15 постов + ~35 комментариев

...

Итого: ~3-4 chunks
```

### Сценарий 3: 2 поста по 100+ комментариев

```
items_per_chunk = 50, overflow = 0.2 → max = 60

Пост 1: вес = 151 (1 + 150 комментариев)
→ Chunk 0: только Пост 1 (вес 151, превышает, но chunk пустой)

Пост 2: вес = 121 (1 + 120 комментариев)
→ Chunk 1: только Пост 2 (вес 121)

Файлы:
- channel_part1.pdf (Пост 1 + 150 комментариев)
- channel_part2.pdf (Пост 2 + 120 комментариев)
```
