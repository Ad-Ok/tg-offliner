"""
API endpoints для работы со страницами
"""
from flask import Blueprint, jsonify, request
from models import db, Page
from datetime import datetime

pages_bp = Blueprint('pages', __name__)

@pages_bp.route('/pages', methods=['GET'])
def get_pages():
    """Возвращает список всех страниц или страниц из конкретного канала."""
    channel_id = request.args.get('channel_id')  # Получаем ID канала из параметров запроса
    if channel_id:
        pages = Page.query.filter_by(channel_id=channel_id).all()
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