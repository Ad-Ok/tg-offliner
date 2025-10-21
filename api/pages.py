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
    Если для канала нет страниц, автоматически создает страницы по 4 поста на каждой."""
    channel_id = request.args.get('channel_id')  # Получаем ID канала из параметров запроса
    if channel_id:
        pages = Page.query.filter_by(channel_id=channel_id).all()
        
        # Если страниц нет, создаем автоматически все страницы для всех постов канала
        if not pages:
            pages = _auto_generate_pages(channel_id)
    else:
        pages = Page.query.all()  # Возвращаем все страницы

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
    """Создает новую страницу."""
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
