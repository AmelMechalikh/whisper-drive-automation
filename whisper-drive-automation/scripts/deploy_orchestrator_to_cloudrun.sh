#!/bin/bash
#
# Script pour déployer l'orchestrateur highlights sur Cloud Run
#
set -e

PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
SERVICE_NAME="highlights-orchestrator"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "📦 Déploiement de l'orchestrateur sur Cloud Run"
echo "================================================"
echo ""

cd "$(dirname "$0")/.."

# Vérifier que gcloud est configuré
if ! gcloud config get-value project &>/dev/null; then
    echo "❌ gcloud n'est pas configuré"
    echo "Lancez: gcloud auth login && gcloud config set project ${PROJECT_ID}"
    exit 1
fi

echo "🔨 Build de l'image Docker (plateforme linux/amd64)..."
docker build --platform linux/amd64 -f deployments/highlights/Dockerfile -t "${IMAGE_NAME}:latest" .

echo ""
echo "📤 Push de l'image vers Google Container Registry..."
docker push "${IMAGE_NAME}:latest"

echo ""
echo "🚀 Déploiement sur Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_NAME}:latest" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=3600 \
    --max-instances=1 \
    --min-instances=0 \
    --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
    --service-account="id-whisper-automation@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo "✅ Déploiement terminé!"
echo ""

# Récupérer l'URL du service
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format='value(status.url)')

echo "📊 Informations du service:"
echo "  URL: ${SERVICE_URL}"
echo ""
echo "🧪 Tester l'endpoint:"
echo "  curl -X POST ${SERVICE_URL}/process"
echo ""
echo "📋 Voir les logs:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region=${REGION}"
