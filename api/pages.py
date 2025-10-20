"""
API endpoints для работы со страницами
"""
from flask import Blueprint, jsonify, request
from models import db, Page

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