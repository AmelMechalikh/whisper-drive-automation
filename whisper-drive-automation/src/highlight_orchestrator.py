#!/usr/bin/env python3
"""
Orchestrateur pour le traitement automatique des highlights
Écoute le dossier "Highlighted Files" et traite les nouveaux fichiers
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from drive_manager import DriveManager
from highlight_extractor import HighlightExtractor
from video_segment_extractor import VideoSegmentExtractor


class HighlightOrchestrator:
    """
    Orchestrateur principal pour le workflow des highlights
    
    Workflow:
    1. Surveille le dossier "Highlighted Files" sur Drive
    2. Détecte les nouveaux fichiers _paragraphs_timestamps.txt annotés
    3. Extrait les timestamps → Génère Excel
    4. Upload Excel sur Drive
    5. Télécharge la vidéo source
    6. Découpe les segments
    7. Upload les segments sur Drive
    """
    
    def __init__(
        self,
        credentials_path: str,
        highlighted_folder_id: str,
        source_files_folder_id: str,
        transcriptions_folder_id: str,
        excel_output_folder_id: str,
        segments_output_folder_id: str,
        temp_dir: str = './temp_highlights',
        logger=None
    ):
        self.logger = logger or self._setup_logger()
        
        # Initialiser les composants
        self.drive_manager = DriveManager(credentials_path, self.logger)
        self.highlight_extractor = HighlightExtractor(self.logger)
        self.video_extractor = VideoSegmentExtractor(self.logger)
        
        # IDs des dossiers Drive
        self.highlighted_folder_id = highlighted_folder_id
        self.source_files_folder_id = source_files_folder_id
        self.transcriptions_folder_id = transcriptions_folder_id
        self.excel_output_folder_id = excel_output_folder_id
        self.segments_output_folder_id = segments_output_folder_id
        
        # Dossier temporaire local
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Historique des fichiers traités
        self.processed_files = set()
        
        # Service Drive pour accès API complet
        self.drive_service = self.drive_manager.service
    
    def _setup_logger(self):
        """Configure le logger"""
        logger = logging.getLogger('HighlightOrchestrator')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def process_highlighted_files(self) -> Dict:
        """
        Traite tous les nouveaux fichiers highlights
        
        Returns:
            Statistiques du traitement
        """
        self.logger.info("🔍 Recherche de nouveaux fichiers highlights...")
        
        # Lister les fichiers dans le dossier Highlighted Files
        files = self.drive_manager.list_files_in_folder(
            self.highlighted_folder_id,
            name_pattern='_paragraphs_timestamps'
        )
        
        new_files = [f for f in files if f['id'] not in self.processed_files]
        
        if not new_files:
            self.logger.info("📭 Aucun nouveau fichier highlight")
            return {'processed': 0, 'errors': 0}
        
        self.logger.info(f"📥 {len(new_files)} nouveau(x) fichier(s) highlight détecté(s)")
        
        stats = {'processed': 0, 'errors': 0}
        
        for file_info in new_files:
            try:
                self.logger.info(f"🎯 Traitement: {file_info['name']}")
                self._process_single_highlight(file_info)
                self.processed_files.add(file_info['id'])
                stats['processed'] += 1
            except Exception as e:
                self.logger.error(f"❌ Erreur traitement {file_info['name']}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def _process_single_highlight(self, file_info: Dict):
        """Traite un fichier highlight complet"""
        file_name = file_info['name']
        file_id = file_info['id']
        
        # Extraire le nom de base (sans _paragraphs_timestamps ou extension)
        base_name = file_name.replace('_paragraphs_timestamps.txt', '').replace('_paragraphs_timestamps', '')
        
        # Vérifier si le fichier a des commentaires
        comments_response = self.drive_service.comments().list(
            fileId=file_id,
            fields='comments(id)',
            includeDeleted=False
        ).execute()
        
        if not comments_response.get('comments'):
            self.logger.info(f"⏭️  Aucun commentaire sur {file_name}, ignoré")
            self.processed_files.add(file_id)
            return
        
        self.logger.info(f"💬 {len(comments_response['comments'])} commentaire(s) détecté(s)")
        
        # 1. Télécharger le fichier JSON complet correspondant
        self.logger.info(f"📥 Recherche du fichier JSON complet...")
        json_filename = f"{base_name}_complete_data.json"
        json_files = self.drive_manager.list_files_in_folder(
            self.transcriptions_folder_id,
            name_pattern=json_filename
        )
        
        if not json_files:
            raise FileNotFoundError(f"JSON complet non trouvé: {json_filename}")
        
        json_path = self.temp_dir / json_filename
        self.drive_manager.download_file(json_files[0]['id'], str(json_path))
        
        # 2. Extraire les highlights depuis les commentaires Google Docs
        self.logger.info(f"📊 Extraction des highlights depuis les commentaires...")
        excel_filename = f"{base_name}_highlights.xlsx"
        excel_path = self.temp_dir / excel_filename
        
        self.highlight_extractor.extract_highlights_from_drive_file(
            self.drive_service,
            file_id,
            str(json_path),
            str(excel_path)
        )
        
        # 3. Upload Excel sur Drive
        self.logger.info(f"📤 Upload Excel sur Drive...")
        excel_id = self.drive_manager.upload_file(
            str(excel_path),
            self.excel_output_folder_id,
            excel_filename
        )
        
        self.logger.info(f"✅ Excel créé: {excel_filename}")
        
        self.logger.info(f"✅ Traitement terminé pour {file_name}")
        self.logger.info(f"   📊 Excel disponible dans 'Highlights Excel'")
        self.logger.info(f"   ▶️  Pour découper la vidéo, lancez: python3 scripts/process_video_segments.py")
    
    def _cleanup_temp_files(self, base_name: str):
        """Nettoie les fichiers temporaires"""
        self.logger.info(f"🧹 Nettoyage des fichiers temporaires...")
        # Supprimer les fichiers temporaires pour ce traitement
        for file in self.temp_dir.glob(f"{base_name}*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    import shutil
                    shutil.rmtree(file)
            except Exception as e:
                self.logger.warning(f"Erreur nettoyage {file}: {e}")
    
    def process_files(self) -> dict:
        """
        Mode one-shot: traite tous les fichiers une fois puis s'arrête
        
        Returns:
            Statistiques du traitement
        """
        self.logger.info("🎯 Traitement one-shot démarré")
        
        try:
            stats = self.process_new_files()
            self.logger.info(f"📊 Stats: {stats}")
            return stats
        except Exception as e:
            self.logger.error(f"❌ Erreur dans le traitement: {e}")
            import traceback
            traceback.print_exc()
            return {'processed': 0, 'errors': 1}
    
    def watch_and_process(self, interval_seconds: int = 300):
        """
        Mode surveillance: vérifie périodiquement les nouveaux fichiers
        [DEPRECATED - Utilisé uniquement pour tests locaux]
        
        Args:
            interval_seconds: Intervalle entre chaque vérification (défaut: 5min)
        """
        self.logger.info(f"👀 Démarrage surveillance (intervalle: {interval_seconds}s)")
        self.logger.warning("⚠️ Mode polling - utilisez plutôt Cloud Run orchestrator en production")
        
        while True:
            try:
                stats = self.process_new_files()
                self.logger.info(f"📊 Stats: {stats}")
                
            except Exception as e:
                self.logger.error(f"❌ Erreur dans la boucle: {e}")
            
            self.logger.info(f"⏳ Attente {interval_seconds}s...")
            time.sleep(interval_seconds)


def main():
    """Point d'entrée principal"""
    # Configuration
    CREDENTIALS_PATH = 'config/credentials.json'
    HIGHLIGHTED_FOLDER_ID = 'YOUR_HIGHLIGHTED_FOLDER_ID'  # À créer
    SOURCE_FILES_FOLDER_ID = '1A29pkQvrBodU_HxNS8deYt6T27AlmbSe'  # Files
    TRANSCRIPTIONS_FOLDER_ID = '1yHcy9um2_We459w9I0cITwHBGXKTlOJa'  # Transcriptions
    EXCEL_OUTPUT_FOLDER_ID = 'YOUR_EXCEL_FOLDER_ID'  # À créer
    SEGMENTS_OUTPUT_FOLDER_ID = 'YOUR_SEGMENTS_FOLDER_ID'  # À créer
    
    orchestrator = HighlightOrchestrator(
        credentials_path=CREDENTIALS_PATH,
        highlighted_folder_id=HIGHLIGHTED_FOLDER_ID,
        source_files_folder_id=SOURCE_FILES_FOLDER_ID,
        transcriptions_folder_id=TRANSCRIPTIONS_FOLDER_ID,
        excel_output_folder_id=EXCEL_OUTPUT_FOLDER_ID,
        segments_output_folder_id=SEGMENTS_OUTPUT_FOLDER_ID
    )
    
    # Mode surveillance
    orchestrator.watch_and_process(interval_seconds=300)


if __name__ == '__main__':
    main()
