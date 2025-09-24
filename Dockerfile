# ===== Базовый образ =====
FROM python:3.12-slim

# ===== Метаданные =====
LABEL maintainer="you@example.com"
LABEL description="Quiz application"

# ===== Рабочая директория =====
WORKDIR /app

# ===== Обновление и установка зависимостей =====
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# ===== Копирование зависимостей =====
COPY requirements.txt .

# ===== Установка зависимостей Python =====
RUN pip install --no-cache-dir -r requirements.txt

# ===== Копирование проекта =====
COPY . .

# ===== Порт приложения =====
EXPOSE 8080

# ===== Команда запуска через Gunicorn =====
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]
