import multiprocessing
multiprocessing.set_start_method("fork", force=True)

import logging
import time
import threading
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from models import db, Post, Channel
from database import create_app, init_db
import os
from weasyprint import HTML
import requests
from flask import request, jsonify
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
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})  # Разрешаем CORS для фронтенда
init_db(app)

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

# def generate_pdf(html_content, pdf_path):
#     """Генерирует PDF из HTML-контента."""
#     try:
#         HTML(string=html_content).write_pdf(pdf_path)
#         logging.info(f"PDF успешно сохранён в {pdf_path}")
#     except Exception as e:
#         logging.error(f"Ошибка при печати PDF: {str(e)}")

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Возвращает список всех постов или постов из конкретного канала."""
    channel_id = request.args.get('channel_id')  # Получаем ID канала из параметров запроса
    if channel_id:
        posts = Post.query.filter_by(channel_id=channel_id).all()  # Фильтруем по каналу
    else:
        posts = Post.query.all()  # Возвращаем все посты

    return jsonify([{
        "id": post.id,
        "telegram_id": post.telegram_id,
        "channel_id": post.channel_id,
        "date": post.date,
        "message": post.message,
        "media_url": post.media_url,
        "media_type": post.media_type,
        "mime_type": post.mime_type,
        "author_name": post.author_name,
        "author_avatar": post.author_avatar,
        "author_link": post.author_link,
        "repost_author_name": post.repost_author_name,
        "repost_author_avatar": post.repost_author_avatar,
        "repost_author_link": post.repost_author_link,
        "reactions": post.reactions,
        "grouped_id": post.grouped_id,
        "reply_to": post.reply_to
    } for post in posts])

@app.route('/api/posts/check', methods=['GET'])
def check_post_exists():
    """Проверяет, существует ли пост с заданным telegram_id и channel_id."""
    telegram_id = request.args.get('telegram_id')
    channel_id = request.args.get('channel_id')
    if not telegram_id or not channel_id:
        return jsonify({"error": "telegram_id и channel_id обязательны"}), 400

    post_exists = Post.query.filter_by(telegram_id=telegram_id, channel_id=channel_id).first() is not None
    return jsonify({"exists": post_exists}), 200

@app.route('/api/posts', methods=['POST'])
def add_post():
    """Добавляет новый пост в базу данных."""
    data = request.json
    new_post = Post(
        telegram_id=data['telegram_id'],
        channel_id=data['channel_id'],  # Указываем ID канала
        date=data['date'],
        message=data.get('message', ''),  # Текст сообщения (по умолчанию пустая строка)
        media_url=data.get('media_url'),  # Сохраняем ссылку на медиа
        media_type=data.get('media_type'),  # Сохраняем тип медиа
        mime_type=data.get('mime_type'),  # Сохраняем MIME-тип
        author_name=data.get('author_name'),  # Имя автора
        author_avatar=data.get('author_avatar'),  # Ссылка на аватар автора
        author_link=data.get('author_link'),  # Ссылка на профиль автора
        repost_author_name=data.get('repost_author_name'),  # Имя автора репоста
        repost_author_avatar=data.get('repost_author_avatar'),  # Ссылка на аватар автора репоста
        repost_author_link=data.get('repost_author_link'),  # Ссылка на профиль автора репоста
        reactions=data.get('reactions'),  # Сохраняем реакции
        grouped_id=data.get('grouped_id'),  # Сохраняем ID медиа-группы
        reply_to=data.get('reply_to')  # Сохраняем ID сообщения, на которое дан ответ
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({"message": "Post added successfully!"}, 201)

@app.route('/api/posts', methods=['DELETE'])
def delete_post():
    """Удаляет пост с заданным telegram_id и channel_id."""
    telegram_id = request.args.get('telegram_id')
    channel_id = request.args.get('channel_id')

    if not telegram_id or not channel_id:
        return jsonify({"error": "telegram_id и channel_id обязательны"}), 400

    post = Post.query.filter_by(telegram_id=telegram_id, channel_id=channel_id).first()
    if post:
        db.session.delete(post)
        db.session.commit()
        return jsonify({"message": f"Пост с ID {telegram_id} успешно удалён."}), 200
    else:
        return jsonify({"error": "Пост не найден."}), 404

@app.route('/api/channels', methods=['POST'])
def add_channel_to_db():
    """Добавляет новый канал в базу данных."""
    data = request.json
    if not data.get('id') or not data.get('name'):
        return jsonify({"error": "id и name обязательны"}), 400

    # Проверяем, существует ли канал
    existing_channel = Channel.query.filter_by(id=data['id']).first()
    if existing_channel:
        return jsonify({"message": "Канал уже существует"}), 200

    # Добавляем новый канал
    new_channel = Channel(
        id=data['id'],
        name=data['name'],
        avatar=data.get('avatar'),
        creation_date=data.get('creation_date'),  # <-- должно быть!
        subscribers=data.get('subscribers'),
        description=data.get('description'),
        discussion_group_id=data.get('discussion_group_id')
    )
    db.session.add(new_channel)
    db.session.commit()
    return jsonify({"message": "Канал успешно добавлен"}), 201

@app.route('/api/add_channel', methods=['POST'])
def run_channel_import():
    """Импортирует канал или переписку с пользователем напрямую через API."""
    app.logger.info('Добавление канала запущено')
    data = request.json
    app.logger.info(f"Получены данные: {data}")
    channel_username = data.get('channel_username')

    if not channel_username:
        app.logger.error("channel_username обязателен")
        return jsonify({"error": "channel_username обязателен"}), 400

    try:
        # Сначала получаем entity, чтобы узнать реальный ID
        from utils.entity_validation import get_entity_by_username_or_id
        from telegram_export import import_channel_direct
        
        # Подключаемся к Telegram для получения реального ID
        client = connect_to_telegram()
        entity, error_message = get_entity_by_username_or_id(client, channel_username)
        
        if entity is None:
            return jsonify({"error": error_message}), 400
        
        # Определяем реальный ID для проверки в базе
        real_id = entity.username or str(entity.id)
        
        # Устанавливаем статус начала загрузки
        set_download_status(real_id, 'downloading', {
            'channel_name': channel_username,
            'started_at': time.time(),
            'processed_posts': 0,
            'processed_comments': 0
        })
        
        # Проверяем, существует ли канал по реальному ID
        existing_channel = Channel.query.filter_by(id=real_id).first()
        if existing_channel:
            app.logger.warning(f"Канал/пользователь {real_id} уже существует.")
            return jsonify({"error": f"Канал/пользователь {real_id} уже импортирован"}), 400

        # Импортируем канал напрямую через API
        result = import_channel_direct(channel_username, real_id)
        
        if result['success']:
            processed_count = result.get('processed', 0)
            comments_count = result.get('comments', 0)
            message = f"Канал/пользователь {real_id} успешно добавлен. Импортировано {processed_count} сообщений"
            if comments_count > 0:
                message += f" и {comments_count} комментариев"
            
            # Устанавливаем статус завершения
            set_download_status(real_id, 'completed', {
                'channel_name': channel_username,
                'completed_at': time.time(),
                'processed_posts': processed_count,
                'processed_comments': comments_count,
                'message': message
            })
            
            app.logger.info(message)
            return jsonify({"message": message}), 200
        else:
            # Устанавливаем статус ошибки
            set_download_status(real_id, 'error', {
                'channel_name': channel_username,
                'error_at': time.time(),
                'error': result['error']
            })
            
            app.logger.error(f"Ошибка импорта канала: {result['error']}")
            return jsonify({"error": result['error']}), 500
            
    except Exception as e:
        # Устанавливаем статус ошибки, если real_id определен
        if 'real_id' in locals():
            set_download_status(real_id, 'error', {
                'channel_name': channel_username,
                'error_at': time.time(),
                'error': str(e)
            })
        
        app.logger.error(f"Исключение: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/download/status/<channel_id>', methods=['GET'])
def get_download_status_api(channel_id):
    """Возвращает статус загрузки канала"""
    status = get_download_status(channel_id)
    if status:
        return jsonify(status), 200
    else:
        return jsonify({"status": "not_found", "details": {}}), 404

@app.route('/api/download/stop/<channel_id>', methods=['POST'])
def stop_download(channel_id):
    """Останавливает загрузку канала"""
    current_status = get_download_status(channel_id)
    
    if not current_status:
        return jsonify({"error": "Загрузка не найдена"}), 404
    
    if current_status.get('status') != 'downloading':
        return jsonify({"error": f"Загрузка уже завершена или остановлена. Текущий статус: {current_status.get('status')}"}), 400
    
    set_download_status(channel_id, 'stopped', {
        'message': 'Загрузка остановлена пользователем',
        'stopped_at': time.time()
    })
    
    app.logger.info(f"Пользователь остановил загрузку канала {channel_id}")
    return jsonify({"message": f"Загрузка канала {channel_id} остановлена"}), 200

@app.route('/api/download/status', methods=['GET'])
def get_all_download_statuses():
    """Возвращает статусы всех загрузок"""
    with download_lock:
        return jsonify(download_status), 200

@app.route('/api/download/progress/<channel_id>', methods=['POST'])
def update_progress(channel_id):
    """Обновляет прогресс загрузки канала"""
    try:
        data = request.get_json()
        posts_processed = data.get('posts_processed', 0)
        total_posts = data.get('total_posts', 0)
        comments_processed = data.get('comments_processed', 0)
        
        update_download_progress(channel_id, posts_processed, total_posts, comments_processed)
        return jsonify({'message': 'Прогресс обновлен'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/channels', methods=['GET'])
def get_channels():
    """Возвращает список всех каналов."""
    channels = Channel.query.all()
    return jsonify([{
        "id": channel.id,
        "name": channel.name,
        "avatar": channel.avatar,
        "description": channel.description,
        "creation_date": channel.creation_date,
        "subscribers": channel.subscribers,
        "discussion_group_id": channel.discussion_group_id
    } for channel in channels])

@app.route('/api/channels/<channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    """Удаляет канал и связанные с ним данные."""
    try:
        # Удаляем канал из таблицы channels
        channel = Channel.query.filter_by(id=channel_id).first()
        if not channel:
            app.logger.warning(f"Канал с ID {channel_id} не найден.")
            return jsonify({"error": "Канал не найден"}), 404

        db.session.delete(channel)
        app.logger.info(f"Канал с ID {channel_id} удалён из таблицы channels.")

        # Удаляем все посты, связанные с этим каналом
        posts_deleted = Post.query.filter_by(channel_id=channel_id).delete()
        app.logger.info(f"Удалено {posts_deleted} постов, связанных с каналом {channel_id}.")

        # Удаляем папку из /downloads
        channel_folder = os.path.join(DOWNLOADS_DIR, channel_id)
        if os.path.exists(channel_folder):
            import shutil
            shutil.rmtree(channel_folder)
            app.logger.info(f"Папка {channel_folder} удалена.")

        # Сохраняем изменения в базе данных
        db.session.commit()

        return jsonify({"message": f"Канал {channel_id} и связанные данные успешно удалены."}), 200
    except Exception as e:
        app.logger.error(f"Ошибка при удалении канала {channel_id}: {str(e)}")
        return jsonify({"error": "Ошибка при удалении канала"}), 500

@app.route('/api/channels/<channel_id>/print', methods=['GET'])
def print_channel_to_pdf(channel_id):
    try:
        ssr_url = f'http://ssr:3000/{channel_id}/posts?pdf=1'
        response = requests.get(ssr_url)
        if response.status_code != 200:
            app.logger.error(f"SSR-сервер вернул ошибку: {response.status_code}")
            return jsonify({"error": "Ошибка SSR-рендеринга"}), 500

        html_content = response.text
        
        pdf_path = os.path.join(DOWNLOADS_DIR, f"{channel_id}.pdf")
        HTML(string=html_content, base_url='http://ssr:3000').write_pdf(pdf_path)

        if not os.path.exists(pdf_path):
            app.logger.error(f"PDF-файл не найден после генерации: {pdf_path}")
            return jsonify({"error": "PDF-файл не был создан"}), 500

        app.logger.info(f"PDF для канала {channel_id} успешно создан: {pdf_path}")
        return send_from_directory(DOWNLOADS_DIR, f"{channel_id}.pdf", as_attachment=True)
    except Exception as e:
        app.logger.error(f"Ошибка при генерации PDF для канала {channel_id}: {str(e)}")
        return jsonify({"error": "Ошибка при генерации PDF"}), 500

@app.route('/api/channel_preview', methods=['GET'])
def channel_preview():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Не передан username'}), 400
    
    app.logger.info(f"Запрос на preview канала: {username}")
    
    client = None
    try:
        app.logger.info("Подключение к Telegram...")
        
        # Обработка проблем с event loop
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        client = connect_to_telegram()
        app.logger.info("Успешно подключились к Telegram")
        
        app.logger.info(f"Получение entity для канала/пользователя: {username}")
        
        # Получаем entity по username или ID
        from utils.entity_validation import get_entity_by_username_or_id, validate_entity_for_download
        entity, error_message = get_entity_by_username_or_id(client, username)
        
        if entity is None:
            return jsonify({'error': error_message}), 400
            
        app.logger.info(f"Успешно получен entity: {type(entity).__name__}")
        
        # Проверяем, что это публичный канал или пользователь
        validation_result = validate_entity_for_download(entity, username)
        
        if not validation_result["valid"]:
            return jsonify({'error': validation_result["error"]}), 400
        
        entity_type = validation_result["type"]
        
        # Определяем имя папки
        folder_name = entity.username or f"user_{entity.id}" if hasattr(entity, 'first_name') else entity.username or f"channel_{entity.id}"
        
        app.logger.info(f"Получение информации о {entity_type}: {username}")
        info = get_channel_info(client, entity, output_dir="downloads", folder_name=folder_name)
        app.logger.info(f"Информация о {entity_type} успешно получена")
        
        return jsonify(info)
    except Exception as e:
        app.logger.error(f"Ошибка в channel_preview для {username}: {str(e)}")
        import traceback
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500
    finally:
        # НЕ закрываем клиент, так как он глобальный и переиспользуется
        # Только логируем завершение запроса
        if client:
            app.logger.info("Запрос к Telegram завершен")

# Маршрут для раздачи медиафайлов
@app.route('/media/<path:filename>')
def serve_media(filename):
    """Раздаёт медиафайлы из папки media."""
    return send_from_directory(MEDIA_DIR, filename)

@app.route('/downloads/<path:filename>')
def serve_downloads(filename):
    """Раздаёт файлы из папки downloads."""
    return send_from_directory(DOWNLOADS_DIR, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')