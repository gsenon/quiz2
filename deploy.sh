#!/bin/bash
set -e

echo "=== Выберите режим запуска ==="
echo "1) minikube"
echo "2) production"
read -rp "Введите 1 или 2: " CHOICE

if [[ "$CHOICE" == "1" ]]; then
    MODE="minikube"
elif [[ "$CHOICE" == "2" ]]; then
    MODE="production"
else
    echo "Неверный выбор"
    exit 1
fi

echo "=== Выбран режим: $MODE ==="

# 1. Проверка Docker и kubectl
echo "=== 1. Проверка Docker и kubectl ==="
docker version
kubectl version --client

# 2. PostgreSQL
echo "=== 2. Развёртывание PostgreSQL ==="
kubectl create namespace quiz-db || true
kubectl apply -f k8s/postgres-deployment.yaml -n quiz-db
kubectl apply -f k8s/postgres-service.yaml -n quiz-db

# 3. Сборка Docker-образа
echo "=== 3. Сборка Docker-образа ==="
docker build -t quiz-app .

# 4. Загрузка образа в Minikube (только minikube)
if [[ "$MODE" == "minikube" ]]; then
    echo "=== 4. Загрузка образа в Minikube ==="
    minikube image load quiz-app
fi

# 5. Применение ConfigMap
echo "=== 5. Применение ConfigMap ==="
kubectl apply -f k8s/configmap.yaml

# 6. Создание/обновление Deployment
echo "=== 6. Создание/обновление Deployment ==="
if [[ "$MODE" == "minikube" ]]; then
    kubectl apply -f k8s/minikube-deployment.yaml
    kubectl apply -f k8s/minikube-service.yaml
else
    kubectl apply -f k8s/production-deployment.yaml
    kubectl apply -f k8s/production-service.yaml
fi

# 7. Перезапуск деплоймента
echo "=== 7. Перезапуск деплоймента ==="
kubectl rollout restart deployment quiz

# 8. Проверка состояния
echo "=== 8. Проверка состояния подов и сервисов ==="
kubectl get pods
kubectl get svc

# 9. Открытие веб-интерфейса
echo "=== 9. Открытие веб-интерфейса ==="
if [[ "$MODE" == "minikube" ]]; then
    IP=$(minikube ip)
    PORT=$(kubectl get svc quiz-service -o jsonpath='{.spec.ports[0].nodePort}')
    URL="http://$IP:$PORT"
else
    URL="http://example.com" # замените на свой домен
fi

echo "Веб-интерфейс доступен по адресу: $URL"
xdg-open $URL 2>/dev/null || open $URL
