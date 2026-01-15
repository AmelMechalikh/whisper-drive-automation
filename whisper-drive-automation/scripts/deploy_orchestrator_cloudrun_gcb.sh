#!/bin/bash
#
# Déploiement orchestrateur sur Cloud Run via Cloud Build (plus rapide et fiable)
#
set -e

PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
SERVICE_NAME="highlights-orchestrator"

echo "📦 Déploiement de l'orchestrateur via Cloud Build"
echo "=================================================="
echo ""

cd "$(dirname "$0")/.."

echo "🔨 Build de l'image via Cloud Build..."
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
gcloud builds submit \
    --config=cloudbuild.orchestrator.yaml \
    .

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

# Récupérer l'URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format='value(status.url)')

echo ""
echo "📊 Service déployé:"
echo "  URL: ${SERVICE_URL}"
echo ""
echo "🧪 Tester:"
echo "  curl -X POST ${SERVICE_URL}/process"
