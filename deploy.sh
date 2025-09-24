#!/bin/bash
set -e

# =========================
# Двухрежимный deploy.sh (вариант 2)
# =========================

MODE=""
MODE_NAME=""
IMAGE_NAME="quiz-app:latest"

# --- Выбор режима ---
echo "=== Выберите режим запуска ==="
echo "1) minikube"
echo "2) production"
read -p "Введите 1 или 2: " MODE
if [[ "$MODE" == "1" ]]; then
    MODE_NAME="minikube"
elif [[ "$MODE" == "2" ]]; then
    MODE_NAME="production"
else
    echo "Некорректный выбор. Выходим."
    exit 1
fi
echo "=== Выбран режим: $MODE_NAME ==="

# --- Проверка Docker и kubectl ---
echo "=== 1. Проверка Docker и kubectl ==="
docker version
kubectl version --client

# ====================
# Блок для Minikube
# ====================
if [[ "$MODE_NAME" == "minikube" ]]; then
    echo "=== 2. Проверка Minikube и загрузка образа ==="
    
    # Сборка локального Docker-образа
    echo "=== 3. Сборка Docker-образа ==="
    docker build -t $IMAGE_NAME .

    # Загрузка образа напрямую в Minikube
    echo "=== 4. Загрузка образа в Minikube ==="
    minikube image load $IMAGE_NAME

    # Применение Kubernetes ресурсов
    echo "=== 5. Применение ConfigMap ==="
    kubectl apply -f k8s/configmap.yaml

    echo "=== 6. Создание/обновление Deployment ==="
    kubectl apply -f k8s/minikube-deployment.yaml

    echo "=== 7. Применение Service ==="
    kubectl apply -f k8s/minikube-service.yaml

# ====================
# Блок для Production
# ====================
else
    echo "=== 2. Сборка Docker-образа для Production ==="
    docker build -t $IMAGE_NAME .

    echo "=== 3. Пуш Docker-образа в registry для Production ==="
    # Настройте ваш Production registry:
    # docker tag $IMAGE_NAME myregistry/quiz-app:latest
    # docker push myregistry/quiz-app:latest

    echo "=== 4. Применение Kubernetes ресурсов (Production) ==="
    kubectl apply -f k8s/secret.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/production-deployment.yaml
    kubectl apply -f k8s/production-service.yaml
    kubectl apply -f k8s/production-ingress.yaml
fi

# --- Перезапуск деплоймента ---
echo "=== 8. Перезапуск деплоймента ($MODE_NAME) ==="
kubectl rollout restart deployment/quiz || true

# --- Проверка статуса подов и сервисов ---
echo "=== 9. Проверка состояния подов и сервисов ==="
kubectl get pods
kubectl get svc

echo "=== Деплой завершён успешно! ==="
