# -*- coding: utf-8 -*-
import logging
import hashlib
import time
import json
from datetime import datetime, timedelta
from config import Config
from models import db, Setting

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AuthSystem:
    def __init__(self):
        self.pending_admin_logins = {}
        logger.debug("Инициализирована система аутентификации")
    
    def get_settings(self):
        """Получение настроек из БД"""
        try:
            auth_settings = Setting.query.filter_by(key='auth').first()
            if auth_settings:
                return json.loads(auth_settings.value)
            return Config.DEFAULT_SETTINGS['auth']
        except Exception as e:
            logger.error(f"Ошибка получения настроек: {e}")
            return Config.DEFAULT_SETTINGS['auth']
    
    def initiate_admin_login(self, username):
        """Инициация процесса входа в админку"""
        if not username:
            logger.error("Пустой username для админки")
            return False
        
        if not Config.is_super_user(username):
            logger.error(f"Пользователь {username} не является суперпользователем")
            return False
        
        code = Config.generate_code()
        expiration = datetime.now() + timedelta(minutes=10)
        
        self.pending_admin_logins[username] = {
            'code': code,
            'expires': expiration,
            'attempts': 0
        }
        
        logger.debug(f"Сгенерирован код для админки {username}: {code}")
        return code
    
    def verify_admin_code(self, username, code):
        """Проверка кода подтверждения для админки"""
        if not username:
            return False
        
        if username not in self.pending_admin_logins:
            logger.error(f"Нет ожидающих вход запросов для админки {username}")
            return False
        
        login_data = self.pending_admin_logins[username]
        
        if datetime.now() > login_data['expires']:
            del self.pending_admin_logins[username]
            logger.error(f"Код истек для админки {username}")
            return False
        
        if login_data['attempts'] >= 3:
            del self.pending_admin_logins[username]
            logger.error(f"Превышено количество попыток для админки {username}")
            return False
        
        login_data['attempts'] += 1
        
        if login_data['code'] == code:
            del self.pending_admin_logins[username]
            logger.info(f"Успешная аутентификация админки для {username}")
            return True
        
        logger.warning(f"Неверный код для админки {username}. Попытка {login_data['attempts']}")
        return False
    
    def authenticate_test_user(self, username, use_domain_auth=False):
        """Аутентификация пользователя для тестирования"""
        settings = self.get_settings()
        
        if use_domain_auth:
            if not username or '@' not in username:
                logger.error(f"Неверный формат username: {username}")
                return False
            
            login = username.split('@')[0].lower()
            domain = username.split('@')[1].lower()
            
            expected_domain = settings["domain_name"]
            if domain != expected_domain:
                logger.error(f"Неверный домен: {domain}, ожидается: {expected_domain}")
                return False
            
            logger.info(f"Доменная аутентификация успешна для {login}")
            return self._create_user_info(login, username, f"{login} ({domain})")
        else:
            if not username or len(username.strip()) < 2:
                logger.error(f"Неверное ФИО: {username}")
                return False
            
            logger.info(f"Аутентификация по ФИО успешна для {username}")
            return self._create_user_info(username, "", username)
    
    def _create_user_info(self, username, email, display_name):
        user_info = {
            "username": username,
            "email": email,
            "display_name": display_name
        }
        logger.debug(f"Информация о пользователе: {user_info}")
        return user_info
    
    def create_session_token(self, username):
        timestamp = str(int(time.time()))
        token_data = f"{username}:{timestamp}:{Config.APP_SECRET}"
        session_token = hashlib.sha256(token_data.encode()).hexdigest()
        logger.debug(f"Создан сессионный токен для: {username}")
        return session_token
    
    def validate_session_token(self, session_token, username):
        try:
            current_time = int(time.time())
            valid_tokens = []
            
            for i in range(0, 86400, 3600):
                timestamp = str(current_time - i)
                token_data = f"{username}:{timestamp}:{Config.APP_SECRET}"
                valid_tokens.append(hashlib.sha256(token_data.encode()).hexdigest())
            
            return session_token in valid_tokens
        except Exception as e:
            logger.error(f"Ошибка валидации токена: {e}")
            return False