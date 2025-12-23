#!/usr/bin/env python3
"""
Process de découpage vidéo - Étape 2
Lit les fichiers Excel et découpe/fusionne les segments vidéo
"""

import sys
import json
import logging
from pathlib import Path
from typing import List, Dict

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drive_manager import DriveManager
from video_segment_extractor import VideoSegmentExtractor


class VideoSegmentProcessor:
    """Process les fichiers Excel pour découper et fusionner les vidéos"""
    
    def __init__(
        self,
        credentials_path: str,
        excel_folder_id: str,
        source_files_folder_id: str,
        segments_output_folder_id: str,
        temp_dir: str = './temp_video_segments',
        logger=None
    ):
        self.logger = logger or self._setup_logger()

        # Initialiser les composants
        self.drive_manager = DriveManager(credentials_path)
        self.video_extractor = VideoSegmentExtractor(self.logger)
        
        # IDs des dossiers
        self.excel_folder_id = excel_folder_id
        self.source_files_folder_id = source_files_folder_id
        self.segments_output_folder_id = segments_output_folder_id
        
        # Dossier temporaire
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Historique des fichiers traités
        self.processed_files = set()
    
    def _setup_logger(self):
        """Configure le logger"""
        logger = logging.getLogger('VideoSegmentProcessor')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def process_excel_files(self) -> Dict:
        """
        Traite tous les nouveaux fichiers Excel
        
        Returns:
            Statistiques du traitement
        """
        self.logger.info("🔍 Recherche de nouveaux fichiers Excel...")
        
        # Lister les fichiers Excel dans le dossier
        files = self.drive_manager.list_files_in_folder(
            self.excel_folder_id,
            name_pattern='_highlights.xlsx'
        )
        
        new_files = [f for f in files if f['id'] not in self.processed_files]
        
        if not new_files:
            self.logger.info("📭 Aucun nouveau fichier Excel")
            return {'processed': 0, 'errors': 0}
        
        self.logger.info(f"📥 {len(new_files)} nouveau(x) fichier(s) Excel détecté(s)")
        
        stats = {'processed': 0, 'errors': 0}
        
        for file_info in new_files:
            try:
                self.logger.info(f"🎯 Traitement: {file_info['name']}")
                self._process_single_excel(file_info)
                self.processed_files.add(file_info['id'])
                stats['processed'] += 1
            except Exception as e:
                self.logger.error(f"❌ Erreur traitement {file_info['name']}: {e}")
                import traceback
                traceback.print_exc()
                stats['errors'] += 1
        
        return stats
    
    def _process_single_excel(self, file_info: Dict):
        """Traite un fichier Excel complet"""
        file_name = file_info['name']
        file_id = file_info['id']
        
        # Extraire le nom de base (sans _highlights.xlsx)
        base_name = file_name.replace('_highlights.xlsx', '')
        
        # 1. Télécharger le fichier Excel
        self.logger.info(f"📥 Téléchargement Excel...")
        excel_path = self.temp_dir / file_name
        self.drive_manager.download_file(file_id, file_name, str(excel_path))
        
        # 2. Chercher la vidéo source
        self.logger.info(f"🎬 Recherche de la vidéo source: {base_name}")
        source_file = self._find_source_video(base_name)
        
        if not source_file:
            self.logger.warning(f"⚠️ Vidéo source non trouvée pour: {base_name}")
            self.logger.info(f"   Vérifiez que le fichier existe dans le dossier 'Files'")
            return
        
        # 3. Télécharger la vidéo source
        self.logger.info(f"📥 Téléchargement vidéo source: {source_file['name']}")
        source_ext = Path(source_file['name']).suffix
        source_path = self.temp_dir / f"{base_name}{source_ext}"
        self.drive_manager.download_file(source_file['id'], source_file['name'], str(source_path))
        
        # 4. Créer dossier pour les segments
        segments_folder = self.temp_dir / f"{base_name}_segments"
        segments_folder.mkdir(exist_ok=True)
        
        # 5. Extraire et fusionner les segments
        self.logger.info(f"✂️ Découpe et fusion des segments vidéo...")
        created_segments = self.video_extractor.extract_segments(
            str(excel_path),
            str(source_path),
            str(segments_folder)
        )
        
        if not created_segments:
            self.logger.warning(f"⚠️ Aucun segment créé")
            return
        
        # 6. Créer un sous-dossier pour cette vidéo
        self.logger.info(f"📁 Création du sous-dossier: {base_name}")
        subfolder_id = self._get_or_create_subfolder(base_name)
        
        # 7. Upload les segments dans le sous-dossier
        self.logger.info(f"📤 Upload des segments dans le sous-dossier...")
        for segment_path in created_segments:
            segment_name = Path(segment_path).name
            # Retirer le préfixe du nom de base pour éviter la redondance
            # Ex: "09.07_-_Guèn_Shri_highlight_01.mp4" -> "highlight_01.mp4"
            clean_name = segment_name.replace(f"{base_name}_", "")
            self.drive_manager.upload_file(
                segment_path,
                clean_name,
                subfolder_id
            )
        
        self.logger.info(f"✅ {len(created_segments)} segment(s) uploadé(s) dans {base_name}/")
        
        # 8. Nettoyage
        self._cleanup_temp_files(base_name)
    
    def _find_source_video(self, base_name: str) -> Dict:
        """Cherche la vidéo source correspondante"""
        video_extensions = ['.mp4', '.mp3', '.wav', '.m4a', '.mov', '.avi']
        
        for ext in video_extensions:
            search_name = f"{base_name}{ext}"
            files = self.drive_manager.list_files_in_folder(
                self.source_files_folder_id,
                name_pattern=search_name
            )
            if files:
                return files[0]
        
        return None
    
    def _get_or_create_subfolder(self, folder_name: str) -> str:
        """
        Récupère ou crée un sous-dossier dans segments_output
        
        Args:
            folder_name: Nom du sous-dossier
            
        Returns:
            ID du sous-dossier
        """
        # Chercher si le dossier existe déjà
        existing_folders = self.drive_manager.list_files_in_folder(
            self.segments_output_folder_id,
            name_pattern=folder_name
        )
        
        # Filtrer pour ne garder que les dossiers (pas les fichiers)
        for item in existing_folders:
            if item.get('mimeType') == 'application/vnd.google-apps.folder':
                self.logger.info(f"📁 Sous-dossier existant trouvé: {folder_name}")
                return item['id']
        
        # Créer le dossier s'il n'existe pas
        self.logger.info(f"📁 Création du sous-dossier: {folder_name}")
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [self.segments_output_folder_id]
        }
        
        folder = self.drive_manager.service.files().create(
            body=folder_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        return folder['id']
    
    def _cleanup_temp_files(self, base_name: str):
        """Nettoie les fichiers temporaires"""
        self.logger.info(f"🧹 Nettoyage des fichiers temporaires...")
        for file in self.temp_dir.glob(f"{base_name}*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    import shutil
                    shutil.rmtree(file)
            except Exception as e:
                self.logger.warning(f"Erreur nettoyage {file}: {e}")
    
    def watch_and_process(self, interval_seconds: int = 300):
        """
        Mode surveillance: vérifie périodiquement les nouveaux fichiers Excel
        [DEPRECATED - Utilisé uniquement pour tests locaux]
        
        Args:
            interval_seconds: Intervalle entre chaque vérification (défaut: 5min)
        """
        import time
        
        self.logger.info(f"👀 Démarrage surveillance (intervalle: {interval_seconds}s)")
        self.logger.warning("⚠️ Mode polling - utilisez plutôt Cloud Run orchestrator en production")
        
        while True:
            try:
                stats = self.process_excel_files()
                self.logger.info(f"📊 Stats: {stats}")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur dans la boucle: {e}")
            
            self.logger.info(f"⏳ Attente {interval_seconds}s...")
            time.sleep(interval_seconds)


def setup_logging():
    """Configure le logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('video_segment_processor.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('VideoSegmentProcessor')


def load_config(config_path):
    """Charge la configuration"""
    with open(config_path) as f:
        return json.load(f)


def main():
    """Point d'entrée principal"""
    logger = setup_logging()
    
    logger.info("🚀 Démarrage du Video Segment Processor")
    
    # Chemins
    script_dir = Path(__file__).parent.parent
    credentials_path = script_dir / 'config' / 'credentials.json'
    config_path = script_dir / 'config' / 'highlight_config.json'
    
    # Charger la configuration
    logger.info("📖 Chargement de la configuration...")
    config = load_config(config_path)
    folders = config['drive_folders']
    processing = config['processing']
    
    # Initialiser le processor
    logger.info("🔧 Initialisation du processor...")
    processor = VideoSegmentProcessor(
        credentials_path=str(credentials_path),
        excel_folder_id=folders['excel_output'],
        source_files_folder_id=folders['source_files'],
        segments_output_folder_id=folders['segments_output'],
        temp_dir=processing.get('temp_dir_video', './temp_video_segments'),
        logger=logger
    )
    
    # Mode one-shot : traiter une fois puis s'arrêter
    logger.info("🎯 Traitement des fichiers Excel (mode one-shot)...")
    stats = processor.process_excel_files()
    
    logger.info(f"📊 Statistiques finales: {stats}")
    logger.info("✅ Traitement terminé - VM prête à s'éteindre")


if __name__ == '__main__':
    main()
