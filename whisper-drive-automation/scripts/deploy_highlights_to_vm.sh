#!/bin/bash
#
# Script pour déployer le code highlights sur la VM
#
set -e

PROJECT_ID="artificial-intelligence-cmk"
ZONE="europe-west1-b"
VM_NAME="highlights-worker-vm"
REMOTE_DIR="/opt/highlights-worker"

echo "📦 Déploiement du code highlights sur la VM"
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
TMP_ARCHIVE="$TMP_DIR/highlights-worker.tar.gz"

# Préparer les fichiers
mkdir -p "$TMP_DIR/highlights-worker"
cp -r src "$TMP_DIR/highlights-worker/"
cp -r config "$TMP_DIR/highlights-worker/"
cp scripts/highlights_vm_worker.py "$TMP_DIR/highlights-worker/"
cp requirements.txt "$TMP_DIR/highlights-worker/" 2>/dev/null || touch "$TMP_DIR/highlights-worker/requirements.txt"

# Créer l'archive
cd "$TMP_DIR"
tar -czf highlights-worker.tar.gz highlights-worker/

# Copier l'archive sur la VM
gcloud compute scp highlights-worker.tar.gz "$VM_NAME:~/" --zone="$ZONE"

# Nettoyer
cd -
rm -rf "$TMP_DIR"

echo "📦 Extraction et installation sur la VM..."

# Déployer et démarrer le worker sur la VM
gcloud compute ssh "$VM_NAME" --zone="$ZONE" --command='
set -e

# Extraire
cd ~
tar -xzf highlights-worker.tar.gz
sudo rm -rf /opt/highlights-worker
sudo mv highlights-worker /opt/highlights-worker
rm highlights-worker.tar.gz

# Installer les dépendances Python
cd /opt/highlights-worker
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt || echo "Certaines dépendances ont échoué"

# Créer le service systemd
sudo tee /etc/systemd/system/highlights-worker.service > /dev/null << EOF
[Unit]
Description=Highlights Worker Service
After=network.target

[Service]
Type=simple
User=amel
WorkingDirectory=/opt/highlights-worker
Environment="PATH=/home/amel/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="PYTHONPATH=/opt/highlights-worker/src"
ExecStart=/usr/bin/python3 /opt/highlights-worker/highlights_vm_worker.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Recharger systemd et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable highlights-worker
sudo systemctl restart highlights-worker

echo "✅ Service démarré"
'

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "📊 Commandes utiles:"
echo "  # Voir le status du service"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo systemctl status highlights-worker'"
echo ""
echo "  # Voir les logs en temps réel"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo journalctl -u highlights-worker -f'"
echo ""
echo "  # Redémarrer le service"
echo "  gcloud compute ssh $VM_NAME --zone=$ZONE --command='sudo systemctl restart highlights-worker'"
echo ""
echo "  # Arrêter la VM (économiser des coûts)"
echo "  gcloud compute instances stop $VM_NAME --zone=$ZONE"
