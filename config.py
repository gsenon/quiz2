# -*- coding: utf-8 -*-
import os
import random
import string
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Безопасность
    APP_SECRET = os.environ.get("APP_SECRET", "super_secret_key_change_in_production")
    SESSION_TIMEOUT = 86400  # 24 часа
    
    # База данных
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "quiz_system")
    DB_USER = os.environ.get("DB_USER", "quiz_user")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "quiz_password")
    
    # PostgreSQL connection string
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Суперпользователи
    SUPER_USERS = ["k.skachilov"]
    
    # Настройки по умолчанию (будут храниться в БД)
    DEFAULT_SETTINGS = {
        "auth": {
            "domain_auth_enabled": False,
            "domain_name": "company.ru"
        },
        "email": {
            "enabled": False,
            "smtp_server": "smtp.company.ru",
            "smtp_port": 587,
            "smtp_username": "noreply@company.ru",
            "smtp_password": "",
            "from_email": "noreply@company.ru",
            "admin_emails": ["admin@company.ru"],
            "subject": "Результаты тестирования",
            "code_subject": "Код доступа для админки"
        }
    }
    
    @classmethod
    def today_pass(cls):
        return datetime.now().strftime("%d%m%Y")
    
    @classmethod
    def generate_code(cls, length=6):
        return ''.join(random.choices(string.digits, k=length))
    
    @classmethod
    def is_super_user(cls, username):
        return username.lower() in [user.lower() for user in cls.SUPER_USERS]