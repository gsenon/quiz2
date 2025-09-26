# database.py - управление подключением к БД
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from models import Base, init_db
import os

db = SQLAlchemy()

def setup_database(app):
    """Настройка подключения к БД для Flask приложения"""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        pg_user = os.environ.get("DB_USER")
        pg_pass = os.environ.get("DB_PASSWORD")
        pg_host = os.environ.get("DB_HOST")
        pg_port = os.environ.get("DB_PORT")
        pg_name = os.environ.get("DB_NAME")
        if pg_user and pg_pass and pg_host and pg_port and pg_name:
            DATABASE_URL = f"postgresql+psycopg2://{pg_user}:{pg_pass}@{pg_host}:{pg_port}/{pg_name}"
        else:
            DATABASE_URL = "sqlite:///quiz_dev.db"

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Инициализация Flask-SQLAlchemy
    db.init_app(app)
    
    # Создание таблиц при первом запуске
    with app.app_context():
        engine = create_engine(DATABASE_URL)
        init_db(engine)
    
    return db