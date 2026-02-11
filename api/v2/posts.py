"""
API v2 - Posts endpoints

POST /api/v2/posts/{channel_id}/{telegram_id}/visibility - Скрыть/показать пост
"""

from flask import jsonify, request
from models import db, Post, Edit
from . import api_v2_bp
from datetime import datetime


@api_v2_bp.route('/posts/<channel_id>/<int:telegram_id>/visibility', methods=['POST'])
def update_post_visibility(channel_id, telegram_id):
    """
    Скрыть или показать пост.
    
    Request body:
        {
            "hidden": true | false
        }
    """
    data = request.get_json()
    if data is None or 'hidden' not in data:
        return jsonify({"error": "Missing 'hidden' field"}), 400
    
    hidden = data['hidden']
    
    # Проверяем существование поста
    post = Post.query.filter_by(channel_id=channel_id, telegram_id=telegram_id).first()
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    # Ищем существующий edit или создаём новый
    edit = Edit.query.filter_by(channel_id=channel_id, telegram_id=telegram_id).first()
    
    if edit:
        # Обновляем существующий
        changes = edit.changes or {}
        changes['hidden'] = 'true' if hidden else 'false'
        edit.changes = changes
        edit.date = datetime.utcnow().isoformat()
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(edit, 'changes')
    else:
        # Создаём новый
        edit = Edit(
            channel_id=channel_id,
            telegram_id=telegram_id,
            date=datetime.utcnow().isoformat(),
            changes={'hidden': 'true' if hidden else 'false'}
        )
        db.session.add(edit)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "telegram_id": telegram_id,
        "channel_id": channel_id,
        "hidden": hidden
    })
