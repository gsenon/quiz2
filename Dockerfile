# Многоступенчатая сборка
FROM python:3.11-slim AS builder

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

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY . .

# Копирование шрифта
RUN mkdir -p /usr/share/fonts/truetype/ && \
    cp DejaVuSans.ttf /usr/share/fonts/truetype/ && \
    chmod 644 /usr/share/fonts/truetype/DejaVuSans.ttf

# Создание директорий для nginx 
RUN mkdir -p /var/log/nginx /var/lib/nginx /var/run/nginx && \
    chown -R www-data:www-data /var/log/nginx /var/lib/nginx /var/run/nginx && \
    chmod -R 755 /var/log/nginx /var/lib/nginx /var/run/nginx

# Создание конфига nginx
RUN echo 'worker_processes auto;\n\
error_log /var/log/nginx/error.log notice;\n\
pid /var/run/nginx/nginx.pid;\n\
events { worker_connections 1024; }\n\
http {\n\
    include /etc/nginx/mime.types;\n\
    default_type application/octet-stream;\n\
    sendfile on;\n\
    keepalive_timeout 65;\n\
    access_log /var/log/nginx/access.log;\n\
    \n\
    upstream flask_app { server 127.0.0.1:8000; }\n\
    \n\
    server {\n\
        listen 8080;\n\
        server_name localhost;\n\
        \n\
        location /static/ {\n\
            alias /app/static/;\n\
            expires 1d;\n\
            add_header Cache-Control "public";\n\
        }\n\
        \n\
        location / {\n\
            proxy_pass http://flask_app;\n\
            proxy_set_header Host \$host;\n\
            proxy_set_header X-Real-IP \$remote_addr;\n\
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;\n\
            proxy_set_header X-Forwarded-Proto \$scheme;\n\
        }\n\
    }\n\
}' > /etc/nginx/nginx.conf

# Настройка прав для приложения
RUN chown -R www-data:www-data /app && \
    chmod -R 755 /app

# Экспорт портов
EXPOSE 8080

# Переключение на пользователя nginx
USER www-data

# Запуск приложения
CMD nginx -g "daemon off;" & python app.py --host=0.0.0.0 --port=8000