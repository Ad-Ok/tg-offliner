from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=True)
    content = db.Column(db.Text, nullable=False)
    date = db.Column(db.String, nullable=False)
    media = db.Column(db.String, nullable=True)  # Ссылка на медиафайлы, если есть
    channel_name = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<Post {self.id} - {self.title}>"