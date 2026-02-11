"""
API endpoints для работы с постами
"""
from flask import Blueprint, jsonify, request
from models import db, Post, Channel, Layout

posts_bp = Blueprint('posts', __name__)


def _get_layouts_map(channel_id, discussion_group_id=None):
    """Возвращает словарь {grouped_id: layout_json_data} для канала и его дискуссионной группы."""
    channel_ids = [channel_id]
    if discussion_group_id:
        channel_ids.append(str(discussion_group_id))
    
    layouts = Layout.query.filter(Layout.channel_id.in_(channel_ids)).all()
    return {layout.grouped_id: layout.json_data for layout in layouts}


@posts_bp.route('/posts', methods=['GET'])
def get_posts():
    """Возвращает список всех постов или постов из конкретного канала."""
    channel_id = request.args.get('channel_id')  # Получаем ID канала из параметров запроса
    layouts_map = {}
    
    if channel_id:
        # Получаем основные посты канала
        posts = Post.query.filter_by(channel_id=channel_id).all()
        
        # Получаем информацию о канале, чтобы найти связанную дискуссионную группу
        channel = Channel.query.filter_by(id=channel_id).first()
        discussion_group_id = channel.discussion_group_id if channel else None
        
        if discussion_group_id:
            # Добавляем комментарии из дискуссионной группы
            discussion_posts = Post.query.filter_by(channel_id=str(discussion_group_id)).all()
            posts.extend(discussion_posts)
        
        # Загружаем layouts для всех групп
        layouts_map = _get_layouts_map(channel_id, discussion_group_id)
    else:
        posts = Post.query.all()  # Возвращаем все посты
        # Загружаем все layouts
        all_layouts = Layout.query.all()
        layouts_map = {layout.grouped_id: layout.json_data for layout in all_layouts}

    return jsonify([{
        "id": post.id,
        "telegram_id": post.telegram_id,
        "channel_id": post.channel_id,
        "date": post.date,
        "message": post.message,
        "media_url": post.media_url,
        "thumb_url": post.thumb_url,
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
        "reply_to": post.reply_to,
        "layout": layouts_map.get(post.grouped_id) if post.grouped_id else None
    } for post in posts])

@posts_bp.route('/posts/check', methods=['GET'])
def check_post_exists():
    """Проверяет, существует ли пост с заданным telegram_id и channel_id."""
    telegram_id = request.args.get('telegram_id')
    channel_id = request.args.get('channel_id')
    if not telegram_id or not channel_id:
        return jsonify({"error": "telegram_id и channel_id обязательны"}), 400

    post_exists = Post.query.filter_by(telegram_id=telegram_id, channel_id=channel_id).first() is not None
    return jsonify({"exists": post_exists}), 200

@posts_bp.route('/posts', methods=['POST'])
def add_post():
    """Добавляет новый пост в базу данных."""
    data = request.json
    new_post = Post(
        telegram_id=data['telegram_id'],
        channel_id=data['channel_id'],  # Указываем ID канала
        date=data['date'],
        message=data.get('message', ''),  # Текст сообщения (по умолчанию пустая строка)
        media_url=data.get('media_url'),  # Сохраняем ссылку на медиа
        thumb_url=data.get('thumb_url'),  # Сохраняем ссылку на миниатюру
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

@posts_bp.route('/posts', methods=['DELETE'])
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
