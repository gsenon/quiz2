#!/bin/bash
set -e

APP_NAME="quiz-app"
IMAGE_NAME="quiz-app:latest"
MINIKUBE_MEMORY=4096
MINIKUBE_CPUS=2
K8S_DIR="k8s"

echo "=== 1. Проверка Minikube и Docker ==="
if ! command -v minikube &> /dev/null; then
    echo "❌ Minikube не установлен!"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    exit 1
fi

echo "=== 2. Запуск Minikube ==="
minikube start --memory=$MINIKUBE_MEMORY --cpus=$MINIKUBE_CPUS --driver=docker
eval $(minikube docker-env)

echo "=== 3. Сборка Docker-образа ==="
docker build -t $IMAGE_NAME .

echo "=== 4. Деплой Postgres ==="
kubectl apply -f $K8S_DIR/postgres-secret.yaml
kubectl apply -f $K8S_DIR/postgres-pvc.yaml
kubectl apply -f $K8S_DIR/postgres-deployment.yaml
kubectl apply -f $K8S_DIR/postgres-service.yaml

echo "=== 5. Деплой Quiz App ==="
kubectl apply -f $K8S_DIR/configmap.yaml
kubectl apply -f $K8S_DIR/secret-example.yaml
kubectl apply -f $K8S_DIR/deployment-minikube.yaml
kubectl apply -f $K8S_DIR/service.yaml

echo "=== 6. Проверка состояния Pod'ов ==="
kubectl get pods

echo "=== 7. Открываем сервис в браузере ==="
minikube service $APP_NAME

echo "✅ Развёртывание завершено!"
