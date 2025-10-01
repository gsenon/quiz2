#!/usr/bin/env python3
"""
Management script для Quiz приложения
"""

import os
import sys
import time
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Импортируем app и database
    from app import app
    from database import db_instance
    
    # Импортируем db из app или создаем
    try:
        from app import db
    except ImportError:
        from flask_sqlalchemy import SQLAlchemy
        db = SQLAlchemy(app)
        
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

def wait_for_postgres(max_retries=30, delay=5):
    """Ожидание доступности PostgreSQL"""
    logger.info("🔄 Ожидание доступности PostgreSQL...")
    
    for i in range(max_retries):
        try:
            # Простая проверка подключения к БД
            db_instance.get_connection()
            logger.info("✅ PostgreSQL доступен")
            return True
        except Exception as e:
            logger.warning(f"Попытка {i+1}/{max_retries}: PostgreSQL недоступен - {e}")
            if i < max_retries - 1:
                time.sleep(delay)
    
    logger.error("❌ PostgreSQL не стал доступен в течение отведенного времени")
    return False

def init_database():
    """Инициализация базы данных"""
    logger.info("🔄 Инициализация базы данных...")
    
    if not wait_for_postgres():
        return False
    
    try:
        # Инициализируем данные через database.py
        logger.info("Инициализация данных...")
        if db_instance.init_database():
            logger.info("✅ База данных инициализирована")
            return True
        else:
            logger.error("❌ Ошибка инициализации базы данных")
            return False
                
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        return False

def run_migrations():
    """Запуск миграций"""
    logger.info("🔄 Запуск миграций...")
    # Здесь можно добавить логику миграций
    logger.info("✅ Миграции завершены")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init_db":
            if init_database():
                logger.info("🎉 База данных успешно инициализирована")
                sys.exit(0)
            else:
                logger.error("💥 Ошибка инициализации базы данных")
                sys.exit(1)
                
        elif command == "run_migrations":
            if run_migrations():
                sys.exit(0)
            else:
                sys.exit(1)
            
        elif command == "runserver":
            logger.info("🚀 Запуск сервера...")
            # Проверяем доступность БД перед запуском
            if not wait_for_postgres():
                logger.error("❌ Не удалось подключиться к БД, выход")
                sys.exit(1)
            app.run(host="0.0.0.0", port=8080, debug=False)
            
        else:
            logger.error(f"❌ Неизвестная команда: {command}")
            print("Доступные команды:")
            print("  init_db       - Инициализация базы данных")
            print("  run_migrations - Запуск миграций")
            print("  runserver     - Запуск сервера")
            sys.exit(1)
    else:
        # Запуск по умолчанию - сервер
        logger.info("🚀 Запуск сервера...")
        if not wait_for_postgres():
            logger.error("❌ Не удалось подключиться к БД, выход")
            sys.exit(1)
        app.run(host="0.0.0.0", port=8080, debug=False)
