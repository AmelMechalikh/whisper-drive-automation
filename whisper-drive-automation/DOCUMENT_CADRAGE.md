# Document de Cadrage - Whisper Drive Automation
## Système d'Extraction Automatique de Segments Vidéo

**Version** : 1.0
**Date** : Janvier 2024
**Statut** : Opérationnel en Production

---

## 📋 Table des Matières

1. [Contexte et Problématique](#1-contexte-et-problématique)
2. [Objectifs du Projet](#2-objectifs-du-projet)
3. [Périmètre Fonctionnel](#3-périmètre-fonctionnel)
4. [Architecture Technique](#4-architecture-technique)
5. [Flux de Données](#5-flux-de-données)
6. [Détails des Composants](#6-détails-des-composants)
7. [Sécurité et Authentification](#7-sécurité-et-authentification)
8. [Déploiement et Infrastructure](#8-déploiement-et-infrastructure)
9. [Monitoring et Logs](#9-monitoring-et-logs)
10. [Coûts Estimés](#10-coûts-estimés)
11. [Limitations et Contraintes](#11-limitations-et-contraintes)
12. [Évolutions Futures](#12-évolutions-futures)
13. [Support et Maintenance](#13-support-et-maintenance)
14. [Annexes Techniques](#14-annexes-techniques)

---

## 1. Contexte et Problématique

### 1.1 Besoin Métier

Les créateurs de contenu vidéo doivent souvent extraire des passages spécifiques de vidéos longues (conférences, podcasts, webinaires) pour :
- Créer des extraits pour les réseaux sociaux
- Isoler des moments clés pour l'édition
- Partager des segments spécifiques avec des collaborateurs
- Créer des compilations thématiques

**Processus manuel actuel** :
1. Visionner toute la vidéo
2. Noter les timestamps
3. Utiliser un logiciel de montage (Premiere, Final Cut, etc.)
4. Découper et exporter manuellement chaque segment
5. ⏱️ **Temps estimé : 2-3 heures pour une vidéo d'1 heure**

### 1.2 Solution Proposée

Un système automatisé permettant de :
1. **Transcrire** automatiquement l'audio avec Whisper AI
2. **Annoter** la transcription via Google Docs (surlignage + commentaires)
3. **Extraire** automatiquement les segments vidéo correspondants
4. ⏱️ **Temps utilisateur : 10-15 minutes d'annotation**

**Gain de productivité : 90% de réduction du temps**

---

## 2. Objectifs du Projet

### 2.1 Objectifs Fonctionnels

| Objectif | Description | Priorité | Statut |
|----------|-------------|----------|--------|
| **Transcription automatique** | Convertir audio → texte avec timestamps | P0 | ✅ Opérationnel |
| **Annotation intuitive** | Interface familière (Google Docs) | P0 | ✅ Opérationnel |
| **Extraction précise** | Découpe vidéo au dixième de seconde près | P0 | ✅ Opérationnel |
| **Fusion de segments** | Combiner plusieurs passages en une vidéo | P1 | ✅ Opérationnel |
| **Traitement automatique** | Aucune intervention manuelle après annotation | P0 | ✅ Opérationnel |
| **Qualité préservée** | Pas de réencodage (copie stream) | P1 | ✅ Opérationnel |

### 2.2 Objectifs Techniques

- **Scalabilité** : Traiter plusieurs fichiers simultanément
- **Fiabilité** : 99% de taux de réussite d'extraction
- **Performance** : Traitement en moins de 10 minutes par fichier
- **Maintenance** : Architecture modulaire et testable
- **Coût** : Utilisation de services cloud serverless pour optimiser les coûts

### 2.3 Critères de Succès

✅ **Atteints** :
- Transcription avec précision > 90%
- Extraction vidéo avec précision ±0.5 secondes
- Traitement automatique toutes les 5 minutes
- Interface utilisateur sans formation technique requise

---

## 3. Périmètre Fonctionnel

### 3.1 Fonctionnalités Incluses

#### Phase 1 : Transcription (Whisper Automation)
- Upload de fichiers audio/vidéo vers Google Drive
- Transcription automatique avec Whisper AI
- Génération de 5 formats de sortie :
  - `_transcription.txt` : Texte brut
  - `_paragraphs_timestamps` : Paragraphes avec timestamps (M:SS)
  - `_with_timestamps.srt` : Format SRT standard
  - `_word_timestamps.txt` : Timestamps mot par mot
  - `_complete_data.json` : Données complètes incluant segments

#### Phase 2 : Annotation et Extraction (Highlights System)
- Copie manuelle du fichier `_paragraphs_timestamps` vers "Highlighted Files"
- Annotation via Google Docs :
  - Surlignage de texte
  - Ajout de commentaires (s1, s2, s3, etc.)
  - Fusion automatique avec même numéro
- Détection automatique des modifications
- Extraction des timestamps exacts depuis `_complete_data.json`
- Génération d'un fichier Excel de highlights
- Découpe vidéo avec ffmpeg
- Upload automatique des segments vers Google Drive

### 3.2 Formats Supportés

**Entrée (vidéo/audio)** :
- Vidéo : MP4, MOV, AVI, MKV, WebM
- Audio : MP3, M4A, WAV, FLAC, AAC, OGG

**Sortie (segments vidéo)** :
- Format : Identique à la source (copie stream)
- Qualité : Identique à la source (pas de réencodage)
- Nommage : `{commentaire}_{MMSS-MMSS}_{MMSS-MMSS}.ext`

### 3.3 Limitations Connues

- **Taille de fichier** : Limite Google Drive (5 TB théorique, 100 GB pratique)
- **Durée de traitement** : ~30% de la durée vidéo pour transcription
- **Précision transcription** : 90-95% selon qualité audio
- **Langue** : Optimisé pour le français (extensible)
- **Concurrence** : 1 processus Cloud Run à la fois (configurable)

---

## 4. Architecture Technique

### 4.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                      UTILISATEUR                             │
│  Upload → Annotation → Récupération                          │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             ▼                                ▼
┌────────────────────────────┐    ┌────────────────────────────┐
│     GOOGLE DRIVE           │    │    GOOGLE DOCS             │
│  - Stockage fichiers       │◄──►│  - Interface annotation    │
│  - Structure dossiers      │    │  - API commentaires        │
└────────────┬───────────────┘    └────────────────────────────┘
             │
             │ Trigger toutes les 5 min
             ▼
┌────────────────────────────────────────────────────────────┐
│              GOOGLE CLOUD SCHEDULER                         │
│  CRON: */5 * * * * (toutes les 5 minutes)                  │
└────────────┬───────────────────────────────────────────────┘
             │
             │ HTTP POST
             ▼
┌────────────────────────────────────────────────────────────┐
│           GOOGLE CLOUD RUN                                  │
│  Service: highlights-processor                              │
│  Image: gcr.io/PROJECT_ID/highlights-processor             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  highlight_orchestrator_cloud.py                     │  │
│  │  - Détecte nouveaux fichiers                         │  │
│  │  - Orchestre le pipeline                             │  │
│  └────────┬──────────────────┬──────────────────────────┘  │
│           │                  │                              │
│           ▼                  ▼                              │
│  ┌────────────────┐  ┌────────────────────────┐           │
│  │ highlight_     │  │ video_segment_         │           │
│  │ extractor.py   │  │ extractor.py           │           │
│  │ - Lit comments │  │ - Découpe ffmpeg       │           │
│  │ - Match texte  │  │ - Fusionne segments    │           │
│  │ - Excel output │  │ - Upload Drive         │           │
│  └────────────────┘  └────────────────────────┘           │
└────────────────────────────────────────────────────────────┘
             │
             │ Logs
             ▼
┌────────────────────────────────────────────────────────────┐
│          GOOGLE CLOUD LOGGING                               │
│  - Logs d'exécution                                         │
│  - Métriques de performance                                 │
└────────────────────────────────────────────────────────────┘
```

### 4.2 Technologies Utilisées

| Composant | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **Runtime** | Python | 3.11 | Compatibilité librairies ML |
| **IA Transcription** | Whisper AI | Large-v2 | Meilleure précision français |
| **Traitement vidéo** | FFmpeg | 6.0+ | Standard industrie |
| **Stockage** | Google Drive API | v3 | Intégration utilisateur |
| **Interface annotation** | Google Docs API | v1 | Interface familière |
| **Orchestration** | Cloud Run | Gen2 | Serverless, scalable |
| **Scheduling** | Cloud Scheduler | - | CRON managé |
| **Logs** | Cloud Logging | - | Monitoring intégré |
| **Container** | Docker | 24.0+ | Portabilité |
| **Build** | Cloud Build | - | CI/CD intégré GCP |

---

## 5. Flux de Données

### 5.1 Workflow Complet

```
PHASE 1: TRANSCRIPTION (Whisper Automation)
┌─────────────────────────────────────────────────┐
│ 1. Upload vidéo/audio                           │
│    Drive/Files/video.mp4                        │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 2. Détection automatique (Whisper Automation)   │
│    - Télécharge fichier                         │
│    - Lance Whisper AI                           │
│    - Génère transcriptions                      │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 3. Upload résultats                             │
│    Drive/Transcriptions/                        │
│    - video_transcription.txt                    │
│    - video_paragraphs_timestamps ⭐             │
│    - video_with_timestamps.srt                  │
│    - video_word_timestamps.txt                  │
│    - video_complete_data.json                   │
└─────────────────────────────────────────────────┘

PHASE 2: ANNOTATION ET EXTRACTION (Highlights System)
┌─────────────────────────────────────────────────┐
│ 4. Copie manuelle utilisateur                   │
│    Transcriptions/ → Highlighted Files/         │
│    video_paragraphs_timestamps                  │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 5. Annotation Google Docs                       │
│    - Ouvrir fichier                             │
│    - Surligner passages                         │
│    - Ajouter commentaires (s1, s2, s3...)       │
│    - Fermer (auto-save)                         │
└────────────┬────────────────────────────────────┘
             │
             │ Trigger automatique (5 min)
             ▼
┌─────────────────────────────────────────────────┐
│ 6. Détection Cloud Run                          │
│    - Liste fichiers Highlighted Files           │
│    - Détecte nouveaux/modifiés                  │
│    - Filtre fichiers déjà traités               │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 7. Extraction highlights                        │
│    A. Télécharge paragraphs_timestamps          │
│    B. Lit commentaires Google Docs              │
│    C. Trouve complete_data.json                 │
│    D. Match texte → timestamps (sliding window) │
│    E. Génère Excel avec segments                │
│    F. Upload Excel → Drive/Excel Output/        │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 8. Découpe vidéo                                │
│    A. Lit Excel highlights                      │
│    B. Trouve vidéo source dans Files/           │
│    C. Extrait segments avec ffmpeg              │
│    D. Fusionne si même commentaire              │
│    E. Upload → Drive/Segments Videos/           │
└────────────┬────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────┐
│ 9. Résultat final                               │
│    Drive/Segments Videos/video/                 │
│    - s1_0230-0308_0411-0525.mp4                │
│    - s2_1003-1116.mp4                           │
└─────────────────────────────────────────────────┘
```

### 5.2 Structure Google Drive

```
📁 Google Drive (Shared Drive: "Transcription Whisper")
│
├── 📁 Files/                                    [ID: 1A29pkQvrBodU_HxNS8deYt6T27AlmbSe]
│   └── 🎬 video_source.mp4                     (Fichier original uploadé par utilisateur)
│
├── 📁 Transcriptions/                           [ID: 1yHcy9um2_We459w9I0cITwHBGXKTlOJa]
│   ├── 📄 video_source_transcription.txt       (Texte brut)
│   ├── 📄 video_source_paragraphs_timestamps   (Format utilisateur) ⭐
│   ├── 📄 video_source_with_timestamps.srt     (Format SRT)
│   ├── 📄 video_source_word_timestamps.txt     (Timestamps mots)
│   └── 📄 video_source_complete_data.json      (Données complètes) 🔧
│
├── 📁 Highlighted Files/                        [ID: 1-LyCTp_CZUvfd3cufIYEHBYVyWCFxxb9]
│   └── 📄 video_source_paragraphs_timestamps   (Copié par utilisateur, annoté)
│
├── 📁 Excel Output/                             [ID: 1krgRVj3Wp18sNY7cL7PwR2vVUtaX2jCj]
│   └── 📊 video_source_highlights.xlsx         (Métadonnées segments)
│
└── 📁 Segments Videos/                          [ID: 1ly79uNIJBUqxQ5yjVOmtTlISemHTBxiP]
    └── 📁 video_source/                         (Sous-dossier créé automatiquement)
        ├── 🎬 s1_0230-0308_0411-0525.mp4       (Segment fusionné)
        └── 🎬 s2_1003-1116.mp4                 (Segment simple)
```

**Légende** :
- ⭐ = Fichier que l'utilisateur manipule
- 🔧 = Fichier technique utilisé par le système
- 📊 = Fichier intermédiaire de métadonnées

---

## 6. Détails des Composants

### 6.1 Highlight Orchestrator (`highlight_orchestrator_cloud.py`)

**Rôle** : Chef d'orchestre du pipeline d'extraction

**Responsabilités** :
1. **Détection** : Scanner le dossier "Highlighted Files" toutes les 5 minutes
2. **Filtrage** : Exclure les fichiers déjà traités (cache mémoire)
3. **Orchestration** : Coordonner extractor → video cutter → upload
4. **Gestion erreurs** : Retry, logging, notifications

**Points techniques clés** :
```python
# Gestion idempotence (évite retraitement)
processed_files = set()  # Cache mémoire

# Support Shared Drive
supportsAllDrives=True  # Essentiel pour Drive API

# Matching fichiers
# video.mp4 → video_paragraphs_timestamps
# video_paragraphs_timestamps → video_complete_data.json
```

**Configuration** : `/config/highlight_config.json`

### 6.2 Highlight Extractor (`highlight_extractor.py`)

**Rôle** : Extraction des highlights depuis Google Docs et matching avec timestamps

**Algorithme de matching (Sliding Window)** :

**Problème résolu** : Segments courts (4-6 mots) non détectés avec recherche simple

**Solution** :
```python
WINDOW_SIZE = 3  # Concaténer 3 segments consécutifs

# Au lieu de chercher dans un seul segment :
# Segment 190: "On change de base, on..." (4 mots) ❌

# On crée des fenêtres :
# Window[190-192]: "On change de base, on... on change de moi.
#                   Intéressant, hein. Par exemple, les gens." ✅

for seg_idx in range(len(segments)):
    window_segments = segments[seg_idx:seg_idx + WINDOW_SIZE]
    window_text = ' '.join(seg.get('text', '') for seg in window_segments)

    if first_words in normalize_for_search(window_text):
        # Match trouvé! Utiliser le timestamp du segment seg_idx
```

**Normalisation du texte** :
```python
def normalize_for_search(text: str) -> str:
    # Retirer ponctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    # Lowercase
    text = text.lower()
    # Espaces multiples → un seul
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
```

**Format Excel généré** :
| Groupe | Numéro | Texte surligné | Début (M:SS) | Fin (M:SS) | Début (secondes) | Fin (secondes) | Durée (secondes) |
|--------|--------|----------------|--------------|------------|------------------|----------------|------------------|
| s1 | 1 | Donc ça, on peut... | 2:30 | 3:08 | 150.0 | 188.0 | 38.0 |
| s1 | 1 | Parce que c'est... | 4:11 | 5:25 | 251.0 | 325.0 | 74.0 |
| s2 | 2 | Donc on imagine... | 10:03 | 11:11 | 603.0 | 671.0 | 68.0 |

### 6.3 Video Segment Extractor (`video_segment_extractor.py`)

**Rôle** : Découpe et fusion de segments vidéo avec ffmpeg

**Commande ffmpeg optimisée** :
```bash
ffmpeg \
  -accurate_seek \           # Seek précis
  -ss 150.0 \                # Début (AVANT -i) ⚠️
  -i source.mp4 \            # Input
  -t 38.0 \                  # Durée
  -c copy \                  # Pas de réencodage
  -avoid_negative_ts make_zero \  # Fix timestamps
  -y \                       # Overwrite
  output.mp4
```

**Pourquoi `-ss` AVANT `-i` ?**
- ❌ Après `-i` : ffmpeg lit tout jusqu'au timestamp → lent + écran noir possible
- ✅ Avant `-i` : ffmpeg seek directement → rapide + précis

**Fusion de segments** :
```python
# 1. Extraire chaque segment
temp_segment_0.mp4  # 2:30-3:08
temp_segment_1.mp4  # 4:11-5:25

# 2. Créer concat list
file '/abs/path/temp_segment_0.mp4'
file '/abs/path/temp_segment_1.mp4'

# 3. Fusionner
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy output.mp4
```

**Nommage des fichiers** :
```python
# Format: {commentaire}_{MMSS-MMSS}_{MMSS-MMSS}.ext
# Exemple: s1_0230-0308_0411-0525.mp4

def _seconds_to_timecode_short(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}{secs:02d}"  # 0230 = 2min 30sec
```

### 6.4 Drive Manager (`drive_manager.py`)

**Rôle** : Abstraction Google Drive API v3

**Fonctionnalités** :
- **Upload avec retry** : Gestion des timeouts
- **Chunked upload** : Pour gros fichiers (>5MB)
- **Shared Drive support** : `supportsAllDrives=True`
- **Recherche par nom** : Avec correspondance exacte
- **Création de dossiers** : Avec structure hiérarchique

**Exemple d'utilisation** :
```python
drive = DriveManager(credentials_path="config/credentials.json")

# Upload vidéo
drive.upload_file(
    local_path="s1_0230-0525.mp4",
    parent_folder_id="1ly79uNIJBUqxQ5yjVOmtTlISemHTBxiP",
    mime_type="video/mp4"
)

# Création sous-dossier
subfolder_id = drive.create_folder(
    folder_name="Conference_2024",
    parent_id="1ly79uNIJBUqxQ5yjVOmtTlISemHTBxiP"
)
```

---

## 7. Sécurité et Authentification

### 7.1 Service Account GCP

**Fichier** : `config/credentials.json`

**Scopes requis** :
```json
[
  "https://www.googleapis.com/auth/drive",
  "https://www.googleapis.com/auth/documents.readonly"
]
```

**Permissions Drive** :
- Lecture : Files, Transcriptions, Highlighted Files
- Écriture : Excel Output, Segments Videos
- Création : Sous-dossiers dans Segments Videos

**Bonnes pratiques** :
- ✅ Service account dédié (non utilisateur)
- ✅ Principe du moindre privilège
- ✅ Rotation des clés annuelle
- ✅ Credentials.json JAMAIS commité dans Git (.gitignore)
- ✅ Stockage sécurisé dans Cloud Secret Manager (production)

### 7.2 Cloud Run Security

**Configuration** :
```yaml
Security:
  ingress: internal-and-cloud-load-balancing  # Pas d'accès public direct
  authentication: require-authentication      # JWT obligatoire
  service-account: highlights-processor@PROJECT.iam.gserviceaccount.com

Permissions IAM:
  - roles/run.invoker → Cloud Scheduler uniquement
  - roles/logging.logWriter
  - roles/storage.objectViewer (pour GCR)
```

**Endpoints protégés** :
- ❌ Accès public : Bloqué
- ✅ Cloud Scheduler : Autorisé avec JWT
- ✅ gcloud CLI : Autorisé pour déploiement

### 7.3 Données Sensibles

**Données manipulées** :
- Contenu vidéo/audio (potentiellement confidentiel)
- Transcriptions (contenu parlé)
- Commentaires utilisateur

**Protection** :
- ✅ Transit : HTTPS uniquement (GCP standard)
- ✅ Stockage : Google Drive encryption at rest
- ✅ Traitement : Mémoire Cloud Run éphémère (pas de persistance)
- ✅ Logs : Pas de contenu sensible loggé (uniquement métadonnées)

**Conformité** :
- RGPD : Données stockées dans Google Drive (responsabilité utilisateur)
- Données traitées en Europe : `--region=europe-west1`

---

## 8. Déploiement et Infrastructure

### 8.1 Cloud Run Configuration

**Service** : `highlights-processor`

**Spécifications** :
```yaml
Region: europe-west1
CPU: 2 vCPU
Memory: 4 GiB
Timeout: 900s (15 minutes)
Concurrency: 1 (un traitement à la fois)
Min instances: 0 (scale to zero)
Max instances: 1 (pas de parallélisation)
Execution environment: Gen2

Container:
  Image: gcr.io/transcription-whisper-automation/highlights-processor:latest
  Port: 8080

Environment variables:
  GOOGLE_APPLICATION_CREDENTIALS: /app/config/credentials.json
  CONFIG_PATH: /app/config/highlight_config.json
```

**Justifications** :
- **4 GiB mémoire** : ffmpeg + pandas + fichiers temporaires
- **15 min timeout** : Vidéos longues (1h+) + multiples segments
- **Concurrency 1** : Éviter conflits sur fichiers Drive
- **Min 0** : Économie (pas de coûts quand inactif)
- **Max 1** : Budget limité, pas besoin de parallélisme

### 8.2 Cloud Scheduler

**Job** : `highlights-processor-trigger`

**Configuration** :
```yaml
Schedule: "*/5 * * * *"  # Toutes les 5 minutes
Timezone: Europe/Paris
Target: HTTP POST
URL: https://highlights-processor-HASH-ew.a.run.app/process
Auth: OIDC token
Service account: cloud-scheduler@PROJECT.iam.gserviceaccount.com
Retry: 3 attempts, exponential backoff
```

**Pourquoi 5 minutes ?**
- ⚖️ Compromis réactivité / coûts
- ✅ Acceptable pour l'utilisateur (max 10 min d'attente)
- ✅ Évite sur-sollicitation Drive API (quotas)

### 8.3 Docker Image

**Dockerfile** :
```dockerfile
FROM python:3.11-slim

# Installer ffmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copier code
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Exposer port
EXPOSE 8080

# Lancer orchestrator
CMD ["python", "scripts/highlight_orchestrator_cloud.py"]
```

**Build et Push** :
```bash
# Build local
docker build -t highlights-processor .

# Tag pour GCR
docker tag highlights-processor \
  gcr.io/transcription-whisper-automation/highlights-processor:latest

# Push vers GCR
docker push gcr.io/transcription-whisper-automation/highlights-processor:latest
```

**Alternative : Cloud Build** :
```bash
gcloud builds submit --tag gcr.io/transcription-whisper-automation/highlights-processor
```

### 8.4 Commandes de Déploiement

**Déploiement complet** :
```bash
# 1. Authentification service account
gcloud auth activate-service-account \
  --key-file=config/credentials.json

# 2. Build et deploy en une commande
gcloud run deploy highlights-processor \
  --source . \
  --region=europe-west1 \
  --memory=4Gi \
  --cpu=2 \
  --timeout=900 \
  --max-instances=1 \
  --min-instances=0 \
  --concurrency=1 \
  --platform=managed \
  --allow-unauthenticated=false \
  --service-account=highlights-processor@PROJECT.iam.gserviceaccount.com

# 3. Vérifier déploiement
gcloud run services describe highlights-processor --region=europe-west1
```

**Rollback** :
```bash
# Lister les révisions
gcloud run revisions list --service=highlights-processor --region=europe-west1

# Rollback vers révision précédente
gcloud run services update-traffic highlights-processor \
  --to-revisions=highlights-processor-00020-xyz=100 \
  --region=europe-west1
```

---

## 9. Monitoring et Logs

### 9.1 Cloud Logging

**Accès logs** :
```bash
# Logs en temps réel
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=highlights-processor" \
  --limit 50 --format json

# Filtrer par niveau
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit 20
```

**Logs structurés** :
```python
# Dans le code Python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Logs avec contexte
logger.info(f"🔍 Traitement fichier: {file_name}")
logger.warning(f"⚠️ Aucun highlight trouvé dans {file_name}")
logger.error(f"❌ Erreur extraction: {error}")
```

**Logs clés à surveiller** :
- `🎬 X segment(s) vidéo créé(s)` : Succès
- `⚠️ Aucun candidat de début trouvé` : Problème matching
- `❌ Échec extraction segment` : Problème ffmpeg
- `📊 Résultat: X ligne(s)` : Nombre de highlights détectés

### 9.2 Métriques Importantes

**À surveiller** :
- **Taux de succès** : % de fichiers traités sans erreur
- **Durée d'exécution** : Temps moyen par fichier
- **Utilisation mémoire** : Pic durant traitement vidéo
- **Erreurs Drive API** : 404, 403, quotas dépassés
- **Erreurs ffmpeg** : Codec non supporté, fichier corrompu

**Dashboard Cloud Monitoring** :
```yaml
Widgets:
  - Invocations count (5 min)
  - Latency p50, p95, p99
  - Error rate %
  - Memory utilization (max)
  - CPU utilization (max)
```

### 9.3 Alertes Recommandées

```yaml
Alertes:
  - Error rate > 10% pendant 15 min
    → Email admin

  - Memory > 3.5 GiB pendant 5 min
    → Risque OOM, augmenter limite

  - Latency > 10 minutes
    → Timeout imminent

  - Drive API 403/429
    → Quotas dépassés
```

---

## 10. Coûts Estimés

### 10.1 Coûts Google Cloud Platform

**Cloud Run** :
```
Pricing:
- vCPU: $0.00002400 / vCPU-second
- Memory: $0.00000250 / GiB-second
- Requests: $0.40 / million requests

Configuration: 2 vCPU, 4 GiB, 1 exécution de 2 min en moyenne

Calcul par exécution:
- vCPU: 2 × 120s × $0.000024 = $0.00576
- Memory: 4 × 120s × $0.0000025 = $0.0012
- Request: $0.0000004

Total par exécution: ~$0.007

Trigger toutes les 5 min = 12 exec/heure × 24h = 288 exec/jour
Coût avec fichiers à traiter: 10 fichiers/jour × $0.007 = $0.07/jour
Coût avec triggers vides: 278 × $0.001 = $0.278/jour

Total estimé: $10-15/mois (selon activité)
```

**Cloud Scheduler** :
```
Pricing: $0.10 / job / mois (3 jobs gratuits)

1 job = $0.10/mois
```

**Cloud Storage (GCR)** :
```
Image Docker: ~1 GB
Stockage: $0.020 / GB / mois
Coût: $0.02/mois
```

**Cloud Logging** :
```
50 GB/mois gratuits
Au-delà: $0.50 / GB

Estimé: Inclus dans forfait gratuit
```

**Total mensuel estimé : $15-20/mois**

### 10.2 Coûts Google Drive

**Google Workspace** :
- Si compte existant : Inclus (pas de coût additionnel)
- Si nouveau compte : ~$6-12/utilisateur/mois selon plan

**Storage** :
- 15 GB gratuits (compte personnel)
- 30 GB-2 TB selon plan Workspace
- Coût additionnel stockage : $0.20/GB/mois au-delà du quota

**Estimations** :
```
Vidéo 1h = ~500 MB (selon qualité)
10 vidéos/mois = 5 GB source
Transcriptions = ~5 MB total
Segments = ~1 GB (selon extraits)

Total: ~6 GB/mois → Inclus dans forfait standard
```

### 10.3 Optimisations Coûts

**Réductions possibles** :
1. **Scale to Zero** : Déjà implémenté (min instances = 0)
2. **Augmenter intervalle Scheduler** : 10 min au lieu de 5 min → -50% requêtes
3. **Batch processing** : Traiter plusieurs fichiers par exécution
4. **Réduire timeout** : 10 min au lieu de 15 min si suffisant
5. **Mémoire** : Tester avec 2 GiB si vidéos courtes

**Coûts évités** :
- ✅ Pas de VM constamment allumée (~$30-50/mois)
- ✅ Pas de base de données managée (~$10-20/mois)
- ✅ Architecture serverless = pay-per-use

---

## 11. Limitations et Contraintes

### 11.1 Limitations Techniques

| Limitation | Détail | Impact | Mitigation |
|------------|--------|--------|------------|
| **Shared Drive uniquement** | Système conçu pour Shared Drive | Ne fonctionne pas avec "My Drive" | Documenter requis |
| **Concurrence** | 1 exécution Cloud Run à la fois | Pas de traitement parallèle | Augmenter max-instances si besoin |
| **Timeout 15 min** | Cloud Run max timeout | Vidéos très longues (>3h) risquent timeout | Découper vidéos ou augmenter timeout |
| **Mémoire 4 GiB** | Limite mémoire container | Vidéos haute résolution risquent OOM | Utiliser `-c copy` (pas de réencodage) |
| **Matching exact** | Sliding window avec 8 mots | Modifications texte brisent matching | Documenter importance copie exacte |

### 11.2 Limitations Fonctionnelles

**Formats vidéo** :
- ✅ Supportés : MP4, MOV, AVI, MKV (codecs standard)
- ⚠️ Limités : Formats propriétaires, DRM
- ❌ Non supportés : Streams en direct, liens YouTube

**Précision** :
- Transcription : 90-95% selon qualité audio
- Timestamps : ±0.5 secondes (limite keyframes vidéo)
- Matching texte : Nécessite minimum 8 mots consécutifs

**Langues** :
- Optimisé : Français
- Supporté : Whisper supporte 50+ langues
- Limitation : Commentaires "s1, s2" en anglais uniquement

### 11.3 Contraintes Opérationnelles

**Utilisateur** :
- Doit copier manuellement `_paragraphs_timestamps` vers "Highlighted Files"
- Doit attendre 5-10 minutes après annotation
- Ne doit pas modifier le texte de la transcription (risque cassage matching)
- Ne doit pas supprimer la vidéo source avant extraction

**Système** :
- Nécessite ffmpeg installé dans container
- Dépend de Google Drive API (quotas, disponibilité)
- Nécessite service account avec permissions appropriées
- Google Docs API : Max 100 commentaires par document (limite pratique)

---

## 12. Évolutions Futures

### 12.1 Améliorations Prioritaires (P0)

**1. Interface Web Simple**
- **Description** : Dashboard pour voir statut des traitements
- **Fonctionnalités** :
  - Upload direct de fichiers
  - Suivi temps réel des transcriptions
  - Historique des extraits créés
  - Téléchargement direct des vidéos
- **Effort** : 2-3 semaines
- **Bénéfice** : UX améliorée, moins de manipulation Drive

**2. Notifications Email**
- **Description** : Email automatique quand extraits prêts
- **Implémentation** : SendGrid ou Gmail API
- **Template** :
  ```
  Sujet: ✅ Vos extraits vidéo sont prêts!

  Bonjour,

  Les extraits vidéo de "Conference_2024.mp4" sont prêts :
  - s1_0230-0525.mp4 (3 min 15s)
  - s2_1003-1116.mp4 (1 min 13s)

  Accéder: [Lien Drive]
  ```
- **Effort** : 2-3 jours
- **Bénéfice** : Pas besoin de vérifier manuellement

**3. Copie Automatique vers Highlighted Files**
- **Description** : Éliminer l'étape manuelle de copie
- **Implémentation** : Trigger sur dossier Transcriptions
- **Effort** : 1 semaine
- **Bénéfice** : Workflow plus fluide

### 12.2 Fonctionnalités Avancées (P1)

**4. Preview des Segments**
- **Description** : Générer thumbnails + aperçu avant extraction
- **Technologie** : ffmpeg pour captures d'écran
- **Effort** : 1-2 semaines

**5. Multi-formats Export**
- **Description** : Exporter en différentes résolutions
- **Options** : 1080p, 720p, 480p, audio seul
- **Effort** : 1 semaine

**6. Sous-titres Automatiques**
- **Description** : Incruster sous-titres dans les segments
- **Format** : SRT overlay avec ffmpeg
- **Effort** : 1 semaine

**7. Annotations Avancées**
- **Description** : Support de tags en plus de s1, s2
- **Exemples** : `intro`, `demo`, `conclusion`
- **Effort** : 2 semaines

### 12.3 Optimisations Techniques (P2)

**8. Cache Intelligent**
- **Description** : Ne pas recalculer highlights identiques
- **Implémentation** : Hash du contenu + metadata DB
- **Bénéfice** : -50% temps traitement pour réannotations

**9. Traitement Parallèle**
- **Description** : Plusieurs Cloud Run instances
- **Configuration** : max-instances=5 avec lock par fichier
- **Bénéfice** : x5 débit

**10. Compression Vidéo Optionnelle**
- **Description** : Réencodage pour réduire taille
- **Options** : H.265, VP9, paramètres qualité
- **Effort** : 1 semaine

**11. Support Multi-langues**
- **Description** : Détection automatique langue + transcription
- **Implémentation** : Whisper auto-detect
- **Effort** : 3-5 jours

### 12.4 Analytics et Reporting (P3)

**12. Dashboard Métriques**
- Nombre de vidéos traitées
- Temps moyen de traitement
- Top formats vidéo utilisés
- Durée moyenne des segments

**13. Export Analytics**
- Rapport mensuel PDF
- Statistiques d'utilisation
- Suggestions d'optimisation

---

## 13. Support et Maintenance

### 13.1 Procédures de Dépannage

**Problème : Vidéos non générées**

**Diagnostic** :
```bash
# 1. Vérifier logs Cloud Run
gcloud logging read "resource.type=cloud_run_revision" \
  --limit 50 | grep "ERROR\|WARNING"

# 2. Vérifier fichier Excel créé
gcloud drive list --folder "Excel Output"

# 3. Vérifier présence vidéo source
gcloud drive list --folder "Files" | grep "nom_fichier"
```

**Causes fréquentes** :
1. ❌ Fichier `_paragraphs_timestamps` pas dans "Highlighted Files"
2. ❌ Nom fichier transcription ≠ nom vidéo source
3. ❌ Commentaires mal formatés (S1 au lieu de s1, espaces)
4. ❌ Vidéo source supprimée ou déplacée
5. ❌ Délai propagation Drive API (attendre 5-10 min)

**Solutions** :
1. ✅ Vérifier checklist documentation utilisateur
2. ✅ Forcer redéclenchement Cloud Run
3. ✅ Vérifier permissions service account
4. ✅ Contacter support avec logs

**Problème : Écran noir dans vidéos**

**Diagnostic** :
- Vérifier ordre paramètres ffmpeg (`-ss` avant `-i`)
- Tester extraction locale avec même commande

**Solution** : Redéployer avec fix ffmpeg (déjà implémenté)

**Problème : Timeout Cloud Run**

**Diagnostic** :
```bash
# Vérifier durée dernières exécutions
gcloud logging read "resource.type=cloud_run_revision" \
  --format="table(timestamp, jsonPayload.message)" | grep "Durée"
```

**Solutions** :
1. ✅ Augmenter timeout : `--timeout=1200` (20 min)
2. ✅ Optimiser : découper vidéo en segments plus petits
3. ✅ Augmenter mémoire/CPU

### 13.2 Maintenance Régulière

**Hebdomadaire** :
- ✅ Vérifier logs erreurs
- ✅ Contrôler utilisation stockage Drive
- ✅ Vérifier état Cloud Scheduler (actif)

**Mensuel** :
- ✅ Analyser métriques Cloud Run
- ✅ Vérifier quotas GCP
- ✅ Audit logs sécurité
- ✅ Backup configuration

**Trimestriel** :
- ✅ Update dépendances Python (`requirements.txt`)
- ✅ Update image Docker base
- ✅ Revue permissions IAM
- ✅ Test plan de reprise après incident

**Annuel** :
- ✅ Rotation clés service account
- ✅ Audit complet sécurité
- ✅ Revue architecture
- ✅ Optimisation coûts

### 13.3 Contacts et Escalade

**Support Technique** :
- Email : [à définir]
- Documentation : `/GUIDE_UTILISATEUR_COMPLET.md`
- FAQ : Section "Questions Fréquentes" du guide

**Escalade** :
- Niveau 1 : Vérification checklist utilisateur
- Niveau 2 : Analyse logs Cloud Run
- Niveau 3 : Debug code + déploiement fix

**SLA cible** :
- Réponse : < 4 heures ouvrées
- Résolution bug critique : < 24 heures
- Résolution bug mineur : < 1 semaine

---

## 14. Annexes Techniques

### 14.1 Requirements.txt

```txt
# Google Cloud & Drive
google-api-python-client==2.108.0
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-auth-httplib2==0.2.0

# Data processing
pandas==2.1.4
openpyxl==3.1.2

# Server
flask==3.0.0
gunicorn==21.2.0

# Utils
python-dateutil==2.8.2
requests==2.31.0
```

### 14.2 Configuration JSON

**`/config/highlight_config.json`** :
```json
{
  "drive_folders": {
    "highlighted_files": "1-LyCTp_CZUvfd3cufIYEHBYVyWCFxxb9",
    "source_files": "1A29pkQvrBodU_HxNS8deYt6T27AlmbSe",
    "transcriptions": "1yHcy9um2_We459w9I0cITwHBGXKTlOJa",
    "excel_output": "1krgRVj3Wp18sNY7cL7PwR2vVUtaX2jCj",
    "segments_output": "1ly79uNIJBUqxQ5yjVOmtTlISemHTBxiP"
  },
  "processing": {
    "window_size": 3,
    "min_words": 8,
    "max_segment_duration": 600
  },
  "ffmpeg": {
    "codec": "copy",
    "accurate_seek": true,
    "avoid_negative_ts": "make_zero"
  }
}
```

### 14.3 Structure du Projet

```
whisper-drive-automation/
├── Dockerfile                          # Image Docker Cloud Run
├── requirements.txt                    # Dépendances Python
├── .gitignore                          # Exclusions Git
│
├── config/
│   ├── credentials.json                # Service account (NON commité)
│   └── highlight_config.json           # Configuration dossiers Drive
│
├── src/
│   ├── __init__.py
│   ├── drive_manager.py                # Abstraction Google Drive API
│   ├── highlight_extractor.py          # Extraction highlights + matching
│   └── video_segment_extractor.py      # Découpe vidéo ffmpeg
│
├── scripts/
│   ├── highlight_orchestrator_cloud.py # Orchestrateur Cloud Run
│   ├── test_local.py                   # Tests locaux
│   └── deploy.sh                       # Script déploiement
│
├── tests/
│   ├── test_highlight_extractor.py
│   ├── test_video_extractor.py
│   └── fixtures/
│       ├── sample_paragraphs.txt
│       ├── sample_complete_data.json
│       └── sample_video.mp4
│
└── docs/
    ├── GUIDE_UTILISATEUR_COMPLET.md    # Guide utilisateur
    ├── DOCUMENT_CADRAGE.md             # Ce document
    └── ARCHITECTURE.md                 # Schémas détaillés
```

### 14.4 Commandes Utiles

**Développement local** :
```bash
# Installer dépendances
pip install -r requirements.txt

# Test extraction locale
python scripts/test_local.py \
  --paragraphs "path/to/_paragraphs_timestamps" \
  --complete-data "path/to/_complete_data.json" \
  --video "path/to/source.mp4"

# Docker build local
docker build -t highlights-processor .
docker run -p 8080:8080 \
  -v $(pwd)/config:/app/config \
  highlights-processor

# Test endpoint
curl -X POST http://localhost:8080/process
```

**Cloud Run** :
```bash
# Déploiement rapide
gcloud run deploy highlights-processor --source .

# Logs temps réel
gcloud logging tail "resource.type=cloud_run_revision"

# Déclencher manuellement
gcloud scheduler jobs run highlights-processor-trigger

# Lister révisions
gcloud run revisions list --service=highlights-processor

# Supprimer anciennes révisions
gcloud run revisions delete highlights-processor-00010-xyz
```

**Cloud Scheduler** :
```bash
# Vérifier état
gcloud scheduler jobs describe highlights-processor-trigger

# Pause
gcloud scheduler jobs pause highlights-processor-trigger

# Reprendre
gcloud scheduler jobs resume highlights-processor-trigger

# Modifier fréquence
gcloud scheduler jobs update http highlights-processor-trigger \
  --schedule="*/10 * * * *"  # Toutes les 10 min
```

### 14.5 Tests et Validation

**Test Checklist** :

- [ ] **Test matching simple** : 1 commentaire s1, 1 segment
- [ ] **Test matching fusion** : 1 commentaire s1, 2 segments
- [ ] **Test segments courts** : Segments < 8 mots
- [ ] **Test segments longs** : Segments > 10 paragraphes
- [ ] **Test ponctuation** : Texte avec ... , ; : !
- [ ] **Test majuscules** : Texte avec variations casse
- [ ] **Test espaces** : Espaces multiples, newlines
- [ ] **Test vidéo courte** : < 5 minutes
- [ ] **Test vidéo longue** : > 1 heure
- [ ] **Test formats** : MP4, MOV, MKV
- [ ] **Test écran noir** : Vérifier début vidéo propre
- [ ] **Test fusion segments** : Vérifier continuité audio

**Tests d'intégration** :
```bash
# Test complet end-to-end
pytest tests/test_integration.py -v

# Test avec fixture réelle
python scripts/test_local.py \
  --paragraphs "tests/fixtures/sample_paragraphs.txt" \
  --complete-data "tests/fixtures/sample_complete_data.json" \
  --video "tests/fixtures/sample_video.mp4"
```

### 14.6 Glossaire Technique

| Terme | Définition |
|-------|-----------|
| **Segment** | Unité de transcription (phrase/paragraphe) avec timestamp début/fin |
| **Highlight** | Passage de texte surligné par l'utilisateur avec commentaire |
| **Sliding Window** | Technique de concaténation de segments consécutifs pour matching |
| **Stream Copy** | Copie directe flux vidéo sans réencodage (`-c copy` dans ffmpeg) |
| **Keyframe** | Image complète dans vidéo compressée (I-frame) |
| **Accurate Seek** | Option ffmpeg pour seek précis au frame près |
| **Shared Drive** | Drive partagé Google Workspace (vs My Drive individuel) |
| **Service Account** | Compte robot GCP pour authentification automatisée |
| **Cloud Run** | Plateforme serverless Google Cloud pour containers |
| **Idempotence** | Propriété garantissant qu'un traitement multiple produit le même résultat |

---

## 📌 Conclusion

Le système **Whisper Drive Automation** répond efficacement au besoin d'extraction automatique de segments vidéo à partir de transcriptions. L'architecture serverless combinée à l'interface familière de Google Docs offre une solution :

✅ **Productive** : 90% de réduction du temps de traitement
✅ **Fiable** : Pipeline robuste avec gestion d'erreurs
✅ **Économique** : ~$15-20/mois en coûts d'infrastructure
✅ **Scalable** : Prête à évoluer selon les besoins
✅ **Maintenable** : Code modulaire et bien documenté

**Statut actuel** : ✅ Opérationnel en production

**Prochaines étapes recommandées** :
1. Interface web pour suivi temps réel
2. Notifications email automatiques
3. Élimination étape manuelle de copie fichier

---

**Document maintenu par** : Équipe Technique
**Dernière mise à jour** : Janvier 2024
**Version** : 1.0
**Contact** : [à définir]
