"""
Orchestrateur léger pour Cloud Run
Gère uniquement la détection de fichiers et création de jobs - pas de transcription
"""
import logging
import os
from pathlib import Path

from .drive_manager import DriveManager


class DriveOrchestrator:
    """Orchestrateur léger pour Cloud Run - sans Whisper"""
    
    def __init__(self, config):
        """
        Initialise l'orchestrateur avec la configuration
        
        Args:
            config: Module de configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialisation uniquement du Drive Manager
        self.drive_manager = None
        
        self._setup_logging()
        self._initialize_components()
    
    def _setup_logging(self):
        """Configure le logging"""
        logging.basicConfig(
            level=getattr(logging, self.config.LOGGING_CONFIG['level']),
            format=self.config.LOGGING_CONFIG['format'],
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(self.config.LOGGING_CONFIG['file'])
            ]
        )
    
    def _initialize_components(self):
        """Initialise le Drive Manager uniquement"""
        try:
            # Google Drive seulement
            self.drive_manager = DriveManager(self.config.CREDENTIALS_PATH)
            
            self.logger.info("✅ Orchestrateur Cloud Run configuré (Drive only)")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation orchestrateur: {e}")
            raise
    
    def test_drive_access(self):
        """Teste l'accès aux dossiers Google Drive"""
        self.logger.info("🧪 Test d'accès aux dossiers...")
        
        folders = self.config.DRIVE_FOLDERS
        
        # Test dossier d'entrée
        if not self.drive_manager.test_folder_access(folders['input'], "Files"):
            raise Exception("Dossier d'entrée inaccessible")
        
        # Test dossier de sortie
        if not self.drive_manager.test_folder_access(folders['output'], "Transcriptions"):
            raise Exception("Dossier de sortie inaccessible")
        
        # Test dossier queue
        if not self.drive_manager.test_folder_access(folders.get('queue', folders['output']), "Queue"):
            raise Exception("Dossier queue inaccessible")
    
    def get_audio_files(self):
        """Récupère la liste des fichiers audio à traiter"""
        folder_id = self.config.DRIVE_FOLDERS['input']
        extensions = self.config.SUPPORTED_EXTENSIONS
        
        return self.drive_manager.list_audio_files(folder_id, extensions)
    
    def check_transcription_exists(self, base_filename):
        """
        Vérifie si une transcription existe déjà
        
        Args:
            base_filename: Nom du fichier sans extension
            
        Returns:
            bool: True si la transcription existe
        """
        output_folder_id = self.config.DRIVE_FOLDERS['output']
        return self.drive_manager.transcription_exists(base_filename, output_folder_id)
