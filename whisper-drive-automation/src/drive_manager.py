"""
Module Google Drive pour l'automation Whisper
Gestion des téléchargements et uploads
"""
import os
import logging
import time
from functools import wraps
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2.service_account import Credentials
from google.auth import default as get_default_credentials
from pathlib import Path
import tempfile
import io


def retry_on_failure(max_retries=3, backoff_factor=2):
    """
    Décorateur pour retry avec backoff exponentiel

    Args:
        max_retries: Nombre maximum de tentatives
        backoff_factor: Facteur multiplicateur pour le temps d'attente
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(__name__)

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        # Dernière tentative, on propage l'erreur
                        logger.error(f"❌ Échec définitif après {max_retries} tentatives: {e}")
                        raise

                    wait_time = backoff_factor ** attempt
                    logger.warning(f"⚠️ Tentative {attempt + 1}/{max_retries} échouée: {e}")
                    logger.info(f"⏳ Nouvelle tentative dans {wait_time}s...")
                    time.sleep(wait_time)

        return wrapper
    return decorator

class DriveManager:
    """Gestionnaire Google Drive pour l'automation de transcription"""
    
    def __init__(self, credentials_path=None, scopes=['https://www.googleapis.com/auth/drive']):
        """
        Initialise le gestionnaire Google Drive

        Args:
            credentials_path: Chemin vers le fichier credentials.json (None pour utiliser les credentials par défaut)
            scopes: Scopes d'autorisation Drive
        """
        self.credentials_path = credentials_path
        self.scopes = scopes
        self.service = None
        self.logger = logging.getLogger(__name__)
        self._setup_drive_service()

    def _setup_drive_service(self):
        """Configure le service Google Drive API"""
        try:
            # Si credentials_path est fourni, utiliser le fichier
            # Sinon, utiliser les credentials par défaut (pour Cloud Run/GCE)
            if self.credentials_path:
                self.creds = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=self.scopes
                )
            else:
                self.creds, project = get_default_credentials(scopes=self.scopes)

            self.service = build('drive', 'v3', credentials=self.creds)
            
            # Test de connexion
            about = self.service.about().get(fields="user").execute()
            user_email = about['user']['emailAddress']
            self.logger.info(f"✅ Google Drive API configurée")
            self.logger.info(f"   Connecté en tant que: {user_email}")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur configuration Google Drive: {e}")
            raise
    
    def test_folder_access(self, folder_id, folder_name=""):
        """
        Teste l'accès à un dossier Drive
        
        Args:
            folder_id: ID du dossier à tester
            folder_name: Nom du dossier (pour logs)
        
        Returns:
            bool: True si accessible, False sinon
        """
        try:
            folder = self.service.files().get(
                fileId=folder_id,
                supportsAllDrives=True
            ).execute()
            
            folder_name = folder_name or folder.get('name', 'Dossier')
            self.logger.info(f"✅ Dossier accessible: {folder_name} (ID: {folder_id})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Dossier inaccessible {folder_name}: {e}")
            return False
    
    def list_audio_files(self, folder_id, supported_extensions):
        """
        Liste les fichiers audio dans un dossier Drive
        
        Args:
            folder_id: ID du dossier à scanner
            supported_extensions: Liste des extensions supportées
        
        Returns:
            list: Liste des fichiers audio trouvés
        """
        try:
            query = f"'{folder_id}' in parents and trashed=false"
            self.logger.info(f"🔍 Requête: {query}")
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            all_files = results.get('files', [])
            self.logger.info(f"📋 Trouvé {len(all_files)} fichier(s) total dans le dossier")
            
            # Filtrer les fichiers audio
            audio_files = []
            for file in all_files:
                file_name = file['name']
                self.logger.info(f"   - {file_name} (type: {file.get('mimeType', 'unknown')})")
                
                # Vérifier l'extension
                if any(file_name.lower().endswith(ext) for ext in supported_extensions):
                    self.logger.info(f"    ✅ Correspond à l'extension {Path(file_name).suffix}")
                    audio_files.append(file)
            
            self.logger.info(f"📁 Trouvé {len(audio_files)} fichier(s) média dans Google Drive")
            return audio_files
            
        except Exception as e:
            self.logger.error(f"❌ Erreur listage fichiers: {e}")
            return []
    
    def download_file(self, file_id, file_name, download_path):
        """
        Télécharge un fichier depuis Drive
        
        Args:
            file_id: ID du fichier Drive
            file_name: Nom du fichier
            download_path: Chemin local de destination
        
        Returns:
            str: Chemin du fichier téléchargé ou None si erreur
        """
        try:
            self.logger.info(f"📥 Téléchargement: {file_name}")
            
            # Créer le dossier de destination
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            # Téléchargement
            request = self.service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True
            )
            
            with open(download_path, 'wb') as file_handle:
                downloader = MediaIoBaseDownload(file_handle, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                    if status:
                        progress = int(status.progress() * 100)
                        if progress % 20 == 0:  # Log tous les 20%
                            self.logger.info(f"📥 Téléchargement: {progress}%")
            
            self.logger.info(f"✅ Fichier téléchargé: {file_name}")
            return download_path
            
        except Exception as e:
            self.logger.error(f"❌ Erreur téléchargement {file_name}: {e}")
            return None
    
    @retry_on_failure(max_retries=3, backoff_factor=2)
    def upload_file(self, local_path, drive_filename, folder_id):
        """
        Upload un fichier vers Drive avec retry automatique

        Args:
            local_path: Chemin du fichier local
            drive_filename: Nom dans Drive
            folder_id: ID du dossier de destination

        Returns:
            str: ID du fichier uploadé

        Raises:
            Exception: Si l'upload échoue après tous les retries
        """
        # Validation des paramètres
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Fichier local introuvable: {local_path}")

        file_size = os.path.getsize(local_path)
        self.logger.info(f"☁️  Upload vers Drive: {drive_filename} ({file_size} bytes)")

        # Déterminer le MIME type
        mime_type = 'text/plain'
        if drive_filename.endswith('.json'):
            mime_type = 'application/json'
        elif drive_filename.endswith('.srt'):
            mime_type = 'text/plain'
        elif drive_filename.endswith('.xlsx'):
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif drive_filename.endswith('.mp4'):
            mime_type = 'video/mp4'
        elif drive_filename.endswith('.mp3'):
            mime_type = 'audio/mpeg'

        # Métadonnées du fichier
        file_metadata = {
            'name': drive_filename,
            'parents': [folder_id]
        }

        # Upload with resumable upload for large files (chunked to avoid OOM)
        # Chunk size: 50MB to avoid loading entire file in memory
        media = MediaFileUpload(
            local_path,
            mimetype=mime_type,
            resumable=True,
            chunksize=50 * 1024 * 1024  # 50 MB chunks
        )

        file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True
        ).execute()

        file_id = file.get('id')

        if not file_id:
            raise Exception(f"Upload échoué: aucun ID retourné pour {drive_filename}")

        self.logger.info(f"✅ Fichier uploadé: {drive_filename} (ID: {file_id})")
        return file_id
    
    def list_recent_audio_files(self, folder_id, extensions, hours_back=1):
        """
        Liste les fichiers audio ajoutés récemment
        
        Args:
            folder_id: ID du dossier à scanner
            extensions: Extensions autorisées
            hours_back: Nombre d'heures en arrière
            
        Returns:
            list: Liste des fichiers récents
        """
        from datetime import datetime, timedelta
        
        try:
            # Calcul de la date limite (RFC 3339 format pour Google API)
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            cutoff_str = cutoff_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            self.logger.info(f"🔍 Recherche de fichiers après {cutoff_str}")
            
            # Construction de la requête avec filtre temporel
            extensions_query = " or ".join([f"name contains '.{ext}'" for ext in extensions])
            query = f"'{folder_id}' in parents and ({extensions_query}) and createdTime > '{cutoff_str}' and trashed=false"
            
            self.logger.debug(f"Requête Drive: {query}")
            
            # Exécution de la requête
            results = self.service.files().list(
                q=query,
                fields="files(id, name, size, createdTime, modifiedTime)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                orderBy='createdTime desc'  # Plus récents en premier
            ).execute()
            
            files = results.get('files', [])
            
            self.logger.info(f"📁 {len(files)} fichiers récents trouvés")
            
            # Log des fichiers trouvés
            for file_info in files:
                created = file_info.get('createdTime', 'Unknown')
                self.logger.info(f"  📄 {file_info['name']} (créé: {created})")
            
            return files
            
        except Exception as e:
            self.logger.error(f"❌ Erreur listage fichiers récents: {e}")
            return []
    
    def get_file_info(self, file_id):
        """
        Récupère les informations d'un fichier par son ID
        
        Args:
            file_id: ID du fichier Google Drive
            
        Returns:
            dict: Informations du fichier ou None si erreur
        """
        try:
            file_info = self.service.files().get(
                fileId=file_id,
                fields="id, name, size, createdTime, modifiedTime, parents",
                supportsAllDrives=True
            ).execute()
            
            return file_info
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération info fichier {file_id}: {e}")
            return None
    
    def transcription_exists(self, base_filename, folder_id):
        """
        Vérifie si une transcription existe déjà pour ce fichier
        
        Args:
            base_filename: Nom de base du fichier (sans extension)
            folder_id: ID du dossier de sortie
            
        Returns:
            bool: True si la transcription existe
        """
        try:
            # Échapper les apostrophes dans le nom de fichier pour la requête Drive
            escaped_filename = base_filename.replace("'", "\\'")

            # Chercher un fichier de transcription avec ce nom de base
            query = f"name contains '{escaped_filename}' and '{folder_id}' in parents and trashed=false"
            self.logger.info(f"🔍 Recherche transcription - Query: {query} | Folder ID: {folder_id}")

            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                pageSize=10,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()

            files = results.get('files', [])
            self.logger.info(f"🔍 Fichiers trouvés pour '{base_filename}': {len(files)} fichier(s)")

            # Log TOUS les fichiers trouvés pour debug
            if files:
                for f in files:
                    self.logger.info(f"  📄 Fichier trouvé: {f['name']}")

            # Vérifier si au moins un fichier de transcription existe
            # IMPORTANT: Filtrage précis pour éviter les faux positifs
            # "Jour 1 séance 1" ne doit PAS matcher "Séance 3 jour 1"
            transcription_suffixes = ['_transcription.txt', '_with_timestamps.srt', '_complete_data.json']

            for file in files:
                file_name = file['name']

                # Vérifier si c'est un fichier de transcription
                is_transcription = any(suffix in file_name for suffix in transcription_suffixes)

                if is_transcription:
                    # Vérifier que le nom du fichier COMMENCE VRAIMENT par le base_filename
                    # Normaliser: lowercase et enlever les espaces multiples pour comparaison
                    file_name_normalized = file_name.lower().strip()
                    base_filename_normalized = base_filename.lower().strip()

                    if file_name_normalized.startswith(base_filename_normalized):
                        self.logger.info(f"✅ Transcription trouvée (match précis): {file_name}")
                        return True
                    else:
                        self.logger.info(f"⚠️  Fichier ignoré (pas un match exact): {file_name}")

            self.logger.info(f"❌ Aucune transcription trouvée pour: {base_filename}")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Erreur vérification transcription: {e}")
            return False
    
    def list_files_in_folder(self, folder_id, name_pattern=None):
        """
        Liste les fichiers dans un dossier avec pattern optionnel
        
        Args:
            folder_id: ID du dossier à scanner
            name_pattern: Pattern optionnel pour filtrer par nom (contains)
        
        Returns:
            list: Liste des fichiers trouvés
        """
        try:
            # Construction de la requête
            query = f"'{folder_id}' in parents and trashed=false"
            if name_pattern:
                escaped_pattern = name_pattern.replace("'", "\\'")
                query += f" and name contains '{escaped_pattern}'"
            
            self.logger.debug(f"🔍 Query list_files_in_folder: {query}")
            
            # Récupérer TOUS les fichiers avec pagination
            files = []
            page_token = None

            while True:
                results = self.service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)",
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                    orderBy='createdTime desc',
                    pageSize=1000,
                    pageToken=page_token
                ).execute()

                files.extend(results.get('files', []))
                page_token = results.get('nextPageToken')

                if not page_token:
                    break

            self.logger.info(f"📁 {len(files)} fichier(s) trouvé(s) dans le dossier")
            
            return files
            
        except Exception as e:
            self.logger.error(f"❌ Erreur listage fichiers: {e}")
            return []
    
    def search_files(self, folder_id, name_contains):
        """
        Cherche des fichiers par nom dans un dossier
        
        Args:
            folder_id: ID du dossier à chercher
            name_contains: Chaîne que le nom doit contenir
        
        Returns:
            list: Liste des fichiers trouvés
        """
        try:
            escaped_name = name_contains.replace("'", "\\'")
            query = f"'{folder_id}' in parents and name contains '{escaped_name}' and trashed=false"
            
            self.logger.debug(f"🔍 Query search_files: {query}")
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, size)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            self.logger.info(f"🔍 {len(files)} fichier(s) trouvé(s) avec '{name_contains}'")
            
            return files
            
        except Exception as e:
            self.logger.error(f"❌ Erreur recherche fichiers: {e}")
            return []
    
    def find_folder(self, parent_folder_id, folder_name):
        """
        Trouve un sous-dossier par nom exact
        
        Args:
            parent_folder_id: ID du dossier parent
            folder_name: Nom exact du dossier à chercher
        
        Returns:
            str: ID du dossier trouvé ou None
        """
        try:
            escaped_name = folder_name.replace("'", "\\'")
            query = f"'{parent_folder_id}' in parents and name='{escaped_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            
            self.logger.debug(f"🔍 Query find_folder: {query}")
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                self.logger.info(f"📁 Dossier trouvé: {folder_name} (ID: {folder_id})")
                return folder_id
            else:
                self.logger.debug(f"📁 Dossier non trouvé: {folder_name}")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Erreur recherche dossier: {e}")
            return None
    
    def create_folder(self, folder_name, parent_folder_id):
        """
        Crée un dossier dans Drive
        
        Args:
            folder_name: Nom du dossier à créer
            parent_folder_id: ID du dossier parent
        
        Returns:
            str: ID du dossier créé ou None
        """
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            
            folder = self.service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            self.logger.info(f"✅ Dossier créé: {folder_name} (ID: {folder_id})")
            return folder_id
            
        except Exception as e:
            self.logger.error(f"❌ Erreur création dossier: {e}")
            return None
    
    def get_file_metadata(self, file_id):
        """
        Récupère les métadonnées d'un fichier
        
        Args:
            file_id: ID du fichier
        
        Returns:
            dict: Métadonnées du fichier ou None
        """
        try:
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields="id, name, mimeType, size, createdTime, modifiedTime, parents",
                supportsAllDrives=True
            ).execute()
            
            return file_metadata
            
        except Exception as e:
            self.logger.error(f"❌ Erreur récupération métadonnées: {e}")
            return None