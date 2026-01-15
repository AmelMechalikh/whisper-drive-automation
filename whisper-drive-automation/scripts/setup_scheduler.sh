#!/bin/bash
#
# Script pour configurer Cloud Scheduler (trigger périodique)
# Peut être lancé séparément si le déploiement principal a échoué
#

set -e

PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
SCHEDULER_JOB_NAME="highlights-orchestrator-trigger"
SCHEDULER_SCHEDULE="*/5 * * * *"  # Toutes les 5 minutes
SCHEDULER_TIMEZONE="Europe/Paris"
CLOUD_RUN_NAME="highlights-orchestrator"

echo "🔧 Configuration Cloud Scheduler..."

# Récupérer l'URL du Cloud Run
CLOUD_RUN_URL=$(gcloud run services describe "$CLOUD_RUN_NAME" \
    --region="$REGION" \
    --format='value(status.url)')

if [ -z "$CLOUD_RUN_URL" ]; then
    echo "❌ Cloud Run $CLOUD_RUN_NAME non trouvé"
    exit 1
fi

echo "📍 URL Cloud Run: $CLOUD_RUN_URL"

# Supprimer le job existant si présent
if gcloud scheduler jobs describe "$SCHEDULER_JOB_NAME" --location="$REGION" &>/dev/null; then
    echo "🗑️  Suppression du job existant..."
    gcloud scheduler jobs delete "$SCHEDULER_JOB_NAME" --location="$REGION" --quiet
fi

# Créer le job
echo "⏰ Création du job..."
gcloud scheduler jobs create http "$SCHEDULER_JOB_NAME" \
    --location="$REGION" \
    --schedule="$SCHEDULER_SCHEDULE" \
    --uri="${CLOUD_RUN_URL}/trigger" \
    --http-method=POST \
    --time-zone="$SCHEDULER_TIMEZONE" \
    --attempt-deadline=60s \
    --description="Trigger highlights processing every 5 minutes"

echo "✅ Cloud Scheduler configuré"
echo "   Nom: $SCHEDULER_JOB_NAME"
echo "   Schedule: $SCHEDULER_SCHEDULE"
echo "   URL cible: ${CLOUD_RUN_URL}/trigger"
echo ""
echo "🧪 Pour tester immédiatement:"
echo "   gcloud scheduler jobs run $SCHEDULER_JOB_NAME --location=$REGION"
