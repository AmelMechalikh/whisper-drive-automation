#!/usr/bin/env python3
"""
Script pour re-transcrire les fichiers créés avant le nouveau format de paragraphes
Nouveau format déployé le: 2025-12-18
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Date de déploiement du nouveau format sur Cloud Run
# Le code a changé le 18 déc, mais le service n'a été redéployé qu'en janvier
NEW_FORMAT_DATE = datetime(2026, 1, 1, 18, 0, 0)


def list_old_transcriptions(drive_manager, output_folder_id):
    """
    Liste tous les fichiers de transcription créés avant le nouveau format

    Returns:
        list: Liste de tuples (file_name, file_id, created_time)
    """
    logger.info(f"🔍 Recherche des transcriptions créées avant {NEW_FORMAT_DATE.strftime('%Y-%m-%d %H:%M')}")

    # Lister tous les fichiers dans le dossier de sortie
    query = f"'{output_folder_id}' in parents and trashed = false"

    results = drive_manager.service.files().list(
        q=query,
        fields="files(id, name, createdTime, mimeType)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get('files', [])
    old_files = []

    for file in files:
        # Ne garder que les fichiers _paragraphs_timestamps (Google Docs ou .txt)
        if '_paragraphs_timestamps' in file['name']:
            created_time_str = file['createdTime']
            # Format: 2025-01-15T10:30:00.000Z
            created_time = datetime.strptime(created_time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')

            if created_time < NEW_FORMAT_DATE:
                old_files.append({
                    'name': file['name'],
                    'id': file['id'],
                    'created_time': created_time,
                    'mime_type': file['mimeType']
                })
                logger.info(f"   📄 Trouvé: {file['name']} (créé le {created_time.strftime('%Y-%m-%d %H:%M')})")

    logger.info(f"✅ Trouvé {len(old_files)} fichiers à re-transcrire")
    return old_files


def extract_base_filename(transcription_name):
    """
    Extrait le nom de base du fichier audio depuis le nom de transcription

    Args:
        transcription_name: ex: "mon_audio_paragraphs_timestamps"

    Returns:
        str: ex: "mon_audio"
    """
    # Enlever "_paragraphs_timestamps" et toute extension
    base = transcription_name.replace('_paragraphs_timestamps', '')
    base = base.replace('.txt', '')
    return base


def find_audio_file(drive_manager, input_folder_id, base_filename, supported_extensions):
    """
    Trouve le fichier audio correspondant au nom de base

    Returns:
        dict: file_info ou None si non trouvé
    """
    for ext in supported_extensions:
        # Chercher avec l'extension
        audio_name = f"{base_filename}.{ext}"
        query = f"'{input_folder_id}' in parents and name = '{audio_name}' and trashed = false"

        results = drive_manager.service.files().list(
            q=query,
            fields="files(id, name, createdTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = results.get('files', [])
        if files:
            return files[0]

    return None


def delete_old_transcriptions(drive_manager, file_id, file_name):
    """
    Supprime une transcription (déplace vers la corbeille)
    """
    try:
        drive_manager.service.files().update(
            fileId=file_id,
            body={'trashed': True},
            supportsAllDrives=True
        ).execute()
        logger.info(f"🗑️  Supprimé: {file_name}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur suppression {file_name}: {e}")
        return False


def delete_all_transcription_files(drive_manager, output_folder_id, base_filename):
    """
    Supprime tous les fichiers de transcription pour un fichier audio donné
    """
    patterns = [
        f"{base_filename}_transcription.txt",
        f"{base_filename}_with_timestamps.srt",
        f"{base_filename}_word_timestamps.txt",
        f"{base_filename}_paragraphs_timestamps",
        f"{base_filename}_complete_data.json"
    ]

    deleted_count = 0
    for pattern in patterns:
        files = drive_manager.search_files(output_folder_id, pattern)
        for file in files:
            if delete_old_transcriptions(drive_manager, file['id'], file['name']):
                deleted_count += 1

    return deleted_count


def main():
    logger.info("🚀 Démarrage du script de re-transcription")

    # Initialiser le DriveManager
    drive_manager = DriveManager(config.CREDENTIALS_PATH)

    output_folder_id = config.DRIVE_FOLDERS['output']
    input_folder_id = config.DRIVE_FOLDERS['input']

    # 1. Lister les anciennes transcriptions
    old_transcriptions = list_old_transcriptions(drive_manager, output_folder_id)

    if not old_transcriptions:
        logger.info("✅ Aucun fichier à re-transcrire!")
        return

    # 2. Pour chaque ancienne transcription, trouver le fichier audio correspondant
    audio_files_to_process = []

    for trans_file in old_transcriptions:
        base_filename = extract_base_filename(trans_file['name'])
        logger.info(f"🔎 Recherche du fichier audio pour: {base_filename}")

        audio_file = find_audio_file(
            drive_manager,
            input_folder_id,
            base_filename,
            config.SUPPORTED_EXTENSIONS
        )

        if audio_file:
            logger.info(f"   ✅ Trouvé: {audio_file['name']}")
            audio_files_to_process.append({
                'base_filename': base_filename,
                'audio_file': audio_file,
                'old_transcriptions': [trans_file]
            })
        else:
            logger.warning(f"   ⚠️  Fichier audio non trouvé pour: {base_filename}")

    if not audio_files_to_process:
        logger.warning("⚠️  Aucun fichier audio correspondant trouvé!")
        return

    # 3. Afficher le résumé et demander confirmation
    logger.info("\n" + "="*80)
    logger.info(f"📊 RÉSUMÉ: {len(audio_files_to_process)} fichiers à re-transcrire")
    logger.info("="*80)

    for item in audio_files_to_process:
        logger.info(f"   • {item['audio_file']['name']}")

    logger.info("\n⚠️  Cette opération va:")
    logger.info("   1. Supprimer toutes les anciennes transcriptions de ces fichiers")
    logger.info("   2. Re-lancer la transcription avec le nouveau format")

    response = input("\n❓ Continuer? (oui/non): ").strip().lower()

    if response not in ['oui', 'yes', 'o', 'y']:
        logger.info("❌ Opération annulée")
        return

    # 4. Supprimer les anciennes transcriptions
    logger.info("\n🗑️  Suppression des anciennes transcriptions...")
    for item in audio_files_to_process:
        deleted = delete_all_transcription_files(
            drive_manager,
            output_folder_id,
            item['base_filename']
        )
        logger.info(f"   ✅ {deleted} fichiers supprimés pour {item['base_filename']}")

    # 5. Re-lancer la transcription
    logger.info("\n🎯 Lancement de la re-transcription...")
    logger.info("   Utilisez la commande suivante pour traiter ces fichiers:")
    logger.info(f"\n   python trigger_processing.py")
    logger.info("\n   Ou lancez process_recent_files avec un filtre de date approprié")

    # Liste les IDs des fichiers à traiter
    logger.info("\n📝 IDs des fichiers à traiter:")
    for item in audio_files_to_process:
        logger.info(f"   • {item['audio_file']['id']} - {item['audio_file']['name']}")

    logger.info("\n✅ Script terminé!")


if __name__ == '__main__':
    main()
