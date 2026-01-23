# TODO: VM Dédiée pour Sous-titres

## Context

Actuellement, le code de sous-titrage avec torch/whisperx est dans `VideoSegmentExtractor` mais:
- ❌ Crash Cloud Run quand importé (bibliothèques trop lourdes)
- ❌ Mélange responsabilités (découpe vidéo + IA pour sous-titres)
- ❌ Coûts élevés si VM tourne avec torch chargé alors qu'on fait juste découper

## Objectif

Créer une **VM séparée** pour générer des sous-titres, activée uniquement sur demande.

## Architecture cible

```
┌─────────────────────────────────────────────────────────────┐
│                    GOOGLE DRIVE                              │
│  📁 queue_segments/     ← Jobs découpe simple               │
│  📁 queue_subtitles/    ← Jobs découpe + sous-titres        │
│  📁 segments_output/    ← Vidéos finales                    │
└─────────────────────────────────────────────────────────────┘
                ↑                               ↑
                │                               │
    ┌───────────┴─────────┐       ┌────────────┴──────────┐
    │  VM Worker          │       │  VM Subtitles         │
    │  (highlights-vm)    │       │  (subtitles-vm)       │
    │                     │       │                       │
    │  • ffmpeg           │       │  • torch              │
    │  • pandas           │       │  • whisperx           │
    │  • Découpe rapide   │       │  • ffmpeg             │
    │  • PAS de torch     │       │  • Sous-titres IA     │
    └─────────────────────┘       └───────────────────────┘
```

## Étapes d'implémentation

### Phase 1: Extraction du code (PRIORITAIRE)

- [ ] Créer `src/subtitle_generator.py`
  - Extraire la logique WhisperX de `VideoSegmentExtractor`
  - Méthodes: `generate_subtitles()`, `burn_subtitles_to_video()`
  - Garder isolation complète (pas d'import dans code léger)

- [ ] Modifier `VideoSegmentExtractor`
  - Supprimer `import torch` (ligne 15)
  - Supprimer `self.whisperx_model`, `self.whisperx_align_model`
  - Garder uniquement découpe ffmpeg simple
  - Paramètre `add_subtitles` → deprecated (log warning)

### Phase 2: Worker Subtitles

- [ ] Créer `scripts/subtitles_vm_worker.py`
  ```python
  # Workflow:
  # 1. Scan queue_subtitles/
  # 2. Pour chaque job:
  #    - Download video from Drive
  #    - Download paragraphs_timestamps.txt
  #    - Generate subtitles with WhisperX
  #    - Burn subtitles with ffmpeg
  #    - Upload to segments_output/
  #    - Mark as PROCESSED
  # 3. Auto-shutdown after 10 min idle
  ```

- [ ] Créer VM GCP séparée
  ```bash
  gcloud compute instances create subtitles-worker-vm \
    --zone=europe-west1-b \
    --machine-type=n1-standard-4 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --image-family=pytorch-latest-gpu \
    --boot-disk-size=50GB
  ```

- [ ] Script de déploiement: `scripts/deploy_subtitles_to_vm.sh`

### Phase 3: Orchestrator

- [ ] Modifier `highlight_orchestrator_cloud.py`
  - Ajouter détection si sous-titres demandés (tag `🎬 SUBTITLES 🎬` ?)
  - Créer job dans `queue_subtitles/` si demandé
  - Créer job dans `queue_segments/` sinon
  - Allumer VM appropriée (compute API)

### Phase 4: Configuration

- [ ] Ajouter dans `highlight_config.json`:
  ```json
  {
    "drive_folders": {
      "queue_segments": "ID_FOLDER",
      "queue_subtitles": "ID_FOLDER"
    },
    "vm_instances": {
      "segments_worker": "highlights-worker-vm",
      "subtitles_worker": "subtitles-worker-vm"
    }
  }
  ```

## Dépendances par composant

### Cloud Run Orchestrator
```
google-api-python-client
google-cloud-compute
pandas
openpyxl
```

### VM Worker (segments)
```
google-api-python-client
google-cloud-storage
pandas
openpyxl
# PAS de torch, whisperx, torchaudio
```

### VM Subtitles (nouveau)
```
google-api-python-client
google-cloud-storage
torch
torchaudio
whisperx
pandas
ffmpeg-python
```

## Coûts estimés

| VM | Type | Coût/h | Usage typique | Coût/mois |
|----|------|--------|---------------|-----------|
| Segments | n1-standard-2 | $0.10 | 2h/mois | ~$0.20 |
| Subtitles | n1-standard-4 + GPU T4 | $0.50 | 0h/mois* | $0 |

*Activée seulement si sous-titres demandés

## Critères de succès

- ✅ Cloud Run stable (pas de crash torch)
- ✅ VM Segments rapide (< 30s par découpe)
- ✅ VM Subtitles isolée (coûts = 0 si pas utilisée)
- ✅ Code propre (séparation concerns)

## Risques

⚠️ **Double facturation**: Si on oublie d'éteindre VM Subtitles
→ Solution: Auto-shutdown après 10 min + alertes billing

⚠️ **Dépendances conflictuelles**: torch vs autres libs
→ Solution: Environnements séparés (VMs différentes)

## Notes

- Pas urgent si sous-titres pas demandés actuellement
- Permet scalabilité future (pods K8s plus tard)
- Architecture microservices propre

## Décision: 2026-01-23

**Status**: TODO (basse priorité)
**Trigger**: Seulement si besoin sous-titres brûlés
**Alternative**: Utiliser service externe (Rev.ai, Descript) si volume faible
