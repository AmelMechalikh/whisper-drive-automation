"""
Module de transcription Whisper pour l'automation
Gestion de la transcription audio avec timestamps
"""
import whisper
import logging
import subprocess
import tempfile
import os
from pathlib import Path
import json

class WhisperTranscriber:
    """Gestionnaire de transcription Whisper"""
    
    def __init__(self, model='large', device='cpu', language='fr'):
        """
        Initialise le transcripteur Whisper
        
        Args:
            model: Modèle Whisper à utiliser (base, small, large)
            device: Device de calcul (cpu, cuda)
            language: Langue de transcription (auto-détection si None)
        """
        self.model_name = model
        self.device = device
        self.language = language
        self.model = None
        self.logger = logging.getLogger(__name__)
        self._load_model()
    
    def _load_model(self):
        """Charge le modèle Whisper"""
        try:
            self.logger.info(f"🤖 Chargement du modèle Whisper: {self.model_name}")
            self.model = whisper.load_model(self.model_name, device=self.device)
            self.logger.info("✅ Modèle Whisper chargé")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement modèle Whisper: {e}")
            raise
    
    def transcribe_audio(self, audio_path, test_mode=False, test_duration=600):
        """
        Transcrit un fichier audio avec Whisper
        
        Args:
            audio_path: Chemin vers le fichier audio
            test_mode: Mode test (limitation durée)
            test_duration: Durée en secondes pour le mode test
        
        Returns:
            dict: Résultat de transcription Whisper
        """
        try:
            file_name = Path(audio_path).name
            self.logger.info(f"🎵 Début transcription: {file_name}")
            
            # Mode test avec limitation durée
            audio_to_transcribe = audio_path
            if test_mode:
                self.logger.info(f"⏱️  Limitation à {test_duration//60} minutes pour le test")
                audio_to_transcribe = self._limit_audio_duration(
                    audio_path, test_duration
                )
            
            # Options de transcription
            transcribe_options = {
                'word_timestamps': True,
                'verbose': False
            }
            
            if self.language:
                transcribe_options['language'] = self.language
            
            # Ajout du vocabulaire technique spécialisé
            if hasattr(self, 'vocabulary') and self.vocabulary:
                # Créer un prompt initial avec les mots techniques
                vocabulary_prompt = "Mots techniques: " + ", ".join(self.vocabulary)
                transcribe_options['initial_prompt'] = vocabulary_prompt
                self.logger.info(f"📝 Vocabulaire technique ajouté: {len(self.vocabulary)} termes")
            
            # Transcription
            result = self.model.transcribe(audio_to_transcribe, **transcribe_options)
            
            # Nettoyage fichier temporaire si mode test
            if test_mode and audio_to_transcribe != audio_path:
                try:
                    os.remove(audio_to_transcribe)
                except:
                    pass
            
            duration_info = f" ({test_duration//60} premières minutes)" if test_mode else ""
            self.logger.info(f"✅ Transcription terminée: {file_name}{duration_info}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur transcription {file_name}: {e}")
            return None
    
    def _limit_audio_duration(self, audio_path, duration_seconds):
        """
        Limite la durée d'un fichier audio avec ffmpeg
        
        Args:
            audio_path: Fichier audio original
            duration_seconds: Durée limite en secondes
        
        Returns:
            str: Chemin du fichier audio limité
        """
        try:
            file_id = Path(audio_path).stem
            temp_audio = f"/tmp/temp_{duration_seconds}s_{file_id}.mp3"
            
            subprocess.run([
                'ffmpeg', '-i', audio_path, '-t', str(duration_seconds), 
                '-c', 'copy', temp_audio, '-y'
            ], check=True, capture_output=True)
            
            self.logger.info(f"✂️  Fichier coupé à {duration_seconds//60} minutes")
            return temp_audio
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Erreur ffmpeg: {e}")
            return audio_path
    
    def group_segments_to_paragraphs(self, segments, pause_threshold=3.0, min_words=5, max_duration=30.0):
        """
        Groupe les segments en paragraphes basés sur les pauses
        
        Args:
            segments: Segments de transcription Whisper
            pause_threshold: Seuil de pause pour nouveau paragraphe (secondes)
            min_words: Minimum de mots par paragraphe
            max_duration: Durée maximale d'un paragraphe (secondes)
        
        Returns:
            list: Liste de paragraphes avec timestamps
        """
        if not segments:
            return []
        
        paragraphs = []
        current_paragraph = {
            'start': segments[0]['start'],
            'end': segments[0]['end'],
            'text': '',
            'word_count': 0
        }
        
        for i, segment in enumerate(segments):
            segment_text = segment['text'].strip()
            segment_words = len(segment_text.split())
            
            # Conditions pour nouveau paragraphe
            should_start_new = False
            
            if i > 0:
                pause_duration = segment['start'] - segments[i-1]['end']
                paragraph_duration = segment['end'] - current_paragraph['start']
                
                if (pause_duration >= pause_threshold or 
                    paragraph_duration >= max_duration or
                    current_paragraph['word_count'] >= 50):
                    should_start_new = True
            
            if should_start_new and current_paragraph['word_count'] >= min_words:
                # Finaliser le paragraphe précédent
                current_paragraph['text'] = current_paragraph['text'].strip()
                paragraphs.append(current_paragraph)
                
                # Commencer nouveau paragraphe
                current_paragraph = {
                    'start': segment['start'],
                    'end': segment['end'],
                    'text': segment_text,
                    'word_count': segment_words
                }
            else:
                # Ajouter au paragraphe actuel
                if current_paragraph['text']:
                    current_paragraph['text'] += ' ' + segment_text
                else:
                    current_paragraph['text'] = segment_text
                
                current_paragraph['end'] = segment['end']
                current_paragraph['word_count'] += segment_words
        
        # Ajouter le dernier paragraphe
        if current_paragraph['text'] and current_paragraph['word_count'] >= min_words:
            current_paragraph['text'] = current_paragraph['text'].strip()
            paragraphs.append(current_paragraph)
        
        return paragraphs