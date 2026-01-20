"""
Processeur principal pour l'automation Whisper + Google Drive
Orchestration complète du workflow
"""
import logging
import tempfile
import os
import json
import traceback
from pathlib import Path
from datetime import datetime

from .drive_manager import DriveManager
from .whisper_transcriber import WhisperTranscriber
from .output_generator import OutputGenerator


class CheckpointManager:
    """Gère les checkpoints pour reprendre après échec"""

    def __init__(self, checkpoint_dir='/tmp/whisper_checkpoints'):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True, parents=True)
        self.logger = logging.getLogger(__name__)

    def _get_checkpoint_path(self, file_name, step):
        """Retourne le chemin du checkpoint pour un fichier et une étape"""
        safe_name = file_name.replace('/', '_').replace(' ', '_')
        return self.checkpoint_dir / f"{safe_name}_{step}.json"

    def save_checkpoint(self, file_name, step, data):
        """Sauvegarde un checkpoint"""
        try:
            checkpoint_path = self._get_checkpoint_path(file_name, step)
            with open(checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"💾 Checkpoint sauvegardé: {step} pour {file_name}")
            return True
        except Exception as e:
            self.logger.warning(f"⚠️ Impossible de sauvegarder checkpoint: {e}")
            return False

    def load_checkpoint(self, file_name, step):
        """Charge un checkpoint s'il existe"""
        try:
            checkpoint_path = self._get_checkpoint_path(file_name, step)
            if checkpoint_path.exists():
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.logger.info(f"📂 Checkpoint chargé: {step} pour {file_name}")
                return data
            return None
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur chargement checkpoint: {e}")
            return None

    def clear_checkpoints(self, file_name):
        """Supprime tous les checkpoints d'un fichier"""
        try:
            safe_name = file_name.replace('/', '_').replace(' ', '_')
            for checkpoint_file in self.checkpoint_dir.glob(f"{safe_name}_*.json"):
                checkpoint_file.unlink()
            self.logger.info(f"🗑️ Checkpoints supprimés pour {file_name}")
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur suppression checkpoints: {e}")


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
        self.checkpoint_manager = CheckpointManager()

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
            
            # Output Generator - passer le drive_manager pour créer des Google Docs
            output_folder_id = self.config.DRIVE_FOLDERS.get('output')
            self.output_generator = OutputGenerator(
                drive_manager=self.drive_manager,
                output_folder_id=output_folder_id
            )

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

        # Variables pour le nettoyage automatique
        local_path = None
        output_files = {}

        try:
            self.logger.info(f"🎯 Traitement: {file_name}")

            # Vérifier si la transcription existe déjà
            from pathlib import Path
            base_filename = Path(file_name).stem
            output_folder_id = self.config.DRIVE_FOLDERS['output']

            if self.drive_manager.transcription_exists(base_filename, output_folder_id):
                self.logger.info(f"⏭️  Transcription déjà existante, skip: {file_name}")
                return True  # Considéré comme succès car déjà fait

            # 1. Téléchargement avec retry
            try:
                local_path = self._download_file(file_info)
            except Exception as e:
                self._log_processing_error(file_name, 'download', e, {'file_id': file_id})
                return False

            # 2. Transcription avec checkpoint
            whisper_result = None

            # Essayer de charger depuis le checkpoint
            checkpoint_data = self.checkpoint_manager.load_checkpoint(file_name, 'transcription')
            if checkpoint_data:
                self.logger.info("🔄 Reprise depuis checkpoint transcription")
                whisper_result = checkpoint_data
            else:
                # Pas de checkpoint, faire la transcription
                try:
                    whisper_result = self._transcribe_file(local_path, file_name)
                    if not whisper_result:
                        self.logger.error(f"❌ Transcription a retourné None")
                        return False

                    # Sauvegarder le checkpoint
                    self.checkpoint_manager.save_checkpoint(file_name, 'transcription', whisper_result)

                except Exception as e:
                    self._log_processing_error(file_name, 'transcription', e, {'local_path': local_path})
                    return False

            # 3. Génération des outputs avec retry
            try:
                output_files = self._generate_outputs(file_name, whisper_result)
                if not output_files:
                    self.logger.error(f"❌ Génération outputs a retourné None")
                    return False
            except Exception as e:
                self._log_processing_error(file_name, 'generate_outputs', e)
                return False

            # 4. Upload vers Drive avec gestion d'erreur
            try:
                uploaded_types = self._upload_results(output_files)

                # 5. Vérification post-upload (optionnel mais recommandé)
                base_filename = Path(file_name).stem
                output_folder_id = self.config.DRIVE_FOLDERS['output']

                if self._verify_upload_complete(base_filename, output_folder_id):
                    self.logger.info("✅ Vérification post-upload réussie")

                    # Supprimer les checkpoints après succès complet
                    self.checkpoint_manager.clear_checkpoints(file_name)
                else:
                    self.logger.warning("⚠️ Vérification post-upload échouée (fichiers potentiellement manquants)")
                    # Garder les checkpoints pour retry

                # 6. Nettoyage SEULEMENT des fichiers uploadés avec succès
                files_to_cleanup = {k: v for k, v in output_files.items() if k in uploaded_types}
                self._cleanup_local_files(local_path, files_to_cleanup)

                # Si des fichiers n'ont pas été uploadés, les conserver pour debug
                failed_files = {k: v for k, v in output_files.items() if k not in uploaded_types}
                if failed_files:
                    self.logger.warning(f"⚠️ Fichiers conservés localement pour debug: {list(failed_files.keys())}")
                    for file_type, file_path in failed_files.items():
                        if file_path and os.path.exists(file_path):
                            self.logger.warning(f"   📁 {file_type}: {file_path}")

            except Exception as upload_error:
                self.logger.error(f"❌ Erreur lors de l'upload: {upload_error}")
                self.logger.warning("⚠️ Fichiers locaux conservés pour retry manuel")
                # Ne pas nettoyer en cas d'erreur - garder les fichiers pour retry
                for file_type, file_path in output_files.items():
                    if file_path and os.path.exists(file_path):
                        self.logger.info(f"   📁 Conservé: {file_path}")
                return False

            # Stats finales
            segments_count = len(whisper_result.get('segments', []))
            language = whisper_result.get('language', 'unknown')
            self.logger.info(f"✅ Traitement terminé pour: {file_name}")
            self.logger.info(f"📊 Stats: {segments_count} segments, {language} détecté")

            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur traitement {file_name}: {e}")
            self.logger.error(traceback.format_exc())
            return False

        finally:
            # 🧹 NETTOYAGE AUTOMATIQUE GARANTI - même en cas d'erreur
            self.logger.info("🧹 Nettoyage automatique des fichiers temporaires...")
            try:
                # Nettoyer le fichier audio téléchargé
                if local_path and os.path.exists(local_path):
                    file_size = os.path.getsize(local_path)
                    os.remove(local_path)
                    self.logger.info(f"   ✅ Fichier audio supprimé ({file_size} bytes): {local_path}")

                    # Supprimer le dossier temporaire s'il est vide
                    temp_dir = os.path.dirname(local_path)
                    try:
                        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                            os.rmdir(temp_dir)
                            self.logger.info(f"   ✅ Dossier temporaire supprimé: {temp_dir}")
                    except OSError:
                        pass  # Dossier non vide ou déjà supprimé

                # Nettoyer les fichiers de sortie générés localement
                if output_files:
                    for file_type, file_path in output_files.items():
                        # Ignorer les Google Docs (préfixe "gdoc:")
                        if file_path and isinstance(file_path, str) and file_path.startswith("gdoc:"):
                            continue

                        # Supprimer les fichiers locaux
                        if file_path and os.path.exists(file_path):
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            self.logger.info(f"   ✅ Fichier sortie supprimé ({file_size} bytes): {os.path.basename(file_path)}")

                self.logger.info("✅ Nettoyage automatique terminé")

            except Exception as cleanup_error:
                self.logger.warning(f"⚠️ Erreur lors du nettoyage automatique: {cleanup_error}")
    
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
        """
        Upload les résultats vers Google Drive avec vérification complète

        Args:
            output_files: Dictionnaire {file_type: file_path}

        Returns:
            list: Liste des types de fichiers uploadés avec succès

        Raises:
            Exception: Si des uploads échouent
        """
        output_folder_id = self.config.DRIVE_FOLDERS['output']

        uploaded = []
        failed = []
        skipped = []

        for file_type, file_path in output_files.items():
            # Vérification 1: Le chemin est-il défini?
            if not file_path:
                self.logger.warning(f"⚠️ Fichier {file_type} est None (pas généré)")
                skipped.append(file_type)
                continue

            # Vérification 2: Est-ce déjà un Google Doc? (préfixe "gdoc:")
            if isinstance(file_path, str) and file_path.startswith("gdoc:"):
                doc_id = file_path.split(":", 1)[1]
                self.logger.info(f"✅ Google Doc déjà créé: {file_type} (ID: {doc_id})")
                uploaded.append(file_type)
                continue

            # Vérification 3: Le fichier existe-t-il localement?
            if not os.path.exists(file_path):
                self.logger.error(f"❌ Fichier {file_type} n'existe pas: {file_path}")
                self._log_upload_error(file_type, file_path, "File not found locally")
                failed.append(file_type)
                continue

            # Tentative d'upload
            try:
                drive_filename = Path(file_path).name
                file_size = os.path.getsize(file_path)
                self.logger.info(f"📤 Upload {file_type}: {drive_filename} ({file_size} bytes)")

                file_id = self.drive_manager.upload_file(
                    file_path, drive_filename, output_folder_id
                )

                if file_id:
                    self.logger.info(f"✅ Upload réussi: {file_type} → {drive_filename} (ID: {file_id})")
                    uploaded.append(file_type)
                else:
                    self.logger.error(f"❌ Upload échoué (retour None): {file_type}")
                    self._log_upload_error(file_type, file_path, "Upload returned None")
                    failed.append(file_type)

            except Exception as e:
                self.logger.error(f"❌ Exception upload {file_type}: {e}")
                self._log_upload_error(file_type, file_path, e)
                failed.append(file_type)

        # Log du résumé
        total = len(output_files)
        self.logger.info(f"📊 Résumé upload: {len(uploaded)}/{total} réussis, {len(failed)} échoués, {len(skipped)} skippés")

        if failed:
            self.logger.error(f"❌ Fichiers échoués: {failed}")
            raise Exception(f"Upload incomplet: {len(failed)} fichier(s) échoué(s) - {failed}")

        if skipped:
            self.logger.warning(f"⚠️ Fichiers skippés: {skipped}")

        return uploaded

    def _verify_upload_complete(self, base_filename, output_folder_id):
        """
        Vérifie que tous les fichiers attendus sont bien uploadés sur Drive

        Args:
            base_filename: Nom de base du fichier (sans extension)
            output_folder_id: ID du dossier de sortie sur Drive

        Returns:
            bool: True si tous les fichiers sont présents, False sinon
        """
        expected_files = []

        # Construire la liste des fichiers attendus selon la config
        if self.config.OUTPUT_FORMATS['transcription']:
            expected_files.append(f"{base_filename}_transcription.txt")
        if self.config.OUTPUT_FORMATS['srt']:
            expected_files.append(f"{base_filename}_with_timestamps.srt")
        if self.config.OUTPUT_FORMATS['word_timestamps']:
            expected_files.append(f"{base_filename}_word_timestamps.txt")
        if self.config.OUTPUT_FORMATS['paragraphs']:
            # Google Doc: pas d'extension .txt
            expected_files.append(f"{base_filename}_paragraphs_timestamps")
        if self.config.OUTPUT_FORMATS['complete_json']:
            expected_files.append(f"{base_filename}_complete_data.json")

        self.logger.info(f"🔍 Vérification post-upload de {len(expected_files)} fichiers...")

        missing = []
        found = []

        for filename in expected_files:
            try:
                files = self.drive_manager.search_files(output_folder_id, filename)
                if files:
                    found.append(filename)
                    self.logger.info(f"   ✅ {filename}")
                else:
                    missing.append(filename)
                    self.logger.error(f"   ❌ {filename} MANQUANT")
            except Exception as e:
                self.logger.error(f"   ⚠️ Erreur vérification {filename}: {e}")
                missing.append(filename)

        # Résumé
        if missing:
            self.logger.error(f"❌ Vérification échouée: {len(missing)}/{len(expected_files)} fichiers manquants")
            self.logger.error(f"   Fichiers manquants: {missing}")
            return False

        self.logger.info(f"✅ Vérification réussie: tous les fichiers sont sur Drive ({len(found)}/{len(expected_files)})")
        return True

    def _log_processing_error(self, file_name, step, error, extra_info=None):
        """
        Log structuré des erreurs de processing pour faciliter le debug

        Args:
            file_name: Nom du fichier en cours de traitement
            step: Étape qui a échoué (download, transcription, generate_outputs, upload)
            error: Exception ou message d'erreur
            extra_info: Informations supplémentaires (dict)
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'file_name': file_name,
            'step': step,
            'error': str(error),
            'traceback': traceback.format_exc() if isinstance(error, Exception) else 'N/A'
        }

        if extra_info:
            error_info.update(extra_info)

        # Log formaté pour faciliter la lecture
        self.logger.error("=" * 80)
        self.logger.error(f"❌ PROCESSING FAILED - {step.upper()}")
        self.logger.error(f"   Fichier: {error_info['file_name']}")
        self.logger.error(f"   Étape: {error_info['step']}")
        self.logger.error(f"   Erreur: {error_info['error']}")
        if extra_info:
            for key, value in extra_info.items():
                self.logger.error(f"   {key}: {value}")
        if error_info['traceback'] != 'N/A':
            self.logger.error(f"   Traceback:\n{error_info['traceback']}")
        self.logger.error("=" * 80)

        # Sauvegarder dans un fichier d'erreurs pour analyse ultérieure
        try:
            error_log_file = '/tmp/whisper_processing_errors.jsonl'
            with open(error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_info, ensure_ascii=False) + '\n')
            self.logger.info(f"📝 Erreur sauvegardée dans: {error_log_file}")
        except Exception as log_error:
            self.logger.warning(f"⚠️ Impossible de sauvegarder l'erreur: {log_error}")

    def _log_upload_error(self, file_type, file_path, error):
        """
        Log structuré des erreurs d'upload pour faciliter le debug

        Args:
            file_type: Type de fichier (ex: 'paragraphs', 'complete_json')
            file_path: Chemin du fichier local
            error: Exception ou message d'erreur
        """
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'file_type': file_type,
            'file_path': str(file_path) if file_path else 'None',
            'file_exists': os.path.exists(file_path) if file_path else False,
            'file_size': os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0,
            'error': str(error),
            'traceback': traceback.format_exc() if isinstance(error, Exception) else 'N/A'
        }

        # Log formaté pour faciliter la lecture
        self.logger.error("=" * 80)
        self.logger.error("❌ UPLOAD FAILED - DÉTAILS:")
        self.logger.error(f"   Type: {error_info['file_type']}")
        self.logger.error(f"   Fichier: {error_info['file_path']}")
        self.logger.error(f"   Existe: {error_info['file_exists']}")
        self.logger.error(f"   Taille: {error_info['file_size']} bytes")
        self.logger.error(f"   Erreur: {error_info['error']}")
        if error_info['traceback'] != 'N/A':
            self.logger.error(f"   Traceback:\n{error_info['traceback']}")
        self.logger.error("=" * 80)

        # Sauvegarder dans un fichier d'erreurs pour analyse ultérieure
        try:
            error_log_file = '/tmp/whisper_upload_errors.jsonl'
            with open(error_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_info, ensure_ascii=False) + '\n')
            self.logger.info(f"📝 Erreur sauvegardée dans: {error_log_file}")
        except Exception as log_error:
            self.logger.warning(f"⚠️ Impossible de sauvegarder l'erreur: {log_error}")

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
                # Ignorer les Google Docs (préfixe "gdoc:")
                if file_path and isinstance(file_path, str) and file_path.startswith("gdoc:"):
                    continue

                # Supprimer les fichiers locaux
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

        except Exception as e:
            self.logger.warning(f"⚠️  Erreur nettoyage fichiers: {e}")