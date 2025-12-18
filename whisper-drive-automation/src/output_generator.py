"""
Module de génération des fichiers de sortie
Formats: TXT, SRT, JSON, Word timestamps, Paragraphs
"""
import json
import logging
from pathlib import Path
from datetime import timedelta

class OutputGenerator:
    """Générateur de fichiers de sortie pour les transcriptions"""
    
    def __init__(self, output_dir='transcriptions_output'):
        """
        Initialise le générateur de sortie
        
        Args:
            output_dir: Dossier de sortie local
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
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
        """Génère le fichier avec paragraphes et timestamps"""
        filename = f"{base_filename}_paragraphs_timestamps.txt"
        file_path = self.output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            for i, paragraph in enumerate(paragraphs, 1):
                start_time = self._seconds_to_timestamp(paragraph['start'])
                end_time = self._seconds_to_timestamp(paragraph['end'])
                
                f.write(f"=== Paragraphe {i} ===\n")
                f.write(f"Temps: {start_time} --> {end_time}\n")
                f.write(f"Mots: {paragraph['word_count']}\n")
                f.write(f"Texte: {paragraph['text']}\n\n")
        
        self.logger.info(f"📝 Paragraphes avec timestamps sauvés: {file_path}")
        return str(file_path)
    
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