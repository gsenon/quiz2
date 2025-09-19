# -*- coding: utf-8 -*-
import os
import json
from datetime import datetime

class Config:
    APP_SECRET = os.environ.get("APP_SECRET", "super_secret_key_change_me")
    DATA_FILE = "quiz_data.json"
    SETTINGS_FILE = "settings.json"
    
    # Настройки по умолчанию
    DEFAULT_SETTINGS = {
        "domain_auth": {
            "enabled": False,
            "domain": "",
            "ldap_server": "",
            "base_dn": ""
        },
        "email": {
            "enabled": False,
            "smtp_server": "",
            "smtp_port": 587,
            "smtp_username": "",
            "smtp_password": "",
            "from_email": "",
            "admin_emails": [],
            "subject": "Результаты тестирования"
        }
    }
    
    @classmethod
    def load_settings(cls):
        if os.path.exists(cls.SETTINGS_FILE):
            try:
                with open(cls.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return cls.DEFAULT_SETTINGS
    
    @classmethod
    def save_settings(cls, settings):
        with open(cls.SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    
    @classmethod
    def today_pass(cls):
        return datetime.now().strftime("%d%m%Y")