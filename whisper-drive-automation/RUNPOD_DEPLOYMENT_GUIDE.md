# RunPod GPU Backend - Guide de Déploiement

Ce guide explique comment déployer le nouveau backend RunPod GPU pour la transcription Whisper Large-v3-turbo.

## Vue d'ensemble de l'architecture

```
Cloud Run Orchestrator
    ↓
    ├─→ [ACTIF] Cloud Run RunPod Worker → RunPod Serverless (Whisper Large-v3-turbo)
    │                                              ↓
    │                                        Google Drive (SRT)
    │
    └─→ [DÉSACTIVÉ] VM Subtitles Worker (CPU faster-whisper)
```

## Prérequis

1. Compte RunPod avec crédit
2. Compte Google Cloud avec projet actif
3. GCS bucket pour fichiers audio temporaires
4. Credentials Google Drive API configurés

## Étape 1: Configuration RunPod

### 1.1 Créer un endpoint Serverless

1. Aller sur https://www.runpod.io/console/serverless
2. Cliquer sur "Create Endpoint"
3. Choisir le template: **"Whisper Large-v3"**
4. Configuration recommandée:
   - **GPU Type**: RTX 4090 (optimal pour large-v3-turbo)
   - **Min Workers**: 0 (auto-scale depuis zéro)
   - **Max Workers**: 5 (ajuster selon budget)
   - **Idle Timeout**: 60 secondes
   - **Max Execution Time**: 600 secondes

5. Cliquer sur "Deploy"

### 1.2 Récupérer les credentials

Une fois l'endpoint créé:

1. Noter l'**Endpoint ID** (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
2. Aller dans "Settings" → "API Keys"
3. Créer une nouvelle API key si nécessaire
4. Noter l'**API Key** (format: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)

## Étape 2: Configuration du bucket GCS

### 2.1 Créer le bucket temporaire

```bash
# Créer le bucket pour les fichiers audio temporaires
gsutil mb -l europe-west1 gs://whisper-temp-audio

# Configurer la durée de vie (auto-delete après 1 jour)
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {"age": 1}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://whisper-temp-audio
rm lifecycle.json
```

### 2.2 Permissions IAM

Donner accès au service account:

```bash
# Remplacer par votre service account
SERVICE_ACCOUNT="id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com"

# Permissions sur le bucket
gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:roles/storage.objectAdmin \
  gs://whisper-temp-audio
```

## Étape 3: Configuration du projet

### 3.1 Mettre à jour highlight_config.json

Éditer `/config/highlight_config.json`:

```json
{
  "transcription_backend": {
    "provider": "gpu_runpod",
    "gpu_runpod": {
      "api_endpoint": "https://api.runpod.ai/v2/<VOTRE_ENDPOINT_ID>",
      "api_key_env": "RUNPOD_API_KEY",
      "timeout_seconds": 600,
      "max_retries": 3
    }
  },
  "gcs_temp_bucket": "whisper-temp-audio",
  "vm_workers": {
    "highlights_vm_enabled": true,
    "subtitles_vm_enabled": false,
    "auto_start_subtitles_vm": false
  }
}
```

**Remplacer** `<VOTRE_ENDPOINT_ID>` par l'ID de votre endpoint RunPod.

### 3.2 Uploader la configuration sur GCS

```bash
gsutil cp config/highlight_config.json \
  gs://artificial-intelligence-cmk/config/highlight_config.json
```

## Étape 4: Build et déploiement Cloud Run

### 4.1 Build de l'image Docker

```bash
cd whisper-drive-automation

# Build l'image
gcloud builds submit \
  --config cloudbuild.yaml \
  --substitutions=_IMAGE_NAME=runpod-transcription-worker \
  --tag gcr.io/artificial-intelligence-cmk/runpod-transcription-worker

# Ou build local puis push
docker build -f Dockerfile.runpod-worker \
  -t gcr.io/artificial-intelligence-cmk/runpod-transcription-worker .

docker push gcr.io/artificial-intelligence-cmk/runpod-transcription-worker
```

### 4.2 Déployer sur Cloud Run

```bash
# Déployer le service
gcloud run deploy runpod-transcription-worker \
  --image gcr.io/artificial-intelligence-cmk/runpod-transcription-worker \
  --region europe-west1 \
  --platform managed \
  --memory 2Gi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 5 \
  --min-instances 0 \
  --set-env-vars RUNPOD_API_KEY="<VOTRE_RUNPOD_API_KEY>" \
  --service-account id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com \
  --no-allow-unauthenticated
```

**Remplacer** `<VOTRE_RUNPOD_API_KEY>` par votre clé API RunPod.

### 4.3 Redéployer l'orchestrator (avec la config mise à jour)

```bash
# Rebuild l'orchestrator pour qu'il lise la nouvelle config
gcloud run deploy highlights-orchestrator \
  --source . \
  --region europe-west1 \
  --platform managed \
  --memory 2Gi \
  --timeout 540 \
  --service-account id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com \
  --no-allow-unauthenticated
```

## Étape 5: Vérification

### 5.1 Test local du client RunPod

Créer un script de test `test_runpod.py`:

```python
import os
from src.runpod_client import RunPodClient

# Configuration
os.environ['RUNPOD_API_KEY'] = 'VOTRE_CLE'
endpoint = 'https://api.runpod.ai/v2/<ENDPOINT_ID>'

# Tester avec un fichier audio public
client = RunPodClient(
    api_key=os.environ['RUNPOD_API_KEY'],
    endpoint=endpoint
)

# URL d'un audio de test (à remplacer)
audio_url = "https://storage.googleapis.com/whisper-temp-audio/test.wav"

result = client.transcribe_audio(
    audio_url=audio_url,
    model="large-v3-turbo",
    language="fr"
)

print(f"✅ Transcription réussie!")
print(f"Segments: {len(result.get('segments', []))}")
```

### 5.2 Vérifier les logs Cloud Run

```bash
# Logs du worker RunPod
gcloud run services logs read runpod-transcription-worker \
  --region europe-west1 \
  --limit 50

# Logs de l'orchestrator
gcloud run services logs read highlights-orchestrator \
  --region europe-west1 \
  --limit 50
```

### 5.3 Test end-to-end

1. Créer un document Google Docs de test
2. Ajouter la balise `🎬 READY 🎬`
3. Attendre le Cloud Scheduler (ou déclencher manuellement)
4. Vérifier les logs:
   - L'orchestrator doit créer un job dans `queue_subtitles/`
   - Le worker RunPod doit le traiter
   - La VM CPU ne doit **PAS** démarrer
5. Vérifier la sortie dans Drive: `segments_output/<dossier>/with_subtitles_<timestamp>/`

## Étape 6: Monitoring et coûts

### 6.1 Monitoring RunPod

- Dashboard: https://www.runpod.io/console/serverless
- Surveiller:
  - Temps d'exécution moyen
  - Cold starts (si > 30s, augmenter min_workers)
  - Erreurs (timeouts, OOM)

### 6.2 Estimation des coûts

**Configuration actuelle (avec RunPod GPU):**
- Cloud Run orchestrator: ~$2.50/mois
- Cloud Run worker RunPod: ~$3/mois
- RunPod RTX 4090:
  - $0.00044/seconde
  - Pour 10 min/mois: ~$0.26/mois
- **Total: ~$5.76/mois**

**Économies possibles:**
- Utiliser GPU moins cher (RTX 3090: $0.00034/s)
- Réduire max_workers si pas besoin d'autoscale

## Rollback vers CPU VM

Si problème avec RunPod:

1. Modifier `highlight_config.json`:

```json
{
  "transcription_backend": {
    "provider": "cpu_local"
  },
  "vm_workers": {
    "subtitles_vm_enabled": true,
    "auto_start_subtitles_vm": true
  }
}
```

2. Upload la config:

```bash
gsutil cp config/highlight_config.json \
  gs://artificial-intelligence-cmk/config/highlight_config.json
```

3. Redéployer l'orchestrator (pour relire la config)

4. Le système revient automatiquement sur VM CPU

## Troubleshooting

### Erreur: "RunPod API key not found"

Vérifier que la variable d'environnement est définie dans Cloud Run:

```bash
gcloud run services describe runpod-transcription-worker \
  --region europe-west1 \
  --format="value(spec.template.spec.containers[0].env)"
```

### Erreur: "Failed to upload audio to GCS"

Vérifier les permissions IAM du service account:

```bash
gsutil iam get gs://whisper-temp-audio
```

### Erreur: "RunPod job timed out"

Augmenter le timeout dans `highlight_config.json`:

```json
{
  "transcription_backend": {
    "gpu_runpod": {
      "timeout_seconds": 900
    }
  }
}
```

### Qualité des sous-titres dégradée

Vérifier que le modèle utilisé est bien `large-v3-turbo`:

```bash
# Voir dans les logs
gcloud run services logs read runpod-transcription-worker \
  --region europe-west1 | grep "model="
```

## Comparaison CPU vs GPU

| Métrique | CPU (faster-whisper base) | GPU (Whisper large-v3-turbo) |
|----------|---------------------------|------------------------------|
| Qualité | Moyenne | Excellente |
| Vitesse | ~10 min pour 5 min audio | ~30s pour 5 min audio |
| Coût | ~$0.20/mois | ~$5.76/mois |
| Cold start | N/A (VM always on) | 5-10s |
| Scalabilité | 1 VM fixe | Auto-scale 0-5 workers |

## Support

En cas de problème:

1. Consulter les logs Cloud Run
2. Vérifier le dashboard RunPod
3. Tester avec le script de test local
4. Si bloqué: rollback vers CPU VM

## Ressources

- [RunPod Documentation](https://docs.runpod.io/serverless/overview)
- [Whisper Large-v3-turbo](https://github.com/openai/whisper)
- [Google Cloud Run](https://cloud.google.com/run/docs)
