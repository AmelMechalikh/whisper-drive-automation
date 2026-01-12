#!/usr/bin/env python3
"""
Cloud Run Service pour le système de highlights
Traite directement les fichiers (pas de VM intermédiaire)
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, '/app/src')

from drive_manager import DriveManager
from highlight_extractor import HighlightExtractor
from video_segment_extractor import VideoSegmentExtractor

# Import pour gérer la VM
from google.cloud import compute_v1

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Configuration VM
PROJECT_ID = "artificial-intelligence-cmk"
ZONE = "europe-west1-b"
VM_NAME = "highlights-worker-vm"


class HighlightsProcessor:
    """Traite les highlights en mode serverless (sans VM)"""
    
    def __init__(self, config: dict, credentials_path: str):
        self.config = config
        self.credentials_path = credentials_path
        
        # Initialiser les composants
        self.drive_manager = DriveManager(credentials_path)
        self.highlight_extractor = HighlightExtractor(logger)
        self.video_extractor = VideoSegmentExtractor(logger)
        
        # Dossiers temporaires
        self.temp_dir = Path('/tmp/highlights')
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Historique des fichiers traités (en mémoire, réinitialisé à chaque instance)
        self.processed_files = set()
    
    def check_new_highlighted_files(self) -> list:
        """
        Vérifie s'il y a de nouveaux fichiers marqués comme PRÊT dans le dossier transcriptions

        Returns:
            Liste des fichiers Google Docs _paragraphs_timestamps avec balise READY
        """
        logger.info("🔍 Vérification fichiers PRÊTS dans transcriptions...")

        # Scanner le dossier transcriptions au lieu de highlighted_files
        transcription_files = self.drive_manager.list_files_in_folder(
            self.config['drive_folders']['transcriptions']
        )

        result = []
        for file_info in transcription_files:
            # Ne traiter que les fichiers _paragraphs_timestamps
            if '_paragraphs_timestamps' not in file_info['name']:
                continue

            logger.info(f"📄 Fichier détecté: {file_info['name']} (type: {file_info.get('mimeType', 'unknown')})")

            # Accepter Google Docs ET fichiers texte
            mime_type = file_info.get('mimeType', '')
            accepted_types = [
                'application/vnd.google-apps.document',  # Google Doc
                'text/plain',                             # Fichier .txt
                'text/x-log',                             # Fichiers log
            ]

            if mime_type not in accepted_types:
                logger.debug(f"⏭️  Ignoré (type non supporté): {file_info['name']}")
                continue

            # Skip si déjà traité dans cette instance
            if file_info['id'] in self.processed_files:
                logger.info(f"⏭️  Ignoré (déjà traité dans cette instance): {file_info['name']}")
                continue

            # Extraire le nom de base pour vérifier si Excel existe déjà
            base_name_check = file_info['name']
            for suffix in ['_paragraphs_timestamps.txt', '_paragraphs_timestamps', '__paragraphs_timestamps.txt', '__paragraphs_timestamps']:
                if base_name_check.endswith(suffix):
                    base_name_check = base_name_check[:-len(suffix)]
                    break

            # Vérifier si un Excel existe déjà pour ce fichier
            excel_name = f"{base_name_check}_highlights.xlsx"
            existing_excel = self.drive_manager.list_files_in_folder(
                self.config['drive_folders']['excel_output'],
                name_pattern=excel_name
            )
            if existing_excel:
                logger.info(f"⏭️  Ignoré (Excel existe déjà): {file_info['name']} → {excel_name}")
                self.processed_files.add(file_info['id'])  # Marquer comme traité
                continue

            # Vérifier si le fichier a la balise READY
            try:
                # Récupérer le contenu du document
                if mime_type == 'application/vnd.google-apps.document':
                    # Google Doc - utiliser l'API Docs
                    from googleapiclient.discovery import build
                    docs_service = build('docs', 'v1', credentials=self.drive_manager.creds)
                    doc = docs_service.documents().get(documentId=file_info['id']).execute()

                    # Extraire le texte
                    content = doc.get('body', {}).get('content', [])
                    text = ''
                    for element in content:
                        if 'paragraph' in element:
                            for text_run in element['paragraph'].get('elements', []):
                                if 'textRun' in text_run:
                                    text += text_run['textRun'].get('content', '')
                else:
                    # Fichier texte - télécharger et lire
                    import io
                    request = self.drive_manager.service.files().get_media(fileId=file_info['id'])
                    file_content = io.BytesIO()
                    from googleapiclient.http import MediaIoBaseDownload
                    downloader = MediaIoBaseDownload(file_content, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                    text = file_content.getvalue().decode('utf-8')

                # Vérifier les balises
                has_ready = '🎬 READY 🎬' in text or '🎬READY🎬' in text
                has_processed = '🎬 PROCESSED 🎬' in text or '🎬PROCESSED🎬' in text

                if has_processed:
                    logger.info(f"⏭️  Ignoré (déjà traité - balise PROCESSED): {file_info['name']}")
                    self.processed_files.add(file_info['id'])
                    continue

                if has_ready:
                    result.append(file_info)
                    logger.info(f"✅ Trouvé: {file_info['name']} (marqué PRÊT)")
                else:
                    logger.info(f"⏭️  Ignoré (pas de balise READY): {file_info['name']}")
                    logger.info(f"   Texte début: {text[:200]}")

            except Exception as e:
                logger.info(f"❌ Erreur vérification balise READY pour {file_info['name']}: {e}")
                import traceback
                logger.info(f"   Traceback: {traceback.format_exc()}")

        return result
    
    def check_new_excel_files(self) -> list:
        """
        Vérifie s'il y a de nouveaux fichiers Excel non traités
        
        Returns:
            Liste des fichiers Excel non traités
        """
        logger.info("🔍 Vérification Excel files...")
        
        excel_files = self.drive_manager.list_files_in_folder(
            self.config['drive_folders']['excel_output'],
            name_pattern='_highlights.xlsx'
        )
        
        result = []
        for excel_file in excel_files:
            # Skip si déjà traité dans cette instance
            if excel_file['id'] in self.processed_files:
                continue
            
            base_name = excel_file['name'].replace('_highlights.xlsx', '')
            
            # Chercher un sous-dossier correspondant dans Segments Videos
            segments_folders = self.drive_manager.list_files_in_folder(
                self.config['drive_folders']['segments_output'],
                name_pattern=base_name
            )
            
            # Si pas de dossier trouvé, le fichier n'a pas été traité
            folder_exists = any(
                f.get('mimeType') == 'application/vnd.google-apps.folder' 
                for f in segments_folders
            )
            
            if not folder_exists:
                result.append(excel_file)
                logger.info(f"✅ Trouvé: {excel_file['name']} (non traité)")
        
        return result

    def mark_as_processed(self, file_id: str, mime_type: str):
        """
        Marque un fichier comme PROCESSED en ajoutant la balise à la fin

        Args:
            file_id: ID du fichier Google Doc
            mime_type: Type MIME du fichier
        """
        try:
            if mime_type == 'application/vnd.google-apps.document':
                # Google Doc - utiliser l'API Docs
                from googleapiclient.discovery import build
                docs_service = build('docs', 'v1', credentials=self.drive_manager.creds)

                # Récupérer le document pour obtenir l'index de fin
                doc = docs_service.documents().get(documentId=file_id).execute()

                # Calculer l'index de la fin du document
                content = doc.get('body', {}).get('content', [])
                if not content:
                    logger.warning(f"Document vide, impossible d'ajouter la balise PROCESSED")
                    return

                # Le dernier élément contient l'index de fin
                end_index = content[-1].get('endIndex', 1) - 1

                # Insérer la balise PROCESSED à la fin
                requests = [{
                    'insertText': {
                        'location': {
                            'index': end_index
                        },
                        'text': '\n\n🎬 PROCESSED 🎬\n'
                    }
                }]

                docs_service.documents().batchUpdate(
                    documentId=file_id,
                    body={'requests': requests}
                ).execute()

                logger.info(f"✅ Balise PROCESSED ajoutée au document")

            # Pour les fichiers texte, on ne peut pas les modifier facilement via l'API
            # On skip pour l'instant
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de l'ajout de la balise PROCESSED: {e}")

    def process_highlighted_file(self, file_info: dict):
        """Traite un fichier avec commentaires → génère Excel"""
        file_name = file_info['name']
        file_id = file_info['id']
        
        logger.info(f"📋 Traitement: {file_name}")
        
        try:
            # Extraire le nom de base (enlever les suffixes possibles)
            base_name = file_name
            # Enlever les extensions et suffixes
            for suffix in ['_paragraphs_timestamps.txt', '_paragraphs_timestamps', '__paragraphs_timestamps.txt', '__paragraphs_timestamps']:
                if base_name.endswith(suffix):
                    base_name = base_name[:-len(suffix)]
                    break
            
            logger.info(f"🔍 Nom de base extrait: '{base_name}'")
            logger.info(f"🔍 Recherche du complete_data.json pour: {base_name}")
            
            # Chercher le fichier _complete_data.json (ou __complete_data.json) correspondant
            complete_json_files = self.drive_manager.search_files(
                self.config['drive_folders']['transcriptions'],
                f"{base_name}_complete_data.json"
            )
            
            # Si pas trouvé avec 1 underscore, essayer avec 2 underscores
            if not complete_json_files:
                logger.debug(f"Pas trouvé avec 1 underscore, essai avec 2...")
                complete_json_files = self.drive_manager.search_files(
                    self.config['drive_folders']['transcriptions'],
                    f"{base_name}__complete_data.json"
                )
            
            if not complete_json_files:
                logger.warning(f"⚠️ Aucun _complete_data.json trouvé pour {base_name}")
                return None
            
            complete_json_id = complete_json_files[0]['id']
            logger.info(f"✅ Trouvé _complete_data.json: {complete_json_files[0]['name']}")
            
            # Télécharger le complete_data.json
            complete_json_path = self.temp_dir / f"{base_name}_complete_data.json"
            self.drive_manager.download_file(
                complete_json_id,
                complete_json_files[0]['name'],
                str(complete_json_path)
            )
            
            # Générer le fichier Excel
            output_excel_path = self.temp_dir / f"{base_name}_highlights.xlsx"

            # Choisir la méthode d'extraction selon la config
            extraction_method = self.config.get('processing', {}).get('extraction_method', 'comments')

            if extraction_method == 'inline_markers':
                logger.info("🎬 Utilisation de la méthode: balises inline")
                excel_path = self.highlight_extractor.extract_highlights_from_inline_markers(
                    document_id=file_id,
                    credentials_path=self.credentials_path,
                    complete_json_path=str(complete_json_path),
                    output_excel_path=str(output_excel_path)
                )
            else:
                logger.info("💬 Utilisation de la méthode: commentaires")
                excel_path = self.highlight_extractor.extract_highlights_from_drive_file(
                    drive_service=self.drive_manager.service,
                    paragraph_file_id=file_id,
                    complete_json_path=str(complete_json_path),
                    output_excel_path=str(output_excel_path)
                )
            
            if not excel_path:
                logger.warning(f"⚠️ Aucun highlight extrait pour {file_name}")
                return None
            
            # Upload l'Excel sur Drive
            excel_filename = Path(excel_path).name
            excel_id = self.drive_manager.upload_file(
                excel_path,
                excel_filename,
                self.config['drive_folders']['excel_output']
            )
            
            logger.info(f"✅ Excel créé et uploadé: {excel_filename} (ID: {excel_id})")

            # Marquer le document comme PROCESSED
            self.mark_as_processed(file_id, file_info.get('mimeType', ''))

            # Marquer comme traité dans cette instance
            self.processed_files.add(file_id)

            return excel_path
            
            logger.info(f"✅ Excel créé: {excel_filename}")
            
            # Nettoyer
            Path(excel_path).unlink()
            
            return excel_filename
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement {file_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def process_excel_file(self, excel_info: dict):
        """Crée un job pour traiter un Excel → la VM s'en occupera"""
        excel_name = excel_info['name']
        excel_id = excel_info['id']
        base_name = excel_name.replace('_highlights.xlsx', '')

        logger.info(f"🎬 Création job pour Excel: {excel_name}")

        try:
            # 1. Trouver la vidéo source
            source_file = self._find_source_video(base_name)
            if not source_file:
                logger.warning(f"⚠️ Vidéo source non trouvée pour: {base_name}")
                return None

            # 2. Créer le job JSON
            job_data = {
                'excel_id': excel_id,
                'excel_name': excel_name,
                'source_id': source_file['id'],
                'source_name': source_file['name'],
                'base_name': base_name,
                'created_at': datetime.now().isoformat()
            }

            # 3. Uploader le job dans queue_highlights
            job_filename = f"highlight_job_{base_name}_{int(time.time())}.json"
            job_local_path = self.temp_dir / job_filename

            with open(job_local_path, 'w') as f:
                json.dump(job_data, f, indent=2)

            queue_folder = self.config['drive_folders']['queue_highlights']
            job_id = self.drive_manager.upload_file(
                str(job_local_path),
                job_filename,
                queue_folder
            )

            # Nettoyer le fichier local
            job_local_path.unlink()

            logger.info(f"✅ Job créé: {job_filename}")
            logger.info(f"   Vidéo: {source_file['name']} (sera traitée par la VM)")

            # Marquer comme traité pour ne pas recréer le job
            self.processed_files.add(excel_id)

            return 1  # 1 job créé

        except Exception as e:
            logger.error(f"❌ Erreur création job pour {excel_name}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _find_source_video(self, base_name: str) -> dict:
        """Cherche la vidéo source correspondante"""
        video_extensions = ['.mp4', '.mp3', '.wav', '.m4a', '.mov', '.avi']
        
        for ext in video_extensions:
            search_name = f"{base_name}{ext}"
            files = self.drive_manager.list_files_in_folder(
                self.config['drive_folders']['source_files'],
                name_pattern=search_name
            )
            if files:
                return files[0]
        
        return None
    
    def _get_or_create_subfolder(self, folder_name: str) -> str:
        """Récupère ou crée un sous-dossier dans segments_output"""
        # Chercher si le dossier existe
        existing_folders = self.drive_manager.list_files_in_folder(
            self.config['drive_folders']['segments_output'],
            name_pattern=folder_name
        )
        
        for item in existing_folders:
            if item.get('mimeType') == 'application/vnd.google-apps.folder':
                return item['id']
        
        # Créer le dossier
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.config['drive_folders']['segments_output']]
        }
        
        folder = self.drive_manager.service.files().create(
            body=folder_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        return folder['id']
    
    def _cleanup_files(self, base_name: str):
        """Nettoie les fichiers temporaires"""
        import shutil
        for file in self.temp_dir.glob(f"{base_name}*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
            except Exception as e:
                logger.warning(f"Erreur nettoyage {file}: {e}")
                logger.warning(f"Erreur nettoyage {file}: {e}")

    def start_vm_if_needed(self):
        """Démarre la VM highlights si elle est arrêtée"""
        try:
            logger.info(f"🔍 Vérification état de la VM {VM_NAME}...")

            # Créer un client Compute Engine
            instances_client = compute_v1.InstancesClient()

            # Récupérer l'état de la VM
            instance = instances_client.get(
                project=PROJECT_ID,
                zone=ZONE,
                instance=VM_NAME
            )

            vm_status = instance.status
            logger.info(f"📊 État VM: {vm_status}")

            if vm_status == 'TERMINATED':
                logger.info(f"🚀 Démarrage de la VM {VM_NAME}...")

                # Démarrer la VM avec l'API
                operation = instances_client.start(
                    project=PROJECT_ID,
                    zone=ZONE,
                    instance=VM_NAME
                )

                logger.info(f"✅ Commande de démarrage envoyée - Operation: {operation.name}")
                logger.info(f"💡 La VM démarrera et le worker s'auto-lancera. Auto-shutdown après 10 min d'inactivité.")

            elif vm_status == 'RUNNING':
                logger.info(f"✅ VM {VM_NAME} déjà en cours d'exécution")
            else:
                logger.warning(f"⚠️  État VM inattendu: {vm_status}")

        except Exception as vm_error:
            logger.warning(f"⚠️  Erreur gestion VM: {vm_error}")
            import traceback
            logger.warning(traceback.format_exc())

    def process(self) -> dict:
        """
        Processus principal de traitement
        
        Returns:
            dict avec le statut et les statistiques
        """
        result = {
            'status': 'success',
            'highlighted_files_processed': 0,
            'excel_files_processed': 0,
            'segments_created': 0,
            'errors': []
        }
        
        try:
            # 1. Traiter les fichiers avec commentaires
            highlighted_files = self.check_new_highlighted_files()
            
            for file_info in highlighted_files:
                try:
                    excel_name = self.process_highlighted_file(file_info)
                    if excel_name:
                        result['highlighted_files_processed'] += 1
                        self.processed_files.add(file_info['id'])
                except Exception as e:
                    result['errors'].append(f"Highlighted file {file_info['name']}: {str(e)}")
            
            # 2. Traiter les fichiers Excel
            excel_files = self.check_new_excel_files()
            
            for excel_info in excel_files:
                try:
                    segments_count = self.process_excel_file(excel_info)
                    if segments_count:
                        result['excel_files_processed'] += 1
                        result['segments_created'] += segments_count
                        self.processed_files.add(excel_info['id'])
                except Exception as e:
                    result['errors'].append(f"Excel file {excel_info['name']}: {str(e)}")

            # 3. Démarrer la VM si des jobs ont été créés
            if result['excel_files_processed'] > 0:
                logger.info(f"📥 {result['excel_files_processed']} job(s) créé(s) - démarrage de la VM...")
                self.start_vm_if_needed()

            if result['errors']:
                result['status'] = 'partial_success'
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur dans le processus: {e}")
            import traceback
            traceback.print_exc()
            result['status'] = 'error'
            result['errors'].append(str(e))
            return result


# Configuration globale (sera chargée au démarrage)
processor = None


@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'highlights-processor'})


@app.route('/trigger', methods=['POST', 'GET'])
def trigger():
    """
    Endpoint principal - traite les fichiers directement
    Peut être appelé par Cloud Scheduler (GET ou POST)
    """
    global processor
    
    if processor is None:
        return jsonify({'error': 'Processor not initialized'}), 500
    
    logger.info("🎯 Trigger reçu - traitement des fichiers...")
    
    try:
        result = processor.process()
        
        logger.info(f"📊 Résultat: {result}")
        
        status_code = 200 if result['status'] in ['success', 'partial_success'] else 500
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"❌ Erreur dans /trigger: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/status', methods=['GET'])
def status():
    """Endpoint pour vérifier le statut"""
    global processor
    
    if processor is None:
        return jsonify({'error': 'Processor not initialized'}), 500
    
    highlighted_files = processor.check_new_highlighted_files()
    excel_files = processor.check_new_excel_files()
    
    return jsonify({
        'status': 'ready',
        'pending_files': {
            'highlighted_files_count': len(highlighted_files),
            'excel_files_count': len(excel_files)
        }
    })


def setup_logging():
    """Configure le logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def load_config():
    """Charge la configuration"""
    # Chercher dans plusieurs emplacements possibles
    possible_paths = [
        Path('/app/config/highlight_config.json'),  # Cloud Run
        Path(__file__).parent.parent / 'config' / 'highlight_config.json',  # Local
    ]
    
    for config_path in possible_paths:
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
    
    raise FileNotFoundError(f"highlight_config.json introuvable dans: {[str(p) for p in possible_paths]}")


def init_processor():
    """Initialise le processor au démarrage du Cloud Run"""
    global processor, logger
    
    logger = setup_logging()
    logger.info("🚀 Initialisation du Highlights Processor...")
    
    # Chercher credentials dans plusieurs emplacements
    possible_creds = [
        Path('/app/config/credentials.json'),  # Cloud Run
        Path(__file__).parent.parent / 'config' / 'credentials.json',  # Local
    ]
    
    credentials_path = None
    for path in possible_creds:
        if path.exists():
            credentials_path = path
            break
    
    if not credentials_path:
        raise FileNotFoundError(f"credentials.json introuvable dans: {[str(p) for p in possible_creds]}")
    
    # Charger la configuration
    config = load_config()
    
    # Initialiser le processor
    processor = HighlightsProcessor(config, str(credentials_path))
    
    logger.info("✅ Processor initialisé")


# Initialiser au démarrage (sauf si en mode test)
if not os.environ.get('PYTEST_CURRENT_TEST'):
    init_processor()


if __name__ == '__main__':
    # Mode développement local
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
