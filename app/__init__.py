from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Создаем экземпляры Flask и SQLAlchemy
app = Flask(__name__)
db = SQLAlchemy()

def create_app():
    """Фабрика приложения"""
    # Конфигурация приложения
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_dev.db'  # по умолчанию
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'dev-secret-key'
    
    # Инициализация расширений
    db.init_app(app)
    
    return app

# Импортируем маршруты после создания приложения чтобы избежать циклических импортов
from app import routes
