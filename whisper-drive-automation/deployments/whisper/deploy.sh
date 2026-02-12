#!/bin/bash

set -e

echo "==========================================="
echo "🚀 Déploiement Whisper Automation"
echo "==========================================="

PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
SERVICE_NAME="whisper-automation"

echo "Projet: $PROJECT_ID"
echo "Région: $REGION"
echo "Service: $SERVICE_NAME"

# Aller à la racine du projet
cd "$(dirname "$0")/../.."

# Backup du Dockerfile s'il existe
if [ -f "Dockerfile" ]; then
    mv Dockerfile Dockerfile.backup
fi

# Copier le Dockerfile whisper comme Dockerfile principal
cp deployments/whisper/Dockerfile ./Dockerfile

# Build et déploiement
echo ""
echo "📦 Build et déploiement..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --platform=managed \
    --allow-unauthenticated \
    --service-account=id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com \
    --memory=4Gi \
    --timeout=3600 \
    --max-instances=10 \
    --min-instances=0

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
