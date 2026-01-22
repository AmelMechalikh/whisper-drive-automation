#!/usr/bin/env python3
"""
Script pour identifier les fichiers ajoutés les 13-14 janvier qui n'ont pas été transcrits
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


def check_files_by_date(drive_manager, start_date, end_date):
    """
    Liste les fichiers audio ajoutés entre deux dates et vérifie s'ils ont été transcrits

    Args:
        drive_manager: Instance de DriveManager
        start_date: Date de début (datetime)
        end_date: Date de fin (datetime)
    """
    input_folder_id = config.DRIVE_FOLDERS['input']
    output_folder_id = config.DRIVE_FOLDERS['output']

    logger.info(f"🔍 Recherche des fichiers ajoutés entre {start_date.strftime('%d/%m/%Y')} et {end_date.strftime('%d/%m/%Y')}")

    # Lister tous les fichiers audio
    audio_files = drive_manager.list_audio_files(input_folder_id, config.SUPPORTED_EXTENSIONS)

    logger.info(f"📁 Total de fichiers audio dans Input: {len(audio_files)}")

    # Filtrer par date de création
    files_in_period = []

    for file in audio_files:
        # Récupérer la date de création
        file_details = drive_manager.service.files().get(
            fileId=file['id'],
            fields='name,createdTime,modifiedTime',
            supportsAllDrives=True
        ).execute()

        created_time_str = file_details.get('createdTime', '')
        if created_time_str:
            # Format: 2026-01-13T10:30:00.000Z
            created_time = datetime.fromisoformat(created_time_str.replace('Z', '+00:00'))
            created_time = created_time.replace(tzinfo=None)  # Remove timezone for comparison

            if start_date <= created_time < end_date:
                files_in_period.append({
                    'name': file['name'],
                    'id': file['id'],
                    'created_time': created_time,
                    'size': file.get('size', 'N/A')
                })

    logger.info(f"\n📊 Fichiers ajoutés dans la période: {len(files_in_period)}")

    if not files_in_period:
        logger.info("✅ Aucun fichier ajouté dans cette période")
        return

    # Vérifier si chaque fichier a été transcrit
    logger.info("\n" + "="*80)
    logger.info("ANALYSE DES TRANSCRIPTIONS")
    logger.info("="*80)

    missing_transcriptions = []
    existing_transcriptions = []

    for file in files_in_period:
        file_name = file['name']
        # Extraire le nom de base (sans extension)
        base_name = '.'.join(file_name.split('.')[:-1])

        # Vérifier si la transcription existe
        transcription_exists = drive_manager.transcription_exists(base_name, output_folder_id)

        if transcription_exists:
            existing_transcriptions.append(file)
            logger.info(f"✅ {file_name}")
            logger.info(f"   Créé le: {file['created_time'].strftime('%d/%m/%Y %H:%M:%S')}")
            logger.info(f"   Statut: Transcription trouvée")
        else:
            missing_transcriptions.append(file)
            logger.info(f"❌ {file_name}")
            logger.info(f"   Créé le: {file['created_time'].strftime('%d/%m/%Y %H:%M:%S')}")
            logger.info(f"   Statut: PAS DE TRANSCRIPTION")
        logger.info("")

    # Résumé final
    logger.info("="*80)
    logger.info("RÉSUMÉ")
    logger.info("="*80)
    logger.info(f"📁 Fichiers ajoutés dans la période: {len(files_in_period)}")
    logger.info(f"✅ Fichiers déjà transcrits: {len(existing_transcriptions)}")
    logger.info(f"❌ Fichiers NON transcrits: {len(missing_transcriptions)}")

    if missing_transcriptions:
        logger.info("\n🚨 FICHIERS À TRANSCRIRE:")
        for file in missing_transcriptions:
            logger.info(f"   • {file['name']} (ID: {file['id']})")

        logger.info("\n💡 Pour lancer la transcription de ces fichiers:")
        logger.info("   1. Vérifiez que les fichiers sont bien dans le dossier Input")
        logger.info("   2. Utilisez le script trigger_processing.py")
        logger.info("   3. Ou attendez que le scheduler automatique les détecte")
    else:
        logger.info("\n✅ Tous les fichiers de cette période ont été transcrits!")


def main():
    logger.info("🚀 Démarrage du diagnostic de transcriptions manquantes")

    # Dates à vérifier
    start_date = datetime(2026, 1, 13, 0, 0, 0)
    end_date = datetime(2026, 1, 15, 0, 0, 0)

    # Initialiser le DriveManager
    try:
        drive_manager = DriveManager(config.CREDENTIALS_PATH)
    except Exception as e:
        logger.error(f"❌ Erreur initialisation DriveManager: {e}")
        logger.error("💡 Assurez-vous que les credentials Google sont configurés")
        return 1

    # Vérifier les fichiers
    check_files_by_date(drive_manager, start_date, end_date)

    logger.info("\n✅ Diagnostic terminé!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
