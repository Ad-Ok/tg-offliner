import multiprocessing
multiprocessing.set_start_method("fork", force=True)

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from models import db, Post
from database import create_app, init_db
import os

MEDIA_DIR = os.path.join(os.path.dirname(__file__), 'media')

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
        "media_type": post.media_type
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
        media_type=data.get('media_type')  # Сохраняем тип медиа
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')