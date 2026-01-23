#!/usr/bin/env python3
"""
Worker VM pour traiter les highlights avec grosses vidéos
Vérifie périodiquement le dossier queue_highlights dans Google Drive
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
# Sur la VM, le fichier est dans /opt/highlights-worker/
current_dir = Path(__file__).parent  # /opt/highlights-worker
src_path = str(current_dir / 'src')
config_path = str(current_dir / 'config')
sys.path.insert(0, src_path)
sys.path.insert(0, config_path)

# Configuration du logging (systemd journal gère les logs)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Boucle principale du worker highlights"""
    logger.info("=" * 60)
    logger.info("🎬 Highlights VM Worker démarré")
    logger.info("=" * 60)

    try:
        from drive_manager import DriveManager
        from video_segment_extractor import VideoSegmentExtractor
        import pandas as pd

        # Charger la config highlights
        config_file = current_dir / 'config' / 'highlight_config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)

        logger.info("🔧 Initialisation...")
        credentials_path = str(current_dir / 'config' / 'credentials.json')
        drive_manager = DriveManager(credentials_path=credentials_path)

        # Lire le paramètre add_subtitles depuis la config
        add_subtitles = config['processing'].get('add_subtitles', False)
        logger.info(f"📺 Sous-titres: {'ACTIVÉS' if add_subtitles else 'DÉSACTIVÉS'}")

        video_extractor = VideoSegmentExtractor(logger, add_subtitles=add_subtitles)

        temp_dir = Path('/tmp/highlights')
        temp_dir.mkdir(exist_ok=True)

        queue_folder = config['drive_folders'].get('queue_highlights')
        if not queue_folder:
            logger.error("❌ Dossier queue_highlights non configuré dans highlight_config.json")
            return 1

        logger.info(f"📂 Surveillance du dossier queue: {queue_folder}")
        logger.info("🔄 Démarrage de la boucle de traitement...")

        check_interval = 60  # Vérifier toutes les 60 secondes
        idle_shutdown_minutes = 10  # Éteindre après 10 minutes d'inactivité
        consecutive_empty_checks = 0
        max_idle_checks = idle_shutdown_minutes * 60 // check_interval

        logger.info(f"⚙️  Auto-shutdown après {idle_shutdown_minutes} minutes d'inactivité")

        while True:
            try:
                logger.info("🔍 Recherche de nouveaux jobs highlights...")

                # Lister les fichiers .json dans le dossier queue
                job_files = drive_manager.list_files_in_folder(
                    queue_folder,
                    name_pattern='highlight_job_*.json'
                )

                if not job_files:
                    consecutive_empty_checks += 1
                    logger.info(f"📭 Aucun job en attente ({consecutive_empty_checks}/{max_idle_checks} avant auto-shutdown)")

                    if consecutive_empty_checks >= max_idle_checks:
                        logger.info(f"💤 {idle_shutdown_minutes} minutes d'inactivité - arrêt automatique de la VM")
                        import subprocess
                        subprocess.run(['sudo', 'shutdown', '-h', 'now'])
                        break
                else:
                    consecutive_empty_checks = 0
                    logger.info(f"📥 {len(job_files)} job(s) trouvé(s)")

                    for job_file in job_files:
                        process_highlights_job(
                            drive_manager,
                            video_extractor,
                            job_file,
                            config,
                            temp_dir
                        )
                        consecutive_empty_checks = 0

                logger.info(f"⏳ Attente {check_interval}s avant la prochaine vérification...")
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("🛑 Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle principale: {e}")
                import traceback
                logger.error(traceback.format_exc())
                logger.info(f"⏳ Pause de 30s avant reprise...")
                time.sleep(30)

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

    logger.info("👋 Highlights VM Worker arrêté")
    return 0


def mark_paragraphs_as_processed(drive_manager, base_name, is_reprocess, config):
    """Marque le document _paragraphs_timestamps comme PROCESSED ou REPROCESSED"""
    try:
        from googleapiclient.discovery import build

        # Chercher le doc paragraphs_timestamps
        transcriptions_folder = config['drive_folders']['transcriptions']
        search_name = f"{base_name}_paragraphs_timestamps"

        files = drive_manager.list_files_in_folder(
            transcriptions_folder,
            name_pattern=search_name
        )

        if not files:
            logger.warning(f"⚠️ Document paragraphs_timestamps non trouvé: {search_name}")
            return

        doc_file = files[0]
        file_id = doc_file['id']
        mime_type = doc_file.get('mimeType', '')

        if mime_type != 'application/vnd.google-apps.document':
            logger.warning(f"⚠️ Fichier n'est pas un Google Doc: {mime_type}")
            return

        # Utiliser l'API Docs pour ajouter la balise
        docs_service = build('docs', 'v1', credentials=drive_manager.creds)
        doc = docs_service.documents().get(documentId=file_id).execute()

        # Extraire le texte pour vérifier si c'est un retraitement
        content = doc.get('body', {}).get('content', [])
        if not content:
            logger.warning(f"⚠️ Document vide")
            return

        # Extraire le texte complet
        text_parts = []
        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                elements = paragraph.get('elements', [])
                for elem in elements:
                    if 'textRun' in elem:
                        text = elem['textRun'].get('content', '')
                        text_parts.append(text)

        full_text = ''.join(text_parts)

        # Vérifier si déjà marqué
        has_processed = ('🎬 PROCESSED 🎬' in full_text or '🎬PROCESSED🎬' in full_text or
                        '🎬 REPROCESSED 🎬' in full_text or '🎬REPROCESSED🎬' in full_text)

        # Choisir la balise appropriée
        tag = '🎬 REPROCESSED 🎬' if (is_reprocess or has_processed) else '🎬 PROCESSED 🎬'

        # Le dernier élément contient l'index de fin
        end_index = content[-1].get('endIndex', 1) - 1

        # Insérer la balise à la fin
        requests = [{
            'insertText': {
                'location': {'index': end_index},
                'text': f'\n\n{tag}\n'
            }
        }]

        docs_service.documents().batchUpdate(
            documentId=file_id,
            body={'requests': requests}
        ).execute()

        logger.info(f"✅ Balise {tag} ajoutée au document {search_name}")

    except Exception as e:
        logger.warning(f"⚠️ Erreur lors de l'ajout de la balise PROCESSED: {e}")
        import traceback
        logger.warning(traceback.format_exc())


def process_highlights_job(drive_manager, video_extractor, job_file, config, temp_dir):
    """Traite un job de highlights"""
    job_name = job_file['name']
    job_id = job_file['id']

    logger.info("=" * 60)
    logger.info(f"🎯 Traitement du job: {job_name}")

    try:
        # Télécharger le fichier job
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        drive_manager.download_file(job_id, job_name, temp_path)

        # Lire le contenu du job
        with open(temp_path, 'r') as f:
            job_data = json.load(f)

        os.remove(temp_path)

        excel_id = job_data.get('excel_id')
        excel_name = job_data.get('excel_name')
        source_id = job_data.get('source_id')
        source_name = job_data.get('source_name')
        base_name = job_data.get('base_name')
        is_reprocess = job_data.get('reprocess_requested', False)

        if not all([excel_id, source_id, base_name]):
            logger.error(f"❌ Job invalide: {job_name}")
            drive_manager.service.files().delete(fileId=job_id, supportsAllDrives=True).execute()
            return

        logger.info(f"📄 Excel: {excel_name}")
        logger.info(f"🎥 Vidéo: {source_name}")

        # 1. Télécharger l'Excel
        excel_path = temp_dir / f"{base_name}_highlights.xlsx"
        logger.info(f"📥 Téléchargement Excel...")
        drive_manager.download_file(excel_id, excel_name, str(excel_path))

        # 2. Télécharger la vidéo
        source_ext = Path(source_name).suffix
        source_path = temp_dir / f"{base_name}{source_ext}"
        logger.info(f"📥 Téléchargement vidéo {source_name} (cela peut prendre du temps)...")
        drive_manager.download_file(source_id, source_name, str(source_path))

        # 3. Créer dossier pour les segments
        segments_folder = temp_dir / f"{base_name}_segments"
        segments_folder.mkdir(exist_ok=True)

        # 4. Découper les segments
        logger.info(f"✂️ Découpage des segments...")
        created_segments = video_extractor.extract_segments(
            str(excel_path),
            str(source_path),
            str(segments_folder)
        )

        if not created_segments:
            logger.warning(f"⚠️ Aucun segment créé")
            # Marquer comme failed
            failed_folder = config['drive_folders'].get('failed_jobs')
            failed_name = job_name.replace('highlight_job_', 'failed_')

            if failed_folder:
                drive_manager.service.files().update(
                    fileId=job_id,
                    addParents=failed_folder,
                    removeParents=config['drive_folders']['queue_highlights'],
                    body={'name': failed_name},
                    supportsAllDrives=True
                ).execute()
                logger.info(f"⚠️  Job déplacé vers failed_jobs: {failed_name}")
            else:
                # Fallback: renommer en erreur dans la queue
                drive_manager.service.files().update(
                    fileId=job_id,
                    body={'name': failed_name},
                    supportsAllDrives=True
                ).execute()
                logger.info(f"⚠️  Job renommé: {failed_name}")
            return

        logger.info(f"✅ {len(created_segments)} segment(s) créé(s)")

        # 4b. Supprimer la vidéo source pour libérer de l'espace
        logger.info(f"🧹 Suppression de la vidéo source ({source_path.stat().st_size / 1024 / 1024:.1f} MB)...")
        source_path.unlink()
        logger.info(f"✅ Vidéo source supprimée")

        # 5. Créer sous-dossier sur Drive avec timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')
        subfolder_name = f"{base_name}_segments_{timestamp}"
        segments_output_folder = config['drive_folders']['segments_output']

        # Créer le sous-dossier avec timestamp unique
        folder_metadata = {
            'name': subfolder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [segments_output_folder]
        }
        folder = drive_manager.service.files().create(
            body=folder_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        subfolder_id = folder['id']
        logger.info(f"📁 Sous-dossier créé: {subfolder_name}")

        # 6. Upload les segments (et les supprimer un par un pour économiser la RAM)
        logger.info(f"📤 Upload des segments...")
        uploaded_count = 0
        for segment_path in created_segments:
            segment_name = Path(segment_path).name
            drive_manager.upload_file(
                segment_path,
                segment_name,
                subfolder_id
            )
            # Supprimer le segment immédiatement après upload
            Path(segment_path).unlink()
            uploaded_count += 1
            logger.info(f"✅ Segment uploadé et supprimé ({uploaded_count}/{len(created_segments)}): {segment_name}")

        logger.info(f"✅ {len(created_segments)} segment(s) uploadé(s)")

        # 7. Marquer le document paragraphs_timestamps comme PROCESSED/REPROCESSED
        logger.info(f"📝 Marquage du document comme {'REPROCESSED' if is_reprocess else 'PROCESSED'}...")
        mark_paragraphs_as_processed(drive_manager, base_name, is_reprocess, config)

        # 8. Nettoyer
        logger.info(f"🧹 Nettoyage...")
        import shutil
        for file in temp_dir.glob(f"{base_name}*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
            except Exception as e:
                logger.warning(f"Erreur nettoyage {file}: {e}")

        # 9. Marquer le job comme completed et le déplacer vers completed_jobs
        completed_folder = config['drive_folders'].get('completed_jobs')

        if completed_folder:
            logger.info(f"📦 Archivage du job dans completed_jobs...")
            completed_name = job_name.replace('highlight_job_', 'completed_')

            # Déplacer vers le dossier completed et renommer
            drive_manager.service.files().update(
                fileId=job_id,
                addParents=completed_folder,
                removeParents=config['drive_folders']['queue_highlights'],
                body={'name': completed_name},
                supportsAllDrives=True
            ).execute()
            logger.info(f"✅ Job archivé: {completed_name}")
        else:
            # Fallback: supprimer si pas de dossier completed configuré
            logger.info(f"🗑️  Suppression du job: {job_name}")
            drive_manager.service.files().delete(
                fileId=job_id,
                supportsAllDrives=True
            ).execute()

        logger.info(f"✅ Job terminé avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur traitement job {job_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Renommer en erreur
        try:
            error_name = job_name.replace('highlight_job_', 'highlight_error_')
            drive_manager.service.files().update(
                fileId=job_id,
                body={'name': error_name},
                supportsAllDrives=True
            ).execute()
            logger.info(f"⚠️  Job renommé en erreur: {error_name}")
        except Exception as rename_error:
            logger.warning(f"⚠️  Impossible de renommer le job: {rename_error}")


if __name__ == '__main__':
    exit(main())
