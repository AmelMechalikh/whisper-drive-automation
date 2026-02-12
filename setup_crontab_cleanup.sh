#!/bin/bash
# 
# Script pour ajouter le nettoyage automatique au crontab local
#

SCRIPT_PATH="/Users/amel/Documents/Transcription-Project/cleanup_docker_images.sh"

echo "📅 Configuration du nettoyage automatique via crontab"
echo "====================================================="
echo ""
echo "Ce script va ajouter une tâche cron qui exécute le nettoyage"
echo "des images Docker chaque 1er dimanche du mois à 3h du matin."
echo ""

# Vérifier si le script existe
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Erreur: Script non trouvé à $SCRIPT_PATH"
    exit 1
fi

# Créer la ligne crontab
CRON_JOB="0 3 1-7 * 0 $SCRIPT_PATH >> /tmp/docker-cleanup.log 2>&1"

# Vérifier si la tâche existe déjà
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
    echo "⚠️  Une tâche cron existe déjà pour ce script"
    echo ""
    echo "Tâches actuelles:"
    crontab -l | grep "$SCRIPT_PATH"
    echo ""
    read -p "Voulez-vous la remplacer? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Annulé"
        exit 1
    fi
    # Supprimer l'ancienne tâche
    crontab -l | grep -v "$SCRIPT_PATH" | crontab -
fi

# Ajouter la nouvelle tâche
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Tâche cron ajoutée avec succès!"
echo ""
echo "📋 Configuration:"
echo "   - Script: $SCRIPT_PATH"
echo "   - Fréquence: 1er dimanche de chaque mois à 3h"
echo "   - Logs: /tmp/docker-cleanup.log"
echo ""
echo "Pour voir vos tâches cron:"
echo "   crontab -l"
echo ""
echo "Pour supprimer cette tâche:"
echo "   crontab -e  # puis supprimer la ligne"
echo ""
