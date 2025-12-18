# 🎙️ Transcription Project

Système automatisé de transcription audio/vidéo pour Google Drive utilisant Whisper AI.

## 📁 Structure

```
Transcription-Project/
├── whisper-drive-automation/    # Système principal (Cloud Run + VM)
├── utils/                        # Scripts de diagnostic
├── archive/                      # Anciens fichiers et documentation
├── service-account-key.json     # Credentials Google Cloud
└── requirements.txt             # Dépendances Python globales
```

## 🚀 Système principal

Le système actif se trouve dans `whisper-drive-automation/`. Voir [whisper-drive-automation/README.md](whisper-drive-automation/README.md) pour la documentation complète.

**Services déployés :**
- Cloud Run : `whisper-automation` (europe-west1)
- VM Worker : `whisper-cpu-worker` (n1-standard-4, auto-start/stop)
- Scheduler : Toutes les heures

## 🛠️ Scripts utilitaires

Les scripts dans `utils/` permettent de diagnostiquer et maintenir le système :

### Vérification
- `check_queue.py` - Nombre de jobs en attente
- `check_duplicates.py` - Doublons dans la Queue
- `check_transcriptions_duplicates.py` - Doublons dans Transcriptions
- `check_mp4_files.py` - Lister les fichiers MP4

### Nettoyage
- `delete_duplicates.py` - Supprimer les doublons (garde le plus récent)

### Diagnostic Drive
- `list_shared_drive_folders.py` - Lister dossiers shared drive
- `check_files_location.py` - Vérifier emplacement des dossiers
- `find_folder_ids.py` - Trouver IDs de dossiers par nom

## 📊 Quick Commands

### Vérifier l'état
```bash
# Queue
cd utils && python3 check_queue.py

# VM status
gcloud compute instances describe whisper-cpu-worker \
  --zone=europe-west1-b --format='value(status)'

# Logs VM
gcloud compute ssh whisper-cpu-worker --zone=europe-west1-b \
  --command="sudo journalctl -u whisper-worker -n 50"
```

### Nettoyer les doublons
```bash
cd utils && python3 delete_duplicates.py
```

## 🔐 Configuration

- **Service Account** : `id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com`
- **Credentials** : `service-account-key.json`
- **Shared Drive** : `0AJsxPbtOtogRUk9PVA`

## 📝 Historique

Le dossier `archive/` contient :
- Documentation des anciennes approches (Vertex AI, GPU, webhooks)
- Scripts prototypes et tests
- Anciennes configurations

## 🎯 Workflow actuel

1. Upload fichier dans Drive `Files/`
2. Scheduler déclenche Cloud Run (toutes les heures)
3. Cloud Run crée job dans `Queue/`
4. VM démarre et traite
5. Résultats dans `Transcriptions/`
6. VM s'éteint après 5 min d'inactivité

## ✅ Statut

✅ **Système opérationnel** - Déployé et fonctionnel
- Transcription automatique activée
- Auto-scaling VM
- Détection doublons
- Support audio + vidéo
