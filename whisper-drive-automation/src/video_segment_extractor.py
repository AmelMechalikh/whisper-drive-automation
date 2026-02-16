#!/usr/bin/env python3
"""
Découpeur de vidéos/audios basé sur les highlights Excel
Extrait les segments vidéo/audio correspondants aux timestamps
"""

import logging
import subprocess
from pathlib import Path
import pandas as pd
from typing import List, Dict, Optional
from datetime import timedelta
import json
import re


class VideoSegmentExtractor:
    """Extrait des segments vidéo/audio basés sur un fichier Excel de highlights"""

    def __init__(self, logger=None, add_subtitles=False, paragraphs_file=None):
        """
        Args:
            logger: Logger optionnel
            add_subtitles: DEPRECATED - Les sous-titres sont gérés par subtitle_generator.py
            paragraphs_file: DEPRECATED - Les sous-titres sont gérés par subtitle_generator.py
        """
        self.logger = logger or logging.getLogger(__name__)

        if add_subtitles:
            self.logger.warning("⚠️ add_subtitles=True is deprecated. Subtitles feature moved to subtitle_generator.py module.")
            self.logger.warning("   VideoSegmentExtractor now only handles simple video cutting with ffmpeg.")

        self.add_subtitles = False  # Force désactivation
        self.paragraphs_file = paragraphs_file
    
    def extract_segments(
        self,
        excel_path: str,
        source_video_path: str,
        output_folder: str
    ) -> List[str]:
        """
        Extrait les segments vidéo/audio définis dans le fichier Excel
        Fusionne automatiquement les segments avec le même commentaire
        
        Args:
            excel_path: Chemin vers le fichier Excel avec les highlights
            source_video_path: Chemin vers la vidéo/audio source
            output_folder: Dossier de sortie pour les segments
            
        Returns:
            Liste des chemins des fichiers créés
        """
        # Lire le fichier Excel
        df = pd.read_excel(excel_path, engine='openpyxl')
        
        # Créer le dossier de sortie
        output_dir = Path(output_folder)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Nom de base du fichier source (sans extension)
        source_name = Path(source_video_path).stem
        source_ext = Path(source_video_path).suffix

        created_files = []
        
        # Grouper par numéro de segment (même commentaire)
        grouped = df.groupby('Numéro')
        
        for segment_num, group in grouped:
            # Vérifier s'il faut fusionner plusieurs sous-segments
            segments_to_merge = []
            
            for idx, row in group.iterrows():
                segments_to_merge.append({
                    'start': row['Début (secondes)'],
                    'end': row['Fin (secondes)'],
                    'duration': row['Durée (secondes)']
                })
            
            # Nom du fichier de sortie avec format: groupe_début-fin_début-fin
            comment = group.iloc[0]['Groupe']

            # Construire le nom avec début-fin de chaque sous-segment
            # Ex: s2_0506-0553_0602-0614.mp4
            segment_ranges = []
            for seg in segments_to_merge:
                start_str = self._seconds_to_timecode_short(seg['start'])
                end_str = self._seconds_to_timecode_short(seg['end'])
                segment_ranges.append(f"{start_str}-{end_str}")

            if len(segments_to_merge) == 1:
                # Un seul sous-segment, extraction simple
                seg = segments_to_merge[0]
                start_str = self._seconds_to_timecode_short(seg['start'])
                end_str = self._seconds_to_timecode_short(seg['end'])
                output_filename = f"{comment}_{start_str}-{end_str}{source_ext}"
                output_path = output_dir / output_filename

                # Extraction simple avec ffmpeg
                success = self._extract_segment_ffmpeg(
                    source_video_path,
                    str(output_path),
                    seg['start'],
                    seg['duration']
                )

                if success:
                    created_files.append(str(output_path))
                    self.logger.info(f"✅ Segment {segment_num} créé: {output_filename}")
                else:
                    self.logger.error(f"❌ Échec extraction segment {segment_num}")

            else:
                # Plusieurs sous-segments: créer les fichiers individuels ET la fusion
                self.logger.info(f"🎬 {len(segments_to_merge)} sous-segments pour '{comment}'")

                # 1. Créer chaque sous-segment individuellement
                for i, seg in enumerate(segments_to_merge, 1):
                    start_str = self._seconds_to_timecode_short(seg['start'])
                    end_str = self._seconds_to_timecode_short(seg['end'])
                    subseg_filename = f"{comment}_{start_str}-{end_str}{source_ext}"
                    subseg_path = output_dir / subseg_filename

                    # Note: subtitles feature moved to subtitle_generator.py
                    success = self._extract_segment_ffmpeg(
                        source_video_path,
                        str(subseg_path),
                        seg['start'],
                        seg['duration']
                    )

                    if success:
                        created_files.append(str(subseg_path))
                        self.logger.info(f"✅ Sous-segment {i}/{len(segments_to_merge)} créé: {subseg_filename}")
                    else:
                        self.logger.error(f"❌ Échec extraction sous-segment {i}")

                # 2. Créer la version fusionnée
                self.logger.info(f"🔗 Fusion de {len(segments_to_merge)} sous-segments en un seul fichier")
                fusion_filename = f"{comment}_FUSION{source_ext}"
                fusion_path = output_dir / fusion_filename

                success = self._extract_and_merge_segments(
                    source_video_path,
                    str(fusion_path),
                    segments_to_merge,
                    output_dir
                )

                if success:
                    created_files.append(str(fusion_path))
                    self.logger.info(f"✅ Segment fusionné créé: {fusion_filename}")
                else:
                    self.logger.error(f"❌ Échec fusion segment {segment_num}")
        
        # Note: Subtitles feature has been moved to subtitle_generator.py

        self.logger.info(f"🎬 {len(created_files)} fichier(s) total créé(s)")
        return created_files

    def _load_whisperx_models(self):
        """
        DEPRECATED: Subtitles feature moved to subtitle_generator.py
        This method is kept for backward compatibility but raises an error.
        """
        raise NotImplementedError(
            "Subtitles feature has been moved to subtitle_generator.py module. "
            "VideoSegmentExtractor now only handles simple video cutting with ffmpeg. "
            "Set add_subtitles=False or use the new SubtitleGenerator class."
        )

    def _load_whisperx_models_OLD(self):
        """OLD VERSION - DO NOT USE"""
        try:
            import torch
            import whisperx

            # Fix pour PyTorch 2.8+ weights_only issue
            try:
                import omegaconf
                torch.serialization.add_safe_globals([omegaconf.listconfig.ListConfig, omegaconf.dictconfig.DictConfig])
            except Exception:
                pass  # Ignorer si omegaconf n'est pas disponible

            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"

            self.logger.info(f"🔄 Chargement des modèles WhisperX sur {device}...")

            # Charger le modèle Whisper pour la transcription initiale
            self.whisperx_model = whisperx.load_model("base", device, compute_type=compute_type)

            # Stocker les métadonnées pour l'alignement
            self.whisperx_metadata = {
                "device": device,
                "compute_type": compute_type
            }

            self.logger.info("✅ Modèles WhisperX chargés")

        except ImportError:
            self.logger.error("❌ WhisperX non installé. Installez avec: pip install whisperx")
            raise
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement WhisperX: {e}")
            raise

    def _extract_text_from_paragraphs(self, start_time: float, end_time: float) -> Optional[str]:
        """
        Extrait le texte du segment depuis _paragraphs_timestamps.txt

        Args:
            start_time: Début du segment en secondes
            end_time: Fin du segment en secondes

        Returns:
            Le texte du segment ou None si non trouvé
        """
        if not self.paragraphs_file or not Path(self.paragraphs_file).exists():
            self.logger.warning(f"⚠️ Fichier paragraphs non trouvé: {self.paragraphs_file}")
            return None

        try:
            with open(self.paragraphs_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Format attendu: (MM:SS) ou (H:MM:SS) Texte du paragraphe
            # Pattern pour matcher (MM:SS) ou (H:MM:SS) au début d'une ligne
            pattern = r'\((\d{1,2}):(\d{2})\)\s*(.+?)(?=\n\(|\n\n|\Z)'
            matches = re.findall(pattern, content, re.DOTALL)

            # Convertir start_time et end_time en secondes pour comparaison
            target_start = start_time
            target_end = end_time

            # Accumuler tous les paragraphes qui sont dans l'intervalle
            collected_texts = []

            for i, match in enumerate(matches):
                m_or_h, s, text = match

                # Convertir en secondes
                para_start = int(m_or_h) * 60 + int(s)

                # Pour la fin du paragraphe, utiliser le début du suivant (ou end_time si dernier)
                if i + 1 < len(matches):
                    next_m_or_h, next_s, _ = matches[i + 1]
                    para_end = int(next_m_or_h) * 60 + int(next_s)
                else:
                    para_end = target_end + 60  # Ajouter une marge pour le dernier paragraphe

                # Vérifier si ce paragraphe chevauche notre segment
                overlap_start = max(target_start, para_start)
                overlap_end = min(target_end, para_end)

                if overlap_end > overlap_start:
                    # Nettoyer le texte
                    cleaned_text = text.strip()
                    if cleaned_text:
                        collected_texts.append(cleaned_text)

            if collected_texts:
                # Joindre tous les paragraphes trouvés
                full_text = " ".join(collected_texts)
                self.logger.info(f"📝 Texte extrait ({len(collected_texts)} paragraphe(s)): {full_text[:100]}...")
                return full_text

            self.logger.warning(f"⚠️ Aucun texte trouvé pour le segment {start_time}-{end_time}")
            return None

        except Exception as e:
            self.logger.error(f"❌ Erreur lecture paragraphs: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _align_text_with_whisperx(self, audio_path: str, text: str, start_offset: float = 0.0) -> Optional[List[Dict]]:
        """
        Utilise WhisperX pour aligner le texte avec l'audio

        Args:
            audio_path: Chemin vers le fichier audio du segment
            text: Texte à aligner (depuis _paragraphs_timestamps.txt)
            start_offset: Offset de temps pour ajuster les timestamps (début du segment)

        Returns:
            Liste de dicts avec word-level timestamps: [{"word": "hello", "start": 0.5, "end": 0.8}, ...]
        """
        try:
            import whisperx

            # Charger les modèles si nécessaire
            self._load_whisperx_models()

            device = self.whisperx_metadata["device"]

            # Charger l'audio
            audio = whisperx.load_audio(audio_path)

            # Transcrire avec Whisper (pour avoir la structure de base)
            result = self.whisperx_model.transcribe(audio, batch_size=16)

            # Charger le modèle d'alignement (langue détectée automatiquement)
            language = result.get("language", "fr")
            model_a, metadata = whisperx.load_align_model(language_code=language, device=device)

            # Forcer l'alignement avec le texte fourni
            # On remplace le texte transcrit par le texte modifié
            result["segments"] = [{"text": text}]

            # Aligner
            aligned_result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                device,
                return_char_alignments=False
            )

            # Extraire les mots avec timestamps
            words = []
            if "segments" in aligned_result and len(aligned_result["segments"]) > 0:
                for segment in aligned_result["segments"]:
                    if "words" in segment:
                        for word_info in segment["words"]:
                            words.append({
                                "word": word_info.get("word", ""),
                                "start": word_info.get("start", 0.0) + start_offset,
                                "end": word_info.get("end", 0.0) + start_offset
                            })

            self.logger.info(f"✅ Alignement réussi: {len(words)} mots")
            return words

        except Exception as e:
            self.logger.error(f"❌ Erreur alignement WhisperX: {e}")
            return None

    def _generate_ass_subtitle(self, words: List[Dict], output_path: str, video_duration: float):
        """
        Génère un fichier ASS avec style Instagram (Indivisible Bold, fond blanc, texte noir)

        Args:
            words: Liste de mots avec timestamps
            output_path: Chemin du fichier .ass à créer
            video_duration: Durée totale de la vidéo en secondes
        """
        try:
            # Header ASS avec style Instagram
            # Police: Indivisible Bold (fallback: Arial Bold si Indivisible n'est pas installée)
            # Couleurs ASS format: &HAABBGGRR (inversé par rapport à RGB normal)
            # &H00000000 = noir (texte), &H00FFFFFF = blanc (fond/outline)
            ass_content = """[Script Info]
Title: Instagram Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Instagram,Indivisible,80,&H00000000,&H000000FF,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,8,0,2,10,10,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

            # Grouper les mots par petits chunks (2-4 mots) pour un style Instagram dynamique
            chunk_size = 3
            chunks = []

            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                if chunk_words:
                    text = " ".join([w["word"] for w in chunk_words])
                    start_time = chunk_words[0]["start"]
                    end_time = chunk_words[-1]["end"]
                    chunks.append({
                        "text": text,
                        "start": start_time,
                        "end": end_time
                    })

            # Ajouter les dialogues
            for chunk in chunks:
                start_str = self._seconds_to_ass_time(chunk["start"])
                end_str = self._seconds_to_ass_time(chunk["end"])
                text = chunk["text"].replace("\n", " ")
                ass_content += f"Dialogue: 0,{start_str},{end_str},Instagram,,0,0,0,,{text}\n"

            # Écrire le fichier
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(ass_content)

            self.logger.info(f"✅ Fichier ASS créé: {output_path}")

        except Exception as e:
            self.logger.error(f"❌ Erreur création ASS: {e}")
            raise

    def _seconds_to_ass_time(self, seconds: float) -> str:
        """Convertit secondes en format ASS: H:MM:SS.CS (centiseconds)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def _save_alignment_json(self, words: List[Dict], output_path: str):
        """Sauvegarde les timestamps alignés en JSON"""
        try:
            data = {
                "words": words,
                "word_count": len(words),
                "source": "WhisperX forced alignment"
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"✅ JSON sauvegardé: {output_path}")

        except Exception as e:
            self.logger.error(f"❌ Erreur sauvegarde JSON: {e}")
            raise
    
    def _extract_segment_with_subtitles(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        duration: float,
        subtitles_dir: Path
    ) -> bool:
        """
        Extrait un segment et ajoute des sous-titres brûlés avec style Instagram

        Args:
            input_path: Fichier source
            output_path: Fichier de sortie final
            start_seconds: Début en secondes
            duration: Durée en secondes
            subtitles_dir: Dossier où sauvegarder les fichiers ASS/JSON

        Returns:
            True si succès
        """
        try:
            # 1. Extraire le segment temporaire (sans sous-titres)
            temp_video = Path(output_path).parent / f"temp_{Path(output_path).name}"

            success = self._extract_segment_ffmpeg(
                input_path,
                str(temp_video),
                start_seconds,
                duration
            )

            if not success:
                return False

            # 2. Extraire l'audio du segment
            temp_audio = Path(output_path).parent / f"temp_audio_{Path(output_path).stem}.wav"

            cmd_audio = [
                'ffmpeg',
                '-i', str(temp_video),
                '-vn',  # Pas de vidéo
                '-acodec', 'pcm_s16le',  # Format WAV
                '-ar', '16000',  # Sample rate pour WhisperX
                '-ac', '1',  # Mono
                '-y',
                str(temp_audio)
            ]

            subprocess.run(cmd_audio, capture_output=True, text=True, check=True)

            # 3. Récupérer le texte depuis _paragraphs_timestamps.txt
            end_seconds = start_seconds + duration
            text = self._extract_text_from_paragraphs(start_seconds, end_seconds)

            if not text:
                self.logger.warning(f"⚠️ Pas de texte trouvé, segment sans sous-titres")
                # Renommer temp_video en output_path
                temp_video.rename(output_path)
                temp_audio.unlink(missing_ok=True)
                return True

            # 4. Aligner avec WhisperX
            words = self._align_text_with_whisperx(str(temp_audio), text, start_offset=0.0)

            if not words or len(words) == 0:
                self.logger.warning(f"⚠️ Alignement échoué, segment sans sous-titres")
                temp_video.rename(output_path)
                temp_audio.unlink(missing_ok=True)
                return True

            # 5. Créer les fichiers de sous-titres
            subtitles_dir.mkdir(parents=True, exist_ok=True)

            base_name = Path(output_path).stem
            ass_file = subtitles_dir / f"{base_name}.ass"
            json_file = subtitles_dir / f"{base_name}.json"

            self._generate_ass_subtitle(words, str(ass_file), duration)
            self._save_alignment_json(words, str(json_file))

            # 6. Brûler les sous-titres dans la vidéo
            cmd_burn = [
                'ffmpeg',
                '-i', str(temp_video),
                '-vf', f"ass={str(ass_file)}",
                '-c:a', 'copy',  # Copier l'audio sans réencoder
                '-y',
                output_path
            ]

            result = subprocess.run(cmd_burn, capture_output=True, text=True, check=True)

            # 7. Nettoyer les fichiers temporaires
            temp_video.unlink(missing_ok=True)
            temp_audio.unlink(missing_ok=True)

            self.logger.info(f"✅ Sous-titres brûlés dans: {Path(output_path).name}")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ Erreur ffmpeg sous-titres: {e.stderr}")
            # Nettoyer
            Path(temp_video).unlink(missing_ok=True)
            Path(temp_audio).unlink(missing_ok=True)
            return False
        except Exception as e:
            self.logger.error(f"❌ Erreur extraction avec sous-titres: {e}")
            return False

    def _extract_segment_ffmpeg(
        self,
        input_path: str,
        output_path: str,
        start_seconds: float,
        duration: float
    ) -> bool:
        """
        Extrait un segment avec ffmpeg

        Args:
            input_path: Fichier source
            output_path: Fichier de sortie
            start_seconds: Début en secondes
            duration: Durée en secondes

        Returns:
            True si succès
        """
        try:
            # Détecter si c'est un fichier audio pur ou une vidéo
            audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma']
            source_ext = Path(input_path).suffix.lower()
            is_audio_only = source_ext in audio_extensions

            # Commande ffmpeg pour extraire le segment
            # -accurate_seek : seek précis même avec -c copy
            # -ss : position de départ (AVANT -i pour éviter écran noir)
            # -i : input file
            # -t : durée
            # Pour audio pur : -c:a copy (pas de ré-encodage, garde format original)
            # Pour vidéo : -c:v copy -c:a aac (ré-encode audio en AAC pour compatibilité)
            # -avoid_negative_ts make_zero : évite les problèmes de timestamps négatifs
            cmd = [
                'ffmpeg',
                '-accurate_seek',
                '-ss', str(start_seconds),
                '-i', input_path,
                '-t', str(duration),
            ]

            # Adapter les codecs selon le type de fichier
            if is_audio_only:
                # Audio pur : copie directe sans ré-encodage
                cmd.extend(['-c:a', 'copy'])
            else:
                # Vidéo : copie vidéo + ré-encode audio en AAC
                cmd.extend(['-c:v', 'copy', '-c:a', 'aac'])

            cmd.extend([
                '-avoid_negative_ts', 'make_zero',
                '-y',  # Overwrite output file
                output_path
            ])
            
            # Exécuter ffmpeg
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur ffmpeg: {e.stderr}")
            return False
        except FileNotFoundError:
            self.logger.error("ffmpeg non trouvé. Installez-le avec: brew install ffmpeg")
            return False
        except Exception as e:
            self.logger.error(f"Erreur extraction segment: {e}")
            return False
    
    def _extract_and_merge_segments(
        self,
        input_path: str,
        output_path: str,
        segments: List[Dict],
        temp_dir: Path
    ) -> bool:
        """
        Extrait plusieurs segments et les fusionne en une seule vidéo

        Args:
            input_path: Fichier source
            output_path: Fichier de sortie final
            segments: Liste de dict avec 'start' et 'duration'
            temp_dir: Dossier temporaire pour les segments intermédiaires

        Returns:
            True si succès
        """
        try:
            temp_segments = []

            # 1. Extraire chaque segment individuellement
            for i, seg in enumerate(segments):
                temp_output = temp_dir / f"temp_segment_{i}.mp4"

                # Note: subtitles feature has been moved to subtitle_generator.py
                # Always use simple extraction
                success = self._extract_segment_ffmpeg(
                    input_path,
                    str(temp_output),
                    seg['start'],
                    seg['duration']
                )

                if success:
                    temp_segments.append(str(temp_output))
                else:
                    self.logger.error(f"Échec extraction segment {i}")
                    return False
            
            # 2. Créer le fichier concat list pour ffmpeg
            concat_file = temp_dir / "concat_list.txt"
            with open(concat_file, 'w') as f:
                for seg_path in temp_segments:
                    # Utiliser le chemin absolu et échapper les apostrophes pour ffmpeg
                    from pathlib import Path
                    abs_path = str(Path(seg_path).absolute())
                    # Échapper les apostrophes en les remplaçant par '\''
                    escaped_path = abs_path.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            # 3. Fusionner tous les segments
            # Détecter si la sortie est audio pur ou vidéo
            audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma']
            output_ext = Path(output_path).suffix.lower()
            is_audio_only = output_ext in audio_extensions

            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
            ]

            # Adapter les codecs selon le type de sortie
            if is_audio_only:
                # Audio pur : copie directe
                cmd.extend(['-c:a', 'copy'])
            else:
                # Vidéo : copie vidéo + AAC pour audio
                cmd.extend(['-c:v', 'copy', '-c:a', 'aac'])

            cmd.extend(['-y', output_path])

            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # 4. Nettoyer les fichiers temporaires
            for temp_file in temp_segments:
                Path(temp_file).unlink(missing_ok=True)
            concat_file.unlink(missing_ok=True)
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erreur fusion ffmpeg: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Erreur fusion segments: {e}")
            return False
    
    def get_segment_info(self, video_path: str) -> Dict:
        """
        Utilise ffprobe pour obtenir les informations d'un segment vidéo

        Args:
            video_path: Chemin vers le fichier vidéo

        Returns:
            Dict avec durée, codec, taille, etc.
        """
        try:
            import json
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            data = json.loads(result.stdout)

            # Extraire les infos importantes
            format_info = data.get('format', {})
            video_stream = next(
                (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
                {}
            )

            return {
                'duration': float(format_info.get('duration', 0)),
                'size_bytes': int(format_info.get('size', 0)),
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'width': video_stream.get('width'),
                'height': video_stream.get('height'),
                'bitrate': int(format_info.get('bit_rate', 0))
            }

        except Exception as e:
            self.logger.error(f"Erreur ffprobe: {e}")
            return {}

    def _sanitize_filename(self, text: str) -> str:
        """Nettoie un texte pour l'utiliser dans un nom de fichier"""
        import re
        # Garder seulement lettres, chiffres, espaces, tirets
        text = re.sub(r'[^\w\s-]', '', text)
        # Remplacer espaces par underscores
        text = re.sub(r'\s+', '_', text)
        return text.strip('_')
    
    def _seconds_to_ffmpeg_time(self, seconds: float) -> str:
        """Convertit secondes en format ffmpeg HH:MM:SS.mmm"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = td.total_seconds() % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

    def _seconds_to_timecode_short(self, seconds: float) -> str:
        """Convertit secondes en format court MMSS pour nom de fichier"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}{secs:02d}"


def main():
    """Test local"""
    logging.basicConfig(level=logging.INFO)
    
    extractor = VideoSegmentExtractor()
    
    # Exemple d'utilisation
    excel_path = "path/to/highlights.xlsx"
    source_video = "path/to/source_video.mp4"
    output_folder = "path/to/output_segments"
    
    extractor.extract_segments(excel_path, source_video, output_folder)


if __name__ == '__main__':
    main()
