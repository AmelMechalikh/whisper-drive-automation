"""
Module de génération des fichiers de sortie
Formats: TXT, SRT, JSON, Word timestamps, Paragraphs (Google Docs)
"""
import json
import logging
from pathlib import Path
from datetime import timedelta

class OutputGenerator:
    """Générateur de fichiers de sortie pour les transcriptions"""

    def __init__(self, output_dir='transcriptions_output', drive_manager=None, output_folder_id=None):
        """
        Initialise le générateur de sortie

        Args:
            output_dir: Dossier de sortie local
            drive_manager: Instance de DriveManager (pour créer des Google Docs)
            output_folder_id: ID du dossier Drive pour les Google Docs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.drive_manager = drive_manager
        self.output_folder_id = output_folder_id
        self.logger = logging.getLogger(__name__)
    
    def generate_all_outputs(self, base_filename, whisper_result, paragraphs=None):
        """
        Génère les formats de sortie essentiels (paragraphs_timestamps + complete_json)

        Args:
            base_filename: Nom de base du fichier (sans extension)
            whisper_result: Résultat de transcription Whisper
            paragraphs: Paragraphes groupés (optionnel)

        Returns:
            dict: Chemins des fichiers générés
        """
        output_files = {}
        try:
            # 1. Paragraphes avec timestamps (Google Doc) - ESSENTIEL
            if paragraphs:
                paragraphs_path = self._generate_paragraphs_timestamps(base_filename, paragraphs)
                output_files['paragraphs'] = paragraphs_path
            else:
                self.logger.warning(f"⚠️ Pas de paragraphes disponibles pour {base_filename}")

            # 2. JSON complet (data.json) - ESSENTIEL
            json_path = self._generate_complete_json(base_filename, whisper_result, paragraphs)
            output_files['complete_json'] = json_path

            self.logger.info(f"✅ Formats essentiels générés pour: {base_filename} (paragraphs + JSON)")
            return output_files

        except Exception as e:
            self.logger.error(f"❌ Erreur génération outputs: {e}")
            return {}

    def _generate_transcription_txt(self, base_filename, result):
        """Génère le fichier de transcription simple"""
        filename = f"{base_filename}_transcription.txt"
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
            
        self.logger.info(f"💾 Transcription sauvée: {file_path}")
        return str(file_path)
    
    def _generate_srt(self, base_filename, result):
        """Génère le fichier SRT avec timestamps"""
        filename = f"{base_filename}_with_timestamps.srt"
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(result['segments'], 1):
                start_time = self._seconds_to_srt_time(segment['start'])
                end_time = self._seconds_to_srt_time(segment['end'])
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{segment['text'].strip()}\n\n")
        
        self.logger.info(f"⏰ SRT sauvé: {file_path}")
        return str(file_path)
    
    def _generate_word_timestamps(self, base_filename, result):
        """Génère le fichier avec timestamps par mot"""
        filename = f"{base_filename}_word_timestamps.txt"
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for segment in result['segments']:
                if 'words' in segment:
                    for word_info in segment['words']:
                        start_time = self._seconds_to_timestamp(word_info['start'])
                        end_time = self._seconds_to_timestamp(word_info['end'])
                        word = word_info['word'].strip()
                        f.write(f"[{start_time} --> {end_time}] {word}\n")
        
        self.logger.info(f"🔤 Word timestamps sauvés: {file_path}")
        return str(file_path)
    
    def _generate_paragraphs_timestamps(self, base_filename, paragraphs):
        """
        Génère le fichier paragraphs_timestamps
        Crée directement un Google Doc si drive_manager est disponible, sinon fichier local
        """
        # Construire le contenu
        content_lines = []
        for paragraph in paragraphs:
            line_parts = []

            if 'segments' in paragraph:
                for segment in paragraph['segments']:
                    timestamp = self._seconds_to_simple_timestamp(segment['start'])
                    text = segment['text'].strip()
                    line_parts.append(f"({timestamp}) {text}")
            else:
                # Format alternatif : paragraphe simple avec un timestamp
                timestamp = self._seconds_to_simple_timestamp(paragraph['start'])
                text = paragraph['text'].strip()
                line_parts.append(f"({timestamp}) {text}")

            # Ajouter la ligne avec tous les segments
            content_lines.append(' '.join(line_parts))

        full_content = '\n\n'.join(content_lines)

        # Créer un Google Doc si drive_manager disponible, sinon TXT local
        if self.drive_manager and self.output_folder_id:
            doc_name = f"{base_filename}_paragraphs_timestamps"
            try:
                doc_id = self._create_google_doc(doc_name, full_content)
                self.logger.info(f"📝 Google Doc créé: {doc_name} (ID: {doc_id})")
                return f"gdoc:{doc_id}"
            except Exception as e:
                self.logger.error(f"❌ Erreur création Google Doc: {e}")
                # Fallback sur fichier local

        # Fichier local TXT (fallback ou si pas de drive_manager)
        filename = f"{base_filename}_paragraphs_timestamps.txt"
        file_path = self.output_dir / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        self.logger.info(f"📝 Paragraphes avec timestamps sauvés (TXT): {file_path}")
        return str(file_path)

    def _create_google_doc(self, doc_name, content):
        """
        Crée un Google Doc avec le contenu spécifié

        Args:
            doc_name: Nom du document
            content: Contenu texte du document

        Returns:
            str: ID du document créé
        """
        from googleapiclient.discovery import build

        # Créer le document vide
        doc_metadata = {
            'name': doc_name,
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [self.output_folder_id]
        }

        doc = self.drive_manager.service.files().create(
            body=doc_metadata,
            supportsAllDrives=True
        ).execute()

        doc_id = doc['id']

        # Insérer le contenu via l'API Docs
        # Utiliser les mêmes credentials que le drive_manager
        from google.auth import default as get_default_credentials
        from google.oauth2.service_account import Credentials

        if self.drive_manager.credentials_path:
            creds = Credentials.from_service_account_file(
                self.drive_manager.credentials_path,
                scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
            )
        else:
            creds, _ = get_default_credentials(
                scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
            )

        docs_service = build('docs', 'v1', credentials=creds)

        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': content
            }
        }]

        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()

        return doc_id
    
    def _seconds_to_simple_timestamp(self, seconds):
        """Convertit secondes en format M:SS (sans zéros inutiles)"""
        minutes, seconds_remainder = divmod(seconds, 60)
        return f"{int(minutes)}:{int(seconds_remainder):02d}"
    
    def _generate_complete_json(self, base_filename, result, paragraphs=None):
        """Génère le fichier JSON complet avec toutes les données"""
        filename = f"{base_filename}_complete_data.json"
        file_path = self.output_dir / filename
        
        complete_data = {
            'metadata': {
                'filename': base_filename,
                'language': result.get('language', 'unknown'),
                'duration': max(segment['end'] for segment in result['segments']) if result['segments'] else 0,
                'total_segments': len(result['segments'])
            },
            'full_text': result['text'],
            'segments': result['segments']
        }
        
        if paragraphs:
            complete_data['paragraphs'] = paragraphs
            complete_data['metadata']['total_paragraphs'] = len(paragraphs)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"📊 JSON complet sauvé: {file_path}")
        return str(file_path)
    
    def _seconds_to_srt_time(self, seconds):
        """Convertit secondes en format SRT (HH:MM:SS,mmm)"""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(td.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds % 1) * 1000)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def _seconds_to_timestamp(self, seconds):
        """Convertit secondes en format MM:SS.mmm"""
        minutes, seconds_remainder = divmod(seconds, 60)
        return f"{int(minutes):02d}:{seconds_remainder:06.3f}"