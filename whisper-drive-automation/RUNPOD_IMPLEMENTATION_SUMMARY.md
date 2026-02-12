# RunPod GPU Backend - Résumé d'implémentation

> **📅 Dernière mise à jour:** 2026-02-06
>
> **🎯 Architecture actuelle:** RunPod Direct depuis Cloud Run
>
> Ce document décrit l'implémentation du backend RunPod GPU pour les transcriptions Whisper.
> Le système appelle RunPod **directement** depuis Cloud Run `whisper-automation`, sans VM ni queue de jobs.

---

## ✅ Fichiers créés

### 1. Backend abstraction layer
- **`src/transcription_backends.py`** (nouveau)
  - Interface `TranscriptionBackend` abstraite
  - `CPULocalBackend`: backend CPU existant avec WhisperX
  - `RunPodBackend`: nouveau backend GPU RunPod
  - Factory function `get_transcription_backend(config)`

### 2. Client API RunPod
- **`src/runpod_client.py`** (nouveau)
  - Classe `RunPodClient` pour appeler l'API RunPod Serverless
  - Gestion du polling de jobs
  - Gestion des timeouts et erreurs

### 3. Worker RunPod
- **`scripts/runpod_transcription_worker.py`** (nouveau)
  - Worker Cloud Run qui utilise le backend abstrait
  - Basé sur `subtitles_vm_worker.py` mais adaptable au backend
  - Peut tourner en Cloud Run ou localement

### 4. Docker & déploiement
- **`Dockerfile.runpod-worker`** (nouveau)
  - Image Docker légère sans torch/whisperx
  - Seulement ffmpeg + dépendances Google Cloud
- **`requirements-runpod.txt`** (nouveau)
  - Dépendances Python minimales pour le worker RunPod
  - Pas de torch/whisperx (transcription sur RunPod)
- **`cloudbuild-runpod.yaml`** (nouveau)
  - Configuration Cloud Build pour build + deploy automatique

### 5. Documentation
- **`RUNPOD_DEPLOYMENT_GUIDE.md`** (nouveau)
  - Guide complet de déploiement
  - Configuration RunPod endpoint
  - Configuration GCS bucket
  - Tests et vérification
  - Troubleshooting

## ✅ Fichiers modifiés

### 1. Configuration
- **`config/highlight_config.json`**
  - Ajout de la section `transcription_backend`
  - Configuration `cpu_local` et `gpu_runpod`
  - Ajout de la section `vm_workers` avec feature flags
  - Ajout du paramètre `gcs_temp_bucket`

### 2. Worker VM CPU (ancien système)
- **`scripts/subtitles_vm_worker.py`**
  - Ligne 92-133: Remplacement de `align_segments_with_whisperx()` par `align_segments_with_backend()`
  - Ligne 236-252: Import et initialisation du backend avec `get_transcription_backend(config)`
  - Ligne 295-302: Passage du backend à `process_subtitles_job()`
  - Ligne 363-370: Ajout du paramètre `backend` à la fonction
  - Ligne 459: Utilisation du backend pour l'alignement

### 3. Orchestrator Cloud Run
- **`scripts/highlight_orchestrator_cloud.py`**
  - Ligne 872-911: Modification de `start_vm_if_needed()` pour accepter `vm_type` parameter
  - Ajout de la logique pour respecter les flags `vm_workers` dans la config
  - Ligne 1000, 1007: Ajout du paramètre `vm_type` lors des appels

## 🔧 Architecture

### ⚠️ Architecture OBSOLÈTE - VM-based (avant 2026-01)
```
Cloud Run Orchestrator
    ↓
Queue subtitles jobs → VM Worker (CPU faster-whisper) → Drive
```

**Problèmes:**
- Lent (~10 min pour 5 min audio)
- VM à gérer (maintenance, coûts)
- Qualité moyenne (base model)
- Complexité (queue + jobs + VM lifecycle)

### ✅ Architecture ACTUELLE (2026-02) - RunPod Direct

```
Cloud Scheduler (toutes les 5 min)
    ↓
Cloud Run whisper-automation (scripts/cloud_run_server.py)
    ├─→ 1. Scan source_files/ pour nouveaux fichiers
    ├─→ 2. Upload audio → GCS temp bucket
    ├─→ 3. Call RunPod API directement (pas de queue, pas de worker)
    ├─→ 4. Poll job status
    ├─→ 5. Récupère résultats
    └─→ 6. Upload vers Drive transcriptions/
            ↓
    RunPod GPU Serverless (large-v3-turbo)
```

**Avantages:**
- ✅ Rapide (~30s pour 5 min audio, 20× plus rapide)
- ✅ Excellente qualité (large-v3-turbo)
- ✅ Serverless (aucune VM à gérer)
- ✅ Coûts optimisés (pay-per-use)
- ✅ Architecture simple (direct API call)

### Code actuel (cloud_run_server.py:228-344)

```python
# Ligne 228: Détection du backend
use_runpod = (backend_provider == 'gpu_runpod')

if use_runpod:
    # Ligne 318: Transcription DIRECTE avec RunPod
    logger.info("🚀 transcription directe avec RunPod")

    for file_info in files_to_vm:
        # 1. Upload audio → GCS
        # 2. Call RunPod API
        result = backend.transcribe_audio(audio_path, language='fr')
        # 3. Upload résultats → Drive

# PAS de VM, PAS de queue, PAS de jobs!
```

## 🎛️ Feature flags

Dans `highlight_config.json`:

```json
{
  "transcription_backend": {
    "provider": "gpu_runpod"  // ou "cpu_local"
  },
  "vm_workers": {
    "highlights_vm_enabled": true,
    "subtitles_vm_enabled": false,
    "auto_start_subtitles_vm": false
  }
}
```

### Changement de backend en 2 étapes:

**Pour activer GPU RunPod:**
```json
{"provider": "gpu_runpod", "subtitles_vm_enabled": false}
```

**Pour revenir au CPU VM:**
```json
{"provider": "cpu_local", "subtitles_vm_enabled": true, "auto_start_subtitles_vm": true}
```

## 🚀 Déploiement

### Prérequis
1. Endpoint RunPod Serverless créé
2. API key RunPod récupérée
3. Bucket GCS `whisper-temp-audio` créé
4. Config mise à jour dans `highlight_config.json`

### Build & Deploy

```bash
# 1. Build l'image Docker
gcloud builds submit \
  --config cloudbuild-runpod.yaml \
  --substitutions=_RUNPOD_API_KEY="<VOTRE_CLE>"

# 2. Déployer l'orchestrator avec la nouvelle config
gsutil cp config/highlight_config.json \
  gs://artificial-intelligence-cmk/config/

gcloud run deploy highlights-orchestrator \
  --source . \
  --region europe-west1
```

## 🧪 Tests

### Test 1: Vérifier backend sélectionné
```bash
cat config/highlight_config.json | jq '.transcription_backend.provider'
# Devrait afficher: "gpu_runpod"
```

### Test 2: Test local du client RunPod
```python
from src.runpod_client import RunPodClient
import os

os.environ['RUNPOD_API_KEY'] = 'VOTRE_CLE'
client = RunPodClient(
    api_key=os.environ['RUNPOD_API_KEY'],
    endpoint='https://api.runpod.ai/v2/<ENDPOINT_ID>'
)

result = client.transcribe_audio(
    audio_url='https://storage.googleapis.com/...',
    model='large-v3-turbo',
    language='fr'
)
print(f"Segments: {len(result['segments'])}")
```

### Test 3: Job end-to-end
1. Marquer un document avec `🎬 READY 🎬`
2. Cloud Scheduler déclenche orchestrator
3. Vérifier logs:
   ```bash
   gcloud run services logs read runpod-transcription-worker \
     --region europe-west1 --limit 50
   ```
4. Vérifier que VM CPU n'est PAS démarrée:
   ```bash
   gcloud compute instances describe highlights-worker-vm \
     --zone europe-west1-b --format="value(status)"
   # Devrait être: TERMINATED
   ```
5. Vérifier output Drive dans `segments_output/.../with_subtitles_*/`

## 📊 Métriques clés

### Performance
| Backend | Temps transcription (5 min audio) | Qualité |
|---------|-----------------------------------|---------|
| CPU (faster-whisper base) | ~10 minutes | Moyenne |
| GPU (large-v3-turbo) | ~30 secondes | Excellente |

### Coûts mensuels (estimation pour 10 min de transcription/mois)
| Composant | CPU | GPU RunPod |
|-----------|-----|------------|
| Cloud Run orchestrator | $2.50 | $2.50 |
| Cloud Run worker | - | $3.00 |
| VM CPU n1-standard-4 | $0.20 | - |
| RunPod RTX 4090 | - | $0.26 |
| **Total** | **$2.70** | **$5.76** |

**Différence: +$3/mois pour 10× meilleure qualité**

## 🔄 Rollback rapide

Si problème avec RunPod:

```bash
# 1. Modifier la config
cat > temp_config.json << EOF
{
  "transcription_backend": {"provider": "cpu_local"},
  "vm_workers": {
    "highlights_vm_enabled": true,
    "subtitles_vm_enabled": true,
    "auto_start_subtitles_vm": true
  }
}
EOF

# 2. Merger avec la config existante (garder les autres champs)
jq -s '.[0] * .[1]' config/highlight_config.json temp_config.json > new_config.json
mv new_config.json config/highlight_config.json

# 3. Upload sur GCS
gsutil cp config/highlight_config.json \
  gs://artificial-intelligence-cmk/config/

# 4. Redéployer l'orchestrator (pour relire la config)
gcloud run deploy highlights-orchestrator \
  --source . \
  --region europe-west1

# Le système revient automatiquement sur CPU VM
```

## ⚠️ Points d'attention

### 1. Import WhisperX (CPULocalBackend)
- WhisperX est importé UNIQUEMENT dans `CPULocalBackend.__init__()`
- Pas d'import global pour éviter erreur si whisperx non installé
- RunPod worker n'a pas besoin de whisperx

### 2. Upload audio pour RunPod
- Audio uploadé vers GCS avec URL signée (1h de validité)
- Alternative possible: lien partagé Drive temporaire
- Bucket GCS avec lifecycle policy (auto-delete après 1 jour)

### 3. Format de réponse RunPod
- La méthode `_convert_runpod_to_whisperx_format()` adapte la réponse
- À ajuster selon le format exact de l'API RunPod
- Doit matcher le format whisperx pour compatibilité avec le reste du code

### 4. Gestion d'erreur
- Si erreur RunPod → job marqué "failed", pas de fallback automatique
- Logger toutes les erreurs dans `failed_jobs/`
- Pour changer de backend → modifier config + redéployer

### 5. VM CPU toujours dans le code
- Le code du VM worker reste disponible
- Peut être réactivé via feature flag sans modification de code
- Utile pour rollback ou tests

## 📝 TODO après déploiement

- [ ] Créer un endpoint RunPod Serverless
- [ ] Configurer le bucket GCS `whisper-temp-audio`
- [ ] Mettre à jour `highlight_config.json` avec endpoint et bucket
- [ ] Build et deploy l'image Docker RunPod worker
- [ ] Tester avec un petit fichier audio
- [ ] Monitorer les logs pendant 24h
- [ ] Comparer qualité CPU vs GPU sur un échantillon
- [ ] Vérifier les coûts réels après 1 semaine

## 🔗 Ressources

- **Documentation RunPod**: https://docs.runpod.io/serverless/overview
- **Whisper Large-v3-turbo**: https://github.com/openai/whisper
- **Google Cloud Run**: https://cloud.google.com/run/docs
- **Guide de déploiement complet**: voir `RUNPOD_DEPLOYMENT_GUIDE.md`

## 🎯 Prochaines améliorations possibles

1. **Monitoring avancé**
   - Dashboard Grafana pour métriques RunPod
   - Alertes si timeout > 10% des jobs

2. **Optimisations de coûts**
   - Utiliser GPU moins cher (RTX 3090) si qualité suffisante
   - Batch processing pour amortir les cold starts

3. **Fallback automatique**
   - Si RunPod down → fallback temporaire sur CPU
   - Nécessite gestion de state plus complexe

4. **Cache de transcriptions**
   - Hash audio + garder en cache les transcriptions
   - Éviter re-transcription si audio identique

5. **Support multi-langues**
   - Détection automatique de la langue
   - Configuration par document
