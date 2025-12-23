#!/usr/bin/env python3
"""
Cloud Run Service pour le système de highlights
Traite directement les fichiers (pas de VM intermédiaire)
"""

import os
import sys
import json
import logging
from pathlib import Path
from flask import Flask, request, jsonify

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, '/app/src')

from drive_manager import DriveManager
from highlight_extractor import HighlightExtractor
from video_segment_extractor import VideoSegmentExtractor

app = Flask(__name__)
logger = logging.getLogger(__name__)


class HighlightsProcessor:
    """Traite les highlights en mode serverless (sans VM)"""
    
    def __init__(self, config: dict, credentials_path: str):
        self.config = config
        self.credentials_path = credentials_path
        
        # Initialiser les composants
        self.drive_manager = DriveManager(credentials_path)
        self.highlight_extractor = HighlightExtractor()
        self.video_extractor = VideoSegmentExtractor()
        
        # Dossiers temporaires
        self.temp_dir = Path('/tmp/highlights')
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Historique des fichiers traités (en mémoire, réinitialisé à chaque instance)
        self.processed_files = set()
    
    def check_new_highlighted_files(self) -> list:
        """
        Vérifie s'il y a de nouveaux fichiers avec commentaires
        
        Returns:
            Liste des fichiers Google Docs avec commentaires
        """
        logger.info("🔍 Vérification Highlighted Files...")
        
        highlighted_files = self.drive_manager.list_files_in_folder(
            self.config['drive_folders']['highlighted_files']
        )
        
        result = []
        for file_info in highlighted_files:
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
                logger.debug(f"⏭️  Ignoré (déjà traité): {file_info['name']}")
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
            
            # Vérifier si le fichier a des commentaires
            try:
                comments = self.drive_manager.service.comments().list(
                    fileId=file_info['id'],
                    fields='comments(id)'
                ).execute()
                
                if comments.get('comments'):
                    result.append(file_info)
                    logger.info(f"✅ Trouvé: {file_info['name']} (avec commentaires)")
            except Exception as e:
                logger.warning(f"Erreur vérification commentaires {file_info['name']}: {e}")
        
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
            
            # Marquer comme traité
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
        """Traite un Excel → découpe les vidéos"""
        excel_name = excel_info['name']
        excel_id = excel_info['id']
        base_name = excel_name.replace('_highlights.xlsx', '')
        
        logger.info(f"🎬 Traitement Excel: {excel_name}")
        
        try:
            # 1. Télécharger l'Excel
            excel_path = self.temp_dir / excel_name
            self.drive_manager.download_file(excel_id, str(excel_path))
            
            # 2. Trouver la vidéo source
            source_file = self._find_source_video(base_name)
            if not source_file:
                logger.warning(f"⚠️ Vidéo source non trouvée pour: {base_name}")
                return None
            
            # 3. Télécharger la vidéo
            source_ext = Path(source_file['name']).suffix
            source_path = self.temp_dir / f"{base_name}{source_ext}"
            logger.info(f"📥 Téléchargement: {source_file['name']}")
            self.drive_manager.download_file(source_file['id'], str(source_path))
            
            # 4. Créer dossier pour les segments
            segments_folder = self.temp_dir / f"{base_name}_segments"
            segments_folder.mkdir(exist_ok=True)
            
            # 5. Découper les segments
            logger.info(f"✂️ Découpage des segments...")
            created_segments = self.video_extractor.extract_segments(
                str(excel_path),
                str(source_path),
                str(segments_folder)
            )
            
            if not created_segments:
                logger.warning(f"⚠️ Aucun segment créé")
                return None
            
            # 6. Créer sous-dossier sur Drive
            subfolder_id = self._get_or_create_subfolder(base_name)
            
            # 7. Upload les segments
            logger.info(f"📤 Upload des segments...")
            for segment_path in created_segments:
                segment_name = Path(segment_path).name
                clean_name = segment_name.replace(f"{base_name}_", "")
                self.drive_manager.upload_file(
                    segment_path,
                    subfolder_id,
                    clean_name
                )
            
            logger.info(f"✅ {len(created_segments)} segment(s) uploadé(s)")
            
            # 8. Nettoyer
            self._cleanup_files(base_name)
            
            return len(created_segments)
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement Excel {excel_name}: {e}")
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
            fields='id'
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
