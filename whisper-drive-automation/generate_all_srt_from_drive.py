#!/usr/bin/env python3
"""
Script pour générer les SRT de tous les segments vidéo existants sur Drive
Parcourt le dossier segments_output et génère un SRT pour chaque vidéo qui n'en a pas encore
Les SRT sont placés dans le même dossier que les vidéos (même structure que subtitles_vm_worker.py)
"""
import sys
import os
import json
import logging
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

# Ajouter les chemins au PYTHONPATH
current_dir = Path(__file__).parent
src_path = str(current_dir / 'src')
config_path = str(current_dir / 'config')
sys.path.insert(0, src_path)
sys.path.insert(0, config_path)

from drive_manager import DriveManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_audio: str) -> bool:
    """Extrait l'audio de la vidéo"""
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        '-y',
        output_audio
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur extraction audio: {e.stderr.decode() if e.stderr else 'Erreur inconnue'}")
        return False


def transcribe_to_srt(audio_path: str, output_srt: str) -> bool:
    """Transcrit l'audio et génère un SRT"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.error("❌ faster-whisper non installé")
        logger.error("   Installez avec: pip install faster-whisper")
        return False

    device = "cpu"
    compute_type = "int8"

    logger.info(f"   📥 Chargement du modèle Whisper...")
    model = WhisperModel("base", device=device, compute_type=compute_type)

    logger.info(f"   ⚙️  Transcription en cours...")
    segments, info = model.transcribe(audio_path, language="fr", word_timestamps=False)

    # Convertir en liste
    segments_list = list(segments)
    logger.info(f"   ✅ {len(segments_list)} segments transcrits")

    # Générer SRT
    with open(output_srt, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments_list, 1):
            start_time = format_timestamp(segment.start)
            end_time = format_timestamp(segment.end)
            text = segment.text.strip()

            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n")
            f.write("\n")

    logger.info(f"   ✅ SRT créé avec {len(segments_list)} segments")
    return True


def format_timestamp(seconds: float) -> str:
    """Convertit secondes en format SRT: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def process_segments_folder(drive_manager, folder_id: str, folder_name: str, temp_dir: Path, dry_run: bool = False):
    """
    Traite tous les segments d'un dossier
    Comme dans subtitles_vm_worker.py, les SRT sont dans le même dossier que les vidéos
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"📁 Dossier: {folder_name}")
    logger.info(f"{'='*70}")

    # 1. Lister les fichiers dans le dossier segments (comme ligne 397 de subtitles_vm_worker.py)
    all_files = drive_manager.list_files_in_folder(folder_id)

    # 2. Séparer vidéos et SRT (comme lignes 400-401 de subtitles_vm_worker.py)
    # Case-insensitive pour gérer .mp4 et .MP4
    video_files = [f for f in all_files if f['name'].lower().endswith('.mp4')]
    srt_files = [f for f in all_files if f['name'].lower().endswith('.srt')]

    # Créer un set des noms de base qui ont déjà un SRT
    srt_basenames = set(Path(f['name']).stem for f in srt_files)

    logger.info(f"📹 {len(video_files)} vidéo(s) trouvée(s)")
    logger.info(f"📝 {len(srt_files)} SRT déjà existant(s)")

    # Identifier les vidéos qui n'ont pas encore de SRT
    videos_without_srt = []
    for video_file in video_files:
        video_stem = Path(video_file['name']).stem
        if video_stem not in srt_basenames:
            videos_without_srt.append(video_file)

    if not videos_without_srt:
        logger.info("✅ Tous les segments ont déjà un SRT")
        return 0

    logger.info(f"🎯 {len(videos_without_srt)} vidéo(s) sans SRT à traiter")

    if dry_run:
        logger.info("\n🔍 MODE DRY RUN - Voici les vidéos qui seraient traitées:")
        for video_file in videos_without_srt:
            logger.info(f"   • {video_file['name']}")
        return len(videos_without_srt)

    # Créer dossier temporaire pour ce batch
    batch_dir = temp_dir / folder_name.replace('/', '_')
    batch_dir.mkdir(exist_ok=True)

    processed_count = 0
    failed_count = 0

    for i, video_file in enumerate(videos_without_srt, 1):
        video_name = video_file['name']
        video_stem = Path(video_name).stem

        logger.info(f"\n{'─'*70}")
        logger.info(f"📹 [{i}/{len(videos_without_srt)}] {video_name}")
        logger.info(f"{'─'*70}")

        try:
            # Télécharger la vidéo
            video_path = batch_dir / video_name
            logger.info(f"   📥 Téléchargement depuis Drive...")
            drive_manager.download_file(video_file['id'], video_name, str(video_path))

            # Extraire l'audio
            audio_path = batch_dir / f"{video_stem}_audio.wav"
            logger.info(f"   🎵 Extraction audio...")
            if not extract_audio(str(video_path), str(audio_path)):
                logger.warning(f"⚠️ Échec extraction audio - vidéo ignorée")
                failed_count += 1
                continue

            # Générer SRT
            srt_path = batch_dir / f"{video_stem}.srt"
            logger.info(f"   🎤 Transcription et génération SRT...")
            if not transcribe_to_srt(str(audio_path), str(srt_path)):
                logger.warning(f"⚠️ Échec transcription - vidéo ignorée")
                failed_count += 1
                continue

            # Upload le SRT sur Drive DANS LE MÊME DOSSIER que la vidéo
            logger.info(f"   📤 Upload SRT sur Drive...")
            drive_manager.upload_file(
                str(srt_path),
                f"{video_stem}.srt",
                folder_id  # Même dossier que les vidéos
            )

            logger.info(f"   ✅ SRT généré et uploadé avec succès!")
            processed_count += 1

            # Nettoyer fichiers temporaires
            video_path.unlink(missing_ok=True)
            audio_path.unlink(missing_ok=True)
            srt_path.unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"   ❌ Erreur: {e}")
            failed_count += 1
            import traceback
            logger.debug(traceback.format_exc())

    logger.info(f"\n{'='*70}")
    logger.info(f"📊 Résumé dossier: {folder_name}")
    logger.info(f"   ✅ Traités: {processed_count}")
    logger.info(f"   ❌ Échecs: {failed_count}")
    logger.info(f"{'='*70}")

    return processed_count


def main():
    logger.info("=" * 70)
    logger.info("🎬 GÉNÉRATION SRT POUR TOUS LES SEGMENTS DU DRIVE")
    logger.info("=" * 70)

    # Vérifier si dry-run
    dry_run = '--dry-run' in sys.argv
    if dry_run:
        logger.info("🔍 MODE DRY RUN - Aucune modification ne sera effectuée")
        logger.info("")

    try:
        # Charger la config
        config_file = current_dir / 'config' / 'highlight_config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Initialiser Drive Manager
        logger.info("🔧 Initialisation de Drive Manager...")
        credentials_path = str(current_dir / 'config' / 'credentials.json')
        drive_manager = DriveManager(credentials_path=credentials_path)

        # Dossier segments_output
        segments_folder = config['drive_folders'].get('segments_output')
        if not segments_folder:
            logger.error("❌ Dossier segments_output non configuré dans highlight_config.json")
            return 1

        logger.info(f"📂 Dossier segments: {segments_folder}")

        # Créer dossier temporaire
        temp_dir = Path('/tmp/srt_generation')
        temp_dir.mkdir(exist_ok=True)

        # Lister tous les sous-dossiers dans segments_output avec leur date de création
        logger.info("\n🔍 Recherche des dossiers de segments...")

        # Récupérer les dossiers avec leur date de création
        results = drive_manager.service.files().list(
            q=f"'{segments_folder}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name, createdTime, mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        all_items = results.get('files', [])

        # Filtrer uniquement les dossiers créés en janvier 2026
        from datetime import datetime
        segment_folders = []
        for item in all_items:
            created_time = item.get('createdTime', '')
            if created_time:
                # Format: 2026-01-15T21:37:51.000Z
                created_date = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                if created_date.year == 2026 and created_date.month == 1:
                    segment_folders.append(item)

        if not segment_folders:
            logger.info("📭 Aucun dossier de segments trouvé")
            return 0

        logger.info(f"📁 {len(segment_folders)} dossier(s) de segments trouvé(s)\n")

        # Traiter chaque dossier
        total_processed = 0
        for folder in segment_folders:
            folder_name = folder['name']
            folder_id = folder['id']

            count = process_segments_folder(
                drive_manager,
                folder_id,
                folder_name,
                temp_dir,
                dry_run=dry_run
            )
            total_processed += count

        # Résumé global
        logger.info("\n" + "=" * 70)
        logger.info("✅ TRAITEMENT TERMINÉ")
        logger.info("=" * 70)
        logger.info(f"📊 Total de segments traités: {total_processed}")

        if dry_run:
            logger.info("\n💡 Pour générer les SRT, relancez sans --dry-run:")
            logger.info("   python generate_all_srt_from_drive.py")

        # Nettoyer
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        return 0

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    exit(main())
