#!/bin/bash
LOG_FILE=deploy_$(date +%Y%m%d_%H%M%S).log
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Запуск деплоя Quiz App ($(date)) ==="

kubectl version --client
minikube status
minikube addons enable ingress || echo "Ingress включён"

kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/quiz-deployment.yaml
kubectl apply -f k8s/quiz-service.yaml
kubectl apply -f k8s/quiz-ingress.yaml

echo "=== Статус подов ==="
kubectl get pods

echo "=== Логи подов Quiz ==="
for pod in $(kubectl get pods -l app=quiz -o jsonpath='{.items[*].metadata.name}'); do
    echo "----- pod/$pod -----"
    kubectl logs $pod --tail=50
done

kubectl get svc
kubectl get ingress
echo "Добавьте в /etc/hosts: 192.168.49.2 quiz.local"
