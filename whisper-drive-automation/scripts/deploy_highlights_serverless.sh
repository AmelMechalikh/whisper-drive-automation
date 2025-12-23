#!/bin/bash
#
# Script de déploiement du système Highlights (100% Serverless)
#
# Ce script déploie :
# 1. Cloud Run processor (traitement direct sans VM)
# 2. Cloud Scheduler pour trigger périodique
#

set -e

# Configuration
PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"

# Cloud Run
CLOUD_RUN_NAME="highlights-processor"

# Cloud Scheduler
SCHEDULER_JOB_NAME="trigger-highlights"
SCHEDULER_SCHEDULE="*/5 * * * *"  # Toutes les 5 minutes
SCHEDULER_TIMEZONE="Europe/Paris"

echo "========================================="
echo "🚀 Déploiement Highlights (Serverless)"
echo "========================================="
echo "Projet: $PROJECT_ID"
echo "Région: $REGION"
echo ""

# Vérifier que gcloud est configuré
if ! gcloud config get-value project &>/dev/null; then
    echo "❌ gcloud n'est pas configuré"
    exit 1
fi

# Définir le projet
gcloud config set project "$PROJECT_ID"

echo "========================================="
echo "📦 ÉTAPE 1: Configuration GCP"
echo "========================================="

# Activer les APIs nécessaires
echo "🔧 Activation des APIs GCP..."
gcloud services enable \
    run.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudbuild.googleapis.com \
    drive.googleapis.com

echo "✅ APIs activées"

echo ""
echo "========================================="
echo "☁️  ÉTAPE 2: Déploiement Cloud Run"
echo "========================================="

# Créer un dossier temporaire pour le build
BUILD_DIR=$(mktemp -d)
echo "📁 Dossier de build: $BUILD_DIR"

# Copier les fichiers nécessaires
cp -r config "$BUILD_DIR/"
cp -r src "$BUILD_DIR/"
cp scripts/highlight_orchestrator_cloud.py "$BUILD_DIR/"
cp requirements.txt "$BUILD_DIR/"

# Créer le Dockerfile pour Cloud Run
cat > "$BUILD_DIR/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Installer ffmpeg (nécessaire pour le découpage vidéo)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir flask gunicorn

# Copier le code
COPY src/ /app/src/
COPY config/ /app/config/
COPY highlight_orchestrator_cloud.py /app/

# Variable d'environnement pour le port
ENV PORT=8080
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Lancer avec gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 4 --timeout 3600 highlight_orchestrator_cloud:app
EOF

echo "✅ Dockerfile créé"

# Déployer sur Cloud Run
echo "🚀 Déploiement Cloud Run..."
gcloud run deploy "$CLOUD_RUN_NAME" \
    --source "$BUILD_DIR" \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=3600 \
    --max-instances=10 \
    --min-instances=0

# Récupérer l'URL du Cloud Run
CLOUD_RUN_URL=$(gcloud run services describe "$CLOUD_RUN_NAME" \
    --region="$REGION" \
    --format='value(status.url)')

echo "✅ Cloud Run déployé"
echo "   URL: $CLOUD_RUN_URL"

# Nettoyer le dossier temporaire
rm -rf "$BUILD_DIR"

echo ""
echo "========================================="
echo "⏰ ÉTAPE 3: Configuration Cloud Scheduler"
echo "========================================="

# Vérifier si le job existe déjà
if gcloud scheduler jobs describe "$SCHEDULER_JOB_NAME" --location="$REGION" &>/dev/null; then
    echo "🗑️  Suppression du job existant..."
    gcloud scheduler jobs delete "$SCHEDULER_JOB_NAME" --location="$REGION" --quiet
fi

# Créer le job Cloud Scheduler
echo "⏰ Création du Cloud Scheduler..."
gcloud scheduler jobs create http "$SCHEDULER_JOB_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULER_SCHEDULE" \
    --uri="${CLOUD_RUN_URL}/trigger" \
    --http-method=POST \
    --time-zone="$SCHEDULER_TIMEZONE" \
    --attempt-deadline=1800s \
    --description="Trigger highlights processing every 5 minutes"

echo "✅ Cloud Scheduler configuré"
echo "   Schedule: $SCHEDULER_SCHEDULE (toutes les 5 minutes)"

echo ""
echo "========================================="
echo "✅ DÉPLOIEMENT TERMINÉ"
echo "========================================="
echo ""
echo "📋 Architecture Déployée:"
echo "   • Cloud Run: $CLOUD_RUN_URL"
echo "   • Scheduler: Trigger toutes les 5 minutes"
echo "   • Mode: 100% Serverless (pas de VM)"
echo ""
echo "💰 Coût estimé: ~0-2€/mois"
echo ""
echo "🧪 Pour tester manuellement:"
echo "   curl -X POST $CLOUD_RUN_URL/trigger"
echo ""
echo "📊 Pour voir le statut:"
echo "   curl $CLOUD_RUN_URL/status"
echo ""
echo "🔍 Pour voir les logs:"
echo "   gcloud run services logs read $CLOUD_RUN_NAME --region=$REGION --limit=50"
echo ""
echo "⏰ Pour déclencher le scheduler immédiatement:"
echo "   gcloud scheduler jobs run $SCHEDULER_JOB_NAME --location=$REGION"
echo ""
