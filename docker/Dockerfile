FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements из папки docker
COPY docker/requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем приложение
COPY app/ .

# Копируем шрифт для PDF
COPY DejaVuSans.ttf /app/DejaVuSans.ttf

# Создаем не-root пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

CMD ["sh", "-c", "python manage.py && gunicorn --bind 0.0.0.0:8080 --workers 2 app:app"]