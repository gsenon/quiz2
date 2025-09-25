# auth.py - authentication helpers for Quiz app (ИСПРАВЛЕННАЯ ВЕРСИЯ)
import logging
import random
import string
from datetime import datetime, timedelta
from config import Config
from models import Setting, db  # Добавлен импорт db
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthSystem:
    def __init__(self):
        self.pending_admin_logins = {}

    def get_settings(self):
        try:
            s = Setting.query.filter_by(key='auth').first()
            if s:
                return json.loads(s.value)
            return {'domain_auth_enabled': False, 'domain_name': 'company.ru'}
        except Exception as e:
            logger.error(f'Error reading settings: {e}')
            return {'domain_auth_enabled': False, 'domain_name': 'company.ru'}

    @staticmethod
    def generate_code(length=6):
        return ''.join(random.choices(string.digits, k=length))

    def initiate_admin_login(self, username):
        if not username:
            return False
        if not Config.is_super_user(username):
            return False
        code = self.generate_code()
        self.pending_admin_logins[username] = {'code': code, 'expires': datetime.utcnow() + timedelta(minutes=10), 'attempts': 0}
        logger.info(f'Generated admin code for {username}')
        return code

    def verify_admin_code(self, username, code):
        if username not in self.pending_admin_logins:
            return False
        data = self.pending_admin_logins.get(username)
        if datetime.utcnow() > data['expires']:
            del self.pending_admin_logins[username]
            return False
        if data['attempts'] >= 3:
            del self.pending_admin_logins[username]
            return False
        data['attempts'] += 1
        if data['code'] == code:
            del self.pending_admin_logins[username]
            return True
        return False

    def authenticate_test_user(self, username, use_domain_auth=False):
        settings = self.get_settings()
        if use_domain_auth:
            if not username or '@' not in username:
                return False
            login, domain = username.split('@', 1)
            if domain.lower() != settings.get('domain_name','').lower():
                return False
            return {'username': login.lower(), 'email': username, 'display_name': login}
        else:
            if not username or len(username.strip()) < 2:
                return False
            return {'username': username, 'email': '', 'display_name': username}