# 🎙️ Whisper Drive Automation

Système automatisé de transcription audio/vidéo utilisant Whisper AI et Google Drive.

## 📋 Architecture

```
Google Drive (Files/)
    ↓
Cloud Run (Scheduler - toutes les heures)
    ↓ 
Google Drive (Queue/)
    ↓
VM Worker (auto-start/stop)
    ↓
Google Drive (Transcriptions/)
```

## 🚀 Services déployés

### Cloud Run
- **Service**: `whisper-automation`
- **Région**: europe-west1
- **URL**: https://whisper-automation-pt4e4lc6uq-ew.a.run.app
- **Déclenchement**: Scheduler toutes les heures

### VM Worker
- **Instance**: `whisper-cpu-worker`
- **Type**: n1-standard-4
- **Zone**: europe-west1-b
- **Auto-shutdown**: 5 minutes d'inactivité

### Scheduler
- **Job**: `whisper-auto-transcription`
- **Fréquence**: Toutes les heures (`0 * * * *`)
- **Région**: europe-west1

## 📁 Structure du projet

```
whisper-drive-automation/
├── config/
│   ├── credentials.json      # Clés service account
│   └── whisper_config.py     # Configuration Drive
├── scripts/
│   ├── cloud_run_server.py   # Serveur HTTP Cloud Run
│   └── vm_worker.py           # Worker VM
├── src/
│   ├── drive_manager.py      # Gestion Google Drive
│   ├── processor.py          # Orchestration
│   ├── whisper_transcriber.py # Transcription Whisper
│   └── output_generator.py   # Génération fichiers
├── Dockerfile                # Image Cloud Run
└── requirements.txt          # Dépendances Python
```

## 🔧 Configuration Drive

### Dossiers (Shared Drive: `0AJsxPbtOtogRUk9PVA`)
- **Files**: `1A29pkQvrBodU_HxNS8deYt6T27AlmbSe` (entrée)
- **Transcriptions**: `1yHcy9um2_We459w9I0cITwHBGXKTlOJa` (sortie)
- **Queue**: `1yvN9VP0bAmZJGfyUlBFG4mzR22c5addV` (jobs)

### Formats supportés
Audio: `.mp3`, `.wav`, `.m4a`, `.flac`, `.aac`
Vidéo: `.mp4`, `.mov`, `.avi`, `.mkv`

## 📤 Formats de sortie

Pour chaque fichier transcrit :
- `*_transcription.txt` - Texte brut
- `*_with_timestamps.srt` - Sous-titres SRT
- `*_word_timestamps.txt` - Timestamps par mot
- `*_paragraphs_timestamps.txt` - Paragraphes avec timestamps
- `*_complete_data.json` - Données complètes JSON

## 🔄 Workflow

1. **Upload** : Déposer fichiers audio/vidéo dans `Files/`
2. **Détection** : Scheduler déclenche Cloud Run toutes les heures
3. **Création jobs** : Cloud Run crée jobs dans `Queue/` pour fichiers non transcrits
4. **Traitement** : VM démarre automatiquement et traite la queue
5. **Résultats** : Transcriptions sauvegardées dans `Transcriptions/`
6. **Arrêt** : VM s'éteint après 5 minutes d'inactivité

## 🛠️ Déploiement

### Cloud Run
```bash
cd whisper-drive-automation
gcloud run deploy whisper-automation \
  --source . \
  --region=europe-west1 \
  --allow-unauthenticated \
  --timeout=3600 \
  --memory=2Gi
```

### VM Worker
```bash
# Copier les fichiers
gcloud compute scp scripts/vm_worker.py whisper-cpu-worker:~/whisper-drive-automation/scripts/ \
  --zone=europe-west1-b

gcloud compute scp src/drive_manager.py whisper-cpu-worker:~/whisper-drive-automation/src/ \
  --zone=europe-west1-b

# Redémarrer le service
gcloud compute ssh whisper-cpu-worker --zone=europe-west1-b \
  --command="sudo systemctl restart whisper-worker"
```

## 📊 Monitoring

### Vérifier la queue
```bash
python3 check_queue.py
```

### État de la VM
```bash
gcloud compute instances describe whisper-cpu-worker \
  --zone=europe-west1-b \
  --format='value(status)'
```

### Logs VM
```bash
gcloud compute ssh whisper-cpu-worker --zone=europe-west1-b \
  --command="sudo journalctl -u whisper-worker -n 50"
```

### Logs Cloud Run
```bash
gcloud run services logs read whisper-automation \
  --region=europe-west1 \
  --limit=50
```

## ✅ Fonctionnalités

- ✅ Détection automatique des nouveaux fichiers
- ✅ Transcription Whisper (modèle large-v2)
- ✅ Support audio et vidéo
- ✅ Génération multi-formats
- ✅ Auto-start/stop VM
- ✅ Détection doublons
- ✅ Gestion erreurs et retry
- ✅ Queue asynchrone

## 🔐 Sécurité

- Service account : `id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com`
- Credentials : `config/credentials.json`
- Accès : Google Drive partagé uniquement
