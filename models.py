from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.Integer, unique=True, nullable=False)
    date = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=True)
    media_url = db.Column(db.String, nullable=True)
    media_type = db.Column(db.String, nullable=True)
    mime_type = db.Column(db.String, nullable=True)
    author_name = db.Column(db.String, nullable=True)  # Имя автора
    author_avatar = db.Column(db.String, nullable=True)  # Ссылка на аватар автора
    author_link = db.Column(db.String, nullable=True)  # Ссылка на профиль автора

    def __repr__(self):
        return f"<Post {self.telegram_id}>"