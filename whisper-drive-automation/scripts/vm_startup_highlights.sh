#!/bin/bash
#
# Script de startup pour la VM highlights
# Ce script s'exécute au démarrage de la VM et lance le traitement complet
#

set -e

echo "========================================="
echo "🚀 Démarrage VM Highlights"
echo "========================================="

# Variables
WORK_DIR="/home/amel/whisper-drive-automation"
LOG_DIR="$WORK_DIR/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/highlights_$TIMESTAMP.log"

# Créer le dossier de logs
mkdir -p "$LOG_DIR"

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Fonction pour s'auto-éteindre
shutdown_vm() {
    log "🛑 Arrêt de la VM..."
    sudo shutdown -h now
}

# Trap pour gérer les erreurs
trap 'log "❌ Erreur détectée - arrêt de la VM"; shutdown_vm' ERR

log "📂 Répertoire de travail: $WORK_DIR"
log "📝 Fichier de log: $LOG_FILE"

# Se déplacer dans le répertoire de travail
cd "$WORK_DIR"

# Activer l'environnement virtuel si existant
if [ -d "venv" ]; then
    log "🐍 Activation de l'environnement virtuel"
    source venv/bin/activate
fi

# Étape 1 : Traiter les fichiers avec commentaires → Générer Excel
log "========================================="
log "📋 ÉTAPE 1: Extraction des highlights"
log "========================================="

python3 scripts/highlight_worker.py 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    log "❌ Erreur dans l'extraction des highlights"
    shutdown_vm
    exit 1
fi

log "✅ Étape 1 terminée"

# Petite pause entre les deux étapes
sleep 5

# Étape 2 : Traiter les Excel → Découper les vidéos
log "========================================="
log "🎬 ÉTAPE 2: Découpage des vidéos"
log "========================================="

python3 scripts/process_video_segments.py 2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    log "❌ Erreur dans le découpage vidéo"
    shutdown_vm
    exit 1
fi

log "✅ Étape 2 terminée"

# Nettoyage des fichiers temporaires
log "========================================="
log "🧹 Nettoyage"
log "========================================="

if [ -d "temp_highlights" ]; then
    log "🗑️  Suppression temp_highlights/"
    rm -rf temp_highlights
fi

if [ -d "temp_video_segments" ]; then
    log "🗑️  Suppression temp_video_segments/"
    rm -rf temp_video_segments
fi

log "✅ Nettoyage terminé"

# Archiver le log sur Drive (optionnel)
log "📤 Upload du log sur Drive..."
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('$WORK_DIR') / 'src'))
from drive_manager import DriveManager
import logging

logger = logging.getLogger()
dm = DriveManager('$WORK_DIR/config/credentials.json', logger)

# Chercher le dossier Logs ou créer
folders = dm.list_files_in_folder('root')
log_folder = next((f for f in folders if f['name'] == 'Highlights Logs' and f.get('mimeType') == 'application/vnd.google-apps.folder'), None)

if not log_folder:
    # Créer le dossier
    folder_metadata = {'name': 'Highlights Logs', 'mimeType': 'application/vnd.google-apps.folder'}
    log_folder = dm.service.files().create(body=folder_metadata, fields='id').execute()
    folder_id = log_folder['id']
else:
    folder_id = log_folder['id']

# Upload le log
dm.upload_file('$LOG_FILE', folder_id, 'highlights_$TIMESTAMP.log')
print('✅ Log uploadé')
" 2>&1 | tee -a "$LOG_FILE"

# Tout est terminé avec succès
log "========================================="
log "✅ TRAITEMENT COMPLET TERMINÉ"
log "========================================="
log "🛑 La VM va s'éteindre dans 10 secondes..."

sleep 10

shutdown_vm
