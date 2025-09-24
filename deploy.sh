#!/bin/bash
set -e

# =========================
# Двухрежимный deploy.sh (аргумент + интерактив)
# =========================

MODE="$1"   # можно передать "minikube" или "production"

if [[ -z "$MODE" ]]; then
    echo "=== Выберите режим запуска ==="
    echo "1) minikube"
    echo "2) production"
    read -p "Введите 1 или 2: " CHOICE
    if [[ "$CHOICE" == "1" ]]; then
        MODE="minikube"
    elif [[ "$CHOICE" == "2" ]]; then
        MODE="production"
    else
        echo "Некорректный выбор. Выходим."
        exit 1
    fi
fi

if [[ "$MODE" != "minikube" && "$MODE" != "production" ]]; then
    echo "Использование: $0 [minikube|production]"
    exit 1
fi

echo "=== Выбран режим: $MODE ==="

# --- Проверка Docker и kubectl ---
echo "=== 1. Проверка Docker и kubectl ==="
docker version
kubectl version --client

IMAGE_NAME="quiz-app:latest"

if [[ "$MODE" == "minikube" ]]; then
    echo "=== 2. Проверка Minikube и загрузка образа ==="
    if ! minikube status >/dev/null 2>&1; then
        echo "Minikube не запущен. Запустите: minikube start"
        exit 1
    fi

    echo "=== 3. Сборка Docker-образа ==="
    docker build -t $IMAGE_NAME .

    echo "=== 4. Загрузка образа в Minikube ==="
    minikube image load $IMAGE_NAME

    echo "=== 5. Применение ConfigMap ==="
    kubectl apply -f k8s/configmap.yaml

    echo "=== 6. Создание/обновление Deployment ==="
    kubectl apply -f k8s/minikube-deployment.yaml

    echo "=== 7. Применение Service ==="
    kubectl apply -f k8s/minikube-service.yaml

elif [[ "$MODE" == "production" ]]; then
    echo "=== 2. Сборка Docker-образа для Production ==="
    docker build -t $IMAGE_NAME .

    echo "=== 3. Пуш Docker-образа в registry (Production) ==="
    # Здесь укажите ваш реестр
    # docker tag $IMAGE_NAME myregistry/quiz-app:latest
    # docker push myregistry/quiz-app:latest

    echo "=== 4. Применение Kubernetes ресурсов (Production) ==="
    kubectl apply -f k8s/secret.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/production-deployment.yaml
    kubectl apply -f k8s/production-service.yaml
    kubectl apply -f k8s/production-ingress.yaml
fi

echo "=== 8. Перезапуск деплоймента ($MODE) ==="
kubectl rollout restart deployment/quiz || true

echo "=== 9. Проверка состояния подов и сервисов ==="
kubectl get pods
kubectl get svc

# --- Автооткрытие веб-интерфейса ---
if [[ "$MODE" == "minikube" ]]; then
    IP=$(minikube ip)
    PORT=$(kubectl get svc quiz-service -o jsonpath='{.spec.ports[0].nodePort}')
    URL="http://$IP:$PORT"
elif [[ "$MODE" == "production" ]]; then
    URL="http://example.com" # заменить на реальный домен
fi

echo "Открываем веб-интерфейс по адресу: $URL"
xdg-open "$URL" 2>/dev/null || open "$URL" 2>/dev/null || true

echo "=== Деплой завершён успешно! ==="
