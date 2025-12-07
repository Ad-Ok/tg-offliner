from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.Integer, nullable=False)
    channel_id = db.Column(db.String, nullable=False)  # ID канала
    date = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String, nullable=True)
    thumb_url = db.Column(db.String, nullable=True)  # Путь к миниатюре
    media_type = db.Column(db.String, nullable=True)
    mime_type = db.Column(db.String, nullable=True)
    author_name = db.Column(db.String, nullable=True)  # Имя автора
    author_avatar = db.Column(db.String, nullable=True)  # Ссылка на аватар автора
    author_link = db.Column(db.String, nullable=True)  # Ссылка на профиль автора
    repost_author_name = db.Column(db.String, nullable=True)  # Имя автора репоста
    repost_author_avatar = db.Column(db.String, nullable=True)  # Аватар автора репоста
    repost_author_link = db.Column(db.String, nullable=True)  # Ссылка на автора репоста
    reactions = db.Column(JSON, nullable=True)  # Хранение реакций в формате JSON
    grouped_id = db.Column(db.BigInteger, nullable=True)  # ID медиа-группы (альбома)
    reply_to = db.Column(db.Integer, nullable=True)  # ID сообщения, на которое дан ответ

    def __repr__(self):
        return f"<Post {self.telegram_id} from channel {self.channel_id}>"

class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.String, primary_key=True)  # ID канала
    name = db.Column(db.String, nullable=False)  # Название канала
    avatar = db.Column(db.String, nullable=True)  # Ссылка на аватар канала
    description = db.Column(db.Text, nullable=True)  # Описание канала
    creation_date = db.Column(db.String, nullable=True)  # Дата создания канала
    subscribers = db.Column(db.String, nullable=True)  # Количество подписчиков
    posts_count = db.Column(db.Integer, nullable=True)  # Количество постов в канале
    comments_count = db.Column(db.Integer, nullable=True)  # Количество комментариев в группе обсуждений
    discussion_group_id = db.Column(db.BigInteger, nullable=True)  # ID группы обсуждений канала
    changes = db.Column(JSON, nullable=False, default='{}')  # JSON с изменениями канала

    def __repr__(self):
        return f"<Channel {self.id} - {self.name}>"

class Edit(db.Model):
    __tablename__ = 'edits'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    telegram_id = db.Column(db.Integer, nullable=False)  # ID телеграм сообщения
    channel_id = db.Column(db.String, nullable=False)  # ID канала
    date = db.Column(db.String, nullable=False)  # Дата редактирования
    changes = db.Column(JSON, nullable=False)  # JSON с изменениями: {"message": "new text", "reactions": {...}, "hidden": "true"}

    def __repr__(self):
        return f"<Edit {self.id} for message {self.telegram_id} in channel {self.channel_id}>"

class Layout(db.Model):
    __tablename__ = 'layouts'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    grouped_id = db.Column(db.BigInteger, nullable=False, unique=True)  # ID медиа-группы
    channel_id = db.Column(db.String, nullable=False)  # ID канала
    json_data = db.Column(JSON, nullable=False)  # JSON с данными layout

    def __repr__(self):
        return f"<Layout for grouped_id {self.grouped_id} in channel {self.channel_id}>"

class Page(db.Model):
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    channel_id = db.Column(db.String, nullable=False)  # ID канала
    json_data = db.Column(JSON, nullable=False)  # JSON с данными сетки и содержимого

    def __repr__(self):
        return f"<Page {self.id} for channel {self.channel_id}>"