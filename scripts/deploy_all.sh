#!/bin/bash
set -e

echo "🚀 Запуск деплоймента Quiz системы"

# Определяем базовую директорию
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
K8S_DIR="$PROJECT_ROOT/k8s"

echo "📁 Рабочая директория: $PROJECT_ROOT"

# Проверяем существование директории k8s
if [ ! -d "$K8S_DIR" ]; then
    echo "❌ Директория k8s не найдена: $K8S_DIR"
    exit 1
fi

# Проверяем Dockerfile
if [ ! -f "$PROJECT_ROOT/docker/Dockerfile" ]; then
    echo "❌ Dockerfile не найден: $PROJECT_ROOT/docker/Dockerfile"
    exit 1
fi

echo "🔍 Проверка файлов..."
for file in configmap.yaml secrets.yaml postgres-deployment.yaml postgres-service.yaml quiz-deployment.yaml quiz-service.yaml quiz-ingress.yaml; do
    if [ -f "$K8S_DIR/$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file"
    fi
done

# Деплоймент
echo ""
echo "🚀 Начало деплоймента..."

# 1. Конфигурации
echo "1. Создаем конфигурации..."
kubectl apply -f "$K8S_DIR/configmap.yaml"
kubectl apply -f "$K8S_DIR/secrets.yaml"

# 2. PostgreSQL PVC
echo "2. Создаем PVC для PostgreSQL..."
if [ -f "$K8S_DIR/postgres-pvc.yaml" ]; then
    kubectl apply -f "$K8S_DIR/postgres-pvc.yaml"
else
    echo "📝 Создаем временный PVC..."
    kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: standard
EOF
fi

# 3. PostgreSQL
echo "3. Запускаем PostgreSQL..."
kubectl apply -f "$K8S_DIR/postgres-deployment.yaml"
kubectl apply -f "$K8S_DIR/postgres-service.yaml"

# 4. Ожидание PostgreSQL
echo "4. Ждем запуска PostgreSQL..."
sleep 20

# 5. Сборка образа с --no-cache
echo "5. Собираем образ приложения с --no-cache..."
echo "🔨 Команда: docker build --no-cache -t quiz-app:latest -f \"$PROJECT_ROOT/docker/Dockerfile\" \"$PROJECT_ROOT\""
docker build --no-cache -t quiz-app:latest -f "$PROJECT_ROOT/docker/Dockerfile" "$PROJECT_ROOT"
echo "✅ Образ собран с --no-cache"

# 6. Загрузка образа
echo "6. Загружаем образ в minikube..."
minikube image load quiz-app:latest

# 7. Приложение
echo "7. Запускаем приложение..."
kubectl apply -f "$K8S_DIR/quiz-deployment.yaml"
kubectl apply -f "$K8S_DIR/quiz-service.yaml"
kubectl apply -f "$K8S_DIR/quiz-ingress.yaml"

# 8. Проверка статуса
echo "8. Проверяем статус..."
sleep 15
kubectl get pods,svc,ingress

echo "🎉 Деплоймент завершен!"
echo "💡 Приложение доступно по: http://quiz.local"
echo "   Добавьте в /etc/hosts: $(minikube ip) quiz.local"