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
        Génère tous les formats de sortie
        
        Args:
            base_filename: Nom de base du fichier (sans extension)
            whisper_result: Résultat de transcription Whisper
            paragraphs: Paragraphes groupés (optionnel)
        
        Returns:
            dict: Chemins des fichiers générés
        """
        output_files = {}
        try:
            # 1. Transcription texte simple
            txt_path = self._generate_transcription_txt(base_filename, whisper_result)
            output_files['transcription'] = txt_path

            # 1b. Transcription Google Doc
            try:
                gdoc_url = self._generate_transcription_gdoc(base_filename, whisper_result)
                output_files['gdoc'] = gdoc_url
            except Exception as e:
                self.logger.error(f"Erreur création Google Doc: {e}")

            # 2. Format SRT avec timestamps
            srt_path = self._generate_srt(base_filename, whisper_result)
            output_files['srt'] = srt_path

            # 3. Word timestamps
            word_timestamps_path = self._generate_word_timestamps(base_filename, whisper_result)
            output_files['word_timestamps'] = word_timestamps_path

            # 4. Paragraphes avec timestamps (si disponible)
            if paragraphs:
                paragraphs_path = self._generate_paragraphs_timestamps(base_filename, paragraphs)
                output_files['paragraphs'] = paragraphs_path

            # 5. JSON complet
            json_path = self._generate_complete_json(base_filename, whisper_result, paragraphs)
            output_files['complete_json'] = json_path

            self.logger.info(f"✅ Tous les formats générés pour: {base_filename}")
            return output_files

        except Exception as e:
            self.logger.error(f"❌ Erreur génération outputs: {e}")
            return {}
        def _generate_transcription_gdoc(self, base_filename, result):
            """Crée un Google Doc sur Drive avec la transcription"""
            import json
            from pathlib import Path
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))
            from drive_manager import DriveManager
            import os
            config_path = Path(__file__).parent.parent / 'config' / 'highlight_config.json'
            with open(config_path) as f:
                config = json.load(f)
            credentials_path = Path(__file__).parent.parent / 'config' / 'credentials.json'
            drive_manager = DriveManager(str(credentials_path))
            folder_id = config['drive_folders']['highlighted_files']

            # Créer le Google Doc
            doc_metadata = {
                'name': f"{base_filename}_transcription",
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [folder_id]
            }
            doc = drive_manager.service.files().create(
                body=doc_metadata,
                supportsAllDrives=True
            ).execute()
            doc_id = doc['id']
            from googleapiclient.discovery import build
            docs_service = build('docs', 'v1', credentials=drive_manager.service._http.credentials)
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1,
                        },
                        'text': result['text']
                    }
                }
            ]
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            url = f"https://docs.google.com/document/d/{doc_id}/edit"
            self.logger.info(f"📝 Google Doc créé: {url}")
            return url
    
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

        # Si drive_manager est disponible, créer un Google Doc
        if self.drive_manager and self.output_folder_id:
            doc_name = f"{base_filename}_paragraphs_timestamps"
            doc_id = self._create_google_doc(doc_name, full_content)
            self.logger.info(f"📝 Google Doc créé: {doc_name} (ID: {doc_id})")
            # Retourner un format qui indique que c'est un Google Doc
            return f"gdoc:{doc_id}"
        else:
            # Fallback: créer un fichier local .txt
            filename = f"{base_filename}_paragraphs_timestamps.txt"
            file_path = self.output_dir / filename

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)

            self.logger.info(f"📝 Paragraphes avec timestamps sauvés: {file_path}")
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
        docs_service = build('docs', 'v1', credentials=self.drive_manager.creds)

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