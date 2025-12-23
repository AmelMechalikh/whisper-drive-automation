#!/usr/bin/env python3
"""
Découpeur de vidéos/audios basé sur les highlights Excel
Extrait les segments vidéo/audio correspondants aux timestamps
"""

import logging
import subprocess
from pathlib import Path
import pandas as pd
from typing import List, Dict
from datetime import timedelta


class VideoSegmentExtractor:
    """Extrait des segments vidéo/audio basés sur un fichier Excel de highlights"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
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
            
            # Nom du fichier de sortie
            comment = group.iloc[0]['Commentaire']
            # Nettoyer le commentaire pour le nom de fichier
            safe_comment = self._sanitize_filename(comment)[:30]
            output_filename = f"{source_name}_highlight_{segment_num:02d}_{safe_comment}{source_ext}"
            output_path = output_dir / output_filename
            
            if len(segments_to_merge) == 1:
                # Un seul segment, extraction simple
                seg = segments_to_merge[0]
                success = self._extract_segment_ffmpeg(
                    source_video_path,
                    str(output_path),
                    seg['start'],
                    seg['duration']
                )
            else:
                # Plusieurs segments à fusionner
                self.logger.info(f"🔗 Fusion de {len(segments_to_merge)} segments pour '{comment}'")
                success = self._extract_and_merge_segments(
                    source_video_path,
                    str(output_path),
                    segments_to_merge,
                    output_dir
                )
            
            if success:
                created_files.append(str(output_path))
                self.logger.info(f"✅ Segment {segment_num} créé: {output_filename}")
            else:
                self.logger.error(f"❌ Échec extraction segment {segment_num}")
        
        self.logger.info(f"🎬 {len(created_files)} segment(s) vidéo créé(s)")
        return created_files
    
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
            # Commande ffmpeg pour extraire le segment
            # -ss : position de départ
            # -t : durée
            # -c copy : copie les streams sans réencoder (rapide)
            # -avoid_negative_ts make_zero : évite les problèmes de timestamps négatifs
            cmd = [
                'ffmpeg',
                '-ss', str(start_seconds),
                '-i', input_path,
                '-t', str(duration),
                '-c', 'copy',
                '-avoid_negative_ts', 'make_zero',
                '-y',  # Overwrite output file
                output_path
            ]
            
            # Exécuter ffmpeg
            result = subprocess.run(
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
                    f.write(f"file '{seg_path}'\n")
            
            # 3. Fusionner tous les segments
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
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
