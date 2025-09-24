FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости сначала для кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Создаем пользователя для безопасности
RUN groupadd -r quizgroup && useradd -r -g quizgroup quizuser \
    && chown -R quizuser:quizgroup /app

USER quizuser

# Проверяем что файлы на месте
RUN echo "=== Checking files ===" && \
    ls -la /app/ && \
    echo "=== Python version ===" && \
    python --version && \
    echo "=== Installed packages ===" && \
    pip freeze

EXPOSE 8000

# Запускаем простой HTTP сервер для тестирования сначала
CMD ["python", "-m", "http.server", "8000"]