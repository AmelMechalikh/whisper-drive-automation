#!/usr/bin/env python3
"""
Script pour lister tous les fichiers du dossier Input avec leurs dates
"""
import sys
from pathlib import Path
from datetime import datetime
import logging

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))

from src.drive_manager import DriveManager
from config import whisper_config as config

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


def list_all_files_with_dates(drive_manager):
    """
    Liste tous les fichiers du dossier Input avec leurs dates de création et modification
    """
    input_folder_id = config.DRIVE_FOLDERS['input']
    output_folder_id = config.DRIVE_FOLDERS['output']

    logger.info("🔍 Listage de tous les fichiers du dossier Input...")
    logger.info("")

    # Lister tous les fichiers
    query = f"'{input_folder_id}' in parents and trashed=false"

    results = drive_manager.service.files().list(
        q=query,
        fields="files(id, name, createdTime, modifiedTime, mimeType, size)",
        orderBy="modifiedTime desc",
        pageSize=100,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get('files', [])

    logger.info(f"📁 Total de fichiers: {len(files)}")
    logger.info("")
    logger.info("="*120)
    logger.info(f"{'NOM DU FICHIER':<60} {'CRÉÉ LE':<20} {'MODIFIÉ LE':<20} {'TRANSCRIT':<10}")
    logger.info("="*120)

    # Dates cibles
    target_start = datetime(2026, 1, 13, 0, 0, 0)
    target_end = datetime(2026, 1, 15, 0, 0, 0)

    files_in_period = []

    for file in files:
        name = file['name']
        created_str = file.get('createdTime', '')
        modified_str = file.get('modifiedTime', '')

        if created_str:
            created = datetime.fromisoformat(created_str.replace('Z', '+00:00')).replace(tzinfo=None)
            created_display = created.strftime('%d/%m/%Y %H:%M')
        else:
            created = None
            created_display = "N/A"

        if modified_str:
            modified = datetime.fromisoformat(modified_str.replace('Z', '+00:00')).replace(tzinfo=None)
            modified_display = modified.strftime('%d/%m/%Y %H:%M')
        else:
            modified = None
            modified_display = "N/A"

        # Vérifier si dans la période (créé OU modifié)
        in_period = False
        if created and target_start <= created < target_end:
            in_period = True
        if modified and target_start <= modified < target_end:
            in_period = True

        # Vérifier transcription
        base_name = '.'.join(name.split('.')[:-1])
        has_transcription = drive_manager.transcription_exists(base_name, output_folder_id)
        transcription_status = "✅" if has_transcription else "❌"

        # Afficher
        if in_period:
            marker = "🔴"
            files_in_period.append({
                'name': name,
                'created': created,
                'modified': modified,
                'has_transcription': has_transcription
            })
        else:
            marker = "  "

        logger.info(f"{marker} {name:<58} {created_display:<20} {modified_display:<20} {transcription_status:<10}")

    logger.info("="*120)
    logger.info("")
    logger.info(f"🔴 = Fichiers créés ou modifiés entre le 13 et 14 janvier 2026")
    logger.info("")
    logger.info("="*120)
    logger.info("RÉSUMÉ - FICHIERS DU 13-14 JANVIER")
    logger.info("="*120)

    if not files_in_period:
        logger.info("✅ Aucun fichier créé ou modifié dans cette période")
    else:
        missing = [f for f in files_in_period if not f['has_transcription']]
        existing = [f for f in files_in_period if f['has_transcription']]

        logger.info(f"📊 Total: {len(files_in_period)} fichier(s)")
        logger.info(f"✅ Transcrits: {len(existing)}")
        logger.info(f"❌ NON transcrits: {len(missing)}")
        logger.info("")

        if missing:
            logger.info("🚨 FICHIERS À TRANSCRIRE:")
            for f in missing:
                logger.info(f"   ❌ {f['name']}")
                if f['created']:
                    logger.info(f"      Créé: {f['created'].strftime('%d/%m/%Y %H:%M:%S')}")
                if f['modified']:
                    logger.info(f"      Modifié: {f['modified'].strftime('%d/%m/%Y %H:%M:%S')}")


def main():
    logger.info("🚀 Listage des fichiers du dossier Input")
    logger.info("")

    try:
        drive_manager = DriveManager(config.CREDENTIALS_PATH)
    except Exception as e:
        logger.error(f"❌ Erreur initialisation DriveManager: {e}")
        return 1

    list_all_files_with_dates(drive_manager)

    logger.info("")
    logger.info("✅ Listage terminé!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
