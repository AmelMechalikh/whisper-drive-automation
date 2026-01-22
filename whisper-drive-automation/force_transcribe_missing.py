#!/usr/bin/env python3
"""
Script pour forcer la transcription des fichiers non transcrits depuis le 13 janvier
"""
import sys
import json
import time
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


def find_missing_transcriptions(drive_manager):
    """
    Trouve tous les fichiers créés/modifiés depuis le 13 janvier qui n'ont pas de transcription

    Returns:
        list: Liste des fichiers sans transcription
    """
    input_folder_id = config.DRIVE_FOLDERS['input']
    output_folder_id = config.DRIVE_FOLDERS['output']

    logger.info("🔍 Recherche des fichiers non transcrits depuis le 13 janvier...")

    # Lister tous les fichiers
    query = f"'{input_folder_id}' in parents and trashed=false"

    results = drive_manager.service.files().list(
        q=query,
        fields='files(id, name, createdTime, modifiedTime, size)',
        orderBy='modifiedTime desc',
        pageSize=100,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get('files', [])

    start_date = datetime(2026, 1, 13, 0, 0, 0)
    missing_files = []

    for f in files:
        created_str = f.get('createdTime', '')
        modified_str = f.get('modifiedTime', '')

        created = None
        modified = None

        if created_str:
            created = datetime.fromisoformat(created_str.replace('Z', '+00:00')).replace(tzinfo=None)
        if modified_str:
            modified = datetime.fromisoformat(modified_str.replace('Z', '+00:00')).replace(tzinfo=None)

        # Vérifier si créé OU modifié après le 13 janvier
        is_recent = False
        if created and created >= start_date:
            is_recent = True
        if modified and modified >= start_date:
            is_recent = True

        if is_recent:
            # Vérifier si a une transcription
            base_name = '.'.join(f['name'].split('.')[:-1])
            has_transcription = drive_manager.transcription_exists(base_name, output_folder_id)

            if not has_transcription:
                missing_files.append({
                    'id': f['id'],
                    'name': f['name'],
                    'size': f.get('size', 'N/A'),
                    'created': created,
                    'modified': modified
                })
                logger.info(f"   ❌ {f['name']}")

    logger.info(f"\n✅ Trouvé {len(missing_files)} fichier(s) à transcrire")
    return missing_files


def create_transcription_jobs(drive_manager, files):
    """
    Crée des jobs de transcription pour les fichiers donnés

    Args:
        drive_manager: Instance de DriveManager
        files: Liste des fichiers à transcrire

    Returns:
        int: Nombre de jobs créés
    """
    queue_folder_id = config.DRIVE_FOLDERS.get('queue', config.DRIVE_FOLDERS['output'])

    logger.info(f"\n📝 Création des jobs de transcription...")

    jobs_created = 0

    for file in files:
        try:
            # Créer le job JSON
            job_data = {
                'file_id': file['id'],
                'file_name': file['name'],
                'file_size': file['size'],
                'created_at': datetime.now().isoformat(),
                'priority': 'high',
                'reason': 'Manual trigger - Missing transcription since 2026-01-13'
            }

            # Nom du job
            timestamp = int(time.time())
            base_name = '.'.join(file['name'].split('.')[:-1])
            job_filename = f"job_{base_name}_{timestamp}.json"

            # Upload du job
            job_content = json.dumps(job_data, indent=2, ensure_ascii=False)

            job_file_metadata = {
                'name': job_filename,
                'parents': [queue_folder_id],
                'mimeType': 'application/json'
            }

            from googleapiclient.http import MediaInMemoryUpload

            media = MediaInMemoryUpload(
                job_content.encode('utf-8'),
                mimetype='application/json',
                resumable=True
            )

            uploaded_job = drive_manager.service.files().create(
                body=job_file_metadata,
                media_body=media,
                fields='id, name',
                supportsAllDrives=True
            ).execute()

            logger.info(f"   ✅ Job créé: {job_filename}")
            jobs_created += 1

        except Exception as e:
            logger.error(f"   ❌ Erreur création job pour {file['name']}: {e}")

    return jobs_created


def main():
    logger.info("="*80)
    logger.info("🚀 FORÇAGE DE TRANSCRIPTION - Fichiers manquants depuis le 13 janvier")
    logger.info("="*80)
    logger.info("")

    # Initialiser le DriveManager
    try:
        drive_manager = DriveManager(config.CREDENTIALS_PATH)
    except Exception as e:
        logger.error(f"❌ Erreur initialisation DriveManager: {e}")
        return 1

    # 1. Trouver les fichiers manquants
    missing_files = find_missing_transcriptions(drive_manager)

    if not missing_files:
        logger.info("✅ Aucun fichier à transcrire!")
        return 0

    # 2. Afficher le résumé
    logger.info("\n" + "="*80)
    logger.info("📊 RÉSUMÉ")
    logger.info("="*80)
    logger.info(f"Fichiers à transcrire: {len(missing_files)}")
    logger.info("")

    for f in missing_files:
        logger.info(f"   • {f['name']}")
        if f['created']:
            logger.info(f"     Créé: {f['created'].strftime('%d/%m/%Y %H:%M:%S')}")
        if f['modified']:
            logger.info(f"     Modifié: {f['modified'].strftime('%d/%m/%Y %H:%M:%S')}")

    # 3. Demander confirmation
    logger.info("\n" + "="*80)
    logger.info("⚠️  Cette opération va créer des jobs de transcription pour ces fichiers.")
    logger.info("   La VM les traitera automatiquement (ou démarrera si elle est éteinte).")
    logger.info("="*80)

    response = input("\n❓ Continuer? (oui/non): ").strip().lower()

    if response not in ['oui', 'yes', 'o', 'y']:
        logger.info("❌ Opération annulée")
        return 0

    # 4. Créer les jobs
    logger.info("")
    jobs_created = create_transcription_jobs(drive_manager, missing_files)

    # 5. Résumé final
    logger.info("\n" + "="*80)
    logger.info("✅ TERMINÉ")
    logger.info("="*80)
    logger.info(f"📝 {jobs_created} job(s) créé(s)")
    logger.info("")
    logger.info("💡 Prochaines étapes:")
    logger.info("   1. Les jobs sont dans le dossier Queue")
    logger.info("   2. La VM va les détecter et démarrer automatiquement")
    logger.info("   3. La transcription prendra quelques heures selon la longueur des vidéos")
    logger.info("")
    logger.info("📊 Pour suivre la progression:")
    logger.info("   - Vérifier le dossier Transcriptions sur Google Drive")
    logger.info("   - Ou consulter les logs de la VM")
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
