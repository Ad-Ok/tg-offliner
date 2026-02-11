"""
Сериализаторы для API v2

Единственное место для преобразования моделей в JSON.
Все endpoints должны использовать эти функции.
"""

from models import Post, Channel, Layout, Edit
from utils.post_filtering import should_hide_post


def serialize_author(post):
    """Сериализация информации об авторе"""
    if not post.author_name:
        return None
    
    return {
        "name": post.author_name,
        "avatar": post.author_avatar,
        "link": post.author_link
    }


def serialize_repost_author(post):
    """Сериализация информации об авторе репоста"""
    if not post.repost_author_name:
        return None
    
    return {
        "name": post.repost_author_name,
        "avatar": post.repost_author_avatar,
        "link": post.repost_author_link
    }


def serialize_post_basic(post, is_hidden=False, layout=None):
    """
    Базовая сериализация поста (без комментариев и group_posts)
    
    Args:
        post: Post model instance
        is_hidden: Скрыт ли пост
        layout: Layout JSON data (для постов с grouped_id)
    """
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
        "author": serialize_author(post),
        "repost_author": serialize_repost_author(post),
        "reactions": post.reactions,
        "grouped_id": post.grouped_id,
        "reply_to": post.reply_to,
        "is_hidden": is_hidden,
        "layout": layout
    }


def serialize_post_full(post, is_hidden=False, layout=None, group_posts=None, comments=None):
    """
    Полная сериализация поста с комментариями и group_posts
    
    Args:
        post: Post model instance  
        is_hidden: Скрыт ли пост
        layout: Layout JSON data
        group_posts: Список постов в группе (для медиа-альбомов)
        comments: Список комментариев
    """
    data = serialize_post_basic(post, is_hidden, layout)
    
    # Добавляем group_posts для медиа-групп
    if group_posts:
        data["group_posts"] = [
            serialize_post_basic(p, is_hidden=gp_hidden, layout=None)
            for p, gp_hidden in group_posts
        ]
    
    # Добавляем комментарии
    data["comments"] = comments or []
    data["comments_count"] = len(comments) if comments else 0
    
    return data


def serialize_channel(channel):
    """Сериализация канала"""
    # Получаем настройки из нового или старого формата
    settings = get_channel_settings(channel)
    
    return {
        "id": channel.id,
        "name": channel.name,
        "avatar": channel.avatar,
        "description": channel.description,
        "creation_date": channel.creation_date,
        "subscribers": channel.subscribers,
        "posts_count": channel.posts_count,
        "comments_count": channel.comments_count,
        "discussion_group_id": channel.discussion_group_id,
        "settings": settings
    }


def get_channel_settings(channel):
    """
    Получает настройки канала в унифицированном формате.
    Поддерживает как новый формат (settings), так и старый (changes + print_settings)
    """
    # Если есть новый формат settings - используем его
    if hasattr(channel, 'settings') and channel.settings:
        return channel.settings
    
    # Иначе собираем из старых полей
    changes = channel.changes or {}
    print_settings = channel.print_settings or {}
    
    return {
        "display": {
            "sort_order": changes.get("sortOrder", "desc"),
            "items_per_chunk": print_settings.get("items_per_chunk", 50)
        },
        "export": {
            "page_size": print_settings.get("page_size", "A4"),
            "margins": print_settings.get("margins", [20, 20, 20, 20]),
            "include_comments": True
        }
    }


def get_default_settings():
    """Возвращает дефолтные настройки"""
    return {
        "display": {
            "sort_order": "desc",
            "items_per_chunk": 50
        },
        "export": {
            "page_size": "A4",
            "margins": [20, 20, 20, 20],
            "include_comments": True
        }
    }


def resolve_param(url_value, saved_value, default_value):
    """
    Разрешает значение параметра по приоритету: URL > Saved > Default
    
    Returns:
        tuple: (value, source) где source = 'url' | 'saved' | 'default'
    """
    if url_value is not None:
        return url_value, 'url'
    if saved_value is not None:
        return saved_value, 'saved'
    return default_value, 'default'


def get_hidden_posts_map(channel_id, discussion_group_id=None):
    """
    Возвращает словарь {(channel_id, telegram_id): True} для скрытых постов.
    Загружает все edits одним запросом вместо N запросов.
    """
    channel_ids = [channel_id]
    if discussion_group_id:
        channel_ids.append(str(discussion_group_id))
    
    edits = Edit.query.filter(Edit.channel_id.in_(channel_ids)).all()
    
    hidden_map = {}
    for edit in edits:
        changes = edit.changes or {}
        if changes.get('hidden') == 'true' or changes.get('hidden') is True:
            hidden_map[(edit.channel_id, edit.telegram_id)] = True
    
    return hidden_map


def get_layouts_map(channel_id, discussion_group_id=None):
    """
    Возвращает словарь {grouped_id: layout_json_data} для всех layouts канала.
    Загружает все layouts одним запросом.
    """
    channel_ids = [channel_id]
    if discussion_group_id:
        channel_ids.append(str(discussion_group_id))
    
    layouts = Layout.query.filter(Layout.channel_id.in_(channel_ids)).all()
    
    return {layout.grouped_id: layout.json_data for layout in layouts}
