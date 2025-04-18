import multiprocessing
multiprocessing.set_start_method("fork", force=True)

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from models import db, Post, Channel
from database import create_app, init_db
import os

MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media')
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')

app = create_app()
CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})  # Разрешаем CORS для фронтенда
init_db(app)

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
    return jsonify({"message": "Post added successfully!"}), 201

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
def add_channel():
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
        description=data.get('description')
    )
    db.session.add(new_channel)
    db.session.commit()
    return jsonify({"message": "Канал успешно добавлен"}), 201

@app.route('/api/channels', methods=['GET'])
def get_channels():
    """Возвращает список всех каналов."""
    channels = Channel.query.all()
    return jsonify([{
        "id": channel.id,
        "name": channel.name,
        "avatar": channel.avatar,
        "description": channel.description
    } for channel in channels])

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