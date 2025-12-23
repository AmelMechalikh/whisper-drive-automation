# Système d'Extraction de Highlights Vidéo

## 📋 Vue d'ensemble

Ce système automatise l'extraction de segments vidéo/audio basés sur des annotations dans les transcriptions.

**Architecture** : 100% Serverless (Cloud Run uniquement)

### Workflow complet

```
⏰ Cloud Scheduler (toutes les 5 min)
    ↓
☁️  Cloud Run Highlights Processor
    ├─ Détecte fichiers avec commentaires
    ├─ Extrait highlights → Génère Excel
    ├─ Télécharge vidéo source
    ├─ Découpe segments (ffmpeg, pas de réencodage)
    ├─ Fusionne segments identiques
    └─ Upload résultats sur Drive
    ↓
📁 Google Drive (résultats organisés par vidéo)
```

**Avantages** :
- 💰 **Coût** : ~0-2€/mois (tier gratuit Cloud Run)
- ⚡ **Latence** : Max 5 minutes + temps de traitement (~2-6 min)
- 🚀 **Déploiement** : 1 commande, aucune VM à gérer
- 🔧 **Maintenance** : Zéro (scale-to-zero automatique)
- ♻️  **Écologique** : Consomme uniquement quand nécessaire

---

## 🗂️ Structure des dossiers Drive

- **Transcriptions** : Dossier principal des transcriptions
  - **Highlighted Files** : Fichiers Google Docs avec commentaires (sous-dossier)
- **Highlights Excel** : Fichiers Excel générés avec timestamps
- **Segments Videos** : Segments vidéo/audio extraits

## ✏️ Format d'annotation

Utilisez les **commentaires Google Docs** pour marquer les passages à extraire.

### Étapes d'annotation :

1. Convertissez le fichier `_paragraphs_timestamps.txt` en Google Doc
2. Sélectionnez le texte à extraire
3. Ajoutez un commentaire (Ctrl+Alt+M ou Cmd+Option+M)
4. Vous pouvez ajouter une note dans le commentaire pour décrire le highlight

### Fusion automatique :

**Important** : Si vous utilisez **exactement le même commentaire** sur plusieurs passages, ils seront automatiquement fusionnés en une seule vidéo !

**Exemple - Fusionner 3 passages sous le thème "Concept clé" :**

```
Passage 1 (minute 2):
(2:15) Première partie de l'explication importante.
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       [Commentaire: "Concept clé"]

Passage 2 (minute 5):
(5:30) Deuxième partie qui complète l'explication.
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       [Commentaire: "Concept clé"]

Passage 3 (minute 8):
(8:45) Conclusion de ce concept.
       ^^^^^^^^^^^^^^^^^^^^^^^^^^
       [Commentaire: "Concept clé"]
```

→ Résultat : **1 seule vidéo** contenant les 3 passages dans l'ordre chronologique

### Exemple :

```
(0:45) Première phrase du segment. (0:48) Deuxième phrase.
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       [Commentaire: "Point clé sur le sujet principal"]

(0:52) Dernière phrase du segment.
```

Le texte sélectionné + commentaire = 1 highlight qui sera extrait.

**Note importante** : Seuls les fichiers **avec au moins un commentaire** seront traités.

## 📊 Format du fichier Excel généré

Le fichier Excel contient les colonnes suivantes :

| Colonne | Description |
|---------|-------------|
| **Numéro** | Numéro du groupe de highlight (segments avec même commentaire) |
| **Groupe** | Contenu du commentaire (identifie le groupe à fusionner) |
| **Sous-segment** | Numéro du sous-segment si fusion (1, 2, 3...) |
| **Total sous-segments** | Nombre total de segments à fusionner dans ce groupe |
| **Début (secondes)** | Timestamp de début en secondes |
| **Fin (secondes)** | Timestamp de fin en secondes |
| **Début (HH:MM:SS)** | Timestamp de début formaté |
| **Fin (HH:MM:SS)** | Timestamp de fin formaté |
| **Durée (secondes)** | Durée du segment |
| **À fusionner** | "Oui" si plusieurs segments avec même commentaire |
| **Texte** | Extrait du texte (150 premiers caractères) |

### Exemple d'Excel généré :

| Numéro | Groupe | Sous-segment | Total | Début (s) | Fin (s) | À fusionner |
|--------|--------|--------------|-------|-----------|---------|-------------|
| 1 | Concept clé | 1 | 3 | 135.2 | 158.4 | Oui |
| 1 | Concept clé | 2 | 3 | 330.5 | 342.1 | Oui |
| 1 | Concept clé | 3 | 3 | 525.8 | 538.9 | Oui |
| 2 | Introduction | - | - | 2.4 | 45.6 | Non |
| 3 | Exemple pratique | 1 | 2 | 615.3 | 658.7 | Oui |
| 3 | Exemple pratique | 2 | 2 | 892.1 | 915.4 | Oui |

→ Résultat vidéo : **4 fichiers** (groupe 1 fusionné, groupe 2 simple, groupe 3 fusionné, pas de groupe 4)

## 🎬 Segments vidéo générés

Les segments sont nommés selon le pattern :
```
{nom_fichier_original}_highlight_{numéro}_{commentaire}.{extension}
```

Exemple avec commentaires simples :
```
seance_3_jour_1_highlight_01_Introduction.mp4
seance_3_jour_1_highlight_02_Concept_cle.mp4
seance_3_jour_1_highlight_03_Exemple_pratique.mp4
```

Exemple avec fusion (même commentaire "Concept clé" sur 3 passages) :
```
seance_3_jour_1_highlight_02_Concept_cle.mp4  ← Contient les 3 passages fusionnés
```

**Note** : Le commentaire dans le nom de fichier est tronqué à 30 caractères et nettoyé (caractères spéciaux remplacés).

---

## 🚀 Installation et Déploiement

### Déploiement Automatique (1 commande)

```bash
cd whisper-drive-automation

# 1. Setup initial (créer dossiers Drive) - une seule fois
python3 scripts/setup_highlights.py

# 2. Déployer Cloud Run + Scheduler
chmod +x scripts/deploy_highlights_serverless.sh
./scripts/deploy_highlights_serverless.sh
```

**Ce script déploie** :
- ☁️  Cloud Run avec ffmpeg intégré
- ⏰ Cloud Scheduler (trigger toutes les 5 min)
- 📦 Configuration automatique

**Durée** : ~3-5 minutes

### Vérification du déploiement

```bash
# Status du système
CLOUD_RUN_URL=$(gcloud run services describe highlights-processor \
  --region=europe-west1 --format='value(status.url)')

curl $CLOUD_RUN_URL/status

# Trigger manuel (test)
curl -X POST $CLOUD_RUN_URL/trigger
```

### Architecture Technique

- **Cloud Run** : 2GB RAM, 2 vCPU, timeout 60 min
- **ffmpeg** : Découpage avec `-c copy` (pas de réencodage)
- **Stockage temporaire** : `/tmp` (10GB disponibles)
- **Scale** : 0 à 10 instances (scale-to-zero automatique)

---

## 📖 Guide d'utilisation

### Mode Production (Automatique)

Une fois déployé, le système fonctionne automatiquement :

1. **Ajoutez un Google Doc avec commentaires** dans `Highlighted Files`
2. **Attendez max 5 minutes** (Cloud Scheduler trigger automatique)
3. **Le Cloud Run traite** :
   - Extrait les highlights → Génère Excel
   - Découpe la vidéo → Fusionne les segments
   - Upload dans `Segments Videos/{nom_video}/`
4. **Récupérez les résultats** organisés par vidéo

**Temps de traitement** :
- Vidéo 30 min avec 5 segments : ~2-3 minutes
- Vidéo 1h30 avec 10 segments : ~4-6 minutes

### Monitoring

```bash
# Logs en temps réel
gcloud run services logs read highlights-processor \
  --region=europe-west1 --follow

# Dernières exécutions
gcloud run services logs read highlights-processor \
  --region=europe-west1 --limit=50
```

---

## 📝 Workflow Utilisateur Complet

### 1. Télécharger la transcription

1. Allez dans le dossier **Transcriptions** sur Google Drive
2. Téléchargez le fichier `{nom}_paragraphs_timestamps.txt`

### 2. Convertir en Google Doc

1. Uploadez le fichier dans **Transcriptions/Highlighted Files**
2. Option A : Clic droit → "Ouvrir avec" → "Google Docs"
3. Option B : Créez un nouveau Google Doc et copiez-collez le contenu

**Important** : Le fichier doit être un Google Doc pour pouvoir ajouter des commentaires.

### 3. Annoter avec des commentaires
[Unit]
Description=Video Segment Processor (Étape 2)
After=network.target

[Service]
Type=simple
User=amel
WorkingDirectory=/home/amel/whisper-drive-automation
ExecStart=/usr/bin/python3 scripts/process_video_segments.py
Restart=always
RestartSec=10
StandardOutput=append:/home/amel/whisper-drive-automation/video_segment_processor.log
StandardError=append:/home/amel/whisper-drive-automation/video_segment_processor.log

[Install]
WantedBy=multi-user.target
```

Activer le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable video-segment-processor
sudo systemctl start video-segment-processor
sudo systemctl status video-segment-processor
```

## 📖 Guide d'utilisation

### Mode manuel (debuggable)

### Étape 1 : Télécharger la transcription

1. Allez dans le dossier **Transcriptions** sur Google Drive
2. Téléchargez le fichier `{nom}_paragraphs_timestamps.txt`

### Étape 2 : Convertir en Google Doc

1. Uploadez le fichier dans **Transcriptions/Highlighted Files**
2. Option A : Clic droit → "Ouvrir avec" → "Google Docs"
3. Option B : Créez un nouveau Google Doc et copiez-collez le contenu

**Important** : Le fichier doit être un Google Doc pour pouvoir ajouter des commentaires.

### 3. Annoter avec des commentaires

1. Sélectionnez le passage de texte à extraire
2. Ajoutez un commentaire (Ctrl+Alt+M / Cmd+Option+M)
3. Optionnel : Décrivez le highlight dans le commentaire
4. Répétez pour chaque passage à extraire

**Astuce fusion** : Utilisez exactement le même commentaire sur plusieurs passages pour les fusionner automatiquement !

Exemple de sélection :
```
(0:30) Introduction générale. (0:35) Contexte du sujet.

[Sélectionnez ce bloc ↓]
(0:45) Explication très importante que je veux extraire.
(0:52) Suite de l'explication importante.
(0:58) Conclusion de cette partie importante.
[Ajoutez commentaire: "Concept clé"]

(1:05) Suite de la transcription normale...

[Sélectionnez ce bloc ↓]
(2:15) Deuxième passage important à extraire.
(2:22) Fin du deuxième passage.
[Ajoutez commentaire: "Exemple pratique"]
```

### 4. Sauvegarder et attendre

- Conservez le fichier dans **Transcriptions/Highlighted Files**
- Le nom doit contenir `_paragraphs_timestamps`
- **Attendez max 5 minutes** - Le Cloud Scheduler déclenche automatiquement

### 5. Suivre le traitement (optionnel)

```bash
# Logs Cloud Run
gcloud run services logs read highlights-orchestrator --region=europe-west1

# Status VM
gcloud compute instances describe highlights-worker \
  --zone=europe-west1-b --format='value(status)'
```

### 6. Vérifier l'Excel (optionnel)

Avant le découpage automatique, vous pouvez **vérifier/corriger** l'Excel :

1. Allez dans le dossier **Highlights Excel**
2. Téléchargez le fichier `{nom}_highlights.xlsx`
3. Vérifiez que :
   - Les timestamps sont corrects
   - Les groupes (colonne "Groupe") correspondent aux commentaires
   - Les segments à fusionner sont bien identifiés ("À fusionner" = Oui)

**Si correction nécessaire** : Modifiez l'Excel et réuploadez-le. La VM le retraitera automatiquement.

### 7. Récupérer les résultats
   - Les timestamps sont corrects
   - Les groupes (colonne "Groupe") correspondent aux commentaires
   - Les segments à fusionner sont bien identifiés ("À fusionner" = Oui)

**Si correction nécessaire** : Modifiez l'Excel et réuploadez-le.

### Étape 7 : Lancer le découpage vidéo

**Mode automatique** : Le worker 2 traite automatiquement les Excel (5 min)

**Mode manuel** :
```bash
python3 scripts/process_video_segments.py
```

Suivre les logs :
```bash
tail -f video_segment_processor.log
```

### Étape 8 : Récupérer les résultats

**Excel avec timestamps :**
- Dossier : **Highlights Excel**
- Nom : `{nom}_highlights.xlsx`

**Segments vidéo :**
- Dossier : **Segments Videos** (avec sous-dossiers par vidéo)
- Structure : `Segments Videos/{nom_vidéo}/highlight_{numero:02d}_{texte_commentaire}.{extension}`

Exemple :
```
📁 Segments Videos/
├── 📁 09.07 - Guèn Shri - Apprendre de tout/
│   ├── highlight_01_concept_clé.mp4
│   ├── highlight_02_exemple_pratique.mp4
├── 📁 15.08 - Interview Jean - Innovation/
│   ├── highlight_01_intro_importante.mp4
│   ├── highlight_02_citation_clé.mp4
```

---

## 🛠️ Mode Debug (Exécution Manuelle)

Si vous voulez exécuter les processus séparément pour débugger :

### Process 1 uniquement (Génération Excel)

```bash
python3 scripts/highlight_worker.py
```

Cela va :
1. Chercher les fichiers dans **Highlighted Files**
2. Extraire les commentaires
3. Générer l'Excel dans **Highlights Excel**
4. S'arrêter (pas de découpage vidéo)

### Process 2 uniquement (Découpage vidéo)

```bash
python3 scripts/process_video_segments.py
```

Cela va :
1. Chercher les Excel dans **Highlights Excel**
2. Télécharger la vidéo source correspondante
3. Extraire et fusionner les segments
4. Uploader dans **Segments Videos**

---

## 🔧 Dépannage

### Le Cloud Run ne se déclenche pas

```bash
# Vérifier le statut
curl https://highlights-processor-XXX-ew.a.run.app/status

# Déclencher manuellement
curl -X POST https://highlights-processor-XXX-ew.a.run.app/trigger

# Voir les logs
gcloud run services logs read highlights-processor --region=europe-west1 --limit=100
```

### Les timestamps ne sont pas trouvés

Assurez-vous que :
- Le fichier JSON complet (`_complete_data.json`) existe dans le dossier **Transcriptions**
- Les commentaires sont ajoutés sur du texte existant dans la transcription
- Le texte sélectionné correspond exactement au texte de la transcription (avec timestamps)

### Les segments vidéo ne sont pas créés

Vérifier que :
- La vidéo source existe dans le dossier **Files**
- Le nom du fichier (sans extension) correspond exactement à celui de la transcription
- Les logs Cloud Run pour voir les erreurs : `gcloud run services logs read highlights-processor`

### Timeout Cloud Run

Si votre vidéo dépasse 60 min de traitement :
- Réduisez le nombre de segments
- Ou contactez-moi pour passer à une architecture hybride Cloud Run + VM

### Vérifier le Cloud Scheduler

```bash
# Liste des jobs
gcloud scheduler jobs list --location=europe-west1

# Déclencher manuellement
gcloud scheduler jobs run trigger-highlights --location=europe-west1

# Voir l'historique
gcloud scheduler jobs describe trigger-highlights --location=europe-west1
```

---

## 💰 Coûts Estimés

| Service | Usage mensuel | Coût |
|---------|---------------|------|
| **Cloud Run** | ~8640 invocations (5 min) | 0€ (tier gratuit) |
| | ~30h compute (si 10 vidéos/mois) | ~0.50€ |
| **Cloud Scheduler** | 1 job | 0€ (3 jobs gratuits) |
| **Storage /tmp** | Temporaire uniquement | 0€ |
| **Network** | Uploads/downloads Drive | <0.50€ |
| **TOTAL** | | **~0-2€/mois** 💰 |

### Comparaison architectures

| Architecture | Coût mensuel | Complexité | Maintenance |
|--------------|--------------|------------|-------------|
| **Serverless (actuel)** | ~1€ | Faible | Zéro |
| **VM on-demand** | ~4€ | Moyenne | Faible |
| **Polling 24/7** | ~20€ | Faible | Moyenne |

---

## 📊 Monitoring

### Vérifier les fichiers traités

```python
from src.drive_manager import DriveManager

dm = DriveManager('config/credentials.json')

# Lister les highlights traités
excel_folder = 'ID_DU_DOSSIER_EXCEL'
files = dm.list_files_in_folder(excel_folder)
print(f"{len(files)} fichiers Excel créés")

# Lister les segments
segments_folder = 'ID_DU_DOSSIER_SEGMENTS'
segments = dm.list_files_in_folder(segments_folder)
print(f"{len(segments)} segments vidéo créés")
```

### Statistiques de traitement

Les logs contiennent les statistiques après chaque cycle :
```
📊 Stats: {'processed': 2, 'errors': 0}
```

## 🎯 Optimisations possibles

### 1. Extraction parallèle
Traiter plusieurs highlights en même temps avec `multiprocessing`

### 2. Compression vidéo
Ajouter une option pour compresser les segments :
```python
# Dans video_segment_extractor.py
cmd = [
    'ffmpeg',
    '-ss', str(start_seconds),
    '-i', input_path,
    '-t', str(duration),
    '-c:v', 'libx264',  # Au lieu de -c copy
    '-crf', '23',        # Qualité (18-28, plus bas = meilleure qualité)
    '-preset', 'medium',
    output_path
]
```

### 3. Notifications
Envoyer une notification quand le traitement est terminé (email, Slack, etc.)

### 4. Interface web
Créer une interface pour :
- Uploader et annoter directement depuis le navigateur
- Visualiser les highlights avec player vidéo intégré
- Télécharger les segments

## 📝 Notes

- **Précision des timestamps** : Le système utilise les word timestamps pour une précision maximale (±0.1s)
- **Formats supportés** : MP4, MP3, WAV, M4A, MOV
- **Copie sans réencodage** : Par défaut, les segments sont copiés sans réencodage (rapide, qualité préservée)
- **Stockage temporaire** : Les fichiers sont téléchargés temporairement et nettoyés après traitement

## 🔗 Ressources

- [Documentation ffmpeg](https://ffmpeg.org/documentation.html)
- [Google Drive API](https://developers.google.com/drive/api/v3/reference)
- [openpyxl Documentation](https://openpyxl.readthedocs.io/)
