# -*- coding: utf-8 -*-
import ldap
from config import Config

class DomainAuth:
    def __init__(self):
        self.settings = Config.load_settings()
    
    def authenticate(self, username, password):
        if not self.settings["domain_auth"]["enabled"]:
            return False
        
        try:
            domain_settings = self.settings["domain_auth"]
            ldap_server = domain_settings["ldap_server"]
            base_dn = domain_settings["base_dn"]
            
            # Подключение к LDAP
            conn = ldap.initialize(ldap_server)
            conn.protocol_version = ldap.VERSION3
            conn.set_option(ldap.OPT_REFERRALS, 0)
            
            # Попытка привязки (аутентификации)
            user_dn = f"cn={username},{base_dn}"
            conn.simple_bind_s(user_dn, password)
            
            conn.unbind()
            return True
            
        except ldap.INVALID_CREDENTIALS:
            return False
        except ldap.SERVER_DOWN:
            print("LDAP сервер недоступен")
            return False
        except Exception as e:
            print(f"Ошибка аутентификации: {e}")
            return False
    
    def get_user_info(self, username):
        return {
            "username": username,
            "display_name": username,
            "email": f"{username}@domain.com"
        }