# Многоступенчатая сборка
FROM python:3.11-slim as builder

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Копирование виртуального окружения
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Создание пользователя
RUN groupadd -r quiz && useradd -r -g quiz quiz

# Рабочая директория
WORKDIR /app

# Копирование файлов проекта
COPY . .

# Копирование шрифта
RUN mkdir -p /usr/share/fonts/truetype/ && \
    cp DejaVuSans.ttf /usr/share/fonts/truetype/ && \
    chmod 644 /usr/share/fonts/truetype/DejaVuSans.ttf

# Настройка прав
RUN chown -R quiz:quiz /app && \
    chmod -R 755 /app && \
    mkdir -p /var/log/nginx /var/lib/nginx && \
    chown -R quiz:quiz /var/log/nginx /var/lib/nginx

# Создание конфигурации nginx
RUN echo 'worker_processes 1;\n\
daemon off;\n\
events { worker_connections 1024; }\n\
http {\n\
    include mime.types;\n\
    default_type application/octet-stream;\n\
    sendfile on;\n\
    keepalive_timeout 65;\n\
    access_log /var/log/nginx/access.log;\n\
    error_log /var/log/nginx/error.log;\n\
    upstream flask_app { server 127.0.0.1:8000; }\n\
    server {\n\
        listen 8080;\n\
        server_name localhost;\n\
        location /static/ {\n\
            alias /app/static/;\n\
            expires 1d;\n\
            add_header Cache-Control "public";\n\
        }\n\
        location / {\n\
            proxy_pass http://flask_app;\n\
            proxy_set_header Host \$host;\n\
            proxy_set_header X-Real-IP \$remote_addr;\n\
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;\n\
            proxy_set_header X-Forwarded-Proto \$scheme;\n\
        }\n\
    }\n\
}' > /etc/nginx/nginx.conf

# Экспорт портов
EXPOSE 8080

# Переключение на непривилегированного пользователя
USER quiz

# Запуск приложения
CMD nginx && python app.py --host=0.0.0.0 --port=8000