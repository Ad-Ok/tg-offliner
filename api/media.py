"""
API endpoints для раздачи медиафайлов
"""
import os
from flask import Blueprint, send_from_directory

media_bp = Blueprint('media', __name__)

# Константы
MEDIA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'media')
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'downloads')

@media_bp.route('/media/<path:filename>')
def serve_media(filename):
    """Раздаёт медиафайлы из папки media."""
    return send_from_directory(MEDIA_DIR, filename)

@media_bp.route('/downloads/<path:filename>')
def serve_downloads(filename):
    """Раздаёт файлы из папки downloads."""
    return send_from_directory(DOWNLOADS_DIR, filename)
