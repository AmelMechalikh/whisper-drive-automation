#!/usr/bin/env python3
"""
Serveur HTTP pour Cloud Run - Déclenchement automatique des transcriptions
"""
import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from pathlib import Path
import sys
import tempfile

# Configuration du logging dès le début
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter les chemins src et config au PYTHONPATH
current_dir = Path(__file__).parent.parent
src_path = str(current_dir / 'src')
config_path = str(current_dir / 'config')
sys.path.insert(0, src_path)
sys.path.insert(0, config_path)
logger.info(f"Ajout du chemin src: {src_path}")
logger.info(f"Ajout du chemin config: {config_path}")

# Importer l'orchestrateur léger (sans Whisper) pour Cloud Run
try:
    logger.info("🔄 Tentative d'import du module src...")
    # Import depuis le package src
    import src
    logger.info(f"📦 Module src importé: {dir(src)}")
    DriveOrchestrator = src.DriveOrchestrator
    logger.info("✅ Module orchestrator importé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur import orchestrator: {e}")
    import traceback
    logger.error(traceback.format_exc())
    
    # Tentative d'import direct en fallback
    try:
        logger.info("🔄 Tentative d'import direct de l'orchestrateur...")
        from src.orchestrator import DriveOrchestrator
        logger.info("✅ Import direct réussi")
    except Exception as e2:
        logger.error(f"❌ Import direct échoué: {e2}")
        DriveOrchestrator = None

# Initialisation Flask
app = Flask(__name__)

def get_orchestrator():
    """Initialise l'orchestrateur Drive (sans Whisper)"""
    if DriveOrchestrator is None:
        logger.error("❌ Classe DriveOrchestrator non disponible")
        return None

    try:
        # Importer le module de configuration - chercher dans plusieurs emplacements
        config_module = None
        config_paths = [
            Path(__file__).parent.parent / 'config' / 'whisper_config.py',  # Relatif au script
            Path('/app/config/whisper_config.py'),  # Chemin absolu conteneur
            Path('config/whisper_config.py')  # Relatif au workdir
        ]
        
        for config_file in config_paths:
            if config_file.exists():
                logger.info(f"📍 Configuration trouvée: {config_file}")
                import importlib.util
                spec = importlib.util.spec_from_file_location("whisper_config", str(config_file))
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                break
        
        if not config_module:
            logger.error(f"❌ Aucun fichier de config trouvé dans: {[str(p) for p in config_paths]}")
            return None

        logger.info(f"Configuration chargée depuis {config_file}")
        logger.info(f"Config module has CREDENTIALS_PATH: {hasattr(config_module, 'CREDENTIALS_PATH')}")

        # Vérifier si les credentials existent
        if not hasattr(config_module, 'CREDENTIALS_PATH'):
            logger.error("❌ Config invalide: CREDENTIALS_PATH manquant")
            return None

        creds_path = config_module.CREDENTIALS_PATH

        # Si creds_path est None, on utilisera Application Default Credentials (service account Cloud Run)
        if creds_path is None:
            logger.info(f"🔑 CREDENTIALS_PATH est None - Utilisation d'Application Default Credentials")
            logger.info(f"   Le DriveManager utilisera le service account de Cloud Run")
        else:
            logger.info(f"🔑 Tentative de chargement des credentials depuis: {creds_path}")

            if not Path(creds_path).exists():
                logger.error(f"❌ Fichier credentials non trouvé: {creds_path}")
                # Liste le contenu du répertoire pour diagnostiquer
                creds_dir = Path(creds_path).parent
                if creds_dir.exists():
                    files = list(creds_dir.glob('*'))
                    logger.info(f"📁 Contenu de {creds_dir}: {[f.name for f in files]}")
                return None

            logger.info(f"✅ Credentials trouvés: {creds_path}")

        return DriveOrchestrator(config_module)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'orchestrateur: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

@app.route('/', methods=['GET'])
def health_check():
    """Health check pour Cloud Run"""
    return jsonify({
        'status': 'healthy',
        'service': 'whisper-drive-automation',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    }), 200

@app.route('/debug/files', methods=['GET'])
def debug_files():
    """Liste tous les fichiers du dossier Files pour debug"""
    try:
        orchestrator = get_orchestrator()
        if not orchestrator:
            return jsonify({'error': 'Orchestrateur non disponible'}), 500
        
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        credentials = Credentials.from_service_account_file(
            orchestrator.config.CREDENTIALS_PATH,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        
        input_folder = orchestrator.config.DRIVE_FOLDERS['input']
        query = f"'{input_folder}' in parents and trashed=false"
        
        results_list = drive_service.files().list(
            q=query,
            fields="files(id, name, size, mimeType, createdTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            pageSize=100
        ).execute()
        
        files = results_list.get('files', [])
        
        # Catégoriser les fichiers
        supported_exts = orchestrator.config.SUPPORTED_EXTENSIONS
        audio_video_files = []
        other_files = []
        
        for f in files:
            name = f['name']
            is_supported = any(name.lower().endswith(ext) for ext in supported_exts)
            size_mb = int(f.get('size', 0)) / (1024 * 1024)
            
            file_info = {
                'name': name,
                'size_mb': round(size_mb, 2),
                'mimeType': f.get('mimeType', 'unknown'),
                'createdTime': f.get('createdTime', 'unknown'),
                'extension': Path(name).suffix
            }
            
            if is_supported:
                audio_video_files.append(file_info)
            else:
                other_files.append(file_info)
        
        return jsonify({
            'total_files': len(files),
            'supported_extensions': supported_exts,
            'audio_video_files': {
                'count': len(audio_video_files),
                'files': audio_video_files
            },
            'other_files': {
                'count': len(other_files),
                'files': other_files[:10]  # Limiter l'affichage
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur debug: {e}")
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/process', methods=['POST'])
def process_files():
    """Traite les nouveaux fichiers audio - Route selon la taille"""
    import subprocess
    import time
    from google.cloud import compute_v1
    start_time = datetime.now()
    logger.info("=== Début du traitement automatique ===")

    try:
        # Configuration
        SIZE_THRESHOLD_MB = 15  # ~20 min à 192kbps
        ZONE = 'europe-west1-b'
        VM_NAME = 'whisper-cpu-worker'
        PROJECT_ID = 'artificial-intelligence-cmk'

        # Load transcription backend from highlight_config.json
        backend = None
        use_runpod = False
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'highlight_config.json'
            logger.info(f"🔍 Checking config at: {config_path}")
            logger.info(f"🔍 Config exists: {config_path.exists()}")

            if config_path.exists():
                with open(config_path, 'r') as f:
                    highlight_config = json.load(f)
                logger.info(f"✅ Config loaded successfully")

                backend_provider = highlight_config.get('transcription_backend', {}).get('provider', 'cpu_local')
                logger.info(f"🔍 Backend provider from config: {backend_provider}")
                use_runpod = (backend_provider == 'gpu_runpod')
                logger.info(f"🔍 use_runpod = {use_runpod}")

                if use_runpod:
                    logger.info("🚀 Attempting to load RunPod backend...")
                    from transcription_backends import get_transcription_backend
                    backend = get_transcription_backend(highlight_config)
                    logger.info(f"🚀 Using transcription backend: {backend.get_backend_name()}")
                else:
                    logger.info("📍 RunPod not enabled, using VM fallback")
            else:
                logger.warning(f"⚠️ Config file not found at: {config_path}")
        except Exception as e:
            logger.warning(f"⚠️ Could not load transcription backend: {e}. Using VM fallback.")
            import traceback
            logger.warning(traceback.format_exc())

        # Initialiser l'orchestrateur
        orchestrator = get_orchestrator()
        if not orchestrator:
            return jsonify({
                'error': 'Impossible d\'initialiser l\'orchestrateur',
                'timestamp': start_time.isoformat()
            }), 500

        # Utiliser le drive_service de l'orchestrateur (qui a déjà les credentials)
        drive_service = orchestrator.drive_manager.service

        # Paramètres de traitement
        request_data = request.get_json() or {}
        hours_back = request_data.get('hours_back', None)  # None = tous les fichiers

        input_folder = orchestrator.config.DRIVE_FOLDERS['input']
        
        # Si hours_back est spécifié, filtrer par date, sinon prendre TOUS les fichiers
        if hours_back is not None:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            cutoff_str = cutoff_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            query = f"'{input_folder}' in parents and createdTime > '{cutoff_str}' and trashed=false"
            logger.info(f"Recherche fichiers récents (dernières {hours_back}h)")
        else:
            # TOUS les fichiers du dossier, peu importe la date
            query = f"'{input_folder}' in parents and trashed=false"
            logger.info(f"Recherche de TOUS les fichiers non transcrits (peu importe la date)")
        results_list = drive_service.files().list(
            q=query,
            fields="files(id, name, size)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()

        files = results_list.get('files', [])
        logger.info(f"📁 {len(files)} fichiers trouvés")

        # Tous les fichiers vont à la VM (pas de traitement local)
        files_to_vm = []

        for file_info in files:
            # Vérifier que c'est un fichier audio supporté
            file_name = file_info['name']
            extensions = orchestrator.config.SUPPORTED_EXTENSIONS
            if not any(file_name.lower().endswith(ext) for ext in extensions):
                logger.info(f"⏭️  Fichier ignoré (non audio): {file_name}")
                continue

            size_mb = int(file_info.get('size', 0)) / (1024 * 1024)

            if use_runpod:
                logger.info(f"📊 {file_name}: {size_mb:.1f} MB → transcription RunPod")
            else:
                logger.info(f"📊 {file_name}: {size_mb:.1f} MB → envoi VM")

            files_to_vm.append(file_info)

        results = {
            'sent_to_vm': [],
            'transcribed_runpod': [],
            'skipped': [],
            'errors': []
        }

        # Vérifier s'il y a déjà des jobs en attente dans Queue
        queue_folder = orchestrator.config.DRIVE_FOLDERS.get('queue', orchestrator.config.DRIVE_FOLDERS['output'])
        query = f"'{queue_folder}' in parents and name contains 'job_' and name contains '.json' and trashed=false"
        queue_check = drive_service.files().list(
            q=query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        pending_jobs = queue_check.get('files', [])
        
        if pending_jobs:
            logger.info(f"📋 {len(pending_jobs)} job(s) en attente dans Queue")
        
        # Envoyer tous les fichiers à la VM via fichiers de commande dans Drive
        if files_to_vm:
            if use_runpod:
                logger.info(f"🚀 {len(files_to_vm)} fichiers: transcription directe avec RunPod")

                # Transcription directe avec RunPod (pas de VM, pas de jobs)
                for file_info in files_to_vm:
                    try:
                        file_id = file_info['id']
                        file_name = file_info['name']

                        # Vérifier si déjà transcrit
                        base_filename = Path(file_name).stem
                        output_folder_id = orchestrator.config.DRIVE_FOLDERS['output']

                        if orchestrator.drive_manager.transcription_exists(base_filename, output_folder_id):
                            logger.info(f"⏭️  Fichier déjà transcrit, skip: {file_name}")
                            results['skipped'].append(file_name)
                            continue

                        # Check if video file to stream extraction
                        file_ext = Path(file_name).suffix.lower()
                        video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv']

                        if file_ext in video_extensions:
                            # Stream video from Drive and extract audio with ffmpeg directly
                            logger.info(f"🎬 Stream + extraction audio: {file_name}")
                            audio_path = tempfile.mktemp(suffix='.wav')

                            # Get media stream from Drive
                            media_request = orchestrator.drive_manager.service.files().get_media(
                                fileId=file_id,
                                supportsAllDrives=True
                            )

                            # Start ffmpeg process to read from stdin
                            import subprocess
                            from googleapiclient.http import MediaIoBaseDownload
                            import io

                            ffmpeg_process = subprocess.Popen([
                                'ffmpeg',
                                '-i', 'pipe:0',  # Read from stdin
                                '-vn',  # No video
                                '-acodec', 'pcm_s16le',  # WAV PCM 16-bit (more robust than MP3)
                                '-ar', '16000',  # Sample rate for Whisper
                                '-ac', '1',  # Mono
                                '-y',  # Overwrite
                                audio_path
                            ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                            # Stream chunks from Drive to ffmpeg stdin
                            try:
                                buffer = io.BytesIO()
                                downloader = MediaIoBaseDownload(buffer, media_request, chunksize=10*1024*1024)  # 10MB chunks
                                done = False
                                progress_logged = 0

                                while not done:
                                    # Download next chunk
                                    status, done = downloader.next_chunk()

                                    # Write accumulated data to ffmpeg and reset buffer
                                    chunk_data = buffer.getvalue()
                                    if chunk_data:
                                        ffmpeg_process.stdin.write(chunk_data)
                                        ffmpeg_process.stdin.flush()
                                        # Reset buffer by clearing it (don't create new BytesIO)
                                        buffer.seek(0)
                                        buffer.truncate()

                                    if status:
                                        progress = int(status.progress() * 100)
                                        if progress >= progress_logged + 20:  # Log every 20%
                                            logger.info(f"📥 Stream: {progress}%")
                                            progress_logged = progress

                                # Close stdin to signal EOF to ffmpeg
                                ffmpeg_process.stdin.close()

                                # Wait for ffmpeg to finish (30 min timeout for large files)
                                returncode = ffmpeg_process.wait(timeout=1800)

                                # Read output
                                stderr_output = ffmpeg_process.stderr.read().decode()

                                if returncode != 0:
                                    logger.error(f"❌ Erreur extraction audio: {stderr_output}")
                                    raise Exception(f"Failed to extract audio: {stderr_output}")

                                # Verify audio file integrity with ffprobe
                                logger.info(f"🔍 Vérification intégrité du fichier audio...")
                                try:
                                    probe_result = subprocess.run([
                                        'ffprobe',
                                        '-v', 'error',
                                        '-show_entries', 'format=duration,size',
                                        '-of', 'default=noprint_wrappers=1:nokey=1',
                                        audio_path
                                    ], capture_output=True, text=True, timeout=30)

                                    if probe_result.returncode != 0:
                                        logger.error(f"❌ Fichier audio corrompu: {probe_result.stderr}")
                                        raise Exception(f"Audio file integrity check failed: {probe_result.stderr}")

                                    # Get duration and size from ffprobe
                                    probe_lines = probe_result.stdout.strip().split('\n')
                                    if len(probe_lines) >= 2:
                                        # Handle 'N/A' values from ffprobe
                                        try:
                                            duration = float(probe_lines[0]) if probe_lines[0] != 'N/A' else 0
                                            size_bytes = int(float(probe_lines[1])) if probe_lines[1] != 'N/A' else Path(audio_path).stat().st_size
                                            logger.info(f"✅ Audio valide: {size_bytes / 1024 / 1024:.1f} MB, durée: {duration:.1f}s")
                                        except (ValueError, IndexError):
                                            # Fallback to file size if conversion fails
                                            logger.info(f"✅ Audio extrait: {Path(audio_path).stat().st_size / 1024 / 1024:.1f} MB")
                                    else:
                                        logger.info(f"✅ Audio extrait: {Path(audio_path).stat().st_size / 1024 / 1024:.1f} MB")

                                except subprocess.TimeoutExpired:
                                    logger.error(f"❌ Timeout lors de la vérification d'intégrité")
                                    raise Exception("Audio integrity check timed out")
                                except Exception as e:
                                    logger.error(f"❌ Erreur vérification intégrité: {e}")
                                    raise

                            except Exception as e:
                                ffmpeg_process.kill()
                                raise
                        else:
                            # Audio file - download normally (small files)
                            logger.info(f"📥 Téléchargement fichier audio: {file_name}")
                            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as temp_file:
                                audio_path = temp_file.name
                                orchestrator.drive_manager.download_file(file_id, file_name, audio_path)

                        # Transcribe with RunPod backend
                        logger.info(f"🎤 Transcription RunPod: {file_name}")
                        transcription_result = backend.transcribe_audio(
                            audio_path=audio_path,
                            language='fr',
                            word_timestamps=True
                        )

                        if transcription_result:
                            # Save transcription results to Drive (same format as VM worker)
                            logger.info(f"💾 Sauvegarde résultats: {file_name}")

                            # Generate outputs using OutputGenerator
                            from whisper_transcriber import WhisperTranscriber
                            from output_generator import OutputGenerator

                            temp_transcriber = WhisperTranscriber(backend=backend)
                            paragraphs = temp_transcriber.group_segments_to_paragraphs(
                                transcription_result.get('segments', [])
                            )

                            # Create OutputGenerator instance (orchestrator is DriveOrchestrator, not Processor)
                            output_generator = OutputGenerator(
                                drive_manager=orchestrator.drive_manager,
                                output_folder_id=output_folder_id
                            )

                            # Save using output_generator
                            output_result = output_generator.generate_all_outputs(
                                base_filename,
                                transcription_result,
                                paragraphs
                            )

                            if output_result:
                                # Upload all generated files to Drive
                                logger.info(f"📤 Upload des fichiers sur Drive: {file_name}")
                                for file_path in output_result.values():
                                    if file_path and os.path.exists(file_path):
                                        file_name_drive = Path(file_path).name
                                        orchestrator.drive_manager.upload_file(
                                            file_path,
                                            file_name_drive,
                                            output_folder_id
                                        )
                                        logger.info(f"  ✅ Uploadé: {file_name_drive}")
                                        # Cleanup local file after upload
                                        os.remove(file_path)

                                logger.info(f"✅ Transcription complète: {file_name}")
                                results['transcribed_runpod'].append(file_name)
                            else:
                                raise Exception("Failed to save transcription results")
                        else:
                            raise Exception("RunPod transcription returned no result")

                        # Cleanup temp file
                        os.remove(audio_path)

                    except Exception as e:
                        logger.error(f"❌ Erreur transcription RunPod {file_name}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        results['errors'].append({'file': file_name, 'error': str(e)})

                logger.info(f"💡 {len(results['transcribed_runpod'])} fichiers transcrits avec RunPod")

            else:
                # Mode VM classique
                logger.info(f"🖥️  {len(files_to_vm)} fichiers: création de jobs pour VM")

                try:
                    # Démarrer la VM si elle est arrêtée - Utiliser l'API Compute Engine
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
                            logger.info(f"💡 La VM démarrera et le worker s'auto-lancera. Auto-shutdown après 5 min d'inactivité.")

                        elif vm_status == 'RUNNING':
                            logger.info(f"✅ VM {VM_NAME} déjà en cours d'exécution")
                        else:
                            logger.warning(f"⚠️  État VM inattendu: {vm_status}")

                    except Exception as vm_error:
                        logger.warning(f"⚠️  Erreur gestion VM: {vm_error}")
                        import traceback
                        logger.warning(traceback.format_exc())
                        # Continue quand même pour créer les jobs
                
                    # Créer un fichier de commande pour chaque fichier
                
                    for file_info in files_to_vm:
                        try:
                            file_id = file_info['id']
                            file_name = file_info['name']
                        
                            # Vérifier si déjà transcrit (éviter création job inutile)
                            base_filename = Path(file_name).stem
                            output_folder_id = orchestrator.config.DRIVE_FOLDERS['output']
                        
                            if orchestrator.drive_manager.transcription_exists(base_filename, output_folder_id):
                                logger.info(f"⏭️  Fichier déjà transcrit, skip création job: {file_name}")
                                results['skipped'].append(file_name)
                                continue
                        
                            # Vérifier si un job existe déjà pour ce fichier (normal OU erreur)
                            # On cherche job_{file_id}_ OU error_{file_id}_
                            existing_job_query = f"'{queue_folder}' in parents and (name contains 'job_{file_id}_' or name contains 'error_{file_id}_') and trashed=false"
                            existing_jobs_result = drive_service.files().list(
                                q=existing_job_query,
                                fields="files(id, name)",
                                supportsAllDrives=True,
                                includeItemsFromAllDrives=True
                            ).execute()
                        
                            existing_jobs = existing_jobs_result.get('files', [])
                        
                            # Si un job existe (même en erreur), on le supprime pour créer un nouveau job propre
                            if existing_jobs:
                                for job in existing_jobs:
                                    job_name = job['name']
                                    is_error = job_name.startswith('error_')
                                    logger.info(f"🗑️  Suppression ancien job {'EN ERREUR' if is_error else ''}: {job_name}")
                                    try:
                                        drive_service.files().delete(
                                            fileId=job['id'],
                                            supportsAllDrives=True
                                        ).execute()
                                        logger.info(f"✅ Job supprimé: {job_name}")
                                    except Exception as del_error:
                                        logger.warning(f"⚠️  Impossible de supprimer {job_name}: {del_error}")
                        
                            logger.info(f"📤 Création job VM: {file_name} (ID: {file_id})")

                            # Créer un fichier JSON de commande
                            job_data = {
                                'file_id': file_id,
                                'file_name': file_name,
                                'timestamp': datetime.now().isoformat(),
                                'status': 'pending'
                            }
                        
                            # Créer un fichier temporaire local avec le job
                            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                                json.dump(job_data, temp_file, indent=2)
                                temp_path = temp_file.name
                        
                            # Upload vers Drive dans le dossier queue
                            job_filename = f"job_{file_id}_{int(time.time())}.json"
                            uploaded = orchestrator.drive_manager.upload_file(
                                temp_path,
                                job_filename,
                                queue_folder
                            )
                        
                            # Nettoyer le fichier temporaire
                            os.remove(temp_path)
                        
                            if uploaded:
                                logger.info(f"✅ Job créé pour: {file_name} → {job_filename}")
                                results['sent_to_vm'].append(file_name)
                            else:
                                error_msg = "Échec upload job vers Drive"
                                logger.error(f"❌ {error_msg}")
                                results['errors'].append({
                                    'file': file_name,
                                    'error': error_msg
                                })

                        except Exception as e:
                            logger.error(f"❌ Erreur création job {file_info['name']}: {e}")
                            results['errors'].append({'file': file_info['name'], 'error': str(e)})
                
                    # Note: La VM doit être configurée pour vérifier périodiquement le dossier queue
                    logger.info(f"💡 {len(results['sent_to_vm'])} jobs créés. La VM les traitera automatiquement.")

                except Exception as e:
                    logger.error(f"❌ Erreur création jobs VM: {e}")
                    # Marquer tous les fichiers comme erreur
                    for file_info in files_to_vm:
                        results['errors'].append({
                            'file': file_info['name'],
                        'error': f"Échec création job: {str(e)}"
                    })
        
        # Si pas de nouveaux fichiers MAIS des jobs en attente, démarrer quand même la VM
        elif pending_jobs:
            logger.info(f"🖥️  Aucun nouveau fichier mais {len(pending_jobs)} job(s) en attente")
            logger.info("🚀 Démarrage de la VM pour traiter les jobs en attente...")
            
            try:
                result = subprocess.run(
                    ['gcloud', 'compute', 'instances', 'describe', VM_NAME,
                     f'--project={PROJECT_ID}', f'--zone={ZONE}',
                     '--format=get(status)'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and result.stdout.strip() == 'TERMINATED':
                    logger.info(f"🚀 Démarrage de la VM {VM_NAME}...")
                    start_result = subprocess.run(
                        ['gcloud', 'compute', 'instances', 'start', VM_NAME,
                         f'--project={PROJECT_ID}', f'--zone={ZONE}'],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                    
                    if start_result.returncode == 0:
                        logger.info(f"✅ VM {VM_NAME} démarrée pour traiter les jobs en attente")
                    else:
                        logger.warning(f"⚠️  Échec démarrage VM: {start_result.stderr}")
                elif result.returncode == 0:
                    logger.info(f"✅ VM déjà en cours : {result.stdout.strip()}")
                    
            except Exception as e:
                logger.warning(f"⚠️  Erreur démarrage VM: {e}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"=== Traitement terminé en {duration:.1f}s ===")
        logger.info(f"📊 Résumé: {len(results['sent_to_vm'])} VM, {len(results['skipped'])} skip, {len(results['errors'])} erreurs")

        return jsonify({
            'status': 'success',
            'sent_to_vm': len(results['sent_to_vm']),
            'skipped': len(results['skipped']),
            'errors': len(results['errors']),
            'duration_seconds': duration,
            'timestamp': start_time.isoformat()
        }), 200

    except Exception as e:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.error(f"❌ Erreur lors du traitement: {e}")

        return jsonify({
            'status': 'error',
            'message': str(e),
            'duration_seconds': duration,
            'timestamp': start_time.isoformat()
        }), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Retourne le statut détaillé du service"""
    try:
        processor = get_processor()
        
        # Statistiques basiques même sans processeur
        stats = {
            'status': 'demo' if not processor else 'operational',
            'message': 'Credentials non configurés - voir documentation' if not processor else 'Service opérationnel',
            'whisper_available': processor is not None,
            'timestamp': datetime.now().isoformat()
        }
        
        if processor:
            stats.update({
                'whisper_model': getattr(processor.config, 'WHISPER_CONFIG', {}).get('model', 'unknown'),
                'vocabulary_terms': len(getattr(processor.config, 'WHISPER_CONFIG', {}).get('vocabulary', [])),
            })
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/manual', methods=['POST'])
def manual_process():
    """Traitement manuel d'un fichier spécifique"""
    try:
        request_data = request.get_json()
        if not request_data or 'file_id' not in request_data:
            return jsonify({
                'error': 'file_id requis dans le body JSON'
            }), 400
        
        processor = get_processor()
        if not processor:
            return jsonify({
                'error': 'Impossible d\'initialiser le processeur'
            }), 500
        
        file_id = request_data['file_id']
        logger.info(f"Traitement manuel du fichier: {file_id}")
        
        result = processor.process_single_file(file_id)
        
        return jsonify({
            'status': 'success' if result else 'failed',
            'file_id': file_id,
            'timestamp': datetime.now().isoformat()
        }), 200 if result else 500
        
    except Exception as e:
        logger.error(f"Erreur traitement manuel: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    # Configuration pour Cloud Run
    port = int(os.environ.get('PORT', 8080))
    
    logger.info(f"Démarrage du serveur Whisper Drive sur le port {port}")
    logger.info("Endpoints disponibles:")
    logger.info("  GET  /        - Health check")
    logger.info("  GET  /status  - Statut détaillé") 
    logger.info("  POST /process - Traitement automatique")
    logger.info("  POST /manual  - Traitement manuel")
    
    try:
        # Lancement du serveur
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"❌ Erreur démarrage serveur: {e}")
        exit(1)