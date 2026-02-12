# Architecture du Système

> **Note:** Ce document décrit l'architecture complète du système incluant :
> - **Système de highlights** (extraction de segments vidéo)
> - **Système de transcription** (audio → texte avec Whisper)

---

# 🎯 Système de Transcription (Whisper)

## Architecture ACTUELLE (2026-02) - RunPod GPU Direct

```
┌─────────────────────────────────────────────────────────────────┐
│                        GOOGLE DRIVE                              │
│  📁 source_files/ ← Fichiers audio/vidéo à transcrire           │
│  📁 transcriptions/ ← Transcriptions générées (.txt, .srt...)   │
└─────────────────────────────────────────────────────────────────┘
                    ↑                           ↓
                    │                           │
         ┌──────────┴──────────┐    ┌──────────┴──────────┐
         │   CLOUD SCHEDULER    │    │                     │
         │  (toutes les 5 min)  │    │                     │
         └──────────┬──────────┘    │                     │
                    │                │                     │
                    ↓                │                     │
         ┌─────────────────────┐    │                     │
         │    CLOUD RUN        │    │                     │
         │  whisper-automation │    │                     │
         │                     │    │                     │
         │ 1. Scan nouveaux    │    │                     │
         │    fichiers         │    │                     │
         │ 2. Upload → GCS     │    │                     │
         │ 3. Call RunPod API  │────┘                     │
         │ 4. Upload résultats │                          │
         └─────────────────────┘                          │
                    ↓                                     │
         ┌─────────────────────┐                         │
         │   RUNPOD GPU        │                         │
         │  (Serverless)       │                         │
         │                     │                         │
         │ - Whisper large-v3  │                         │
         │ - RTX 4090/A100     │                         │
         │ - ~30s pour 5min    │                         │
         └─────────────────────┘
```

### Workflow de transcription

```python
1. Cloud Scheduler trigger toutes les 5 minutes
2. Cloud Run (whisper-automation):
   - Scan source_files/ pour nouveaux fichiers
   - Vérifie si déjà transcrit (skip si oui)
   - Pour chaque nouveau fichier:
     a. Upload audio → GCS temp bucket (URL signée 1h)
     b. Call RunPod API avec audio_url
     c. Poll job status jusqu'à completion
     d. Récupère résultats (segments, timestamps)
     e. Génère tous les formats:
        - transcription.txt
        - with_timestamps.srt
        - word_timestamps.txt
        - paragraphs_timestamps (Google Doc)
        - complete_data.json
     f. Upload vers Drive transcriptions/
3. Aucune VM requise ✅
```

### Configuration (highlight_config.json)

```json
{
  "transcription_backend": {
    "provider": "gpu_runpod",
    "gpu_runpod": {
      "device": "cuda",
      "model": "large-v3-turbo",
      "api_endpoint": "https://api.runpod.ai/v2/XXXXX",
      "api_key_env": "RUNPOD_API_KEY",
      "timeout_seconds": 600,
      "max_retries": 3
    }
  }
}
```

### Coûts (transcription)

| Composant | Coût/heure | Usage typique |
|-----------|------------|---------------|
| Cloud Run whisper-automation | Gratuit (free tier) | 5 min toutes les 5 min |
| RunPod GPU (RTX 4090) | $0.26/hr | ~30s par 5min audio |
| GCS Storage | $0.02/GB/mois | Temp files (auto-delete 1j) |

**Coût total: ~$0.01 par heure d'audio transcrit**

---

## Architecture OBSOLÈTE ⚠️ (VM-based) - Désuète depuis 2026-01

> **Cette architecture n'est plus utilisée.** Elle est gardée pour référence historique.

### Ancien système (CPU local sur VM)

```
┌─────────────────────────────────────────┐
│         GOOGLE DRIVE                     │
│  📁 source_files/ ← Audio/vidéo          │
│  📁 queue/ ← Jobs JSON                   │
│  📁 transcriptions/ ← Résultats          │
└─────────────────────────────────────────┘
            ↓                      ↑
┌─────────────────────┐   ┌──────────────┐
│   CLOUD RUN         │   │   VM GCP     │
│  (Orchestrateur)    │   │   Worker     │
│                     │   │              │
│ 1. Scan fichiers    │   │ 1. Poll jobs │
│ 2. Crée jobs JSON   │   │ 2. Whisper   │
│ 3. Allume VM        │──→│    (CPU)     │
└─────────────────────┘   │ 3. Upload    │
                          │ 4. Shutdown  │
                          └──────────────┘
```

### Pourquoi obsolète ?

| Critère | Ancien (VM) | Nouveau (RunPod) |
|---------|-------------|------------------|
| **Vitesse** | ~10 min pour 5 min audio | ~30s pour 5 min audio |
| **Qualité** | Base model (moyenne) | Large-v3 (excellente) |
| **Coût** | VM toujours allumée $20/mois | Serverless $5/mois |
| **Complexité** | VM + queue + jobs | Direct API call |
| **Maintenance** | VM à gérer | Serverless (aucune) |

---

# 🎬 Système de Highlights (Extraction vidéo)

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                        GOOGLE DRIVE                              │
│  📁 transcriptions/ ← Documents avec 🎬 READY 🎬                │
│  📁 queue_highlights/ ← Fichiers JOB (.json)                    │
│  📁 excel_output/ ← Excel générés                               │
│  📁 segments_output/ ← Vidéos découpées                         │
└─────────────────────────────────────────────────────────────────┘
                    ↑                           ↑
                    │                           │
         ┌──────────┴──────────┐    ┌──────────┴──────────┐
         │   CLOUD SCHEDULER    │    │                     │
         │  (toutes les 5-10min)│    │                     │
         └──────────┬──────────┘    │                     │
                    │                │                     │
                    ↓                │                     │
         ┌─────────────────────┐    │                     │
         │    CLOUD RUN        │    │                     │
         │  (Orchestrateur)    │    │                     │
         │                     │    │                     │
         │ 1. Scan READY       │    │                     │
         │ 2. Crée JOBs        │    │                     │
         │ 3. Allume VM        │────┘                     │
         └─────────────────────┘                          │
                                                          │
                                   ┌──────────────────────┘
                                   │
                                   ↓
                        ┌─────────────────────┐
                        │   VM GCP (Worker)   │
                        │                     │
                        │ 1. Traite JOBs      │
                        │ 2. Génère Excel     │
                        │ 3. Découpe vidéos   │
                        │ 4. Auto-shutdown    │
                        └─────────────────────┘
```

## Composants

### 1. Cloud Scheduler
- **Rôle**: Déclenche l'orchestrateur périodiquement
- **Fréquence**: Toutes les 5-10 minutes
- **Action**: Appelle Cloud Run endpoint

### 2. Cloud Run (Orchestrateur)
- **Fichier**: `scripts/highlight_orchestrator_cloud.py`
- **Mode**: API Flask (HTTP endpoint)
- **Coût**: ❌ GRATUIT (serverless, ne tourne que quand appelé)

**Workflow:**
```python
1. Receive HTTP call from Cloud Scheduler
2. Scan dossier transcriptions/ (Shared Drive)
   - Cherche fichiers avec 🎬 READY 🎬
   - Ignore fichiers avec 🎬 PROCESSED 🎬
3. Pour chaque fichier READY:
   - Crée un fichier JOB (.json) dans queue_highlights/
   - JOB contient: document_id, complete_json_id, video_id
4. Si JOBs créés:
   - Allume la VM via Compute Engine API
5. Retourne status: { "jobs_created": N }
```

### 3. VM GCP (Worker)
- **Fichier**: `scripts/highlights_vm_worker.py`
- **Mode**: Loop continu (scan toutes les 60s)
- **Coût**: 💰 Payant SEULEMENT quand allumée

**Workflow:**
```python
1. Démarre automatiquement quand allumée par Cloud Run
2. Loop infini:
   - Scan queue_highlights/ pour fichiers JOB (.json)
   - Si JOBs trouvés:
     a. Traite chaque JOB:
        - Extrait timestamps avec inline markers
        - Génère Excel dans excel_output/
        - Découpe vidéo en segments
        - Upload segments dans segments_output/
     b. Supprime le fichier JOB
     c. Marque document comme 🎬 PROCESSED 🎬
   - Si AUCUN JOB pendant 10 minutes:
     - Auto-shutdown (économie coûts)
3. Utilise ffmpeg pour découper vidéos
```

## Format des fichiers

### Fichier JOB (.json)
```json
{
  "document_id": "1jxJi6WQj...",
  "complete_json_id": "165C8_Z7t...",
  "video_id": "1A29pk...",
  "created_at": "2026-01-12T16:00:00Z"
}
```

### Document avec marqueurs inline
```
🎬 READY 🎬

Transcription du contenu...

🎬 S1 🎬
Texte du premier segment highlight...
🎬 /S1 🎬

🎬 S2 🎬
Texte du deuxième segment...
🎬 /S2 🎬

🎬 PROCESSED 🎬  ← Ajouté automatiquement quand terminé
```

## Dossiers Google Drive

| Dossier | ID | Usage |
|---------|----|----- |
| **transcriptions** | `1yHcy9um2_We459w9I0cITwHBGXKTlOJa` | Documents avec READY |
| **queue_highlights** | `1Dc5kkTvBOSYXuB103vAwYHTpPAsW8G9Q` | Fichiers JOB |
| **excel_output** | `1krgRVj3Wp18sNY7cL7PwR2vVUtaX2jCj` | Excel générés |
| **segments_output** | `1ly79uNIJBUqxQ5yjVOmtTlISemHTBxiP` | Vidéos découpées |
| **source_files** | `1A29pkQvrBodU_HxNS8deYt6T27AlmbSe` | Vidéos sources |

## Économie de coûts

**Avant (mauvaise architecture):**
- VM allumée 24/7 → 💰💰💰 ~$50-100/mois

**Après (bonne architecture):**
- Cloud Run: GRATUIT (dans free tier)
- VM: Allumée seulement pendant traitement → 💰 ~$5-10/mois
- **Économie: ~90%**

## Déploiement

### Cloud Run
```bash
./scripts/deploy_to_cloud_run.sh
```

### Cloud Scheduler
```bash
gcloud scheduler jobs create http highlights-orchestrator \
  --schedule="*/10 * * * *" \
  --uri="https://highlights-XXXXX.run.app/process" \
  --http-method=POST
```

### VM Worker
```bash
./scripts/deploy_highlights_to_vm.sh
```

## Isolation des dépendances (IMPORTANT)

### ⚠️ Problème identifié (2026-01-23)

**Symptôme**: Cloud Run crashe avec SIGABRT lors du scan de fichiers
```
[SSL] record layer failure (_ssl.c:2590)
free(): invalid next size (normal)
Uncaught signal: 6, pid=2, tid=7
```

**Cause**: `VideoSegmentExtractor` charge des bibliothèques lourdes:
- `torch` (PyTorch - ~2GB)
- `torchaudio`
- `whisperx` (pour sous-titres)
- `numpy`, `pandas`

**Impact**:
- Mémoire excessive dans Cloud Run (serverless)
- Corruption mémoire OpenSSL sous charge
- Crash pendant appels API Google Drive

### ✅ Solution: Séparation des responsabilités

| Composant | Dépendances | Rôle |
|-----------|-------------|------|
| **Cloud Run Orchestrator** | pandas, google-api-python-client | Scan Drive, crée Excel, génère jobs |
| **VM Worker (actuelle)** | ffmpeg, pandas | Découpe vidéos (SANS sous-titres) |
| **VM Subtitles (future)** | torch, whisperx, ffmpeg | Génère sous-titres brûlés |

### 🚀 Architecture future (sous-titres)

```
Cloud Run Orchestrator
    │
    ├─> Crée JOB (type: "segments")      ──> VM Worker (vidéos simples)
    │
    └─> Crée JOB (type: "subtitles")     ──> VM Subtitles (avec whisperx)
```

**Avantages**:
- Cloud Run léger et stable
- VM Worker rapide (pas de torch)
- VM Subtitles isolée (coûts seulement si sous-titres demandés)
- Pas de mélange de dépendances conflictuelles

### 📝 Notes implémentation

**NE JAMAIS faire**:
```python
# ❌ DANS CLOUD RUN - PROVOQUE CRASHES
from video_segment_extractor import VideoSegmentExtractor  # Charge torch!
```

**Toujours faire**:
```python
# ✅ DANS CLOUD RUN - Léger
from highlight_extractor import HighlightExtractor  # Pandas seulement
```

**Pour sous-titres futurs**:
- Créer `subtitles_vm_worker.py` séparé
- Installer torch/whisperx UNIQUEMENT sur cette VM
- Job JSON avec flag: `"add_subtitles": true`

## État actuel (2026-02-06)

### Système de transcription
✅ **Cloud Run whisper-automation**: Transcription directe via RunPod GPU
✅ **RunPod Serverless**: Large-v3-turbo sur RTX 4090
✅ **GCS Bucket**: Stockage temporaire audio (auto-delete 1j)
❌ **VM Worker CPU**: Obsolète, désactivé

### Système de highlights
✅ **Cloud Run highlights-orchestrator**: Scan documents READY (léger, sans torch)
✅ **VM Worker highlights**: Découpe vidéos (sans sous-titres)
🔜 **VM Subtitles**: À créer si besoin sous-titres brûlés

**Architecture actuelle:**
- **Transcription:** Cloud Run → RunPod API → Drive (serverless, rapide)
- **Highlights:** Cloud Run → VM Worker → Drive (VM on-demand)

**Dernières évolutions:**
1. ✅ Migration vers RunPod GPU pour transcriptions (2026-01)
2. ✅ Suppression VM CPU transcription (économies + vitesse)
3. ✅ Backend abstraction layer (facile de changer)
4. ✅ Configuration unifiée (highlight_config.json)
