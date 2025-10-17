"""
API endpoints для работы с layouts галерей
"""
from flask import Blueprint, jsonify, request
from models import db, Layout

layouts_bp = Blueprint('layouts', __name__)

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