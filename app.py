import multiprocessing
multiprocessing.set_start_method("fork", force=True)

import logging
import time
import threading
import os
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from weasyprint import HTML
from models import db, Post, Channel, Page
from database import create_app, init_db
from message_processing.channel_info import get_channel_info
from telegram_client import connect_to_telegram

MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media')
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')

# Настройка логирования
logging.basicConfig(
    filename='server.log',  # Имя файла для логов
    level=logging.INFO,     # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Формат логов
)

app = create_app()
CORS(app, resources={
    r"/*": {
        "origins": "http://localhost:3000",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})  # Разрешаем CORS для фронтенда
init_db(app)

# Регистрация blueprints
from api.posts import posts_bp
from api.channels import channels_bp
from api.downloads import downloads_bp
from api.media import media_bp
from api.edits import edits_bp
from api.layouts import layouts_bp
from api.pages import pages_bp
from api.chunks import chunks_bp

# API v2
from api.v2 import api_v2_bp

app.register_blueprint(posts_bp, url_prefix='/api')
app.register_blueprint(channels_bp, url_prefix='/api')
app.register_blueprint(downloads_bp, url_prefix='/api')
app.register_blueprint(media_bp)  # Без префикса, так как пути уже начинаются с /media и /downloads
app.register_blueprint(edits_bp)  # Без префикса, так как пути уже начинаются с /api
app.register_blueprint(layouts_bp, url_prefix='/api')
app.register_blueprint(pages_bp, url_prefix='/api')
app.register_blueprint(chunks_bp, url_prefix='/api')

# API v2 - новые унифицированные endpoints
app.register_blueprint(api_v2_bp)

# Глобальные переменные для управления загрузкой
download_status = {}  # Статус загрузки для каждого канала
download_lock = threading.Lock()  # Блокировка для thread-safe операций

def set_download_status(channel_id, status, details=None):
    """Устанавливает статус загрузки канала"""
    with download_lock:
        download_status[channel_id] = {
            'status': status,  # 'downloading', 'stopped', 'completed', 'error'
            'details': details or {},
            'timestamp': time.time()
        }

def update_download_progress(channel_id, posts_processed=0, total_posts=0, comments_processed=0):
    """Обновляет прогресс загрузки канала"""
    with download_lock:
        if channel_id in download_status:
            download_status[channel_id]['details'].update({
                'posts_processed': posts_processed,
                'total_posts': total_posts,
                'comments_processed': comments_processed
            })

def get_download_status(channel_id):
    """Получает статус загрузки канала"""
    with download_lock:
        return download_status.get(channel_id)

def should_stop_download(channel_id):
    """Проверяет, нужно ли остановить загрузку"""
    status = get_download_status(channel_id)
    return status and status.get('status') == 'stopped'

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
