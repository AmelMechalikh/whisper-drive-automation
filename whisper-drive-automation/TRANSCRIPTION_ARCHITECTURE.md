# Architecture de Transcription - Guide Rapide

> **📅 À jour:** 2026-02-06
> **🎯 Architecture:** RunPod Direct depuis Cloud Run

---

## 🚀 Comment ça marche maintenant

### Flow simplifié

```
Nouveau fichier audio dans Drive
         ↓
Cloud Scheduler (trigger toutes les 5 min)
         ↓
Cloud Run: whisper-automation
         ├─→ Détecte le nouveau fichier
         ├─→ Upload vers GCS (temporaire)
         ├─→ Appelle RunPod API
         ├─→ Attend résultats (~30s)
         └─→ Upload transcription vers Drive
                  ↓
         ✅ TERMINÉ
```

**Temps total:** ~1-2 minutes pour un fichier de 5 minutes d'audio

---

## 📁 Services impliqués

| Service | Rôle | Fichier |
|---------|------|---------|
| **Cloud Scheduler** | Trigger toutes les 5 min | GCP Console |
| **Cloud Run: whisper-automation** | Détecte + transcrit | `scripts/cloud_run_server.py` |
| **RunPod Serverless** | Transcription GPU | API externe |
| **GCS Bucket** | Stockage temp audio | `whisper-temp-audio` |
| **Google Drive** | Stockage final | Dossier `transcriptions/` |

---

## 🔧 Configuration

### Fichier: `config/highlight_config.json`

```json
{
  "transcription_backend": {
    "provider": "gpu_runpod",
    "gpu_runpod": {
      "device": "cuda",
      "model": "large-v3-turbo",
      "api_endpoint": "https://api.runpod.ai/v2/52nwp917j565t3",
      "api_key_env": "RUNPOD_API_KEY",
      "timeout_seconds": 600,
      "max_retries": 3
    }
  }
}
```

### Variables d'environnement (Cloud Run)

```bash
RUNPOD_API_KEY=<clé API RunPod>
```

---

## 🔍 Où chercher les logs

### Logs Cloud Run (détection + orchestration)

```bash
gcloud logging read "resource.labels.service_name=whisper-automation" \
  --limit 100 --format "value(timestamp,textPayload)" --freshness=2h
```

**Ce que vous devriez voir:**
- `🎯 Traitement: <nom_fichier>`
- `🔍 Recherche transcription`
- `❌ Aucune transcription trouvée` (si nouveau)
- `🚀 transcription directe avec RunPod`
- `✅ Transcription terminée`

### Logs RunPod (transcription GPU)

Les logs RunPod ne sont PAS dans GCP. Pour déboguer RunPod:
1. Aller sur https://runpod.io/console
2. Regarder les logs de l'endpoint
3. Vérifier le status du job via API

---

## ❌ Ce qui N'EXISTE PLUS

### Ancienne architecture (VM-based)

```
❌ VM Worker CPU pour transcription → SUPPRIMÉE
❌ Queue de jobs JSON → SUPPRIMÉE
❌ Système de polling VM → SUPPRIMÉ
❌ Whisper CPU local → SUPPRIMÉ
```

**Ces composants sont obsolètes depuis janvier 2026.**

Si vous voyez du code mentionnant:
- `subtitles_vm_worker.py` pour transcription → obsolète (utilisé seulement pour sous-titres maintenant)
- Queue `queue_subtitles/` → obsolète pour transcription
- Feature flag `subtitles_vm_enabled` → obsolète pour transcription

---

## 🐛 Debugging

### Problème: "Fichier ajouté mais pas transcrit"

1. **Vérifier qu'il est dans le bon dossier Drive**
   ```
   Dossier: source_files (ID: 1A29pkQvrBodU_HxNS8deYt6T27AlmbSe)
   ```

2. **Vérifier qu'il n'est pas déjà transcrit**
   ```bash
   # Regarder les logs pour "Fichier déjà transcrit"
   gcloud logging read "resource.labels.service_name=whisper-automation" \
     --limit 50 --freshness=30m | grep "skip"
   ```

3. **Vérifier que RunPod est appelé**
   ```bash
   # Chercher logs RunPod
   gcloud logging read "resource.labels.service_name=whisper-automation" \
     --limit 100 --freshness=1h | grep -i "runpod"
   ```

4. **Vérifier les erreurs**
   ```bash
   gcloud logging read "resource.labels.service_name=whisper-automation AND severity>=ERROR" \
     --limit 50 --freshness=1h
   ```

### Problème: "RunPod timeout ou erreur"

1. **Vérifier la clé API RunPod**
   ```bash
   gcloud run services describe whisper-automation \
     --region europe-west1 \
     --format "value(spec.template.spec.containers[0].env)"
   ```

2. **Tester l'endpoint RunPod manuellement**
   ```python
   from src.runpod_client import RunPodClient

   client = RunPodClient(
       api_key="VOTRE_CLE",
       endpoint="https://api.runpod.ai/v2/52nwp917j565t3"
   )
   # Test avec petit fichier
   ```

3. **Vérifier le bucket GCS**
   ```bash
   gsutil ls gs://artificial-intelligence-cmk-whisper-temp-audio/
   ```

---

## 💰 Coûts

| Composant | Coût mensuel (10h audio) |
|-----------|--------------------------|
| Cloud Run whisper-automation | Gratuit (free tier) |
| RunPod RTX 4090 | ~$2.60 (10h × 0.26$/hr) |
| GCS Storage temp | ~$0.10 |
| **Total** | **~$2.70/mois** |

**20× plus rapide que CPU, 5× moins cher qu'une VM permanente**

---

## 📚 Autres docs

- **Architecture complète:** `ARCHITECTURE.md`
- **Détails implémentation RunPod:** `RUNPOD_IMPLEMENTATION_SUMMARY.md`
- **Guide de déploiement:** `RUNPOD_DEPLOYMENT_GUIDE.md`
- **Configuration référence:** `CONFIG_REFERENCE.md`
