"""
API v2 - Layouts endpoints

PUT /api/v2/layouts/{grouped_id} - Обновить layout галереи
GET /api/v2/layouts/{grouped_id} - Получить layout галереи
"""

import os
from flask import jsonify, request, current_app
from models import db, Post, Layout
from . import api_v2_bp
from utils.gallery_layout import generate_gallery_layout


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')


def _resolve_image_path(post):
    """Возвращает путь к изображению поста"""
    candidates = []
    
    if post.thumb_url:
        candidates.append(os.path.join(DOWNLOADS_DIR, post.thumb_url.lstrip('/')))
    
    if post.media_url:
        media_relative = post.media_url.lstrip('/')
        candidates.append(os.path.join(DOWNLOADS_DIR, media_relative))
        candidates.append(os.path.join(
            DOWNLOADS_DIR,
            media_relative.replace('/media/', '/thumbs/')
        ))
    
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    
    return None


@api_v2_bp.route('/layouts/<grouped_id>', methods=['GET'])
def get_layout(grouped_id):
    """Получить layout галереи"""
    channel_id = request.args.get('channel_id')
    
    if not channel_id:
        return jsonify({"error": "channel_id parameter is required"}), 400
    
    layout = Layout.query.filter_by(grouped_id=grouped_id, channel_id=channel_id).first()
    
    if not layout:
        return jsonify({"error": "Layout not found"}), 404
    
    return jsonify({
        "grouped_id": grouped_id,
        "channel_id": channel_id,
        "layout": layout.json_data
    })


@api_v2_bp.route('/layouts/<grouped_id>', methods=['PUT'])
def update_layout(grouped_id):
    """
    Обновить или пересоздать layout галереи.
    
    Request body:
        {
            "channel_id": "llamasass",
            "columns": 3,           // optional
            "border_width": "2",    // optional
            "no_crop": false,       // optional
            "regenerate": true      // если true - пересчитать cells
        }
    """
    data = request.get_json()
    
    if not data or 'channel_id' not in data:
        return jsonify({"error": "channel_id is required"}), 400
    
    channel_id = data['channel_id']
    columns = data.get('columns')
    border_width = data.get('border_width', '0')
    no_crop = data.get('no_crop', False)
    regenerate = data.get('regenerate', False)
    
    # Получаем существующий layout
    layout = Layout.query.filter_by(grouped_id=grouped_id, channel_id=channel_id).first()
    
    if regenerate or not layout:
        # Нужно пересоздать layout
        photo_posts = (
            Post.query
            .filter_by(grouped_id=grouped_id, channel_id=channel_id, media_type='MessageMediaPhoto')
            .order_by(Post.telegram_id.asc())
            .all()
        )
        
        if not photo_posts:
            return jsonify({"error": "No photo posts found for the requested group"}), 404
        
        image_paths = []
        for post in photo_posts:
            path = _resolve_image_path(post)
            if path:
                image_paths.append(path)
        
        if len(image_paths) < 2:
            return jsonify({"error": "At least two images are required to generate layout"}), 400
        
        layout_data = generate_gallery_layout(image_paths, columns=columns, no_crop=no_crop)
        
        if not layout_data:
            return jsonify({"error": "Layout generation failed"}), 500
        
        layout_data['border_width'] = str(border_width)
        
        if layout:
            layout.json_data = layout_data
        else:
            layout = Layout(
                grouped_id=grouped_id,
                channel_id=channel_id,
                json_data=layout_data
            )
            db.session.add(layout)
    else:
        # Только обновляем параметры без пересчёта
        layout_data = layout.json_data
        
        if border_width is not None:
            layout_data['border_width'] = str(border_width)
        
        if columns is not None:
            layout_data['columns'] = columns
        
        layout.json_data = layout_data
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(layout, 'json_data')
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "grouped_id": grouped_id,
        "channel_id": channel_id,
        "layout": layout.json_data
    })
