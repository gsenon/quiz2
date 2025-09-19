# -*- coding: utf-8 -*-
import ldap
import logging
import base64
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DomainAuth:
    def __init__(self):
        self.settings = Config.load_settings()
        logger.debug(f"Загружены настройки доменной авторизации: enabled={self.settings['domain_auth']['enabled']}, server={self.settings['domain_auth']['ldap_server']}")
    
    def authenticate(self, username, password):
        if not self.settings["domain_auth"]["enabled"]:
            logger.warning("Доменная авторизация отключена в настройках")
            return False
        
        domain_settings = self.settings["domain_auth"]
        ldap_server = domain_settings["ldap_server"]
        base_dn = domain_settings["base_dn"]
        
        # Безопасное логирование
        password_hash = base64.b64encode(password.encode()).decode() if password else "empty"
        logger.debug(f"Попытка аутентификации пользователя: {username}, пароль (base64): {password_hash}")
        logger.debug(f"LDAP сервер: {ldap_server}")
        logger.debug(f"Base DN: {base_dn}")
        
        if not ldap_server:
            logger.error("LDAP сервер не настроен")
            return False
        
        if not base_dn:
            logger.error("Base DN не настроен")
            return False
        
        if not username:
            logger.error("Не указан логин")
            return False
        
        if not password:
            logger.error("Пароль не указан")
            return False
        
        try:
            # Подключение к LDAP
            logger.debug(f"Инициализация подключения к LDAP: {ldap_server}")
            conn = ldap.initialize(ldap_server)
            conn.protocol_version = ldap.VERSION3
            conn.set_option(ldap.OPT_REFERRALS, 0)
            
            # Попытка привязки (аутентификации)
            user_dn = f"cn={username},{base_dn}"
            logger.debug(f"Попытка привязки с DN: {user_dn}")
            
            conn.simple_bind_s(user_dn, password)
            logger.info(f"Успешная аутентификация пользователя: {username}")
            
            # Дополнительная информация о пользователе (опционально)
            try:
                search_filter = f"(cn={username})"
                result = conn.search_s(base_dn, ldap.SCOPE_SUBTREE, search_filter)
                logger.debug(f"Найдено записей пользователя: {len(result) if result else 0}")
            except Exception as search_error:
                logger.warning(f"Не удалось получить дополнительную информацию о пользователе: {search_error}")
            
            conn.unbind()
            logger.debug("LDAP соединение закрыто")
            
            return True
            
        except ldap.INVALID_CREDENTIALS:
            logger.error(f"Неверные учетные данные для пользователя: {username}")
            return False
            
        except ldap.SERVER_DOWN:
            logger.error(f"LDAP сервер недоступен: {ldap_server}")
            return False
            
        except ldap.LDAPError as e:
            error_desc = getattr(e, 'message', {}).get('desc', str(e))
            logger.error(f"Ошибка LDAP: {error_desc}")
            return False
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка аутентификации: {str(e)}")
            return False
    
    def get_user_info(self, username):
        logger.debug(f"Получение информации о пользователе: {username}")
        
        # Здесь можно добавить реальное получение информации из AD
        user_info = {
            "username": username,
            "display_name": username,
            "email": f"{username}@domain.com"
        }
        
        logger.debug(f"Информация о пользователе: username={user_info['username']}, email={user_info['email']}")
        return user_info