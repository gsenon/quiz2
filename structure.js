
/* 
Quiz_/
├── 🐳 docker/                          # Docker конфигурации
│   ├── Dockerfile                     # Docker образ приложения
│   └── requirements.txt               # Python зависимости
│
├── 🚀 app/                            # Основное приложение
│   ├── __init__.py                    # Инициализация приложения
│   ├── app.py                         # Основное Flask приложение
│   ├── models.py                      # Модели базы данных
│   ├── auth.py                        # Система аутентификации
│   ├── config.py                      # Конфигурация приложения
│   ├── manage.py                      # Утилита управления БД
│   │
│   ├── 🎯 generators/                 # Генератор вопросов
│   │   ├── __init__.py
│   │   └── question_generator.py      # Логика генерации вопросов
│   │
│   ├── 📄 templates/                  # HTML шаблоны
│   │   ├── index.html                 # Главная страница
│   │   ├── test.html                  # Страница тестирования
│   │   ├── results.html               # Результаты теста
│   │   ├── admin_login.html           # Вход в админку
│   │   ├── admin_dashboard.html       # Панель управления
│   │   ├── admin_questions.html       # Управление вопросами
│   │   ├── admin_settings.html        # Настройки системы
│   │   ├── admin_users.html           # Управление пользователями
│   │   └── admin_stats.html           # Статистика
│   │
│   └── 🎨 static/                     # Статические файлы
│       ├── css/
│       │   └── style.css              # Основные стили
│       ├── js/
│       │   └── test.js                # JavaScript для тестов
│       └── fonts/
│           └── DejaVuSans.ttf         # Шрифт для PDF (опционально)
│
├── ☸️ k8s/                            # Kubernetes конфигурации
│   ├── postgres-deployment.yaml       # Развертывание PostgreSQL
│   ├── postgres-service.yaml          # Сервис PostgreSQL
│   ├── quiz-deployment.yaml           # Развертывание приложения
│   ├── quiz-service.yaml              # Сервис приложения
│   ├── quiz-ingress.yaml              # Ingress для доступа
│   ├── configmap.yaml                 # Конфигурационные данные
│   └── secrets.yaml                   # Секреты (пароли, ключи)
│
├── 📜 scripts/                        # Скрипты развертывания
│   ├── deploy_all.sh                  # Полное развертывание
│   ├── deploy_final.sh                # Финальное развертывание
│   ├── build_and_deploy.sh            # Сборка и деплой
│   └── check_structure.sh             # Проверка структуры
│
├── 📋 Документация и настройки
│   ├── .env                           # Переменные окружения
│   ├── .env.example                   # Пример переменных окружения
│   ├── .gitignore                     # Игнорируемые файлы Git
│   ├── .dockerignore                  # Игнорируемые файлы Docker
│   └── README.md                      # Документация проекта
│
└── 📊 Данные и ресурсы
    ├── quiz_data.json                 # База вопросов (исходная)
    └── материалы/                     # Дополнительные материалы
        ├️── взаимодействие_компонентов.txt
        └── инциденты_и_конфигурирование.pdf

    
*/