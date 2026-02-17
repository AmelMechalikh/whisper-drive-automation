#!/usr/bin/env python3
"""
Script pour nettoyer les fichiers inutilisés sur Google Drive

Supprime :
- *_transcription.txt (texte simple sans timestamps)
- *_with_timestamps.srt (format sous-titres)
- *_word_timestamps.txt (timestamps par mot)

Garde :
- *_paragraphs_timestamps (Google Docs)
- *_complete.json (données complètes)
"""

import sys
import os
import json
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.drive_manager import DriveManager
import logging

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cleanup_unused_files(drive_manager, folder_id, dry_run=True):
    """
    Nettoie les fichiers inutilisés dans un dossier Drive

    Args:
        drive_manager: Instance de DriveManager
        folder_id: ID du dossier à nettoyer
        dry_run: Si True, liste seulement sans supprimer
    """
    # Patterns des fichiers à supprimer
    patterns_to_delete = [
        '_transcription.txt',
        '_with_timestamps.srt',
        '_word_timestamps.txt'
    ]

    logger.info(f"🔍 Scan du dossier Drive (ID: {folder_id})...")

    # Lister TOUS les fichiers dans le dossier (avec pagination)
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        files = []
        page_token = None

        while True:
            results = drive_manager.service.files().list(
                q=query,
                fields='nextPageToken, files(id, name, mimeType)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1000,
                pageToken=page_token
            ).execute()

            files.extend(results.get('files', []))
            page_token = results.get('nextPageToken')

            if not page_token:
                break

        logger.info(f"📁 {len(files)} fichiers trouvés")

    except Exception as e:
        logger.error(f"❌ Erreur lors du scan: {e}")
        return

    # Filtrer les fichiers à supprimer
    files_to_delete = []
    for file in files:
        file_name = file['name']
        file_id = file['id']

        # Vérifier si le fichier correspond à un pattern à supprimer
        for pattern in patterns_to_delete:
            if file_name.endswith(pattern):
                files_to_delete.append({
                    'id': file_id,
                    'name': file_name
                })
                break

    if not files_to_delete:
        logger.info("✅ Aucun fichier inutile trouvé")
        return

    logger.info(f"🗑️  {len(files_to_delete)} fichiers à supprimer:")
    for file in files_to_delete:
        logger.info(f"   - {file['name']}")

    if dry_run:
        logger.info("⚠️  MODE DRY-RUN: Aucun fichier supprimé")
        logger.info("💡 Pour supprimer réellement, relance avec: --no-dry-run")
        return

    # Supprimer les fichiers
    logger.info("🗑️  Suppression en cours...")
    deleted_count = 0
    error_count = 0

    for file in files_to_delete:
        try:
            drive_manager.service.files().delete(
                fileId=file['id'],
                supportsAllDrives=True
            ).execute()
            logger.info(f"   ✅ Supprimé: {file['name']}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"   ❌ Erreur suppression {file['name']}: {e}")
            error_count += 1

    logger.info(f"✅ Nettoyage terminé: {deleted_count} supprimés, {error_count} erreurs")


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Nettoyer les fichiers inutilisés sur Drive')
    parser.add_argument('--no-dry-run', action='store_true',
                       help='Supprimer réellement les fichiers (sinon mode simulation)')
    parser.add_argument('--folder', type=str, default='transcriptions',
                       help='Dossier à nettoyer (transcriptions ou source_files)')
    args = parser.parse_args()

    # Charger la configuration
    config_path = Path(__file__).parent / 'config' / 'highlight_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Initialiser le DriveManager
    logger.info("🔑 Initialisation de l'authentification Google Drive...")
    credentials_path = Path(__file__).parent / 'config' / 'credentials.json'
    drive_manager = DriveManager(str(credentials_path))

    # Déterminer le dossier à nettoyer
    if args.folder == 'transcriptions':
        folder_id = config['drive_folders']['transcriptions']
        logger.info("📂 Nettoyage du dossier: transcriptions/")
    elif args.folder == 'source_files':
        folder_id = config['drive_folders']['source_files']
        logger.info("📂 Nettoyage du dossier: source_files/")
    else:
        logger.error(f"❌ Dossier invalide: {args.folder}")
        sys.exit(1)

    # Nettoyer
    dry_run = not args.no_dry_run
    cleanup_unused_files(drive_manager, folder_id, dry_run=dry_run)


if __name__ == '__main__':
    main()
