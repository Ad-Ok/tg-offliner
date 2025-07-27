import multiprocessing
multiprocessing.set_start_method("fork", force=True)

import logging
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from models import db, Post, Channel
from database import create_app, init_db
import os
import subprocess
import wx
import wx.html2
from weasyprint import HTML
import requests

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

def generate_pdf(html_content, pdf_path):
    """Генерирует PDF из HTML-контента."""
    try:
        HTML(string=html_content).write_pdf(pdf_path)
        logging.info(f"PDF успешно сохранён в {pdf_path}")
    except Exception as e:
        logging.error(f"Ошибка при печати PDF: {str(e)}")

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
        "reactions": post.reactions
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
        reactions=data.get('reactions')  # Сохраняем реакции
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
        description=data.get('description')
    )
    db.session.add(new_channel)
    db.session.commit()
    return jsonify({"message": "Канал успешно добавлен"}), 201

@app.route('/api/add_channel', methods=['POST'])
def run_channel_import():
    """Вызывает скрипт для добавления канала."""
    app.logger.info('Добавление канала запущено')
    data = request.json
    app.logger.info(f"Получены данные: {data}")
    channel_username = data.get('channel_username')

    if not channel_username:
        app.logger.error("channel_username обязателен")
        return jsonify({"error": "channel_username обязателен"}), 400

    # Проверяем, существует ли канал
    existing_channel = Channel.query.filter_by(id=channel_username).first()
    if existing_channel:
        app.logger.warning(f"Канал {channel_username} уже существует.")
        return jsonify({"error": f"Канал {channel_username} уже импортирован"}), 400

    try:
        # Вызываем скрипт telegram_export.py с аргументом --channel
        result = subprocess.run(
            ['python', 'telegram_export.py', '--channel', channel_username],
            capture_output=True,
            text=True
        )
        app.logger.info(f"Результат выполнения скрипта: {result.stdout}")
        if result.returncode == 0:
            return jsonify({"message": f"Канал {channel_username} успешно добавлен"}), 200
        else:
            app.logger.error(f"Ошибка выполнения скрипта: {result.stderr}")
            return jsonify({"error": result.stderr}), 500
    except Exception as e:
        app.logger.error(f"Исключение: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
        "subscribers": channel.subscribers
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