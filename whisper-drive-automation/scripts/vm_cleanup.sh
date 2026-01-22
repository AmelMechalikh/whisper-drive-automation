#!/bin/bash
# Script de nettoyage intelligent pour la VM Whisper
# Nettoie les fichiers temporaires sans casser les processus en cours
# Usage: ./vm_cleanup.sh [--dry-run]

set -e

LOG_FILE="/var/log/vm_cleanup.log"
DRY_RUN=false

# Parse arguments
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
fi

log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $1" | tee -a "$LOG_FILE"
}

# Fonction pour vérifier si un fichier est utilisé
is_file_in_use() {
    local file="$1"
    # Utiliser lsof pour vérifier si le fichier est ouvert
    if sudo lsof "$file" >/dev/null 2>&1; then
        return 0  # En cours d'utilisation
    else
        return 1  # Libre
    fi
}

# Vérifier si le worker est actif
is_worker_running() {
    if pgrep -f "vm_worker.py" >/dev/null 2>&1; then
        return 0  # Worker actif
    else
        return 1  # Worker arrêté
    fi
}

# Fonction de nettoyage sécurisé
safe_delete() {
    local file="$1"
    local age_minutes="$2"
    local force_if_no_worker="${3:-false}"

    # Vérifier que le fichier existe
    if [[ ! -e "$file" ]]; then
        return
    fi

    # Vérifier que le fichier n'est pas utilisé
    if is_file_in_use "$file"; then
        log "   ⏭️  Ignoré (en cours d'utilisation): $(basename "$file")"
        return
    fi

    # Si le worker tourne, être plus prudent avec les délais
    if is_worker_running; then
        # Worker actif: respecter le délai de sécurité
        local file_age=$(find "$file" -mmin +$age_minutes 2>/dev/null)
        if [[ -z "$file_age" ]]; then
            return  # Fichier trop récent, on garde
        fi
    else
        # Worker arrêté: on peut nettoyer tous les fichiers non utilisés
        if [[ "$force_if_no_worker" == "true" ]]; then
            log "   🔄 Worker arrêté, nettoyage du fichier orphelin"
        else
            # Respecter quand même un délai minimum de 10 minutes
            local file_age=$(find "$file" -mmin +10 2>/dev/null)
            if [[ -z "$file_age" ]]; then
                return
            fi
        fi
    fi

    # Obtenir la taille
    local size=$(du -h "$file" 2>/dev/null | cut -f1)

    if [[ "$DRY_RUN" == true ]]; then
        log "   [DRY-RUN] Supprimerait: $(basename "$file") ($size)"
    else
        rm -f "$file" 2>/dev/null || sudo rm -f "$file" 2>/dev/null
        log "   ✅ Supprimé: $(basename "$file") ($size)"
    fi
}

# Début du nettoyage
if [[ "$DRY_RUN" == true ]]; then
    log "🧹 Démarrage du nettoyage (DRY-RUN MODE)"
else
    log "🧹 Démarrage du nettoyage automatique"
fi

# Vérifier l'état du worker
if is_worker_running; then
    log "ℹ️  Worker actif détecté - nettoyage prudent activé"
    AUDIO_DELAY=360  # 6 heures si worker actif (gros fichiers peuvent prendre du temps)
else
    log "ℹ️  Worker arrêté - nettoyage agressif des fichiers orphelins"
    AUDIO_DELAY=10   # 10 minutes si worker arrêté (fichiers orphelins)
fi

# 1. Nettoyer les fichiers audio/vidéo temporaires
log "1️⃣ Nettoyage des fichiers audio/vidéo (délai: ${AUDIO_DELAY}min)..."
file_count=0
for pattern in "*.mp4" "*.mp3" "*.wav" "*.m4a" "*.mov" "*.avi" "*.mkv" "*.flac" "*.aac"; do
    while IFS= read -r -d '' file; do
        safe_delete "$file" "$AUDIO_DELAY"
        ((file_count++))
    done < <(find /tmp -type f -name "$pattern" -print0 2>/dev/null)
done
log "   Fichiers audio/vidéo traités: $file_count"

# 2. Nettoyer les dossiers temporaires vides
log "2️⃣ Nettoyage des dossiers temporaires vides..."
if [[ "$DRY_RUN" == false ]]; then
    deleted=$(find /tmp -type d -name "tmp*" -empty -delete -print 2>/dev/null | wc -l)
    log "   ✅ Dossiers vides supprimés: $deleted"
fi

# 3. Nettoyer les vieux checkpoints (plus de 7 jours)
log "3️⃣ Nettoyage des checkpoints anciens (>7 jours)..."
checkpoint_count=0
if [[ -d /tmp/whisper_checkpoints ]]; then
    while IFS= read -r -d '' file; do
        safe_delete "$file" $((7*24*60))  # 7 jours en minutes
        ((checkpoint_count++))
    done < <(find /tmp/whisper_checkpoints -type f -name "*.json" -print0 2>/dev/null)
fi
log "   Checkpoints traités: $checkpoint_count"

# 4. Nettoyer les vieux logs (plus de 30 jours)
log "4️⃣ Nettoyage des vieux logs (>30 jours)..."
log_count=0
while IFS= read -r -d '' file; do
    safe_delete "$file" $((30*24*60))  # 30 jours
    ((log_count++))
done < <(find /tmp -type f -name "*.log" -print0 2>/dev/null)
log "   Logs traités: $log_count"

# 5. Nettoyer les fichiers JSON temporaires orphelins (plus de 60 minutes)
log "5️⃣ Nettoyage des fichiers JSON temporaires (>1h)..."
json_count=0
while IFS= read -r -d '' file; do
    safe_delete "$file" 60
    ((json_count++))
done < <(find /tmp -maxdepth 1 -type f -name "tmp*.json" -print0 2>/dev/null)
log "   JSON temporaires traités: $json_count"

# 6. Vérifier l'espace disque et alerter si nécessaire
log "6️⃣ Vérification de l'espace disque..."
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
DISK_AVAILABLE=$(df -h / | tail -1 | awk '{print $4}')

log "   Utilisation disque: ${DISK_USAGE}% (${DISK_AVAILABLE} disponible)"

if [[ "$DISK_USAGE" -gt 85 ]]; then
    log "   ⚠️  ALERTE: Disque à ${DISK_USAGE}% - nettoyage agressif recommandé"

    if [[ "$DRY_RUN" == false ]] && [[ "$DISK_USAGE" -gt 90 ]]; then
        log "7️⃣ Nettoyage d'urgence (disque >90%)..."

        # Nettoyer les fichiers temporaires de plus de 30 minutes
        log "   Suppression fichiers récents (>30 min)..."
        find /tmp -type f \( -name "*.mp4" -o -name "*.mp3" -o -name "*.wav" \) -mmin +30 -exec bash -c 'if ! sudo lsof "{}" >/dev/null 2>&1; then rm -f "{}"; fi' \; 2>/dev/null

        # Nettoyer le cache pip
        if [[ -d /home/amel/.cache/pip ]]; then
            cache_size=$(du -sh /home/amel/.cache/pip 2>/dev/null | cut -f1)
            log "   Nettoyage cache pip ($cache_size)..."
            rm -rf /home/amel/.cache/pip/
            log "   ✅ Cache pip supprimé"
        fi

        DISK_USAGE_AFTER=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
        log "   Utilisation après nettoyage d'urgence: ${DISK_USAGE_AFTER}%"
    fi
fi

# 8. Rotation du fichier de log
if [[ "$DRY_RUN" == false ]]; then
    # Garder seulement les 500 dernières lignes du log
    if [[ -f "$LOG_FILE" ]]; then
        tail -500 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
    fi
fi

log "✅ Nettoyage terminé"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
