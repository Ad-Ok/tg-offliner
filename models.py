from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.Integer, unique=True, nullable=False)
    channel_id = db.Column(db.String, nullable=False)  # ID канала
    date = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String, nullable=True)
    media_type = db.Column(db.String, nullable=True)
    mime_type = db.Column(db.String, nullable=True)
    author_name = db.Column(db.String, nullable=True)  # Имя автора
    author_avatar = db.Column(db.String, nullable=True)  # Ссылка на аватар автора
    author_link = db.Column(db.String, nullable=True)  # Ссылка на профиль автора
    repost_author_name = db.Column(db.String, nullable=True)  # Имя автора репоста
    repost_author_avatar = db.Column(db.String, nullable=True)  # Аватар автора репоста
    repost_author_link = db.Column(db.String, nullable=True)  # Ссылка на автора репоста
    reactions = db.Column(JSON, nullable=True)  # Хранение реакций в формате JSON

    def __repr__(self):
        return f"<Post {self.telegram_id} from channel {self.channel_id}>"

class Channel(db.Model):
    __tablename__ = 'channels'

    id = db.Column(db.String, primary_key=True)  # ID канала
    name = db.Column(db.String, nullable=False)  # Название канала
    avatar = db.Column(db.String, nullable=True)  # Ссылка на аватар канала
    description = db.Column(db.Text, nullable=True)  # Описание канала

    def __repr__(self):
        return f"<Channel {self.id} - {self.name}>"