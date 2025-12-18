"""
Processeur principal pour l'automation Whisper + Google Drive
Orchestration complète du workflow
"""
import logging
import tempfile
import os
from pathlib import Path

from .drive_manager import DriveManager
from .whisper_transcriber import WhisperTranscriber
from .output_generator import OutputGenerator

class WhisperDriveProcessor:
    """Processeur principal pour l'automation complète"""
    
    def __init__(self, config):
        """
        Initialise le processeur avec la configuration
        
        Args:
            config: Module de configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialisation des composants
        self.drive_manager = None
        self.transcriber = None
        self.output_generator = None
        
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
        """Initialise tous les composants"""
        try:
            # Google Drive
            self.drive_manager = DriveManager(self.config.CREDENTIALS_PATH)
            
            # Whisper Transcriber
            whisper_config = self.config.WHISPER_CONFIG
            self.transcriber = WhisperTranscriber(
                model=whisper_config['model'],
                device=whisper_config['device'],
                language=whisper_config.get('language')
            )
            
            # Ajouter le vocabulaire technique si disponible
            if 'vocabulary' in whisper_config:
                self.transcriber.vocabulary = whisper_config['vocabulary']
            
            # Output Generator
            self.output_generator = OutputGenerator()
            
            self.logger.info("✅ Configuration terminée")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur initialisation: {e}")
            raise
    
    def run_full_process(self):
        """Lance le processus complet d'automation"""
        try:
            self.logger.info("🚀 Début du traitement des fichiers")
            
            # Test d'accès aux dossiers
            self._test_drive_access()
            
            # Récupération des fichiers audio
            audio_files = self._get_audio_files()
            
            if not audio_files:
                self.logger.info("📭 Aucun fichier audio trouvé")
                return
            
            # Traitement de chaque fichier
            for file_info in audio_files:
                self._process_single_file(file_info)
            
            self.logger.info("🏁 Traitement terminé!")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur processus principal: {e}")
            raise
    
    def process_recent_files(self, hours_back=1):
        """
        Traite les fichiers ajoutés récemment
        
        Args:
            hours_back: Nombre d'heures en arrière pour chercher les nouveaux fichiers
            
        Returns:
            dict: Résultats du traitement avec files processed/skipped/errors
        """
        from datetime import datetime, timedelta
        
        self.logger.info(f"🔍 Recherche de fichiers récents (dernières {hours_back}h)")
        
        try:
            # Test d'accès préliminaire
            self._test_drive_access()
            
            # Récupération des fichiers avec filtre temporel
            recent_files = self.drive_manager.list_recent_audio_files(
                self.config.DRIVE_FOLDERS['input'], 
                self.config.SUPPORTED_EXTENSIONS,
                hours_back=hours_back
            )
            
            results = {
                'processed': [],
                'skipped': [],
                'errors': []
            }
            
            if not recent_files:
                self.logger.info(f"📭 Aucun fichier récent trouvé (dernières {hours_back}h)")
                return results
            
            self.logger.info(f"📁 {len(recent_files)} fichiers récents trouvés")
            
            # Traitement de chaque fichier récent
            for file_info in recent_files:
                try:
                    success = self._process_single_file(file_info)
                    if success:
                        results['processed'].append(file_info['name'])
                    else:
                        results['skipped'].append(file_info['name'])
                except Exception as e:
                    self.logger.error(f"❌ Erreur sur {file_info['name']}: {e}")
                    results['errors'].append({
                        'file': file_info['name'],
                        'error': str(e)
                    })
            
            self.logger.info(f"📊 Résultats: {len(results['processed'])} traités, {len(results['skipped'])} ignorés, {len(results['errors'])} erreurs")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur traitement récent: {e}")
            raise
    
    def process_single_file(self, file_id):
        """
        Traite un fichier spécifique par son ID
        
        Args:
            file_id: ID du fichier Google Drive
            
        Returns:
            bool: True si succès, False sinon
        """
        try:
            # Récupérer les infos du fichier
            file_info = self.drive_manager.get_file_info(file_id)
            if not file_info:
                self.logger.error(f"❌ Fichier {file_id} introuvable")
                return False
            
            return self._process_single_file(file_info)
            
        except Exception as e:
            self.logger.error(f"❌ Erreur traitement fichier {file_id}: {e}")
            return False
    
    def _test_drive_access(self):
        """Teste l'accès aux dossiers Google Drive"""
        self.logger.info("🧪 Test d'accès aux dossiers...")
        
        folders = self.config.DRIVE_FOLDERS
        
        # Test dossier d'entrée
        if not self.drive_manager.test_folder_access(folders['input'], "Files"):
            raise Exception("Dossier d'entrée inaccessible")
        
        # Test dossier de sortie
        if not self.drive_manager.test_folder_access(folders['output'], "Transcriptions"):
            raise Exception("Dossier de sortie inaccessible")
    
    def _get_audio_files(self):
        """Récupère la liste des fichiers audio à traiter"""
        folder_id = self.config.DRIVE_FOLDERS['input']
        extensions = self.config.SUPPORTED_EXTENSIONS
        
        return self.drive_manager.list_audio_files(folder_id, extensions)
    
    def _process_single_file(self, file_info):
        """
        Traite un fichier audio complet
        
        Args:
            file_info: Informations du fichier Drive
        """
        file_name = file_info['name']
        file_id = file_info['id']
        
        try:
            self.logger.info(f"🎯 Traitement: {file_name}")
            
            # Vérifier si la transcription existe déjà
            from pathlib import Path
            base_filename = Path(file_name).stem
            output_folder_id = self.config.DRIVE_FOLDERS['output']
            
            if self.drive_manager.transcription_exists(base_filename, output_folder_id):
                self.logger.info(f"⏭️  Transcription déjà existante, skip: {file_name}")
                return True  # Considéré comme succès car déjà fait
            
            # 1. Téléchargement
            local_path = self._download_file(file_info)
            if not local_path:
                return False
            
            # 2. Transcription
            whisper_result = self._transcribe_file(local_path, file_name)
            if not whisper_result:
                return False
            
            # 3. Génération des outputs
            output_files = self._generate_outputs(file_name, whisper_result)
            
            # 4. Upload vers Drive
            self._upload_results(output_files)
            
            # 5. Nettoyage
            self._cleanup_local_files(local_path, output_files)
            
            # Stats finales
            segments_count = len(whisper_result.get('segments', []))
            language = whisper_result.get('language', 'unknown')
            self.logger.info(f"✅ Traitement terminé pour: {file_name}")
            self.logger.info(f"📊 Stats: {segments_count} segments, {language} détecté")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur traitement {file_name}: {e}")
            return False
    
    def _download_file(self, file_info):
        """Télécharge un fichier depuis Drive"""
        file_name = file_info['name']
        file_id = file_info['id']
        
        # Fichier temporaire
        temp_dir = tempfile.mkdtemp()
        local_path = os.path.join(temp_dir, file_name)
        
        return self.drive_manager.download_file(file_id, file_name, local_path)
    
    def _transcribe_file(self, local_path, file_name):
        """Transcrit un fichier audio"""
        test_config = self.config.TEST_MODE
        
        return self.transcriber.transcribe_audio(
            local_path,
            test_mode=test_config['enabled'],
            test_duration=test_config['duration_seconds']
        )
    
    def _generate_outputs(self, file_name, whisper_result):
        """Génère tous les fichiers de sortie"""
        base_filename = Path(file_name).stem
        
        # Génération des paragraphes
        paragraphs = None
        if self.config.OUTPUT_FORMATS['paragraphs']:
            paragraph_config = self.config.PARAGRAPH_CONFIG
            paragraphs = self.transcriber.group_segments_to_paragraphs(
                whisper_result['segments'],
                pause_threshold=paragraph_config['pause_threshold'],
                min_words=paragraph_config['min_words'],
                max_duration=paragraph_config['max_duration']
            )
        
        return self.output_generator.generate_all_outputs(
            base_filename, whisper_result, paragraphs
        )
    
    def _upload_results(self, output_files):
        """Upload les résultats vers Google Drive"""
        output_folder_id = self.config.DRIVE_FOLDERS['output']
        
        for file_type, file_path in output_files.items():
            if not file_path or not os.path.exists(file_path):
                continue
            
            drive_filename = Path(file_path).name
            self.drive_manager.upload_file(
                file_path, drive_filename, output_folder_id
            )
    
    def _cleanup_local_files(self, downloaded_file, output_files):
        """Nettoie les fichiers locaux temporaires"""
        try:
            # Supprimer le fichier téléchargé
            if downloaded_file and os.path.exists(downloaded_file):
                os.remove(downloaded_file)
                # Supprimer le dossier temporaire s'il est vide
                temp_dir = os.path.dirname(downloaded_file)
                try:
                    os.rmdir(temp_dir)
                except:
                    pass
            
            # Supprimer les fichiers de sortie locaux
            for file_path in output_files.values():
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
            
        except Exception as e:
            self.logger.warning(f"⚠️  Erreur nettoyage fichiers: {e}")