import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_url = os.environ.get("DATABASE_URL")
        self.conn = None
        
    def get_connection(self):
        """Получение соединения с базой данных"""
        try:
            if self.db_url and self.db_url.startswith('postgresql'):
                # PostgreSQL
                self.conn = psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
            else:
                # SQLite (по умолчанию)
                if not self.db_url:
                    self.db_url = "sqlite:///quiz_dev.db"
                db_path = self.db_url.replace('sqlite:///', '')
                self.conn = sqlite3.connect(db_path, check_same_thread=False)
                self.conn.row_factory = sqlite3.Row
                
            return self.conn
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise

    def execute_query(self, query, params=None):
        """Выполнение SQL запроса"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if query.strip().upper().startswith('SELECT'):
                result = cursor.fetchall()
            else:
                conn.commit()
                result = None
                
            return result
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка выполнения запроса: {e}")
            raise
        finally:
            cursor.close()

    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            # Таблица пользователей
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_access BOOLEAN DEFAULT FALSE,
                    manage_questions BOOLEAN DEFAULT FALSE,
                    manage_settings BOOLEAN DEFAULT FALSE,
                    manage_users BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица админов
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS admins (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица настроек
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица вопросов
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS questions (
                    id SERIAL PRIMARY KEY,
                    question_text TEXT NOT NULL,
                    question_type VARCHAR(50) DEFAULT 'single_choice',
                    options JSON,
                    correct_answer JSON,
                    category VARCHAR(100) DEFAULT 'general',
                    level VARCHAR(10) DEFAULT 'L1',
                    weight INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица сессий тестирования
            self.execute_query('''
                CREATE TABLE IF NOT EXISTS test_sessions (
                    id SERIAL PRIMARY KEY,
                    user_identifier VARCHAR(255),
                    user_display_name VARCHAR(255),
                    questions_data JSON,
                    answers_data JSON,
                    score INTEGER DEFAULT 0,
                    percent DECIMAL(5,2) DEFAULT 0,
                    level VARCHAR(10),
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Добавляем администратора по умолчанию
            self.execute_query('''
                INSERT OR IGNORE INTO admins (username) VALUES ('admin')
            ''')
            
            # Добавляем базовые настройки
            default_settings = [
                ('domain_auth_enabled', 'false'),
                ('smtp_enabled', 'false'),
                ('smtp_host', ''),
                ('smtp_port', '587'),
                ('smtp_username', ''),
                ('smtp_password', ''),
                ('notification_email', ''),
                ('test_duration', '60'),
                ('questions_per_test', '50')
            ]
            
            for key, value in default_settings:
                self.execute_query('''
                    INSERT OR IGNORE INTO settings (key, value) 
                    VALUES (?, ?)
                ''', (key, value))
            
            logger.info("База данных успешно инициализирована")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            return False

    def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()

# Глобальный экземпляр базы данных
db_instance = Database()