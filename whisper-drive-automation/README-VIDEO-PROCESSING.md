# Système de Découpage Vidéo - Guide d'Utilisation

## Vue d'Ensemble

Ce système permet de découper automatiquement des vidéos/audios en segments basés sur des timestamps extraits depuis des commentaires Google Docs.

**Workflow complet**:
```
Google Doc annoté
     ↓
Extraction highlights + timestamps
     ↓
Génération fichier Excel
     ↓
Découpage vidéo en segments
     ↓
Fusion segments d'un même groupe
     ↓
Upload dans Drive (sous-dossiers)
```

## Prérequis

### 1. FFmpeg

**Installation**:
```bash
# macOS (Homebrew)
brew install ffmpeg

# Vérification
ffmpeg -version
ffprobe -version
```

### 2. Python & Dépendances

```bash
pip install -r requirements.txt
```

Dépendances clés:
- `pandas` - Lecture/écriture Excel
- `openpyxl` - Format XLSX
- `google-api-python-client` - API Google Drive

### 3. Configuration Drive

**Fichier**: `config/highlight_config.json`

```json
{
  "drive_folders": {
    "source_files": "FOLDER_ID",      // Dossier Medias (vidéos/audios sources)
    "excel_output": "FOLDER_ID",      // Dossier avec fichiers Excel de highlights
    "segments_output": "FOLDER_ID"    // Dossier pour stocker les segments vidéo
  }
}
```

**Fichier**: `config/credentials.json` (credentials Google Service Account)

## Architecture

### Composants Principaux

1. **`src/video_segment_extractor.py`**
   - Classe `VideoSegmentExtractor`
   - Découpe vidéo avec ffmpeg (sans réencodage)
   - Fusion automatique de segments

2. **`scripts/process_video_segments.py`**
   - Orchestration complète du workflow
   - Téléchargement Excel + vidéo source depuis Drive
   - Upload segments dans sous-dossiers Drive

3. **`scripts/test_video_processing_e2e.py`**
   - Script de test end-to-end
   - Mode interactif pour tester le système

## Utilisation

### Test Local (Recommandé pour débuter)

```bash
# Lancer le test interactif
python3 scripts/test_video_processing_e2e.py
```

Le script va:
1. ✅ Vérifier que ffmpeg est installé
2. 📋 Lister les fichiers Excel disponibles
3. 🎯 Vous demander lequel tester
4. 📥 Télécharger Excel + vidéo source
5. ✂️  Découper et fusionner les segments
6. 🔍 Valider les segments (durée, codec, taille)
7. 🧹 Proposer le nettoyage des fichiers temporaires

**Résultat**: Segments vidéo créés dans `./temp_test_video/{base_name}_segments/`

### Production (Workflow Complet avec Drive)

```bash
# Traiter tous les nouveaux fichiers Excel
python3 scripts/process_video_segments.py
```

Le script va:
1. Lister les fichiers Excel dans `excel_output` folder
2. Pour chaque Excel:
   - Télécharger Excel + vidéo source
   - Extraire et fusionner segments
   - Créer sous-dossier dans `segments_output`
   - Upload tous les segments
   - Nettoyer fichiers temporaires

**Résultat**: Segments uploadés dans Drive avec structure:
```
Segments Output/
├── video_1/
│   ├── highlight_01_Intro.mp4
│   ├── highlight_02_Concept.mp4
│   └── ...
└── video_2/
    └── ...
```

## Format du Fichier Excel

Le fichier Excel de highlights doit contenir les colonnes suivantes:

| Colonne | Type | Description |
|---------|------|-------------|
| `Numéro` | int | Numéro du highlight (groupage) |
| `Groupe` | str | Nom du groupe/commentaire |
| `Début (secondes)` | float | Timestamp de début (ex: 45.2) |
| `Fin (secondes)` | float | Timestamp de fin (ex: 78.5) |
| `Durée (secondes)` | float | Durée du segment (ex: 33.3) |

**Exemple**:
```
Numéro | Groupe    | Début (s) | Fin (s) | Durée (s)
-------|-----------|-----------|---------|----------
1      | Intro     | 45.2      | 78.5    | 33.3
1      | Intro     | 120.1     | 145.8   | 25.7     ← Même groupe = fusion auto
2      | Concept   | 200.0     | 240.5   | 40.5
```

**Comportement**:
- Les lignes avec le **même Numéro** sont automatiquement **fusionnées** en une seule vidéo
- Les segments sont extraits **sans réencodage** (très rapide, ~2-5s par segment)
- Les noms de fichiers sont générés avec: `{source_name}_highlight_{num:02d}_{groupe}.{ext}`

## Fonctionnalités Clés

### 1. Extraction sans Réencodage

```bash
# Commande ffmpeg utilisée
ffmpeg -ss {start} -i {input} -t {duration} -c copy -avoid_negative_ts make_zero output.mp4
```

**Avantages**:
- ⚡ **Très rapide** (10-50x plus rapide qu'avec réencodage)
- 🎥 **Préserve la qualité** originale
- 💾 **Pas de perte** de qualité

### 2. Fusion Automatique

Si plusieurs segments ont le **même numéro** (même groupe):

```bash
# 1. Extraire chaque segment individuellement
ffmpeg -ss 45.2 -i video.mp4 -t 33.3 -c copy temp_segment_0.mp4
ffmpeg -ss 120.1 -i video.mp4 -t 25.7 -c copy temp_segment_1.mp4

# 2. Créer liste de concaténation
echo "file 'temp_segment_0.mp4'" > concat_list.txt
echo "file 'temp_segment_1.mp4'" >> concat_list.txt

# 3. Fusionner sans réencodage
ffmpeg -f concat -safe 0 -i concat_list.txt -c copy output.mp4
```

### 3. Diagnostic des Segments

Le script de test utilise `ffprobe` pour valider les segments:

```python
info = extractor.get_segment_info('highlight_01.mp4')
# {
#   'duration': 33.3,           # Durée en secondes
#   'video_codec': 'h264',      # Codec (doit être identique à la source)
#   'width': 1920,              # Résolution préservée
#   'height': 1080,
#   'size_bytes': 15728640,     # 15 MB
#   'bitrate': 4000000          # 4 Mbps
# }
```

## Performance

| Opération | Temps | Notes |
|-----------|-------|-------|
| Extraction 1 segment (30s) | 2-5s | Sans réencodage |
| Fusion 3 segments | 5-10s | Concat, pas de réencodage |
| Upload segment (100 MB) | 30-60s | Dépend de la connexion |
| **Workflow complet** (5 segments) | **5-10 min** | Incluant téléchargements |

## Troubleshooting

### Problème: "ffmpeg non trouvé"

```bash
# Solution: Installer ffmpeg
brew install ffmpeg

# Vérifier
which ffmpeg
ffmpeg -version
```

### Problème: "Vidéo source non trouvée"

**Cause**: Le nom du fichier Excel ne correspond pas au nom de la vidéo source.

**Solution**:
1. Le fichier Excel s'appelle: `Mon_Video_highlights.xlsx`
2. La vidéo source doit s'appeler: `Mon_Video.mp4` (ou .mp3, .wav, .m4a, .mov, .avi)
3. Vérifier que la vidéo est bien dans le dossier `source_files` configuré

### Problème: "Colonne 'Groupe' non trouvée"

**Cause**: L'Excel utilise l'ancien format avec colonne 'Commentaire'

**Solution**: Régénérer l'Excel avec `highlight_extractor.py` (version récente qui génère 'Groupe')

### Problème: Segments trop courts ou trop longs

**Cause**: Timestamps incorrects dans l'Excel

**Solution**:
1. Vérifier que les timestamps dans l'Excel correspondent à la vidéo source
2. Utiliser le script de test pour voir les durées réelles des segments créés
3. Ajuster les timestamps dans le Google Doc source et régénérer l'Excel

### Problème: Erreur "Codec not supported"

**Cause**: Format vidéo rare ou non supporté par ffmpeg

**Solution**:
```bash
# Vérifier le format de la vidéo source
ffprobe video.mp4

# Si besoin, convertir en format standard
ffmpeg -i video.mov -c:v libx264 -c:a aac video.mp4
```

## Exemples d'Utilisation

### Test Simple

```bash
# 1. Vérifier ffmpeg
ffmpeg -version

# 2. Lancer test interactif
python3 scripts/test_video_processing_e2e.py

# 3. Choisir un fichier Excel à tester
# 4. Vérifier les segments créés dans ./temp_test_video/
# 5. Lire un segment pour valider la qualité
open ./temp_test_video/video_segments/highlight_01_Intro.mp4
```

### Production Complète

```bash
# 1. S'assurer que la config est correcte
cat config/highlight_config.json

# 2. Traiter tous les nouveaux Excel
python3 scripts/process_video_segments.py

# 3. Vérifier les segments dans Drive
# Aller dans le dossier "Segments Output" sur Drive
```

### Workflow Manuel (Avancé)

```python
from video_segment_extractor import VideoSegmentExtractor

extractor = VideoSegmentExtractor()

# Extraire segments depuis Excel local
segments = extractor.extract_segments(
    excel_path='highlights.xlsx',
    source_video_path='video.mp4',
    output_folder='./segments_output'
)

# Valider un segment
info = extractor.get_segment_info(segments[0])
print(f"Durée: {info['duration']}s")
print(f"Codec: {info['video_codec']}")
```

## Structure des Fichiers

```
whisper-drive-automation/
├── src/
│   ├── video_segment_extractor.py      # Découpage/fusion avec ffmpeg
│   ├── highlight_extractor.py          # Extraction highlights depuis Google Docs
│   └── drive_manager.py                # API Google Drive
├── scripts/
│   ├── process_video_segments.py       # Workflow production complet
│   └── test_video_processing_e2e.py    # Script de test interactif
├── config/
│   ├── highlight_config.json           # Configuration dossiers Drive
│   └── credentials.json                # Credentials Google Service Account
└── README-VIDEO-PROCESSING.md          # Ce fichier
```

## FAQ

**Q: Puis-je utiliser des audios (MP3, WAV) au lieu de vidéos?**
R: Oui! Le système supporte: `.mp4`, `.mp3`, `.wav`, `.m4a`, `.mov`, `.avi`

**Q: Les segments sont-ils réencodés?**
R: Non, on utilise `ffmpeg -c copy` qui copie les streams sans réencodage. C'est très rapide et préserve la qualité.

**Q: Puis-je fusionner plus de 2 segments?**
R: Oui, tous les segments avec le même numéro seront fusionnés automatiquement, peu importe le nombre.

**Q: Comment nettoyer les fichiers temporaires?**
R: Le système nettoie automatiquement après chaque traitement. Pour le test manuel, répondre 'o' à la question de nettoyage.

**Q: Où sont stockés les segments dans Drive?**
R: Dans le dossier `segments_output`, avec un sous-dossier par vidéo source.

## Support

Pour toute question ou problème:
1. Consulter la section Troubleshooting ci-dessus
2. Lancer le script de test pour diagnostiquer: `python3 scripts/test_video_processing_e2e.py`
3. Vérifier les logs du système
4. Contacter l'équipe de développement
