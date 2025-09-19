# -*- coding: utf-8 -*-
import smtplib
import logging
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from config import Config

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        self.settings = Config.load_settings()
        # Безопасное логирование настроек
        email_settings = self.settings["email"].copy()
        if email_settings["smtp_password"]:
            email_settings["smtp_password"] = "***"  # Скрываем пароль
        logger.debug(f"Загружены настройки email: enabled={email_settings['enabled']}, server={email_settings['smtp_server']}")
    
    def send_results(self, user_info, pdf_data, results):
        if not self.settings["email"]["enabled"]:
            logger.warning("Отправка email отключена в настройках")
            return False
        
        try:
            email_settings = self.settings["email"]
            logger.debug(f"Попытка отправки email для пользователя: {user_info['username']}")
            
            # Проверка обязательных параметров
            if not email_settings["smtp_server"]:
                logger.error("SMTP сервер не настроен")
                return False
            if not email_settings["smtp_username"]:
                logger.error("SMTP пользователь не настроен")
                return False
            if not email_settings["smtp_password"]:
                logger.error("SMTP пароль не настроен")
                return False
            if not email_settings["from_email"]:
                logger.error("Email отправителя не настроен")
                return False
            
            # Создание сообщения
            msg = MIMEMultipart()
            msg['From'] = email_settings["from_email"]
            msg['To'] = user_info.get("email", "")
            msg['Cc'] = ", ".join(email_settings["admin_emails"])
            msg['Subject'] = email_settings["subject"]
            
            # Текст письма
            body = f"""
            Уважаемый(ая) {user_info.get('display_name', 'пользователь')},
            
            Ваши результаты тестирования:
            - Итоговый результат: {results['percent']}%
            - Рекомендуемый уровень: {results['level']}
            
            Во вложении детальный отчет.
            """
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Вложение PDF
            pdf_attachment = MIMEApplication(pdf_data)
            pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=f"results_{user_info['username']}.pdf")
            msg.attach(pdf_attachment)
            
            logger.debug(f"Подготовка к отправке на SMTP: {email_settings['smtp_server']}:{email_settings['smtp_port']}")
            
            # Отправка
            with smtplib.SMTP(email_settings["smtp_server"], email_settings["smtp_port"]) as server:
                logger.debug("Установлено соединение с SMTP сервером")
                
                server.starttls()
                logger.debug("STARTTLS выполнен")
                
                # Безопасное логирование авторизации
                logger.debug(f"Авторизация пользователя: {email_settings['smtp_username']}")
                server.login(email_settings["smtp_username"], email_settings["smtp_password"])
                logger.debug("Успешная авторизация на SMTP сервере")
                
                recipients = [user_info.get("email", "")] + email_settings["admin_emails"]
                logger.debug(f"Получатели: {recipients}")
                
                server.sendmail(email_settings["from_email"], recipients, msg.as_string())
                logger.info(f"Email успешно отправлен пользователю {user_info['username']}")
            
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"Ошибка аутентификации SMTP: {e}")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"Ошибка подключения к SMTP серверу: {e}")
            return False
        except smtplib.SMTPServerDisconnected as e:
            logger.error(f"Сервер SMTP разорвал соединение: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"Ошибка SMTP: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка отправки email: {str(e)}")
            return False