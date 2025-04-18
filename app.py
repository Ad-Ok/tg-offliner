import multiprocessing
multiprocessing.set_start_method("fork", force=True)

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from models import db, Post
from database import create_app, init_db
import os

MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media')
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')

app = create_app()
CORS(app, resources={r"/*": {"origins": "http://localhost:8080"}})  # Разрешаем CORS для фронтенда
init_db(app)

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Возвращает список всех постов."""
    posts = Post.query.all()
    return jsonify([{
        "id": post.id,
        "date": post.date,
        "message": post.message,
        "media_url": post.media_url,
        "media_type": post.media_type,
        "mime_type": post.mime_type,
        "author_name": post.author_name,  # Имя автора
        "author_avatar": post.author_avatar,  # Ссылка на аватар автора
        "author_link": post.author_link,  # Ссылка на профиль автора
        "repost_author_name": post.repost_author_name,  # Имя автора репоста
        "repost_author_avatar": post.repost_author_avatar,  # Ссылка на аватар автора репоста
        "repost_author_link": post.repost_author_link  # Ссылка на профиль автора репоста
    } for post in posts])

@app.route('/api/posts', methods=['POST'])
def add_post():
    """Добавляет новый пост в базу данных."""
    data = request.json
    new_post = Post(
        telegram_id=data['telegram_id'],
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
        repost_author_link=data.get('repost_author_link')  # Ссылка на профиль автора репоста
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({"message": "Post added successfully!"}), 201

@app.route('/api/posts', methods=['DELETE'])
def delete_posts():
    """Удаляет все посты из базы данных."""
    try:
        num_deleted = db.session.query(Post).delete()
        db.session.commit()
        return jsonify({"message": f"{num_deleted} постов удалено из базы данных."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

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