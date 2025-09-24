#!/bin/bash

set -e

echo "=== Deploying Quiz System to Minikube ==="

# Проверка инструментов
command -v minikube >/dev/null 2>&1 || { echo "❌ Minikube not installed"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "❌ Kubectl not installed"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not installed"; exit 1; }

# Проверка существования файлов
echo "📁 Checking required files..."
REQUIRED_FILES=(
    "k8s/namespace.yaml"
    "k8s/storageclass.yaml" 
    "k8s/postgres-secret.yaml"
    "k8s/postgres-pvc.yaml"
    "k8s/postgres-deployment.yaml"
    "k8s/postgres-service.yaml"
    "k8s/app-configmap.yaml"
    "k8s/app-secret.yaml"
    "k8s/app-deployment.yaml"
    "k8s/app-service.yaml"
    "k8s/app-ingress.yaml"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing file: $file"
        exit 1
    fi
    echo "✅ Found: $file"
done

# Пересоздаем кластер с нужными параметрами
echo "🔄 Recreating Minikube cluster..."
minikube delete || true
minikube start --cpus=4 --memory=8192 --disk-size=20g --driver=docker

# Настройка docker environment
echo "🔧 Configuring Docker environment..."
eval $(minikube docker-env)

# Сборка образа
echo "🐳 Building Docker image..."
docker build -t quiz-system:latest .

# Проверяем что образ создан
echo "🔍 Checking Docker images..."
docker images | grep quiz-system

# Создание namespace первым делом
echo "📁 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Создание StorageClass
echo "💾 Creating StorageClass..."
kubectl apply -f k8s/storageclass.yaml

# Установка PostgreSQL
echo "🗄️ Deploying PostgreSQL..."
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml

# Ожидание PostgreSQL
echo "⏳ Waiting for PostgreSQL to be ready..."
for i in {1..60}; do
    if kubectl get pods -n quiz-system -l app=postgresql 2>/dev/null | grep -q "1/1"; then
        echo "✅ PostgreSQL is ready!"
        # Даем дополнительное время для инициализации БД
        sleep 10
        break
    fi
    echo "⏱️ Waiting for PostgreSQL... ($i/60)"
    sleep 5
done

# Проверяем что PostgreSQL действительно готов
if ! kubectl wait --for=condition=ready pod -l app=postgresql -n quiz-system --timeout=30s; then
    echo "❌ PostgreSQL failed to start"
    kubectl describe pods -n quiz-system -l app=postgresql
    kubectl logs -n quiz-system -l app=postgresql
    exit 1
fi

# Сначала обновим app-deployment.yaml с imagePullPolicy: Never
echo "⚙️  Updating app deployment with local image settings..."
cat > k8s/app-deployment-fixed.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: quiz-app
  namespace: quiz-system
  labels:
    app: quiz-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: quiz-app
  template:
    metadata:
      labels:
        app: quiz-app
    spec:
      containers:
      - name: quiz-app
        image: quiz-system:latest
        imagePullPolicy: Never
        env:
        - name: DB_HOST
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DB_HOST
        - name: DB_PORT
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DB_PORT
        - name: DB_NAME
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DB_NAME
        - name: DB_USER
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DB_USER
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: password
        - name: APP_SECRET
          valueFrom:
            secretKeyRef:
              name: app-secret
              key: secret
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
          timeoutSeconds: 5
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 5
          timeoutSeconds: 3
        resources:
          requests:
            memory: "512Mi"
            cpu: "200m"
          limits:
            memory: "1Gi"
            cpu: "500m"
EOF

# Установка приложения
echo "🚀 Deploying Application..."
kubectl apply -f k8s/app-configmap.yaml
kubectl apply -f k8s/app-secret.yaml
kubectl apply -f k8s/app-deployment-fixed.yaml
kubectl apply -f k8s/app-service.yaml

# Ожидание приложения
echo "⏳ Waiting for Application to be ready..."
for i in {1..60}; do
    if kubectl get pods -n quiz-system -l app=quiz-app 2>/dev/null | grep -q "1/1"; then
        echo "✅ Application is ready!"
        break
    fi
    
    # Проверяем статус пода
    POD_STATUS=$(kubectl get pods -n quiz-system -l app=quiz-app -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "Unknown")
    echo "⏱️ Waiting for application... ($i/60) - Status: $POD_STATUS"
    
    # Если есть ошибки, покажем логи после 10 попыток
    if [ "$i" -gt 10 ]; then
        echo "🔍 Checking application logs..."
        kubectl logs -n quiz-system -l app=quiz-app --tail=20 || echo "No logs available yet"
    fi
    
    sleep 5
done

# Проверяем что приложение готово
if kubectl wait --for=condition=ready pod -l app=quiz-app -n quiz-system --timeout=30s; then
    echo "✅ Application started successfully!"
else
    echo "⚠️  Application may be having issues, checking details..."
    kubectl describe pods -n quiz-system -l app=quiz-app
    echo "=== Application logs ==="
    kubectl logs -n quiz-system -l app=quiz-app --tail=50
fi

# Включение Ingress
echo "🌐 Enabling Ingress..."
minikube addons enable ingress
sleep 20

# Проверяем что Ingress controller запустился
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ingress-nginx -n ingress-nginx --timeout=60s

# Установка Ingress
echo "🔗 Deploying Ingress..."
kubectl apply -f k8s/app-ingress.yaml

# Даем время Ingress'у настроиться
sleep 25

# Получение URL
echo "✅ Deployment Completed!"
echo ""
echo "📊 Pods status:"
kubectl get pods -n quiz-system -o wide

echo ""
echo "🌐 Services:"
kubectl get services -n quiz-system

echo ""
echo "🔗 Ingress:"
kubectl get ingress -n quiz-system

# Проверяем доступность приложения
echo ""
echo "🎯 Testing application accessibility..."
APP_URL=$(minikube service quiz-app-service -n quiz-system --url || echo "Unable to get URL")
echo "   Application URL: $APP_URL"

MINIKUBE_IP=$(minikube ip)
echo "   Direct access via: http://$MINIKUBE_IP"

echo ""
echo "🔍 Monitoring commands:"
echo "   kubectl logs -f deployment/quiz-app -n quiz-system"
echo "   kubectl logs -f deployment/postgresql -n quiz-system"
echo "   kubectl get all -n quiz-system"

echo ""
echo "🔄 If application has issues, try restarting:"
echo "   kubectl rollout restart deployment/quiz-app -n quiz-system"

echo ""
echo "🗑️ To clean up: kubectl delete namespace quiz-system"

# Очистка временного файла
rm -f k8s/app-deployment-fixed.yaml