"""
API endpoints для работы с layouts галерей
"""
import os

from flask import Blueprint, jsonify, request, current_app

from models import db, Layout, Post
from utils.gallery_layout import generate_gallery_layout

layouts_bp = Blueprint('layouts', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')


def _resolve_image_path(post):
    """Return absolute path for a post thumbnail or media file if present."""

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


@layouts_bp.route('/layouts/<grouped_id>', methods=['GET'])
def get_layout(grouped_id):
    """Возвращает layout для указанного grouped_id."""
    channel_id = request.args.get('channel_id')
    
    if not channel_id:
        return jsonify({"error": "channel_id parameter is required"}), 400
    
    layout = Layout.query.filter_by(grouped_id=grouped_id, channel_id=channel_id).first()
    if layout:
        return jsonify(layout.json_data)
    else:
        return jsonify({"error": "Layout not found"}), 404

@layouts_bp.route('/layouts/<grouped_id>/reload', methods=['POST'])
def reload_layout(grouped_id):
    """Перегенерирует layout для указанной медиа-группы и сохраняет его."""

    payload = request.get_json(silent=True) or {}
    channel_id = payload.get('channel_id') or request.args.get('channel_id')

    if not channel_id:
        return jsonify({"error": "channel_id parameter is required"}), 400

    try:
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

        layout_data = generate_gallery_layout(image_paths)

        if not layout_data:
            return jsonify({"error": "Layout generation failed"}), 500

        existing_layout = Layout.query.filter_by(grouped_id=grouped_id, channel_id=channel_id).first()
        if existing_layout:
            existing_layout.channel_id = channel_id
            existing_layout.json_data = layout_data
        else:
            existing_layout = Layout(grouped_id=grouped_id, channel_id=channel_id, json_data=layout_data)
            db.session.add(existing_layout)

        db.session.commit()

        return jsonify({"layout": layout_data})

    except Exception as exc:  # pragma: no cover - defensive logging for runtime diagnostics
        current_app.logger.exception('Failed to regenerate layout for %s: %s', grouped_id, exc)
        db.session.rollback()
        return jsonify({"error": "Failed to regenerate layout"}), 500