#!/bin/bash
#
# Moniteur de progression de la VM
#

echo "🔍 Surveillance de la VM en cours..."
echo ""

while true; do
    # Récupérer les 5 dernières lignes des logs
    LOGS=$(gcloud compute ssh highlights-worker-vm --zone=europe-west1-b --command='sudo journalctl -u highlights-worker -n 5 --no-pager' 2>&1 | tail -5)

    # Afficher l'heure et les logs
    echo "[$(date +%H:%M:%S)]"
    echo "$LOGS"
    echo ""

    # Vérifier si le traitement est terminé
    if echo "$LOGS" | grep -q "✅.*segments vidéo uploadés"; then
        echo "🎉 Traitement terminé!"
        break
    fi

    # Vérifier si erreur
    if echo "$LOGS" | grep -q "❌"; then
        echo "⚠️  Erreur détectée, arrêt de la surveillance"
        break
    fi

    # Attendre 30 secondes avant la prochaine vérification
    sleep 30
done
