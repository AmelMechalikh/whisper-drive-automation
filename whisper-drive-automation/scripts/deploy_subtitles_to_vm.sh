#!/bin/bash
#
# Script pour déployer le worker subtitles sur la VM
#
set -e

PROJECT_ID="artificial-intelligence-cmk"
ZONE="europe-west1-b"
VM_NAME="highlights-worker-vm"
REMOTE_DIR="/opt/subtitles-worker"

echo "📺 Déploiement du worker Subtitles sur la VM"
echo "==========================================="
echo ""

# Vérifier que la VM existe
if ! gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
    echo "❌ La VM $VM_NAME n'existe pas"
    echo "Lancez d'abord: ./scripts/setup_highlights_vm.sh"
    exit 1
fi

# Vérifier que la VM est démarrée
VM_STATUS=$(gcloud compute instances describe "$VM_NAME" --zone="$ZONE" --format='get(status)')
if [ "$VM_STATUS" != "RUNNING" ]; then
    echo "⚠️  La VM est $VM_STATUS. Démarrage..."
    gcloud compute instances start "$VM_NAME" --zone="$ZONE"
    echo "⏳ Attente du démarrage (30s)..."
    sleep 30
fi

echo "📤 Copie des fichiers..."

# Créer un archive temporaire avec les fichiers nécessaires
TMP_DIR=$(mktemp -d)
TMP_ARCHIVE="$TMP_DIR/subtitles-worker.tar.gz"

# Préparer les fichiers
mkdir -p "$TMP_DIR/subtitles-worker"
cp -r src "$TMP_DIR/subtitles-worker/"
cp -r config "$TMP_DIR/subtitles-worker/"
cp scripts/subtitles_vm_worker.py "$TMP_DIR/subtitles-worker/"
cp requirements.txt "$TMP_DIR/subtitles-worker/" 2>/dev/null || touch "$TMP_DIR/subtitles-worker/requirements.txt"

# Créer l'archive
cd "$TMP_DIR"
tar -czf subtitles-worker.tar.gz subtitles-worker/

# Copier l'archive sur la VM
gcloud compute scp subtitles-worker.tar.gz "$VM_NAME:~/" --zone="$ZONE"

# Nettoyer
cd -
rm -rf "$TMP_DIR"

echo "📦 Extraction et installation sur la VM..."

# Déployer et démarrer le worker sur la VM
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command='
set -e

# Extraire
cd ~
tar -xzf subtitles-worker.tar.gz
sudo rm -rf /opt/subtitles-worker
sudo mv subtitles-worker /opt/subtitles-worker
rm subtitles-worker.tar.gz

# Les dépendances Python sont déjà installées (partagées avec highlights-worker)
# Mais on va installer whisperx et faster-whisper qui sont nécessaires
cd /opt/subtitles-worker
python3 -m pip install --upgrade pip
python3 -m pip install whisperx faster-whisper || echo "Certaines dépendances ont échoué"

# Créer le service systemd
sudo tee /etc/systemd/system/subtitles-worker.service > /dev/null << EOF
[Unit]
Description=Subtitles Worker Service
After=network.target

[Service]
Type=simple
User=amel
WorkingDirectory=/opt/subtitles-worker
Environment="PATH=/home/amel/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/opt/subtitles-worker/src"
ExecStart=/usr/bin/python3 /opt/subtitles-worker/subtitles_vm_worker.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recharger systemd et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable subtitles-worker
sudo systemctl restart subtitles-worker

echo "✅ Service démarré"
'

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "📊 Commandes utiles:"
echo "  # Voir le status du service"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo systemctl status subtitles-worker'"
echo ""
echo "  # Voir les logs en temps réel"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo journalctl -u subtitles-worker -f'"
echo ""
echo "  # Redémarrer le service"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo systemctl restart subtitles-worker'"
echo ""
echo "  # Voir tous les services"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo systemctl status highlights-worker subtitles-worker'"
echo ""
