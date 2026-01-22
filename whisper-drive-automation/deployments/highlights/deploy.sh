#!/bin/bash

set -e

echo "==========================================="
echo "🚀 Déploiement Highlights Processor"
echo "==========================================="

PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
SERVICE_NAME="highlights-orchestrator"

echo "Projet: $PROJECT_ID"
echo "Région: $REGION"
echo "Service: $SERVICE_NAME"

# Aller à la racine du projet
cd "$(dirname "$0")/../.."

# Backup du Dockerfile s'il existe
if [ -f "Dockerfile" ]; then
    mv Dockerfile Dockerfile.backup
fi

# Copier le Dockerfile highlights comme Dockerfile principal
cp deployments/highlights/Dockerfile ./Dockerfile

# Build et déploiement
echo ""
echo "📦 Build et déploiement..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=3600 \
    --max-instances=10 \
    --min-instances=0 \
    --set-env-vars="PYTHONPATH=/app/src"

# Restaurer
rm -f ./Dockerfile
if [ -f "Dockerfile.backup" ]; then
    mv Dockerfile.backup Dockerfile
fi

echo ""
echo "✅ Déploiement terminé !"
echo ""
echo "Service URL:"
gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --format='value(status.url)'
