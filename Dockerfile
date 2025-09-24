# ===== Базовый образ =====
FROM python:3.9-bullseye-slim

# ===== Метаданные =====
LABEL maintainer="your_email@example.com"
LABEL description="Quiz app for Minikube and Kubernetes"

# ===== Рабочая директория =====
WORKDIR /app

# ===== Установка системных зависимостей =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# ===== Копируем зависимости =====
COPY requirements.txt .

# ===== Установка Python-зависимостей =====
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# ===== Копируем исходный код =====
COPY . .

# ===== Создаем безопасного пользователя =====
RUN groupadd -r quizgroup && useradd -r -g quizgroup quizuser \
    && chown -R quizuser:quizgroup /app

USER quizuser

# ===== Порт приложения =====
EXPOSE 8000

# ===== Переменные окружения =====
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV APP_WORKERS=2

# ===== Команда запуска =====
# Для Minikube можно использовать простой запуск Flask:
# CMD ["python", "app.py"]
# Для продакшена через Gunicorn:
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "app:app"]
