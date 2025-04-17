import multiprocessing
multiprocessing.set_start_method("fork", force=True)

from flask import Flask, jsonify, request
from models import db, Post
from database import create_app, init_db

app = create_app()
init_db(app)

@app.route('/api/posts', methods=['GET'])
def get_posts():
    """Возвращает список всех постов."""
    posts = Post.query.all()
    return jsonify([{
        "id": post.id,
        "telegram_id": post.telegram_id,
        "title": post.title,
        "content": post.content,
        "date": post.date,
        "media": post.media,
        "channel_name": post.channel_name
    } for post in posts])

@app.route('/api/posts', methods=['POST'])
def add_post():
    """Добавляет новый пост в базу данных."""
    data = request.json
    new_post = Post(
        telegram_id=data['telegram_id'],
        title=data.get('title'),
        content=data['content'],
        date=data['date'],
        media=data.get('media'),
        channel_name=data['channel_name']
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({"message": "Post added successfully!"}), 201

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')