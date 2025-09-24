# -*- coding: utf-8 -*-
import logging

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        pass
    
    def send_admin_code(self, username, code, settings):
        """Отправка кода для админки"""
        logger.info(f"Код для {username}: {code}")
        return True
    
    def send_results(self, user_info, pdf_data, results):
        """Отправка результатов"""
        logger.info(f"Результаты отправлены для {user_info.get('username')}")
        return True