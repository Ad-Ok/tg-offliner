from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.Integer, unique=True, nullable=False)
    date = db.Column(db.String, nullable=False)
    message = db.Column(db.Text, nullable=True)  # Поле для текста сообщения

    def __repr__(self):
        return f"<Post {self.telegram_id}>"