"""
API endpoints для работы с chunks (частями контента)
"""
from flask import Blueprint, jsonify, request
from models import Channel, Layout
from utils.chunking import calculate_chunks, get_chunk_posts_and_comments
from idml_export.constants import DEFAULT_PRINT_SETTINGS

chunks_bp = Blueprint('chunks', __name__)


def serialize_post(post, layouts_map=None):
    """Сериализация Post для JSON"""
    layout = None
    if layouts_map and post.grouped_id:
        layout = layouts_map.get(post.grouped_id)
    
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
        "reply_to": post.reply_to,
        "layout": layout
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
    
    # Получаем сортировку из changes или из query param
    changes = channel.changes or {}
    sort_order = request.args.get('sort_order', changes.get('sortOrder', 'desc'))
    
    # Вычисляем chunks
    chunks = calculate_chunks(channel_id, items_per_chunk, overflow_threshold, sort_order)
    
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
            "posts_count": int,
            "comments_count": int,
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
    
    # Получаем сортировку из changes или из query param
    changes = channel.changes or {}
    sort_order = request.args.get('sort_order', changes.get('sortOrder', 'desc'))
    
    # Вычисляем chunks
    chunks = calculate_chunks(channel_id, items_per_chunk, overflow_threshold, sort_order)
    
    if chunk_index >= len(chunks):
        return jsonify({"error": f"Chunk {chunk_index} not found. Total chunks: {len(chunks)}"}), 404
    
    chunk = chunks[chunk_index]
    posts, comments = get_chunk_posts_and_comments(chunk)
    
    # Загружаем layouts для всех групп в этом chunk
    all_posts = posts + comments
    channel_ids = set(p.channel_id for p in all_posts)
    layouts = Layout.query.filter(Layout.channel_id.in_(channel_ids)).all()
    layouts_map = {layout.grouped_id: layout.json_data for layout in layouts}
    
    return jsonify({
        "channel_id": channel_id,
        "chunk_index": chunk_index,
        "posts_count": len(posts),
        "comments_count": len(comments),
        "posts": [serialize_post(p, layouts_map) for p in posts],
        "comments": [serialize_post(c, layouts_map) for c in comments]
    })
