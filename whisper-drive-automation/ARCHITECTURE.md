# Architecture du Système Highlights

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

## État actuel (2026-01-23)

✅ **Cloud Run**: Orchestrateur déployé (léger, sans torch)
✅ **VM Worker**: Découpe vidéos (sans sous-titres)
🔜 **VM Subtitles**: À créer si besoin sous-titres

**Derniers fixes:**
1. ✅ Suppression import VideoSegmentExtractor de l'orchestrator
2. ✅ Filtrage server-side des _paragraphs_timestamps
3. ✅ Création automatique de jobs pour nouveaux fichiers
