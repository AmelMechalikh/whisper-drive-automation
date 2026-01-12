#!/bin/bash
#
# Script pour déployer l'orchestrateur highlights sur la VM
#
set -e

PROJECT_ID="artificial-intelligence-cmk"
ZONE="europe-west1-b"
VM_NAME="highlights-worker-vm"
REMOTE_DIR="/opt/highlights-worker"

echo "📦 Déploiement de l'ORCHESTRATEUR sur la VM"
echo "==========================================="
echo ""

# Vérifier que la VM existe
if ! gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
    echo "❌ La VM $VM_NAME n'existe pas"
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

# Créer un archive temporaire
TMP_DIR=$(mktemp -d)
TMP_ARCHIVE="$TMP_DIR/highlights-orchestrator.tar.gz"

# Préparer les fichiers
mkdir -p "$TMP_DIR/highlights-worker"
cp -r src "$TMP_DIR/highlights-worker/"
cp -r config "$TMP_DIR/highlights-worker/"
cp scripts/highlight_orchestrator_cloud.py "$TMP_DIR/highlights-worker/"
cp requirements.txt "$TMP_DIR/highlights-worker/" 2>/dev/null || touch "$TMP_DIR/highlights-worker/requirements.txt"

# Créer l'archive
cd "$TMP_DIR"
tar -czf highlights-orchestrator.tar.gz highlights-worker/

# Copier sur la VM
gcloud compute scp highlights-orchestrator.tar.gz "$VM_NAME:~/" --zone="$ZONE"

# Nettoyer
cd -
rm -rf "$TMP_DIR"

echo "📦 Extraction et installation sur la VM..."

# Déployer et démarrer l'orchestrateur
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command='
set -e

# Extraire
cd ~
tar -xzf highlights-orchestrator.tar.gz
sudo rm -rf /opt/highlights-worker
sudo mv highlights-worker /opt/highlights-worker
rm highlights-orchestrator.tar.gz

# Installer les dépendances
cd /opt/highlights-worker
python3 -m pip install --upgrade pip --user
python3 -m pip install -r requirements.txt --user || echo "Certaines dépendances ont échoué"

# Créer le service systemd pour ORCHESTRATEUR
sudo tee /etc/systemd/system/highlights-orchestrator.service > /dev/null << EOF
[Unit]
Description=Highlights Orchestrator Service
After=network.target

[Service]
Type=simple
User=amel
WorkingDirectory=/opt/highlights-worker
Environment="PATH=/home/amel/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/opt/highlights-worker/src"
ExecStart=/usr/bin/python3 /opt/highlights-worker/highlight_orchestrator_cloud.py --loop
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Arrêter l ancien worker s il tourne
sudo systemctl stop highlights-worker 2>/dev/null || true
sudo systemctl disable highlights-worker 2>/dev/null || true

# Recharger systemd et démarrer orchestrateur
sudo systemctl daemon-reload
sudo systemctl enable highlights-orchestrator
sudo systemctl restart highlights-orchestrator

echo "✅ Orchestrateur démarré"
'

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "📊 Commandes utiles:"
echo "  # Voir le status"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo systemctl status highlights-orchestrator'"
echo ""
echo "  # Voir les logs en temps réel"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo journalctl -u highlights-orchestrator -f'"
echo ""
echo "  # Redémarrer"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo systemctl restart highlights-orchestrator'"
echo ""
