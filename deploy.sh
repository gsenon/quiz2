#!/bin/bash
set -e

MODE=$1  # "minikube" или "production"
IMAGE_NAME="quiz-app:latest"
LOCAL_REGISTRY="localhost:5000"  # Для Minikube
PROD_REGISTRY="myregistry"       # Для продакшена, замените на ваш registry

if [[ "$MODE" != "minikube" && "$MODE" != "production" ]]; then
    echo "Использование: ./deploy.sh [minikube|production]"
    exit 1
fi

echo "=== Выбран режим: $MODE ==="
echo "=== 1. Проверка Docker и kubectl ==="
docker version
kubectl version --client

# ====================
# Минекюб
# ====================
if [[ "$MODE" == "minikube" ]]; then
    echo "=== 2. Проверка Minikube ==="
    minikube status >/dev/null

    echo "=== 3. Сборка Docker-образа ==="
    docker build -t $IMAGE_NAME .

    echo "=== 4. Загрузка образа в Minikube ==="
    minikube image load $IMAGE_NAME

    echo "=== 5. Применение ConfigMap и Secret ==="
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secret.yaml

    echo "=== 6. Создание/обновление Deployment и Service ==="
    kubectl apply -f k8s/minikube-deployment.yaml
    kubectl apply -f k8s/minikube-service.yaml

# ====================
# Продакшен
# ====================
else
    echo "=== 2. Сборка Docker-образа для продакшена ==="
    docker build -t $IMAGE_NAME .

    echo "=== 3. Тегирование и пуш в registry ==="
    docker tag $IMAGE_NAME $PROD_REGISTRY/quiz-app:latest
    docker push $PROD_REGISTRY/quiz-app:latest

    echo "=== 4. Применение ConfigMap, Secret и Deployment ==="
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secret.yaml
    kubectl apply -f k8s/production-deployment.yaml
    kubectl apply -f k8s/production-service.yaml
    kubectl apply -f k8s/production-ingress.yaml
fi

echo "=== 7. Перезапуск деплоймента ==="
kubectl rollout restart deployment/quiz || true

echo "=== 8. Проверка состояния подов и сервисов ==="
kubectl get pods
kubectl get svc

# ====================
# Открытие веб-интерфейса
# ====================
if [[ "$MODE" == "minikube" ]]; then
    IP=$(minikube ip)
    PORT=$(kubectl get svc quiz-service -o jsonpath='{.spec.ports[0].nodePort}')
    URL="http://$IP:$PORT"
else
    URL="http://quiz.example.com"  # замените на ваш домен
fi

echo "=== 9. Веб-интерфейс: $URL ==="
xdg-open $URL 2>/dev/null || open $URL
