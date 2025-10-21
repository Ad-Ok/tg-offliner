"""
API endpoints для работы со страницами
"""
from flask import Blueprint, jsonify, request
from models import db, Page, Post
from datetime import datetime

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/pages', methods=['GET'])
def get_pages():
    """Возвращает список всех страниц или страниц из конкретного канала.
    Если для канала нет страниц, автоматически создает страницу с первыми 4 постами."""
    channel_id = request.args.get('channel_id')  # Получаем ID канала из параметров запроса
    if channel_id:
        pages = Page.query.filter_by(channel_id=channel_id).all()
        
        # Если страниц нет, создаем автоматически с первыми 4 постами
        if not pages:
            pages = [_auto_generate_page(channel_id)]
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


def _auto_generate_page(channel_id):
    """
    Автоматически генерирует страницу для канала с первыми 4 постами.
    Создает сетку 2x2 с блоками размером 6x6.
    
    Args:
        channel_id: ID канала
        
    Returns:
        Page: Созданная страница
    """
    # Получаем первые 4 поста канала
    posts = Post.query.filter_by(channel_id=channel_id).order_by(Post.telegram_id.asc()).limit(4).all()
    
    # Позиции блоков в сетке 2x2 (каждый блок 6x6)
    positions = [
        {"x": 0, "y": 0, "w": 6, "h": 6},  # Верхний левый
        {"x": 6, "y": 0, "w": 6, "h": 6},  # Верхний правый
        {"x": 0, "y": 6, "w": 6, "h": 6},  # Нижний левый
        {"x": 6, "y": 6, "w": 6, "h": 6},  # Нижний правый
    ]
    
    # Создаем блоки для постов
    blocks = []
    for i, post in enumerate(posts):
        if i < 4:  # Берем максимум 4 поста
            block = {
                "id": f"block-{i+1}",
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
    db.session.commit()
    
    return new_page
