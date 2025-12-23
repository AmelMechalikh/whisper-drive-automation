#!/usr/bin/env python3
"""
Extracteur de highlights depuis les fichiers annotés
Génère un fichier Excel avec les timestamps de début/fin
"""

import re
import json
import logging
import html
from pathlib import Path
from datetime import timedelta
import pandas as pd
from typing import List, Dict, Tuple, Optional


class HighlightExtractor:
    """Extrait les highlights et génère un Excel avec timestamps"""
    
    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)
    
    def extract_highlights_from_drive_file(
        self, 
        drive_service,
        paragraph_file_id: str,
        complete_json_path: str,
        output_excel_path: str
    ) -> str:
        """
        Extrait les highlights d'un fichier Google Docs annoté avec commentaires
        
        Args:
            drive_service: Service Google Drive API
            paragraph_file_id: ID du fichier Google Docs avec commentaires
            complete_json_path: Chemin vers le fichier _complete_data.json
            output_excel_path: Chemin de sortie pour le fichier Excel
            
        Returns:
            Chemin du fichier Excel créé
        """
        # Charger les données complètes (segments avec word timestamps)
        with open(complete_json_path, 'r', encoding='utf-8') as f:
            complete_data = json.load(f)
        
        # Extraire les commentaires Google Docs
        highlights = self._extract_comments_from_drive(drive_service, paragraph_file_id)
        
        if not highlights:
            self.logger.warning("Aucun commentaire trouvé dans le fichier")
            return None
        
        # Pour chaque highlight, trouver les timestamps précis
        highlight_data = []
        
        # Grouper les highlights par commentaire identique
        grouped_highlights = {}
        for highlight_info in highlights:
            comment = highlight_info.get('comment', '').strip()
            if not comment:
                comment = f"Sans commentaire {len(grouped_highlights) + 1}"
            
            if comment not in grouped_highlights:
                grouped_highlights[comment] = []
            grouped_highlights[comment].append(highlight_info['text'])
        
        # Pour chaque groupe de highlights
        segment_num = 1
        for comment, texts in grouped_highlights.items():
            # Trouver les timestamps pour chaque texte du groupe
            segments_info = []
            for text in texts:
                start_time, end_time = self._find_exact_timestamps(text, complete_data)
                if start_time is not None and end_time is not None:
                    # Nettoyer le texte avant de le stocker
                    clean_text = self._clean_highlight_text(text)
                    segments_info.append({
                        'start': start_time,
                        'end': end_time,
                        'text': clean_text
                    })
            
            if not segments_info:
                continue
            
            # Trier par timestamp de début
            segments_info.sort(key=lambda x: x['start'])
            
            # Créer une entrée par segment (pour le découpage vidéo)
            for i, seg in enumerate(segments_info):
                highlight_data.append({
                    'Numéro': segment_num,
                    'Groupe': comment,  # Le commentaire identifie le groupe
                    'Sous-segment': i + 1 if len(segments_info) > 1 else None,
                    'Total sous-segments': len(segments_info) if len(segments_info) > 1 else None,
                    'Début (secondes)': seg['start'],
                    'Fin (secondes)': seg['end'],
                    'Début (HH:MM:SS)': self._seconds_to_timecode(seg['start']),
                    'Fin (HH:MM:SS)': self._seconds_to_timecode(seg['end']),
                    'Durée (secondes)': round(seg['end'] - seg['start'], 2),
                    'À fusionner': 'Oui' if len(segments_info) > 1 else 'Non',
                    'Texte': seg['text']  # Texte complet sans troncature
                })
            
            segment_num += 1
        
        # Créer le DataFrame et exporter vers Excel
        df = pd.DataFrame(highlight_data)
        df.to_excel(output_excel_path, index=False, engine='openpyxl')
        
        self.logger.info(f"✅ Excel créé avec {len(highlight_data)} highlights: {output_excel_path}")
        return output_excel_path
    
    def _clean_highlight_text(self, text: str) -> str:
        """
        Nettoie le texte d'un highlight en retirant les marqueurs de formatage

        Args:
            text: Texte brut du highlight

        Returns:
            Texte nettoyé sans les marqueurs
        """
        clean_text = text
        # Retirer les marqueurs de l'ancien format
        clean_text = re.sub(r'===\s*Paragraphe\s+\d+\s*===', '', clean_text)
        clean_text = re.sub(r'Temps:\s*\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}', '', clean_text)
        clean_text = re.sub(r'Mots:\s*\d+', '', clean_text)
        clean_text = re.sub(r'Texte:\s*', '', clean_text)
        # Retirer les timestamps inline du nouveau format
        clean_text = re.sub(r'\(\d+:\d+\)', '', clean_text)
        # Normaliser les espaces et sauts de ligne
        clean_text = ' '.join(clean_text.split())
        return clean_text.strip()

    def _extract_comments_from_drive(self, drive_service, file_id: str) -> List[Dict]:
        """
        Extrait les commentaires Google Docs et le texte qu'ils annotent
        
        Args:
            drive_service: Service Google Drive API
            file_id: ID du fichier Google Docs
            
        Returns:
            Liste de dict avec 'text' et 'comment' pour chaque highlight
        """
        highlights = []
        
        try:
            # Récupérer les commentaires du fichier
            comments_response = drive_service.comments().list(
                fileId=file_id,
                fields='comments(id,content,quotedFileContent,anchor)',
                includeDeleted=False
            ).execute()
            
            comments = comments_response.get('comments', [])
            
            if not comments:
                self.logger.info("Aucun commentaire trouvé")
                return []
            
            self.logger.info(f"📝 {len(comments)} commentaire(s) trouvé(s)")
            
            # Pour chaque commentaire, extraire le texte annoté
            for comment in comments:
                # Le texte sélectionné/annoté est dans quotedFileContent
                quoted_text = comment.get('quotedFileContent', {}).get('value', '')
                comment_text = comment.get('content', '')
                
                if quoted_text:
                    # Décoder les entités HTML (&#39; → ', &#233; → é, etc.)
                    decoded_text = html.unescape(quoted_text.strip())
                    decoded_comment = html.unescape(comment_text.strip())
                    
                    highlights.append({
                        'text': decoded_text,
                        'comment': decoded_comment
                    })
                    self.logger.info(f"  - Trouvé highlight: {quoted_text[:50]}...")
            
        except Exception as e:
            self.logger.error(f"Erreur extraction commentaires: {e}")
            return []
        
        return highlights
    
    def _extract_highlighted_sections(self, content: str) -> List[str]:
        """
        Extrait les sections entre marqueurs de commentaires
        Supporte plusieurs formats: [HIGHLIGHT], <!-- HIGHLIGHT -->, etc.
        """
        highlights = []
        
        # Pattern pour détecter les sections highlightées
        # Format attendu : du texte entre marqueurs (commentaires Google Docs, brackets, etc.)
        patterns = [
            r'\[HIGHLIGHT\](.*?)\[/HIGHLIGHT\]',  # [HIGHLIGHT]...[/HIGHLIGHT]
            r'<!--\s*HIGHLIGHT\s*-->(.*?)<!--\s*/HIGHLIGHT\s*-->',  # <!-- HIGHLIGHT -->...<!-- /HIGHLIGHT -->
            r'===\s*HIGHLIGHT\s*===(.*?)===\s*/HIGHLIGHT\s*===',  # === HIGHLIGHT ===...=== /HIGHLIGHT ===
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                highlight_text = match.group(1).strip()
                if highlight_text:
                    highlights.append(highlight_text)
        
        return highlights
    
    def _find_exact_timestamps(
        self, 
        highlight_text: str, 
        complete_data: Dict
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Trouve les timestamps exacts en utilisant les word timestamps
        
        Args:
            highlight_text: Texte du highlight (peut être tronqué)
            complete_data: Données JSON complètes avec segments et words
            
        Returns:
            (start_time, end_time) en secondes
        """
        # Fonction helper pour normaliser le texte (retirer ponctuation pour comparaison)
        def normalize_for_search(text):
            """Retire la ponctuation lourde et normalise les espaces"""
            text = re.sub(r'[,\.!?;:]', ' ', text)
            text = ' '.join(text.split())  # Normaliser les espaces multiples
            return text.lower().strip()
        
        # Nettoyer le texte du highlight en utilisant la méthode dédiée
        clean_text = self._clean_highlight_text(highlight_text)
        clean_text_normalized = normalize_for_search(clean_text)
        
        # Extraire les mots (garder les apostrophes pour matcher "qu'on", "l'attachement", etc.)
        words = [w for w in clean_text_normalized.split() if w.strip()]
        if len(words) < 2:
            self.logger.warning(f"Pas assez de mots dans le highlight: {clean_text[:50]}")
            return None, None
        
        # Utiliser les premiers mots pour la recherche
        # Chercher avec les 4 premiers mots complets (ignorer le 5ème qui peut être tronqué)
        num_words_search = min(4, len(words))
        first_words = ' '.join(words[:num_words_search])
        
        # Pour la fin, utiliser seulement le dernier mot (peut être tronqué, et peut être sur un segment différent)
        last_word = words[-1] if words else None

        self.logger.debug(f"Recherche début: '{first_words[:50]}...'")
        self.logger.debug(f"Recherche fin: dernier mot '{last_word}'")

        # Chercher dans les segments avec word timestamps
        start_time = None
        end_time = None
        start_segment_idx = None

        self.logger.debug(f"🔍 Recherche de '{first_words}' → dernier mot '{last_word}'")
        
        segments = complete_data.get('segments', [])
        MAX_SEGMENT_DISTANCE = 30  # Limiter la recherche aux 30 segments suivant le début

        for seg_idx, segment in enumerate(segments):
            segment_text_normalized = normalize_for_search(segment.get('text', ''))

            # Chercher le début
            if start_time is None and first_words in segment_text_normalized:
                # Utiliser word timestamps si disponibles
                if 'words' in segment and segment['words']:
                    for word_info in segment['words']:
                        word_normalized = normalize_for_search(word_info['word'])
                        # Chercher le premier mot du highlight
                        if words[0] in word_normalized:
                            start_time = word_info['start']
                            start_segment_idx = seg_idx
                            break
                if start_time is None:
                    start_time = segment['start']
                    start_segment_idx = seg_idx

            # Chercher la fin dans les segments PROCHES du début (limité à MAX_SEGMENT_DISTANCE)
            if start_time is not None and start_segment_idx is not None and last_word:
                # Vérifier qu'on est dans la fenêtre de recherche
                if seg_idx >= start_segment_idx and seg_idx <= start_segment_idx + MAX_SEGMENT_DISTANCE:
                    if 'words' in segment and segment['words']:
                        for word_info in segment['words']:
                            word_normalized = normalize_for_search(word_info['word'])
                            # Match partiel pour gérer les mots tronqués
                            if last_word in word_normalized or word_normalized.startswith(last_word):
                                # S'assurer que c'est après le début
                                if word_info['end'] >= start_time:
                                    end_time = word_info['end']
                                    # On continue pour trouver la DERNIÈRE occurrence dans la fenêtre
        
        if start_time is None or end_time is None:
            self.logger.warning(f"Timestamps non trouvés pour: {clean_text[:80]}")
            return None, None
        
        # Ajouter une petite marge de sécurité à la fin pour finir le mot/la phrase
        # 0.4 secondes permettent de capturer la fin complète du dernier mot
        end_time_with_margin = end_time + 0.4
        
        self.logger.info(f"✅ Timestamps trouvés: {start_time:.2f}s → {end_time_with_margin:.2f}s (marge +0.4s) pour '{clean_text[:50]}...'")
        return start_time, end_time_with_margin
    
    def _seconds_to_timecode(self, seconds: float) -> str:
        """Convertit secondes en HH:MM:SS"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        secs = int(td.total_seconds() % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    """Test local"""
    logging.basicConfig(level=logging.INFO)
    
    extractor = HighlightExtractor()
    
    # Exemple d'utilisation
    paragraph_file = "path/to/file_paragraphs_timestamps.txt"
    json_file = "path/to/file_complete_data.json"
    output_excel = "path/to/output_highlights.xlsx"
    
    extractor.extract_highlights_from_paragraph_file(
        paragraph_file,
        json_file,
        output_excel
    )


if __name__ == '__main__':
    main()
