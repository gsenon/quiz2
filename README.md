# Quiz_Rambler


# Удаляем старый контейнер
sudo docker rm quiz-app

# Пересобираем образ
sudo docker build -t quiz-rambler-app:latest .

# Запускаем контейнер
sudo docker run -d -p 8080:8080 --name quiz-app quiz-rambler-app:latest

# Проверяем статус
sudo docker ps

# Смотрим логи
sudo docker logs quiz-app

# Сохраняем образ в файл
sudo docker save -o quiz-rambler-app.tar quiz-rambler-app:latest

# Можно также сжать файл
sudo docker save quiz-rambler-app:latest | gzip > quiz-rambler-app.tar.gz

# Проверяем размер файла
ls -lh quiz-rambler-app.tar/tar.gz

# #############################################################################

# Загрузка образа
sudo docker load -i quiz-rambler-app.tar

# Или для сжатого файла
sudo docker load -i quiz-rambler-app.tar.gz

# Проверка, что образ загрузился
sudo docker images

# ##############################################################################

