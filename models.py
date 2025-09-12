
# -*- coding: utf-8 -*-
"""
Базовые доменные знания для генератора вопросов.
"""

INTERNAL_KNOWLEDGE = {
    "components": {
        "resmtp": {"description": "обрабатывает входящие SMTP-сообщения и выполняет первичную проверку"},
        "mx-in": {"description": "очередь входящих писем"},
        "director": {"description": "балансировка IMAP-подключений"},
        "dovecot-rms": {"description": "хранение тел писем в Cassandra"},
        "mx-out": {"description": "очередь исходящих писем"},
        "compose": {"description": "создание исходящих писем"},
        "mail-id": {"description": "авторизация пользователей"},
        "caldav": {"description": "работа с календарями"},
        "beanstalkd": {"description": "очередь событий"},
        "caldav-mail": {"description": "уведомления о событиях календаря"},
        "templatemail": {"description": "шаблоны писем"},
        "diskus": {"description": "обработка вложений календаря"},
        "wsgate": {"description": "websocket-шлюз"},
        "nats": {"description": "шина сообщений"},
        "mail-events": {"description": "логирование событий"},
        "journaling": {"description": "архивирование писем"},
        "adsync": {"description": "синхронизация с AD"},
        "memcached": {"description": "кеширование сессий"},
        "rms-gc": {"description": "очистка удаленных объектов"}
    },
    "interactions": [
        "resmtp → mx-in → director → dovecot-rms",
        "compose → mx-out → внешний MX",
        "mail-id проверяет JWT в memcached",
        "caldav использует diskus для вложений",
        "caldav-mail отправляет через templatemail",
        "wsgate подписывается на события в nats",
        "mail-events получает из beanstalkd",
        "journaling читает из dovecot-rms",
        "adsync обновляет данные в mail-id"
    ],
    "incidents": [
        "Ошибка авторизации → проверить: mail-id, memcached, adsync",
        "Письма теряются → проверить: journaling, nats, mail-events",
        "Рассинхронизация БД → изменения вне dovecot-rms",
        "Календарь не синхронизируется → проверить: caldav, beanstalkd, network",
        "Не отправляются письма → проверить: mx-out, compose, фильтры",
        "Пользователь не получает письма → проверить: resmtp, mx-in, квоту в directory"
    ],
    "rules": [
        "Только dovecot-rms может изменять данные в БД",
        "Все подключения пользователя должны идти в один dovecot-rms",
        "Изменения в БД вне dovecot-rms приводят к рассинхронизации",
        "Вложения календаря обрабатываются через diskus"
    ]
}
