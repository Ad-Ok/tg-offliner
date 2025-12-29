"""
API endpoints для работы со страницами

Автогенерация страниц:
- При запросе страниц канала, если их нет, автоматически создаются ВСЕ страницы
- Посты разбиваются на группы по 4 поста
- Каждая группа становится отдельной страницей с сеткой 2×2 (блоки 6×6)
- Все страницы создаются за один раз и сохраняются в одной транзакции
"""
from flask import Blueprint, jsonify, request
from models import db, Page, Post
from datetime import datetime

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/pages', methods=['GET'])
def get_pages():
    """Возвращает список всех страниц или страниц из конкретного канала.
    Если для канала нет страниц, автоматически создает страницы по 4 поста на каждой.
    
    Параметры:
    - channel_id: фильтр по ID канала
    - page_number: фильтр по номеру страницы (работает только вместе с channel_id)
    - limit: количество страниц для загрузки (по умолчанию: все)
    - offset: смещение для пагинации
    """
    channel_id = request.args.get('channel_id')
    page_number = request.args.get('page_number', type=int)
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', type=int, default=0)
    
    if channel_id:
        # Базовый запрос по каналу
        query = Page.query.filter_by(channel_id=channel_id)
        
        # Фильтр по номеру страницы (если есть поле page_number в json_data)
        if page_number is not None:
            # Поиск по json_data -> page_number
            query = query.filter(Page.json_data['page_number'].astext.cast(db.Integer) == page_number)
        
        # Пагинация
        if limit:
            query = query.offset(offset).limit(limit)
        
        pages = query.all()
        
        # Если страниц нет И не запрашивали конкретную страницу, создаем автоматически
        if not pages and page_number is None:
            pages = _auto_generate_pages(channel_id)
    else:
        # Возвращаем все страницы
        query = Page.query
        if limit:
            query = query.offset(offset).limit(limit)
        pages = query.all()

    return jsonify([{
        "id": page.id,
        "channel_id": page.channel_id,
        "json_data": page.json_data
    } for page in pages])


@pages_bp.route('/pages/<int:page_id>', methods=['GET'])
def get_page(page_id):
    """Возвращает конкретную страницу по ID."""
    page = Page.query.get(page_id)
    if not page:
        return jsonify({"error": "Page not found"}), 404
    
    return jsonify({
        "id": page.id,
        "channel_id": page.channel_id,
        "json_data": page.json_data
    })


@pages_bp.route('/pages', methods=['POST'])
def create_page():
    """Создает новую страницу.
    
    Ожидаемые данные:
    {
        "channel_id": "str",
        "page_number": int (опционально),
        "json_data": {...}
    }
    """
    data = request.get_json()
    
    if not data or 'channel_id' not in data:
        return jsonify({"error": "channel_id is required"}), 400
    
    # Структура json_data по умолчанию
    default_json_data = {
        "version": 1,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "grid": {
            "cellHeight": 100,
            "columns": 12
        },
        "blocks": []
    }
    
    json_data = data.get('json_data', default_json_data)
    
    # Добавляем page_number в json_data если передан
    if 'page_number' in data:
        json_data['page_number'] = data['page_number']
    
    # Убедимся что есть временные метки
    if 'created_at' not in json_data:
        json_data['created_at'] = datetime.utcnow().isoformat()
    json_data['updated_at'] = datetime.utcnow().isoformat()
    
    new_page = Page(
        channel_id=data['channel_id'],
        json_data=json_data
    )
    
    db.session.add(new_page)
    db.session.commit()
    
    return jsonify({
        "id": new_page.id,
        "channel_id": new_page.channel_id,
        "json_data": new_page.json_data
    }), 201


@pages_bp.route('/pages/<int:page_id>', methods=['PUT'])
def update_page(page_id):
    """Обновляет существующую страницу."""
    page = Page.query.get(page_id)
    if not page:
        return jsonify({"error": "Page not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Обновляем json_data
    if 'json_data' in data:
        json_data = data['json_data']
        # Обновляем timestamp
        json_data['updated_at'] = datetime.utcnow().isoformat()
        page.json_data = json_data
    
    # Можем изменить channel_id если нужно
    if 'channel_id' in data:
        page.channel_id = data['channel_id']
    
    db.session.commit()
    
    return jsonify({
        "id": page.id,
        "channel_id": page.channel_id,
        "json_data": page.json_data
    })


@pages_bp.route('/pages/<int:page_id>', methods=['DELETE'])
def delete_page(page_id):
    """Удаляет страницу."""
    page = Page.query.get(page_id)
    if not page:
        return jsonify({"error": "Page not found"}), 404
    
    db.session.delete(page)
    db.session.commit()
    
    return jsonify({"message": "Page deleted successfully"}), 200


def _auto_generate_pages(channel_id):
    """
    Автоматически генерирует все страницы для канала.
    Создает страницы по 4 поста на каждой в сетке 2x2 (блоки размером 6x6).
    
    Args:
        channel_id: ID канала
        
    Returns:
        list[Page]: Список созданных страниц
    """
    # Получаем все посты канала
    all_posts = Post.query.filter_by(channel_id=channel_id).order_by(Post.telegram_id.asc()).all()
    
    if not all_posts:
        return []
    
    # Позиции блоков в сетке 2x2 (каждый блок 6x6)
    positions = [
        {"x": 0, "y": 0, "w": 6, "h": 6},  # Верхний левый
        {"x": 6, "y": 0, "w": 6, "h": 6},  # Верхний правый
        {"x": 0, "y": 6, "w": 6, "h": 6},  # Нижний левый
        {"x": 6, "y": 6, "w": 6, "h": 6},  # Нижний правый
    ]
    
    created_pages = []
    
    # Разбиваем посты на группы по 4
    for page_num in range(0, len(all_posts), 4):
        posts_chunk = all_posts[page_num:page_num + 4]
        
        # Создаем блоки для постов текущей страницы
        blocks = []
        for i, post in enumerate(posts_chunk):
            block = {
                "id": f"block-{page_num + i + 1}",
                "x": positions[i]["x"],
                "y": positions[i]["y"],
                "w": positions[i]["w"],
                "h": positions[i]["h"],
                "content": {
                    "channel_id": channel_id,
                    "telegram_id": post.telegram_id
                }
            }
            blocks.append(block)
        
        # Создаем JSON данные для страницы
        json_data = {
            "version": 1,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "grid": {
                "cellHeight": 100,
                "columns": 12
            },
            "blocks": blocks
        }
        
        # Создаем и сохраняем страницу
        new_page = Page(
            channel_id=channel_id,
            json_data=json_data
        )
        
        db.session.add(new_page)
        created_pages.append(new_page)
    
    # Сохраняем все страницы одной транзакцией
    db.session.commit()
    
    return created_pages


@pages_bp.route('/pages/<channel_id>', methods=['POST'])
def save_frozen_layout(channel_id):
    """
    Сохраняет frozen layout для канала.
    Удаляет все существующие страницы канала и создает новые с frozen координатами.
    
    Ожидаемые данные:
    {
        "channel_id": "str",
        "pages": [
            {
                "page_number": 1,
                "posts": [
                    {
                        "telegram_id": 123,
                        "channel_id": "llamasass",
                        "type": "post",
                        "bounds": {"top": 20, "left": 20, "width": 170, "height": 80},
                        "elements": [...]
                    }
                ]
            }
        ]
    }
    """
    data = request.get_json()
    
    if not data or 'pages' not in data:
        return jsonify({"error": "pages array is required"}), 400
    
    frozen_pages = data['pages']
    
    try:
        # Удаляем все существующие страницы канала
        Page.query.filter_by(channel_id=channel_id).delete()
        
        # Создаем новые страницы с frozen layout
        created_pages = []
        for frozen_page in frozen_pages:
            json_data = {
                "version": "frozen_1.0",
                "type": "frozen_layout",
                "created_at": datetime.utcnow().isoformat(),
                "page_number": frozen_page.get('page_number', 1),
                "posts": frozen_page.get('posts', [])
            }
            
            new_page = Page(
                channel_id=channel_id,
                json_data=json_data
            )
            
            db.session.add(new_page)
            created_pages.append(new_page)
        
        # Сохраняем все страницы одной транзакцией
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Saved {len(created_pages)} frozen pages for channel {channel_id}",
            "pages_count": len(created_pages)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to save frozen layout",
            "details": str(e)
        }), 500


@pages_bp.route('/pages/<channel_id>/frozen', methods=['GET'])
def get_frozen_layout(channel_id):
    """
    Получить frozen layout для канала.
    Возвращает только страницы с type="frozen_layout".
    """
    pages = Page.query.filter_by(channel_id=channel_id).all()
    
    # Фильтруем только frozen layout страницы
    frozen_pages = [
        page for page in pages 
        if page.json_data.get('type') == 'frozen_layout'
    ]
    
    if not frozen_pages:
        return jsonify({
            "error": "No frozen layout found for this channel",
            "channel_id": channel_id
        }), 404
    
    # Сортируем по номеру страницы
    frozen_pages.sort(key=lambda p: p.json_data.get('page_number', 0))
    
    return jsonify({
        "channel_id": channel_id,
        "pages_count": len(frozen_pages),
        "pages": [page.json_data for page in frozen_pages]
    })
