# Mise à jour de la configuration - Guide Rapide

## ⚠️ IMPORTANT

**Quand vous modifiez `config/highlight_config.json`, vous devez redéployer Cloud Run !**

Cloud Run lit la config depuis le fichier **inclus dans l'image Docker**, pas depuis votre disque local.

---

## 🚀 Procédure complète

### 1. Modifier la config

```bash
cd whisper-drive-automation
nano config/highlight_config.json
```

### 2. Redéployer Cloud Run

```bash
gcloud run deploy whisper-automation \
  --source . \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars="RUNPOD_API_KEY=$(gcloud secrets versions access latest --secret=RUNPOD_API_KEY)" \
  --memory=2Gi \
  --timeout=600 \
  --max-instances=1
```

**Temps:** ~5-10 minutes (build Docker + déploiement)

### 3. Vérifier la nouvelle config

```bash
# Tester
curl -X POST https://whisper-automation-pt4e4lc6uq-ew.a.run.app/process \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -d '{}'

# Voir les logs
gcloud logging read "resource.labels.service_name=whisper-automation" \
  --limit 50 --freshness=5m | grep -E "backend|RunPod|VM"
```

Vous devriez voir :
- ✅ `🚀 Using transcription backend: RunPodBackend`
- ✅ `🚀 X fichiers: transcription directe avec RunPod`

---

## 🔧 Solution alternative (plus rapide)

Pour éviter de redéployer à chaque changement de config, on peut faire lire la config depuis GCS :

### Modification du code (cloud_run_server.py ligne 222)

**Avant :**
```python
config_path = Path(__file__).parent.parent / 'config' / 'highlight_config.json'
```

**Après :**
```python
# Essayer d'abord GCS, sinon fichier local
try:
    from google.cloud import storage
    storage_client = storage.Client()
    bucket = storage_client.bucket('artificial-intelligence-cmk')
    blob = bucket.blob('config/highlight_config.json')
    highlight_config = json.loads(blob.download_as_text())
    logger.info("✅ Config chargée depuis GCS")
except Exception as gcs_error:
    logger.warning(f"⚠️ GCS config non disponible: {gcs_error}, using local")
    config_path = Path(__file__).parent.parent / 'config' / 'highlight_config.json'
    with open(config_path, 'r') as f:
        highlight_config = json.load(f)
```

### Upload config vers GCS

```bash
gsutil cp config/highlight_config.json \
  gs://artificial-intelligence-cmk/config/
```

**Avantage :** Changement de config instantané, pas besoin de redéployer !

---

## 📋 Checklist de changement de config

- [ ] Config modifiée localement
- [ ] Config commitée dans git (optionnel)
- [ ] **Cloud Run redéployé** (obligatoire !)
- [ ] Test avec curl
- [ ] Vérification logs
- [ ] VM arrêtée si RunPod activé

---

## ⏱️ Temps d'attente

| Action | Temps |
|--------|-------|
| Modifier config locale | 1 min |
| **Redéployer Cloud Run** | **5-10 min** |
| Tester | 30 sec |
| **Total** | **~10 min** |

Avec GCS : ~1 min (juste upload config)
