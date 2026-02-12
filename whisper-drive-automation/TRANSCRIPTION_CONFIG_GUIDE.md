# Guide de Configuration - Système de Transcription

> **🎯 Objectif:** Pouvoir basculer facilement entre VM CPU et RunPod GPU

---

## 🎛️ Configuration actuelle (highlight_config.json)

### Pour activer RunPod GPU (RECOMMANDÉ)

```json
{
  "transcription_backend": {
    "provider": "gpu_runpod"
  },
  "vm_workers": {
    "transcription_vm_enabled": false
  }
}
```

**Résultat:**
- ✅ Cloud Run `whisper-automation` utilise RunPod directement
- ❌ VM `whisper-cpu-worker` ne doit PAS tourner
- ⚡ Rapide (30s pour 5 min audio)
- 🎯 Excellente qualité (large-v3-turbo)

### Pour revenir à VM CPU (FALLBACK)

```json
{
  "transcription_backend": {
    "provider": "cpu_local"
  },
  "vm_workers": {
    "transcription_vm_enabled": true
  }
}
```

**Résultat:**
- ❌ Cloud Run `whisper-automation` n'utilise PAS RunPod
- ✅ VM `whisper-cpu-worker` traite les transcriptions
- 🐢 Lent (10 min pour 5 min audio)
- 📊 Qualité moyenne (base model)

---

## 🚀 Procédure de basculement

### Passer à RunPod GPU (configuration actuelle)

#### 1. Mettre à jour la config

La config est déjà à jour :
```json
{
  "transcription_backend": {"provider": "gpu_runpod"},
  "vm_workers": {"transcription_vm_enabled": false}
}
```

#### 2. Arrêter la VM CPU

```bash
# Arrêter la VM
gcloud compute instances stop whisper-cpu-worker --zone=europe-west1-b

# Vérifier qu'elle est arrêtée
gcloud compute instances list --filter="name=whisper-cpu-worker"
```

#### 3. Tester avec un nouveau fichier

```bash
# Déclencher Cloud Run manuellement
curl -X POST https://whisper-automation-pt4e4lc6uq-ew.a.run.app/process \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{}'

# Vérifier les logs pour voir RunPod en action
gcloud logging read "resource.labels.service_name=whisper-automation" \
  --limit 50 --freshness=10m | grep -i "runpod\|transcription"
```

#### 4. Désactiver le démarrage automatique de la VM (optionnel)

Pour éviter que la VM se rallume automatiquement :

```bash
# Option 1: Supprimer le startup script
gcloud compute instances remove-metadata whisper-cpu-worker \
  --zone=europe-west1-b \
  --keys=startup-script

# Option 2: Modifier pour ne rien faire
gcloud compute instances add-metadata whisper-cpu-worker \
  --zone=europe-west1-b \
  --metadata=startup-script='#!/bin/bash
echo "VM transcription disabled - using RunPod instead" > /var/log/vm-disabled.log'
```

---

### Revenir à VM CPU (rollback)

#### 1. Modifier la config

```bash
cd whisper-drive-automation

# Créer la nouvelle config
cat > config/highlight_config.json << 'EOF'
{
  "drive_folders": {
    "highlighted_files": "1-LyCTp_CZUvfd3cufIYEHBYVyWCFxxb9",
    "source_files": "1A29pkQvrBodU_HxNS8deYt6T27AlmbSe",
    "transcriptions": "1yHcy9um2_We459w9I0cITwHBGXKTlOJa",
    "excel_output": "1krgRVj3Wp18sNY7cL7PwR2vVUtaX2jCj",
    "segments_output": "1ly79uNIJBUqxQ5yjVOmtTlISemHTBxiP",
    "queue_highlights": "1Dc5kkTvBOSYXuB103vAwYHTpPAsW8G9Q",
    "queue_subtitles": "185oHzsbo_FdpXWvIHacfN2gtvTZg3IN7",
    "completed_jobs": "1KhcY5pdGUMdiEeJNC01UNjsLcyNmJ7RD",
    "failed_jobs": "1XbDgFtAKZCDOKm-wOo0tp9dDLMyKPbGA"
  },
  "processing": {
    "watch_interval_seconds": 300,
    "temp_dir": "./temp_highlights",
    "extraction_method": "inline_markers",
    "add_subtitles": true
  },
  "transcription_backend": {
    "provider": "cpu_local",
    "cpu_local": {
      "device": "cpu",
      "model": "base",
      "compute_type": "int8"
    }
  },
  "vm_workers": {
    "highlights_vm_enabled": true,
    "subtitles_vm_enabled": false,
    "auto_start_subtitles_vm": false,
    "transcription_vm_enabled": true
  }
}
EOF
```

#### 2. Démarrer la VM

```bash
gcloud compute instances start whisper-cpu-worker --zone=europe-west1-b
```

#### 3. Vérifier le service sur la VM

```bash
# SSH dans la VM
gcloud compute ssh whisper-cpu-worker --zone=europe-west1-b

# Vérifier le service
systemctl status whisper-worker

# Voir les logs
tail -f /var/log/whisper-worker.log
```

---

## 🔍 Vérification de l'état actuel

### Quel système est actif ?

```bash
# 1. Vérifier la config
cat config/highlight_config.json | grep -A2 '"provider"'
cat config/highlight_config.json | grep -A2 '"transcription_vm_enabled"'

# 2. Vérifier si la VM tourne
gcloud compute instances list --filter="name=whisper-cpu-worker"

# 3. Vérifier les logs Cloud Run
gcloud logging read "resource.labels.service_name=whisper-automation" \
  --limit 20 --freshness=30m | grep -E "runpod|RunPod|backend"
```

**Interprétation:**
- Si `provider: "gpu_runpod"` ET `transcription_vm_enabled: false` ET VM arrêtée → ✅ **RunPod actif**
- Si `provider: "cpu_local"` ET `transcription_vm_enabled: true` ET VM running → ✅ **VM CPU active**
- Si les deux tournent → ⚠️ **Conflit! VM va transcrire avant RunPod**

---

## ⚠️ Problèmes courants

### Problème: Les deux systèmes tournent en même temps

**Symptômes:**
- VM `whisper-cpu-worker` est RUNNING
- Config dit `provider: "gpu_runpod"`
- Tous les fichiers sont "déjà transcrits" quand Cloud Run tourne

**Solution:**
```bash
# Arrêter la VM immédiatement
gcloud compute instances stop whisper-cpu-worker --zone=europe-west1-b
```

### Problème: RunPod ne fonctionne pas

**Vérifications:**
1. Vérifier la clé API RunPod
   ```bash
   gcloud run services describe whisper-automation \
     --region europe-west1 \
     --format "value(spec.template.spec.containers[0].env)" | grep RUNPOD
   ```

2. Tester l'endpoint RunPod manuellement
   ```bash
   # Voir RUNPOD_DEPLOYMENT_GUIDE.md pour les tests
   ```

3. Vérifier les logs d'erreur
   ```bash
   gcloud logging read "resource.labels.service_name=whisper-automation AND severity>=ERROR" \
     --limit 50 --freshness=2h
   ```

**Solution de rollback rapide:**
```bash
# Revenir à VM CPU immédiatement
gcloud compute instances start whisper-cpu-worker --zone=europe-west1-b
```

---

## 📊 Comparaison des systèmes

| Critère | VM CPU | RunPod GPU |
|---------|--------|------------|
| **Vitesse** | 🐢 ~10 min pour 5 min | ⚡ ~30s pour 5 min |
| **Qualité** | 📊 Moyenne (base) | 🎯 Excellente (large-v3) |
| **Coût/heure audio** | $0.02 | $0.01 |
| **Maintenance** | 🔧 VM à gérer | 🌐 Serverless |
| **Démarrage** | ⏱️ 2-3 min (boot VM) | ⚡ Instantané |
| **Rollback** | ✅ Facile (juste démarrer VM) | ✅ Facile (juste config) |

---

## 📝 Checklist de migration

### Migration vers RunPod (à faire maintenant)

- [x] Config mise à jour (`provider: "gpu_runpod"`)
- [x] Flag `transcription_vm_enabled: false` ajouté
- [ ] VM `whisper-cpu-worker` arrêtée
- [ ] Test avec nouveau fichier
- [ ] Vérification logs RunPod
- [ ] Surveillance 24h
- [ ] Désactiver startup script VM (optionnel)

### Commandes rapides

```bash
# Arrêter VM (faire maintenant)
gcloud compute instances stop whisper-cpu-worker --zone=europe-west1-b

# Tester RunPod
curl -X POST https://whisper-automation-pt4e4lc6uq-ew.a.run.app/process \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{}'

# Surveiller logs
gcloud logging read "resource.labels.service_name=whisper-automation" \
  --limit 100 --freshness=10m | grep -E "🚀|RunPod|Transcription"
```
