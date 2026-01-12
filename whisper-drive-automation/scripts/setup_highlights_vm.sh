#!/bin/bash
#
# Script pour créer et configurer la VM pour le traitement des highlights
#
set -e

PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
ZONE="europe-west1-b"
VM_NAME="highlights-worker-vm"
MACHINE_TYPE="n2-standard-4"  # 4 vCPU, 16 GB RAM
DISK_SIZE="200GB"  # Pour les grosses vidéos

echo "🚀 Setup VM Highlights Worker"
echo "================================"
echo "Project: $PROJECT_ID"
echo "Zone: $ZONE"
echo "VM: $VM_NAME"
echo "Machine: $MACHINE_TYPE"
echo "Disk: $DISK_SIZE"
echo ""

# Vérifier si la VM existe déjà
if gcloud compute instances describe "$VM_NAME" --zone="$ZONE" &>/dev/null; then
    echo "⚠️  La VM $VM_NAME existe déjà"
    read -p "Voulez-vous la recréer? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Annulé"
        exit 1
    fi
    echo "🗑️  Suppression de la VM existante..."
    gcloud compute instances delete "$VM_NAME" --zone="$ZONE" --quiet
fi

# Créer la VM
echo "🏗️  Création de la VM..."
gcloud compute instances create "$VM_NAME" \
    --project="$PROJECT_ID" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size="$DISK_SIZE" \
    --boot-disk-type=pd-standard \
    --scopes=https://www.googleapis.com/auth/cloud-platform \
    --metadata=startup-script='#!/bin/bash
set -e

# Installation des dépendances
apt-get update
apt-get install -y python3-pip python3-venv git ffmpeg

# Créer un répertoire de travail
mkdir -p /opt/highlights-worker
cd /opt/highlights-worker

# Cloner le repo (ou télécharger les fichiers nécessaires)
# Pour linstant on va uploader les fichiers manuellement
echo "VM prête pour le déploiement du code"
'

echo "✅ VM créée avec succès"
echo ""
echo "📋 Prochaines étapes:"
echo "1. Attendre que la VM démarre (~2 minutes)"
echo "2. Copier le code:"
echo "   ./scripts/deploy_highlights_to_vm.sh"
echo "3. La VM téléchargera et traitera les jobs automatiquement"
echo ""
echo "🔍 Pour voir les logs:"
echo "   gcloud compute ssh $VM_NAME --zone=$ZONE --command='tail -f /tmp/highlights_vm_worker.log'"
echo ""
echo "🛑 Pour arrêter la VM:"
echo "   gcloud compute instances stop $VM_NAME --zone=$ZONE"
echo ""
echo "🔥 Pour supprimer la VM:"
echo "   gcloud compute instances delete $VM_NAME --zone=$ZONE"
