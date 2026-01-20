#!/usr/bin/env python3
"""
Worker VM pour traiter les gros fichiers audio
Vérifie périodiquement le dossier queue dans Google Drive
"""
import os
import json
import time
import logging
import tempfile
from pathlib import Path
from datetime import datetime
import sys

# Ajouter les chemins au PYTHONPATH
current_dir = Path(__file__).parent.parent
src_path = str(current_dir / 'src')
config_path = str(current_dir / 'config')
sys.path.insert(0, src_path)
sys.path.insert(0, config_path)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/vm_worker.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Boucle principale du worker"""
    logger.info("=" * 60)
    logger.info("🤖 VM Worker démarré")
    logger.info("=" * 60)
    
    try:
        # Importer la configuration et le processeur
        import whisper_config as config
        from src.processor import WhisperDriveProcessor
        from src.drive_manager import DriveManager
        
        # Initialiser le processeur
        logger.info("🔧 Initialisation du processeur...")
        processor = WhisperDriveProcessor(config)
        drive_manager = processor.drive_manager
        
        queue_folder = config.DRIVE_FOLDERS.get('queue', config.DRIVE_FOLDERS['output'])
        
        logger.info(f"📂 Surveillance du dossier queue: {queue_folder}")
        logger.info("🔄 Démarrage de la boucle de traitement...")
        
        check_interval = 60  # Vérifier toutes les 60 secondes
        idle_shutdown_minutes = 5  # Éteindre après 5 minutes d'inactivité
        consecutive_empty_checks = 0  # Compteur de vérifications consécutives sans job
        max_idle_checks = idle_shutdown_minutes * 60 // check_interval
        
        logger.info(f"⚙️  Auto-shutdown après {idle_shutdown_minutes} minutes d'inactivité (sans traitement en cours)")
        
        while True:
            try:
                logger.info("🔍 Recherche de nouveaux jobs...")
                
                # Lister les fichiers .json dans le dossier queue
                query = f"'{queue_folder}' in parents and name contains 'job_' and name contains '.json' and trashed=false"
                results = drive_manager.service.files().list(
                    q=query,
                    fields="files(id, name, createdTime)",
                    orderBy='createdTime',
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                job_files = results.get('files', [])
                
                if not job_files:
                    consecutive_empty_checks += 1
                    logger.info(f"📭 Aucun job en attente ({consecutive_empty_checks}/{max_idle_checks} avant auto-shutdown)")
                    
                    # Arrêt automatique uniquement si aucun job ET aucun traitement en cours
                    if consecutive_empty_checks >= max_idle_checks:
                        logger.info(f"💤 {idle_shutdown_minutes} minutes d'inactivité - arrêt automatique de la VM")
                        import subprocess
                        subprocess.run(['sudo', 'shutdown', '-h', 'now'])
                        break
                else:
                    # Reset du compteur - il y a des jobs à traiter
                    consecutive_empty_checks = 0
                    logger.info(f"📥 {len(job_files)} job(s) trouvé(s)")
                    
                    for job_file in job_files:
                        process_job(processor, drive_manager, job_file, queue_folder)
                        # Après chaque job traité, reset le compteur car on est actif
                        consecutive_empty_checks = 0
                
                # Attendre avant la prochaine vérification
                logger.info(f"⏳ Attente {check_interval}s avant la prochaine vérification...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("🛑 Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle principale: {e}")
                logger.info(f"⏳ Pause de 30s avant reprise...")
                time.sleep(30)
    
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    logger.info("👋 VM Worker arrêté")
    return 0


def process_job(processor, drive_manager, job_file, queue_folder):
    """Traite un fichier job"""
    job_name = job_file['name']
    job_id = job_file['id']

    logger.info("=" * 60)
    logger.info(f"🎯 Traitement du job: {job_name}")

    # Variable pour le nettoyage automatique
    temp_path = None

    try:
        # Télécharger le fichier job
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        success = drive_manager.download_file(job_id, job_name, temp_path)

        if not success:
            logger.error(f"❌ Échec téléchargement job: {job_name}")
            return

        # Lire le contenu du job
        with open(temp_path, 'r') as f:
            job_data = json.load(f)

        file_id = job_data.get('file_id')
        file_name = job_data.get('file_name')

        if not file_id:
            logger.error(f"❌ Job invalide (pas de file_id): {job_name}")
            # Supprimer le job invalide
            drive_manager.service.files().delete(fileId=job_id, supportsAllDrives=True).execute()
            return
        
        logger.info(f"📄 Fichier à traiter: {file_name} (ID: {file_id})")
        
        # Vérifier si la transcription existe déjà (éviter retraitement)
        from pathlib import Path
        base_filename = Path(file_name).stem
        output_folder_id = processor.config.DRIVE_FOLDERS['output']
        
        if drive_manager.transcription_exists(base_filename, output_folder_id):
            logger.info(f"✅ Transcription déjà existante pour: {file_name}")
            logger.info(f"🗑️  Suppression du job devenu obsolète: {job_name}")
            try:
                drive_manager.service.files().delete(
                    fileId=job_id,
                    supportsAllDrives=True
                ).execute()
                logger.info(f"✅ Job obsolète supprimé")
            except Exception as e:
                logger.warning(f"⚠️  Impossible de supprimer le job: {e}")
            return
        
        # Traiter le fichier
        logger.info(f"🚀 Démarrage transcription...")
        success = processor.process_single_file(file_id)
        
        if success:
            logger.info(f"✅ Transcription réussie: {file_name}")
            # Supprimer le job après traitement réussi
            try:
                drive_manager.service.files().delete(fileId=job_id, supportsAllDrives=True).execute()
                logger.info(f"🗑️  Job supprimé: {job_name}")
            except Exception as e:
                logger.warning(f"⚠️  Impossible de supprimer le job (déjà supprimé?): {e}")
        else:
            logger.error(f"❌ Échec transcription: {file_name}")
            # Renommer le job en erreur
            try:
                error_name = job_name.replace('job_', 'error_')
                drive_manager.service.files().update(
                    fileId=job_id,
                    body={'name': error_name}
                ).execute()
                logger.info(f"⚠️  Job renommé en erreur: {error_name}")
            except Exception as e:
                logger.warning(f"⚠️  Impossible de renommer le job: {e}")
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement job {job_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Renommer en erreur (ne pas lancer d'exception si échec)
        try:
            error_name = job_name.replace('job_', 'error_')
            drive_manager.service.files().update(
                fileId=job_id,
                body={'name': error_name}
            ).execute()
            logger.info(f"⚠️  Job renommé en erreur: {error_name}")
        except Exception as rename_error:
            logger.warning(f"⚠️  Impossible de renommer le job en erreur: {rename_error}")

    finally:
        # 🧹 NETTOYAGE AUTOMATIQUE du fichier job temporaire
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"🧹 Fichier job temporaire supprimé: {temp_path}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️  Erreur nettoyage fichier job: {cleanup_error}")


if __name__ == '__main__':
    exit(main())
