#!/usr/bin/env python3
"""
Script pour lister tous les dossiers de segments avec leur date de création
"""
import sys
import json
import logging
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


def main():
    logger.info("=" * 80)
    logger.info("📂 LISTE DES DOSSIERS DE SEGMENTS")
    logger.info("=" * 80)

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

        logger.info(f"📂 Dossier segments: {segments_folder}\n")

        # Récupérer TOUS les dossiers avec leur date de création
        results = drive_manager.service.files().list(
            q=f"'{segments_folder}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name, createdTime, mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="createdTime desc"
        ).execute()

        all_folders = results.get('files', [])

        if not all_folders:
            logger.info("📭 Aucun dossier trouvé")
            return 0

        logger.info(f"📁 {len(all_folders)} dossier(s) trouvé(s)\n")
        logger.info("=" * 80)

        # Grouper par mois
        folders_by_month = {}
        for folder in all_folders:
            created_time = folder.get('createdTime', '')
            if created_time:
                created_date = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                month_key = f"{created_date.year}-{created_date.month:02d}"

                if month_key not in folders_by_month:
                    folders_by_month[month_key] = []

                folders_by_month[month_key].append({
                    'name': folder['name'],
                    'id': folder['id'],
                    'created': created_date
                })

        # Afficher par mois
        for month_key in sorted(folders_by_month.keys(), reverse=True):
            folders = folders_by_month[month_key]
            year, month = month_key.split('-')
            month_names = {
                '01': 'Janvier', '02': 'Février', '03': 'Mars', '04': 'Avril',
                '05': 'Mai', '06': 'Juin', '07': 'Juillet', '08': 'Août',
                '09': 'Septembre', '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
            }
            month_name = month_names.get(month, month)

            logger.info(f"\n📅 {month_name} {year} - {len(folders)} dossier(s)")
            logger.info("─" * 80)

            for folder in sorted(folders, key=lambda x: x['created'], reverse=True):
                created_str = folder['created'].strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"  • {folder['name']}")
                logger.info(f"    Créé le: {created_str}")
                logger.info(f"    ID: {folder['id']}")
                logger.info("")

        logger.info("=" * 80)
        return 0

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1


if __name__ == '__main__':
    exit(main())
