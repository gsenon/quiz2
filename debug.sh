#!/bin/bash

echo "=== Debugging Quiz System ==="

# Проверяем поды
echo "📊 Pods status:"
kubectl get pods -n quiz-system -o wide

echo ""
echo "🔍 Application logs:"
kubectl logs -n quiz-system -l app=quiz-app --tail=50

echo ""
echo "🐛 Checking application container:"
kubectl exec -n quiz-system -it deployment/quiz-app -- ls -la /app/

echo ""
echo "🐍 Checking Python environment:"
kubectl exec -n quiz-system -it deployment/quiz-app -- python --version

echo ""
echo "📦 Checking installed packages:"
kubectl exec -n quiz-system -it deployment/quiz-app -- pip freeze

echo ""
echo "🔗 Checking database connection:"
kubectl exec -n quiz-system -it deployment/quiz-app -- python -c "
import os
print('DB_HOST:', os.environ.get('DB_HOST'))
print('DB_PORT:', os.environ.get('DB_PORT')) 
print('DB_NAME:', os.environ.get('DB_NAME'))
print('DB_USER:', os.environ.get('DB_USER'))
print('DB_PASSWORD:', '***' if os.environ.get('DB_PASSWORD') else 'None')
"

echo ""
echo "✅ Debug information collected"