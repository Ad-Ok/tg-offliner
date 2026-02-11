"""
API v2 - Channels endpoints

GET /api/v2/channels/{channel_id}/posts - Получение постов
PUT /api/v2/channels/{channel_id}/settings - Обновление настроек
GET /api/v2/channels/{channel_id}/chunks - Метаданные chunks
"""

from flask import jsonify, request
from models import db, Post, Channel, Layout, Edit
from . import api_v2_bp
from .serializers import (
    serialize_post_full,
    serialize_post_basic,
    serialize_channel,
    get_channel_settings,
    get_default_settings,
    resolve_param,
    get_hidden_posts_map,
    get_layouts_map
)
from utils.chunking import build_content_units, calculate_chunks, get_chunk_posts_and_comments


@api_v2_bp.route('/channels/<channel_id>/posts', methods=['GET'])
def get_channel_posts(channel_id):
    """
    Получить посты канала с полной информацией.
    
    Query params:
        sort_order: 'asc' | 'desc' (default: saved или 'desc')
        chunk: number (default: null = все посты)
        items_per_chunk: number (default: saved или 50)
        include_hidden: boolean (default: false)
        include_comments: boolean (default: true)
    
    Returns:
        {
            channel: {...},
            pagination: {...},
            applied_params: {...},
            posts: [...]
        }
    """
    # Получаем канал
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    
    # Получаем настройки канала и дефолты
    saved_settings = get_channel_settings(channel)
    defaults = get_default_settings()
    
    # Разрешаем параметры по приоритету: URL > Saved > Default
    url_sort = request.args.get('sort_order')
    sort_order, sort_source = resolve_param(
        url_sort,
        saved_settings.get('display', {}).get('sort_order'),
        defaults['display']['sort_order']
    )
    
    url_chunk = request.args.get('chunk', type=int)
    # chunk не имеет saved значения - это runtime параметр
    
    url_items = request.args.get('items_per_chunk', type=int)
    items_per_chunk, items_source = resolve_param(
        url_items,
        saved_settings.get('display', {}).get('items_per_chunk'),
        defaults['display']['items_per_chunk']
    )
    
    include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'
    include_comments = request.args.get('include_comments', 'true').lower() != 'false'
    
    # Получаем discussion_group_id
    discussion_group_id = channel.discussion_group_id
    discussion_id_str = str(discussion_group_id) if discussion_group_id else None
    
    # Загружаем все layouts и hidden states одним запросом
    layouts_map = get_layouts_map(channel_id, discussion_id_str)
    hidden_map = get_hidden_posts_map(channel_id, discussion_id_str)
    
    # Строим content units (посты + группы + комментарии)
    all_units = build_content_units(channel_id, sort_order)
    
    # Применяем chunking если запрошен
    if url_chunk is not None:
        chunks = calculate_chunks(channel_id, items_per_chunk, 0.2, sort_order)
        
        if url_chunk >= len(chunks):
            return jsonify({
                "error": f"Chunk {url_chunk} not found. Total chunks: {len(chunks)}"
            }), 404
        
        chunk_data = chunks[url_chunk]
        units_to_process = chunk_data['units']
        
        pagination = {
            "current_chunk": url_chunk,
            "total_chunks": len(chunks),
            "total_posts": sum(c['posts_count'] for c in chunks),
            "total_comments": sum(c['comments_count'] for c in chunks),
            "items_per_chunk": items_per_chunk,
            "has_next": url_chunk < len(chunks) - 1,
            "has_prev": url_chunk > 0
        }
    else:
        units_to_process = all_units
        
        total_posts = sum(
            len(u['group_posts']) if u['is_group'] else 1 
            for u in all_units
        )
        total_comments = sum(len(u['comments']) for u in all_units)
        
        pagination = {
            "current_chunk": None,
            "total_chunks": 1,
            "total_posts": total_posts,
            "total_comments": total_comments,
            "items_per_chunk": items_per_chunk,
            "has_next": False,
            "has_prev": False
        }
    
    # Сериализуем посты
    posts = []
    for unit in units_to_process:
        main_post = unit['post']
        
        # Проверяем скрытость
        is_hidden = (main_post.channel_id, main_post.telegram_id) in hidden_map
        
        # Пропускаем скрытые если не запрошено include_hidden
        if is_hidden and not include_hidden:
            continue
        
        # Получаем layout для групп
        layout = None
        if unit['is_group'] and main_post.grouped_id:
            layout = layouts_map.get(main_post.grouped_id)
        
        # Сериализуем group_posts
        group_posts = None
        if unit['is_group']:
            group_posts = []
            for gp in unit['group_posts']:
                gp_hidden = (gp.channel_id, gp.telegram_id) in hidden_map
                if not gp_hidden or include_hidden:
                    group_posts.append((gp, gp_hidden))
        
        # Сериализуем комментарии
        comments = []
        if include_comments:
            for comment in unit['comments']:
                c_hidden = (comment.channel_id, comment.telegram_id) in hidden_map
                if not c_hidden or include_hidden:
                    comments.append(serialize_post_basic(comment, is_hidden=c_hidden))
        
        # Создаём полный объект поста
        post_data = serialize_post_full(
            main_post,
            is_hidden=is_hidden,
            layout=layout,
            group_posts=group_posts,
            comments=comments
        )
        posts.append(post_data)
    
    # Определяем общий source для applied_params
    sources = [sort_source, items_source]
    if 'url' in sources:
        overall_source = 'url'
    elif 'saved' in sources:
        overall_source = 'saved'
    else:
        overall_source = 'default'
    
    return jsonify({
        "channel": serialize_channel(channel),
        "pagination": pagination,
        "applied_params": {
            "sort_order": sort_order,
            "chunk": url_chunk,
            "items_per_chunk": items_per_chunk,
            "include_hidden": include_hidden,
            "include_comments": include_comments,
            "source": overall_source
        },
        "posts": posts
    })


@api_v2_bp.route('/channels/<channel_id>/settings', methods=['PUT'])
def update_channel_settings(channel_id):
    """
    Обновить настройки канала.
    
    Request body:
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
    """
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Получаем текущие настройки
    current_settings = get_channel_settings(channel)
    
    # Мержим с новыми
    if 'display' in data:
        current_settings['display'] = {
            **current_settings.get('display', {}),
            **data['display']
        }
    
    if 'export' in data:
        current_settings['export'] = {
            **current_settings.get('export', {}),
            **data['export']
        }
    
    # Сохраняем в старые поля (пока не мигрировали на settings)
    # TODO: После миграции сохранять в channel.settings
    if not channel.changes:
        channel.changes = {}
    channel.changes['sortOrder'] = current_settings['display'].get('sort_order', 'desc')
    
    if not channel.print_settings:
        channel.print_settings = {}
    channel.print_settings['items_per_chunk'] = current_settings['display'].get('items_per_chunk', 50)
    channel.print_settings['page_size'] = current_settings['export'].get('page_size', 'A4')
    channel.print_settings['margins'] = current_settings['export'].get('margins', [20, 20, 20, 20])
    
    # Помечаем как изменённые для SQLAlchemy
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(channel, 'changes')
    flag_modified(channel, 'print_settings')
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "settings": current_settings
    })


@api_v2_bp.route('/channels/<channel_id>/chunks', methods=['GET'])
def get_channel_chunks_info(channel_id):
    """
    Получить метаданные chunks для навигации.
    
    Query params:
        sort_order: 'asc' | 'desc'
        items_per_chunk: number
    """
    channel = Channel.query.get(channel_id)
    if not channel:
        return jsonify({"error": "Channel not found"}), 404
    
    saved_settings = get_channel_settings(channel)
    defaults = get_default_settings()
    
    url_sort = request.args.get('sort_order')
    sort_order, _ = resolve_param(
        url_sort,
        saved_settings.get('display', {}).get('sort_order'),
        defaults['display']['sort_order']
    )
    
    url_items = request.args.get('items_per_chunk', type=int)
    items_per_chunk, _ = resolve_param(
        url_items,
        saved_settings.get('display', {}).get('items_per_chunk'),
        defaults['display']['items_per_chunk']
    )
    
    chunks = calculate_chunks(channel_id, items_per_chunk, 0.2, sort_order)
    
    return jsonify({
        "channel_id": channel_id,
        "total_chunks": len(chunks),
        "items_per_chunk": items_per_chunk,
        "sort_order": sort_order,
        "chunks": [{
            "index": c['index'],
            "posts_count": c['posts_count'],
            "comments_count": c['comments_count'],
            "total_weight": c['total_weight'],
            "date_from": c['date_from'],
            "date_to": c['date_to']
        } for c in chunks]
    })
