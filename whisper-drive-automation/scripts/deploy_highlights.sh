#!/bin/bash
#
# Script de déploiement du système Highlights avec VM on-demand
#
# Ce script déploie :
# 1. Cloud Run orchestrator (API de déclenchement)
# 2. VM Compute Engine avec auto-shutdown
# 3. Cloud Scheduler pour trigger périodique
#

set -e

# Configuration
PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
ZONE="europe-west1-b"

# Cloud Run
CLOUD_RUN_NAME="highlights-orchestrator"
CLOUD_RUN_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${CLOUD_RUN_NAME}"

# VM Configuration
VM_NAME="highlights-worker"
VM_MACHINE_TYPE="e2-standard-2"  # 2 vCPU, 8GB RAM (pour ffmpeg)
VM_DISK_SIZE="30GB"
VM_IMAGE_FAMILY="debian-11"
VM_IMAGE_PROJECT="debian-cloud"

# Cloud Scheduler
SCHEDULER_JOB_NAME="trigger-highlights"
SCHEDULER_SCHEDULE="*/5 * * * *"  # Toutes les 5 minutes
SCHEDULER_TIMEZONE="Europe/Paris"

echo "========================================="
echo "🚀 Déploiement Système Highlights"
echo "========================================="
echo "Projet: $PROJECT_ID"
echo "Région: $REGION"
echo "Zone: $ZONE"
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
    compute.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudbuild.googleapis.com \
    drive.googleapis.com

echo "✅ APIs activées"

echo ""
echo "========================================="
echo "☁️  ÉTAPE 2: Déploiement Cloud Run"
echo "========================================="

# Copier les fichiers nécessaires pour Cloud Run
echo "📝 Préparation des fichiers..."

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

# Installer les dépendances système
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements
COPY requirements.txt .

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir flask gunicorn google-cloud-compute

# Copier le code
COPY src/ /app/src/
COPY config/ /app/config/
COPY highlight_orchestrator_cloud.py /app/

# Variable d'environnement pour le port
ENV PORT=8080

# Lancer avec gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 highlight_orchestrator_cloud:app
EOF

echo "✅ Dockerfile créé"

# Mettre à jour highlight_config.json avec les IDs de projet et VM
python3 << EOF
import json
from pathlib import Path

config_path = Path("$BUILD_DIR/config/highlight_config.json")
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
    
    # Ajouter la configuration GCP
    config['gcp'] = {
        'project_id': '$PROJECT_ID',
        'zone': '$ZONE',
        'vm_name': '$VM_NAME'
    }
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("✅ Configuration GCP ajoutée à highlight_config.json")
EOF

# Déployer sur Cloud Run
echo "🚀 Déploiement Cloud Run..."
gcloud run deploy "$CLOUD_RUN_NAME" \
    --source "$BUILD_DIR" \
    --region="$REGION" \
    --platform=managed \
    --allow-unauthenticated \
    --memory=1Gi \
    --timeout=60s \
    --max-instances=1 \
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
echo "🖥️  ÉTAPE 3: Création de la VM"
echo "========================================="

# Vérifier si la VM existe déjà
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
    echo "⚠️  VM $VM_NAME existe déjà"
    read -p "Voulez-vous la recréer ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Suppression de la VM existante..."
        gcloud compute instances delete "$VM_NAME" --zone="$ZONE" --quiet
    else
        echo "⏭️  Conservation de la VM existante"
        VM_EXISTS=true
    fi
fi

if [ -z "$VM_EXISTS" ]; then
    echo "🔨 Création de la VM..."
    
    # Créer la VM avec le script de startup
    gcloud compute instances create "$VM_NAME" \
        --zone="$ZONE" \
        --machine-type="$VM_MACHINE_TYPE" \
        --image-family="$VM_IMAGE_FAMILY" \
        --image-project="$VM_IMAGE_PROJECT" \
        --boot-disk-size="$VM_DISK_SIZE" \
        --boot-disk-type=pd-standard \
        --scopes=cloud-platform \
        --metadata-from-file=startup-script=scripts/vm_startup_highlights.sh \
        --tags=highlights-worker
    
    echo "✅ VM créée"
    
    # Arrêter la VM immédiatement (elle sera lancée par le Cloud Run)
    echo "🛑 Arrêt de la VM..."
    gcloud compute instances stop "$VM_NAME" --zone="$ZONE"
    echo "✅ VM arrêtée"
fi

# Copier les fichiers sur la VM
echo "📤 Copie des fichiers sur la VM..."
gcloud compute scp --recurse config src scripts requirements.txt \
    "amel@${VM_NAME}:~/whisper-drive-automation/" \
    --zone="$ZONE" || echo "⚠️ Erreur de copie - la VM doit être démarrée"

echo ""
echo "========================================="
echo "⏰ ÉTAPE 4: Configuration Cloud Scheduler"
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
    --attempt-deadline=60s

echo "✅ Cloud Scheduler configuré"
echo "   Schedule: $SCHEDULER_SCHEDULE (toutes les 5 minutes)"

echo ""
echo "========================================="
echo "✅ DÉPLOIEMENT TERMINÉ"
echo "========================================="
echo ""
echo "📋 Résumé:"
echo "   • Cloud Run: $CLOUD_RUN_URL"
echo "   • VM: $VM_NAME (arrêtée)"
echo "   • Scheduler: Trigger toutes les 5 minutes"
echo ""
echo "🧪 Pour tester manuellement:"
echo "   curl -X POST $CLOUD_RUN_URL/trigger"
echo ""
echo "📊 Pour voir le statut:"
echo "   curl $CLOUD_RUN_URL/status"
echo ""
echo "🔍 Pour voir les logs Cloud Run:"
echo "   gcloud run services logs read $CLOUD_RUN_NAME --region=$REGION"
echo ""
echo "🔍 Pour voir les logs VM:"
echo "   gcloud compute ssh $VM_NAME --zone=$ZONE --command='tail -f ~/whisper-drive-automation/logs/highlights_*.log'"
echo ""
