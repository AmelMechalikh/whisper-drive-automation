#!/usr/bin/env python3
"""
Script pour vérifier les SRT réellement présents sur Drive
"""
import sys
import json
import logging
from pathlib import Path

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


def main():
    logger.info("=" * 80)
    logger.info("🔍 VÉRIFICATION DES SRT SUR DRIVE")
    logger.info("=" * 80)

    try:
        # Charger la config
        config_file = current_dir / 'config' / 'highlight_config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Initialiser Drive Manager
        credentials_path = str(current_dir / 'config' / 'credentials.json')
        drive_manager = DriveManager(credentials_path=credentials_path)

        # Dossier segments_output
        segments_folder = config['drive_folders'].get('segments_output')

        # Récupérer les dossiers de janvier 2026
        from datetime import datetime
        results = drive_manager.service.files().list(
            q=f"'{segments_folder}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name, createdTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        all_folders = results.get('files', [])

        # Filtrer janvier 2026
        january_folders = []
        for folder in all_folders:
            created_time = folder.get('createdTime', '')
            if created_time:
                created_date = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                if created_date.year == 2026 and created_date.month == 1:
                    january_folders.append(folder)

        logger.info(f"\n📁 {len(january_folders)} dossier(s) de janvier 2026\n")

        total_videos = 0
        total_srts = 0

        for folder in january_folders:
            folder_name = folder['name']
            folder_id = folder['id']

            # Lister les fichiers dans ce dossier
            all_files = drive_manager.list_files_in_folder(folder_id)

            videos = [f for f in all_files if f['name'].endswith('.mp4')]
            srts = [f for f in all_files if f['name'].endswith('.srt')]

            total_videos += len(videos)
            total_srts += len(srts)

            if videos:
                logger.info(f"📁 {folder_name}")
                logger.info(f"   📹 Vidéos: {len(videos)}")
                logger.info(f"   📝 SRT: {len(srts)}")

                if srts:
                    logger.info(f"   ✅ Fichiers SRT présents:")
                    for srt in srts:
                        logger.info(f"      • {srt['name']}")
                else:
                    logger.info(f"   ❌ Aucun SRT trouvé!")

                logger.info("")

        logger.info("=" * 80)
        logger.info(f"📊 TOTAL:")
        logger.info(f"   📹 Vidéos: {total_videos}")
        logger.info(f"   📝 SRT: {total_srts}")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    exit(main())
