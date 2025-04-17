from flask import Flask
from models import db
import multiprocessing

# Устанавливаем метод запуска процессов "fork"
multiprocessing.set_start_method("fork", force=True)

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db?check_same_thread=False'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def init_db(app):
    with app.app_context():
        db.create_all()