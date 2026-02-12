# Configuration Reference - RunPod Backend

## highlight_config.json - Structure complète

```json
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
    "provider": "gpu_runpod",
    "cpu_local": {
      "device": "cpu",
      "model": "base",
      "compute_type": "int8"
    },
    "gpu_runpod": {
      "device": "cuda",
      "model": "large-v3-turbo",
      "api_endpoint": "https://api.runpod.ai/v2/<YOUR_ENDPOINT_ID>",
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

## Paramètres de configuration

### transcription_backend

#### provider
- **Type**: `string`
- **Valeurs**: `"cpu_local"` | `"gpu_runpod"`
- **Défaut**: `"cpu_local"`
- **Description**: Choix du backend de transcription
- **Exemple**: `"gpu_runpod"`

#### cpu_local.device
- **Type**: `string`
- **Valeurs**: `"cpu"` | `"cuda"`
- **Défaut**: `"cpu"`
- **Description**: Device pour WhisperX local
- **Exemple**: `"cpu"`

#### cpu_local.model
- **Type**: `string`
- **Valeurs**: `"tiny"` | `"base"` | `"small"` | `"medium"` | `"large-v2"`
- **Défaut**: `"base"`
- **Description**: Modèle Whisper pour CPU local
- **Exemple**: `"base"`

#### cpu_local.compute_type
- **Type**: `string`
- **Valeurs**: `"int8"` | `"float16"` | `"float32"`
- **Défaut**: `"int8"`
- **Description**: Type de calcul pour faster-whisper
- **Exemple**: `"int8"`

#### gpu_runpod.device
- **Type**: `string`
- **Valeurs**: `"cuda"`
- **Défaut**: `"cuda"`
- **Description**: Device RunPod (toujours CUDA)
- **Exemple**: `"cuda"`

#### gpu_runpod.model
- **Type**: `string`
- **Valeurs**: `"large-v3"` | `"large-v3-turbo"`
- **Défaut**: `"large-v3-turbo"`
- **Description**: Modèle Whisper sur RunPod
- **Exemple**: `"large-v3-turbo"`

#### gpu_runpod.api_endpoint
- **Type**: `string`
- **Format**: `https://api.runpod.ai/v2/<ENDPOINT_ID>`
- **Requis**: Oui (si provider=gpu_runpod)
- **Description**: URL de l'endpoint RunPod Serverless
- **Exemple**: `"https://api.runpod.ai/v2/abc123def456"`

#### gpu_runpod.api_key_env
- **Type**: `string`
- **Défaut**: `"RUNPOD_API_KEY"`
- **Description**: Nom de la variable d'environnement contenant l'API key
- **Exemple**: `"RUNPOD_API_KEY"`

#### gpu_runpod.timeout_seconds
- **Type**: `integer`
- **Défaut**: `600`
- **Range**: `60` - `3600`
- **Description**: Timeout pour les jobs RunPod (secondes)
- **Exemple**: `600`

#### gpu_runpod.max_retries
- **Type**: `integer`
- **Défaut**: `3`
- **Range**: `1` - `10`
- **Description**: Nombre de retries en cas d'erreur
- **Exemple**: `3`

### gcs_temp_bucket
- **Type**: `string`
- **Requis**: Oui (si provider=gpu_runpod)
- **Description**: Nom du bucket GCS pour fichiers audio temporaires
- **Exemple**: `"whisper-temp-audio"`

### vm_workers

#### highlights_vm_enabled
- **Type**: `boolean`
- **Défaut**: `true`
- **Description**: Activer/désactiver la VM pour highlights
- **Exemple**: `true`

#### subtitles_vm_enabled
- **Type**: `boolean`
- **Défaut**: `true`
- **Description**: Activer/désactiver la VM pour sous-titres
- **Impact**: Si `false`, les jobs sous-titres sont traités par le worker RunPod
- **Exemple**: `false`

#### auto_start_subtitles_vm
- **Type**: `boolean`
- **Défaut**: `true`
- **Description**: Démarrer automatiquement la VM subtitles quand des jobs sont créés
- **Impact**: Si `false`, la VM ne démarre jamais automatiquement
- **Exemple**: `false`

## Configurations communes

### Configuration 1: RunPod GPU (production)

```json
{
  "transcription_backend": {
    "provider": "gpu_runpod"
  },
  "vm_workers": {
    "highlights_vm_enabled": true,
    "subtitles_vm_enabled": false,
    "auto_start_subtitles_vm": false
  }
}
```

**Résultat:**
- ✅ Highlights traités par VM CPU
- ✅ Sous-titres traités par RunPod GPU
- ✅ Haute qualité transcription
- 💰 Coût: ~$5.76/mois

### Configuration 2: CPU local uniquement (développement)

```json
{
  "transcription_backend": {
    "provider": "cpu_local"
  },
  "vm_workers": {
    "highlights_vm_enabled": true,
    "subtitles_vm_enabled": true,
    "auto_start_subtitles_vm": true
  }
}
```

**Résultat:**
- ✅ Highlights traités par VM CPU
- ✅ Sous-titres traités par VM CPU avec WhisperX
- ⚠️ Qualité moyenne
- 💰 Coût: ~$2.70/mois

### Configuration 3: Test local sans VM

```json
{
  "transcription_backend": {
    "provider": "cpu_local"
  },
  "vm_workers": {
    "highlights_vm_enabled": false,
    "subtitles_vm_enabled": false,
    "auto_start_subtitles_vm": false
  }
}
```

**Résultat:**
- ✅ Worker tourne en local
- ⚠️ Pas de démarrage automatique de VM
- 🧪 Idéal pour développement/debug

### Configuration 4: Hybrid (highlights VM + subtitles RunPod)

```json
{
  "transcription_backend": {
    "provider": "gpu_runpod"
  },
  "vm_workers": {
    "highlights_vm_enabled": true,
    "subtitles_vm_enabled": false,
    "auto_start_subtitles_vm": false
  }
}
```

**Résultat:**
- ✅ Meilleure des deux mondes
- ✅ Highlights: CPU VM (rapide et pas cher)
- ✅ Sous-titres: RunPod GPU (haute qualité)

## Variables d'environnement

### RUNPOD_API_KEY
- **Requis si**: `provider="gpu_runpod"`
- **Type**: `string`
- **Source**: RunPod Console → Settings → API Keys
- **Exemple**: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Définition dans Cloud Run

```bash
gcloud run deploy runpod-transcription-worker \
  --set-env-vars RUNPOD_API_KEY="your_api_key"
```

### Définition en local

```bash
export RUNPOD_API_KEY="your_api_key"
```

## Validation de la configuration

### Vérifier le provider actif

```bash
cat config/highlight_config.json | jq '.transcription_backend.provider'
```

### Vérifier l'état des VM workers

```bash
cat config/highlight_config.json | jq '.vm_workers'
```

### Tester la configuration

```python
import json

with open('config/highlight_config.json') as f:
    config = json.load(f)

provider = config['transcription_backend']['provider']
vm_enabled = config['vm_workers']['subtitles_vm_enabled']

print(f"Provider: {provider}")
print(f"VM subtitles enabled: {vm_enabled}")

if provider == 'gpu_runpod' and vm_enabled:
    print("⚠️  ATTENTION: provider=gpu_runpod mais VM encore activée!")
elif provider == 'cpu_local' and not vm_enabled:
    print("⚠️  ATTENTION: provider=cpu_local mais VM désactivée!")
else:
    print("✅ Configuration cohérente")
```

## Migration entre configurations

### De CPU vers RunPod GPU

```bash
# 1. Modifier la config
jq '.transcription_backend.provider = "gpu_runpod" |
    .vm_workers.subtitles_vm_enabled = false |
    .vm_workers.auto_start_subtitles_vm = false' \
  config/highlight_config.json > temp.json

mv temp.json config/highlight_config.json

# 2. Vérifier
cat config/highlight_config.json | jq '.transcription_backend'

# 3. Upload sur GCS
gsutil cp config/highlight_config.json \
  gs://artificial-intelligence-cmk/config/

# 4. Redéployer l'orchestrator
gcloud run deploy highlights-orchestrator --source .
```

### De RunPod GPU vers CPU

```bash
# 1. Modifier la config
jq '.transcription_backend.provider = "cpu_local" |
    .vm_workers.subtitles_vm_enabled = true |
    .vm_workers.auto_start_subtitles_vm = true' \
  config/highlight_config.json > temp.json

mv temp.json config/highlight_config.json

# 2. Upload et redéployer
gsutil cp config/highlight_config.json \
  gs://artificial-intelligence-cmk/config/

gcloud run deploy highlights-orchestrator --source .
```

## Troubleshooting

### Erreur: "Unknown backend: XYZ"

**Cause**: Valeur invalide pour `provider`

**Solution**: Vérifier que `provider` est soit `"cpu_local"` soit `"gpu_runpod"`

```bash
jq '.transcription_backend.provider' config/highlight_config.json
```

### Erreur: "RunPod api_endpoint not configured"

**Cause**: Endpoint RunPod manquant dans la config

**Solution**: Ajouter l'endpoint dans `gpu_runpod.api_endpoint`

```bash
jq '.transcription_backend.gpu_runpod.api_endpoint = "https://api.runpod.ai/v2/YOUR_ID"' \
  config/highlight_config.json > temp.json
mv temp.json config/highlight_config.json
```

### Erreur: "RunPod API key not found"

**Cause**: Variable d'environnement `RUNPOD_API_KEY` non définie

**Solution**: Définir la variable dans Cloud Run

```bash
gcloud run services update runpod-transcription-worker \
  --set-env-vars RUNPOD_API_KEY="your_key"
```

### VM ne démarre pas pour sous-titres

**Cause**: `subtitles_vm_enabled=false` ou `auto_start_subtitles_vm=false`

**Solution**: Vérifier la config

```bash
jq '.vm_workers' config/highlight_config.json
```

Si intentionnel (utilisation de RunPod), c'est normal.

## Références

- [RunPod API Documentation](https://docs.runpod.io/serverless/endpoints/send-requests)
- [Google Cloud Run Environment Variables](https://cloud.google.com/run/docs/configuring/environment-variables)
- [Whisper Models Comparison](https://github.com/openai/whisper#available-models-and-languages)
