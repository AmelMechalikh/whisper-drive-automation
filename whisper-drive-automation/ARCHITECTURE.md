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

## État actuel (2026-01-12)

❌ **INCORRECT**: Orchestrateur déployé sur VM (tourne 24/7)
✅ **CORRECT**: Worker déployé sur VM

**À FAIRE:**
1. Déployer orchestrateur sur Cloud Run
2. Configurer Cloud Scheduler
3. Arrêter l'orchestrateur sur la VM
