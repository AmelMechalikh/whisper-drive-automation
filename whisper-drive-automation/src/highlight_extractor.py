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
                # Trouver le contexte pour ce highlight
                context_before, context_after = "", ""
                for highlight_info in highlights:
                    if highlight_info['text'] == text:
                        context_before = highlight_info.get('context_before', '')
                        context_after = highlight_info.get('context_after', '')
                        break

                start_time, end_time = self._find_exact_timestamps(
                    text,
                    complete_data,
                    context_before=context_before,
                    context_after=context_after
                )
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
    
    def extract_highlights_from_inline_markers(
        self,
        document_id: str,
        credentials_path: str,
        complete_json_path: str,
        output_excel_path: str
    ) -> str:
        """
        Extrait les highlights depuis des balises inline (🎬 S1 🎬) dans le document
        Alternative à l'extraction par commentaires

        Args:
            document_id: ID du document Google Docs
            credentials_path: Chemin vers credentials.json
            complete_json_path: Chemin vers le fichier _complete_data.json
            output_excel_path: Chemin de sortie pour le fichier Excel

        Returns:
            Chemin du fichier Excel créé ou None
        """
        from inline_marker_extractor import InlineMarkerExtractor

        self.logger.info("🎬 Extraction via balises inline")

        # Charger les données complètes (segments avec word timestamps)
        with open(complete_json_path, 'r', encoding='utf-8') as f:
            complete_data = json.load(f)

        # Extraire les segments depuis le document
        marker_extractor = InlineMarkerExtractor(logger=self.logger)
        segments = marker_extractor.extract_segments_from_document(
            document_id,
            credentials_path
        )

        if not segments:
            self.logger.warning("Aucun segment trouvé dans le document")
            return None

        # Matcher avec le transcript
        matched_segments = marker_extractor.match_segments_with_transcript(
            segments,
            complete_data
        )

        if not matched_segments:
            self.logger.warning("Aucun segment matché avec le transcript")
            return None

        # Créer le DataFrame pour l'Excel
        # Grouper les segments par segment_id pour permettre la fusion
        from collections import defaultdict
        grouped_by_id = defaultdict(list)
        for seg in matched_segments:
            grouped_by_id[seg['segment_id']].append(seg)

        highlight_data = []
        segment_num = 1

        for segment_id in sorted(grouped_by_id.keys()):
            segments_in_group = grouped_by_id[segment_id]

            # Trier les segments du groupe par timestamp de début
            segments_in_group.sort(key=lambda x: x['start'])

            for idx, seg in enumerate(segments_in_group):
                highlight_data.append({
                    'Numéro': segment_num,  # Même numéro pour tous les segments du groupe
                    'Groupe': seg['segment_id'],
                    'Sous-segment': idx + 1 if len(segments_in_group) > 1 else None,
                    'Total sous-segments': len(segments_in_group) if len(segments_in_group) > 1 else None,
                    'Début (secondes)': seg['start'],
                    'Fin (secondes)': seg['end'],
                    'Début (HH:MM:SS)': self._seconds_to_timecode(seg['start']),
                    'Fin (HH:MM:SS)': self._seconds_to_timecode(seg['end']),
                    'Durée (secondes)': seg['duration'],
                    'À fusionner': 'Oui' if len(segments_in_group) > 1 else 'Non',
                    'Texte': seg['text'][:500]  # Limiter pour Excel
                })

            segment_num += 1

        # Générer l'Excel
        if highlight_data:
            df = pd.DataFrame(highlight_data)
            df.to_excel(output_excel_path, index=False, engine='openpyxl')
            self.logger.info(f"✅ Excel créé: {output_excel_path}")
            self.logger.info(f"   {len(highlight_data)} segment(s) extrait(s)")
            return output_excel_path
        else:
            return None

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

    def _get_document_full_text(self, drive_service, file_id: str) -> str:
        """
        Récupère le texte complet du document Google Docs

        Args:
            drive_service: Service Google Drive API
            file_id: ID du fichier Google Docs

        Returns:
            Texte complet du document en texte brut
        """
        try:
            # Exporter le document en texte brut
            content = drive_service.files().export(
                fileId=file_id,
                mimeType='text/plain'
            ).execute()

            return content.decode('utf-8')
        except Exception as e:
            self.logger.warning(f"Impossible de récupérer le document complet: {e}")
            return ""

    def _extract_context_from_document(self, full_text: str, highlight_text: str, context_words: int = 50) -> Tuple[str, str]:
        """
        Extrait le contexte (avant/après) d'un highlight dans le document complet

        Args:
            full_text: Texte complet du document
            highlight_text: Texte du highlight à chercher
            context_words: Nombre de mots de contexte à extraire avant/après

        Returns:
            (context_before, context_after) ou ("", "") si non trouvé
        """
        # Nettoyer le texte du highlight pour la recherche
        clean_highlight = self._clean_highlight_text(highlight_text)

        # Extraire juste les premiers 20 mots du highlight pour la recherche
        highlight_words = clean_highlight.split()[:20]
        search_text = ' '.join(highlight_words)

        # STRATÉGIE 1: Si le highlight contient un marqueur de paragraphe, l'utiliser pour trouver la bonne occurrence
        paragraph_marker = None
        import re
        marker_match = re.search(r'===\s*Paragraphe\s+(\d+)\s*===', highlight_text)
        if marker_match:
            paragraph_marker = marker_match.group(0)
            self.logger.debug(f"Marqueur de paragraphe trouvé: {paragraph_marker}")

        # Chercher toutes les occurrences du texte
        occurrences = []
        start_pos = 0
        while True:
            pos = full_text.find(search_text, start_pos)
            if pos == -1:
                break
            occurrences.append(pos)
            start_pos = pos + 1

        if not occurrences:
            self.logger.debug(f"Contexte non trouvé pour: {search_text[:100]}")
            return "", ""

        # Choisir la bonne occurrence
        chosen_pos = occurrences[0]  # Par défaut, la première

        if len(occurrences) > 1:
            self.logger.debug(f"Plusieurs occurrences trouvées ({len(occurrences)}), disambiguation...")

            if paragraph_marker and paragraph_marker in full_text:
                # Trouver l'occurrence la plus proche du marqueur de paragraphe
                marker_pos = full_text.find(paragraph_marker)
                if marker_pos != -1:
                    # Choisir l'occurrence avant le marqueur (car le texte est avant le marqueur)
                    for occ_pos in reversed(occurrences):
                        if occ_pos < marker_pos and marker_pos - occ_pos < 5000:  # Moins de 5000 chars
                            chosen_pos = occ_pos
                            self.logger.debug(f"Occurrence choisie via marqueur de paragraphe: pos {chosen_pos}")
                            break
            else:
                # Sinon, prendre la dernière occurrence (heuristique)
                chosen_pos = occurrences[-1]
                self.logger.debug(f"Pas de marqueur, utilisation de la dernière occurrence: pos {chosen_pos}")

        # Extraire le contexte avant
        text_before = full_text[:chosen_pos]
        words_before = text_before.split()
        context_before = ' '.join(words_before[-context_words:]) if len(words_before) > context_words else text_before

        # Extraire le contexte après
        text_after = full_text[chosen_pos + len(search_text):]
        words_after = text_after.split()
        context_after = ' '.join(words_after[:context_words]) if len(words_after) > context_words else text_after

        return context_before.strip(), context_after.strip()

    def _extract_comments_from_drive(self, drive_service, file_id: str) -> List[Dict]:
        """
        Extrait les commentaires Google Docs avec contexte

        Args:
            drive_service: Service Google Drive API
            file_id: ID du fichier Google Docs

        Returns:
            Liste de dict avec 'text', 'comment', 'context_before', 'context_after'
        """
        highlights = []

        try:
            # Récupérer le document complet pour le contexte
            full_text = self._get_document_full_text(drive_service, file_id)

            # Récupérer les commentaires du fichier
            comments_response = drive_service.comments().list(
                fileId=file_id,
                fields='comments(id,content,quotedFileContent,anchor,resolved)',
                includeDeleted=False
            ).execute()

            all_comments = comments_response.get('comments', [])

            # Filtrer pour ne garder que les commentaires NON RÉSOLUS
            comments = [c for c in all_comments if not c.get('resolved', False)]

            if not all_comments:
                self.logger.info("Aucun commentaire trouvé")
                return []

            self.logger.info(f"📝 {len(all_comments)} commentaire(s) trouvé(s) au total")
            self.logger.info(f"   → {len(comments)} commentaire(s) non résolu(s)")

            if len(all_comments) > len(comments):
                resolved_count = len(all_comments) - len(comments)
                self.logger.info(f"   ⏭️  {resolved_count} commentaire(s) résolu(s) ignoré(s)")

            if not comments:
                self.logger.warning("Aucun commentaire non résolu trouvé")
                return []

            # Pour chaque commentaire, extraire le texte annoté + contexte
            for comment in comments:
                # Le texte sélectionné/annoté est dans quotedFileContent
                quoted_text = comment.get('quotedFileContent', {}).get('value', '')
                comment_text = comment.get('content', '')

                if quoted_text:
                    # Décoder les entités HTML (&#39; → ', &#233; → é, etc.)
                    decoded_text = html.unescape(quoted_text.strip())
                    decoded_comment = html.unescape(comment_text.strip())

                    # Extraire le contexte si le document complet est disponible
                    context_before, context_after = "", ""
                    if full_text:
                        context_before, context_after = self._extract_context_from_document(
                            full_text,
                            decoded_text,
                            context_words=50
                        )

                    highlights.append({
                        'text': decoded_text,
                        'comment': decoded_comment,
                        'context_before': context_before,
                        'context_after': context_after
                    })
                    self.logger.info(f"  - Trouvé highlight: {quoted_text[:50]}...")
                    if context_before or context_after:
                        self.logger.debug(f"    Contexte: ...{context_before[-30:]} [{quoted_text[:20]}...] {context_after[:30]}...")

        except Exception as e:
            self.logger.error(f"Erreur extraction commentaires: {e}")
            return []

        return highlights
    
    def _disambiguate_with_context(
        self,
        start_candidates: List[Dict],
        segments: List[Dict],
        context_before: str,
        context_after: str,
        normalize_func
    ) -> Tuple[Optional[float], Optional[int]]:
        """
        Utilise le contexte pour choisir le bon candidat parmi plusieurs occurrences

        Args:
            start_candidates: Liste des candidats avec 'time', 'segment_idx', 'segment_text'
            segments: Tous les segments du transcript
            context_before: Contexte avant le highlight dans Google Docs
            context_after: Contexte après le highlight dans Google Docs
            normalize_func: Fonction de normalisation du texte

        Returns:
            (start_time, segment_idx) du meilleur candidat ou (None, None)
        """
        if not context_before and not context_after:
            self.logger.debug("Pas de contexte disponible pour disambiguation")
            return None, None

        best_candidate = None
        best_score = -1

        for candidate in start_candidates:
            seg_idx = candidate['segment_idx']
            score = 0

            # Récupérer 3-5 segments avant et après pour le contexte
            context_range_before = segments[max(0, seg_idx - 5):seg_idx]
            context_range_after = segments[seg_idx + 1:min(len(segments), seg_idx + 6)]

            # Construire le contexte du transcript
            transcript_context_before = ' '.join([s.get('text', '') for s in context_range_before])
            transcript_context_after = ' '.join([s.get('text', '') for s in context_range_after])

            # Normaliser
            transcript_before_norm = normalize_func(transcript_context_before)
            transcript_after_norm = normalize_func(transcript_context_after)
            doc_before_norm = normalize_func(context_before)
            doc_after_norm = normalize_func(context_after)

            # Comparer le contexte avant (prendre les derniers mots pour comparaison)
            if doc_before_norm:
                doc_before_words = doc_before_norm.split()[-20:]  # 20 derniers mots
                overlap_before = sum(1 for word in doc_before_words if word in transcript_before_norm)
                score += overlap_before

            # Comparer le contexte après (prendre les premiers mots)
            if doc_after_norm:
                doc_after_words = doc_after_norm.split()[:20]  # 20 premiers mots
                overlap_after = sum(1 for word in doc_after_words if word in transcript_after_norm)
                score += overlap_after

            self.logger.debug(f"  Candidat à {candidate['time']:.2f}s: score={score}")

            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate and best_score > 5:  # Seuil minimum de confiance
            self.logger.info(f"✅ Candidat sélectionné à {best_candidate['time']:.2f}s (score={best_score})")
            return best_candidate['time'], best_candidate['segment_idx']

        return None, None

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

    def _flatten_words_from_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Crée une liste plate de tous les mots avec gestion des apostrophes

        Whisper tokenize "c'est" en ["c", "'est"], cette fonction les recolle

        Args:
            segments: Liste des segments avec words

        Returns:
            Liste de dicts: [{'word': 'cest', 'start': 849.22, 'end': 849.32, 'index': 0}, ...]
        """
        all_words = []
        global_index = 0

        for segment in segments:
            if 'words' not in segment:
                continue

            for word_info in segment['words']:
                word_text = word_info.get('word', '').strip()

                # Si le mot commence par une apostrophe et qu'il y a un mot précédent, le fusionner
                if (word_text.startswith("'") or word_text.startswith("'")) and all_words:
                    # Fusionner avec le mot précédent
                    prev_word = all_words[-1]
                    # Retirer toutes les apostrophes pour uniformiser
                    clean_text = word_text.replace("'", "").replace("'", "")
                    prev_word['word'] = prev_word['word'] + clean_text
                    prev_word['end'] = word_info.get('end', prev_word['end'])
                else:
                    # Nouveau mot - retirer les apostrophes pour uniformiser
                    clean_text = word_text.replace("'", "").replace("'", "").lower()
                    all_words.append({
                        'word': clean_text,
                        'start': word_info.get('start', 0),
                        'end': word_info.get('end', 0),
                        'index': global_index
                    })
                    global_index += 1

        return all_words

    def _find_word_sequence_candidates(
        self,
        all_words: List[Dict],
        search_words: List[str],
        min_score: float = 0.7
    ) -> List[Dict]:
        """
        Trouve tous les candidats où la séquence de mots apparaît

        Args:
            all_words: Liste plate de tous les mots avec timestamps
            search_words: Liste des mots à chercher (déjà normalisés)
            min_score: Score minimum pour considérer un candidat (0-1)

        Returns:
            Liste de candidats avec score: [{'index': 0, 'start': 849.22, 'score': 0.95, 'matched': 5}, ...]
        """
        candidates = []

        # Normaliser les mots de recherche
        def normalize_word(w):
            # Retirer ponctuation (y compris apostrophes)
            w = re.sub(r"[,\.!?;:\(\)''']", '', w)
            return w.lower().strip()

        search_normalized = [normalize_word(w) for w in search_words if normalize_word(w)]

        if not search_normalized:
            return []

        # Chercher chaque position où le premier mot apparaît
        first_word = search_normalized[0]

        for i, word_info in enumerate(all_words):
            word_norm = normalize_word(word_info['word'])

            # Si le premier mot matche, compter combien de mots consécutifs matchent
            if first_word == word_norm or first_word in word_norm or word_norm in first_word:
                matched_count = 1

                # Compter les mots suivants qui matchent
                for j in range(1, min(len(search_normalized), len(all_words) - i)):
                    next_word_norm = normalize_word(all_words[i + j]['word'])
                    search_word_norm = search_normalized[j]

                    if search_word_norm == next_word_norm or search_word_norm in next_word_norm or next_word_norm in search_word_norm:
                        matched_count += 1
                    else:
                        break

                # Calculer le score
                score = matched_count / len(search_normalized)

                if score >= min_score:
                    candidates.append({
                        'index': i,
                        'start': word_info['start'],
                        'end': all_words[min(i + matched_count - 1, len(all_words) - 1)]['end'],
                        'score': score,
                        'matched': matched_count
                    })

        return candidates

    def _find_exact_timestamps(
        self,
        highlight_text: str,
        complete_data: Dict,
        context_before: str = "",
        context_after: str = ""
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Trouve les timestamps exacts en utilisant UNIQUEMENT les word timestamps
        Approche basée sur séquence de mots avec scoring (pas de segments)

        Args:
            highlight_text: Texte du highlight (peut être tronqué)
            complete_data: Données JSON complètes avec segments et words
            context_before: Contexte avant le highlight (pour disambiguation)
            context_after: Contexte après le highlight (pour disambiguation)

        Returns:
            (start_time, end_time) en secondes
        """
        # Nettoyer le texte du highlight
        clean_text = self._clean_highlight_text(highlight_text)

        # Extraire les mots normalisés
        words = [w for w in clean_text.split() if w.strip()]
        if len(words) < 2:
            self.logger.warning(f"Pas assez de mots dans le highlight: {clean_text[:50]}")
            return None, None

        self.logger.debug(f"🔍 Recherche de {len(words)} mots: '{clean_text[:80]}...'")

        # ÉTAPE 1: Aplatir tous les mots de tous les segments
        segments = complete_data.get('segments', [])
        all_words = self._flatten_words_from_segments(segments)

        if not all_words:
            self.logger.warning("Aucun mot trouvé dans les segments")
            return None, None

        self.logger.debug(f"📋 {len(all_words)} mots au total dans le transcript")

        # ÉTAPE 2: Chercher le début avec les 6-8 premiers mots
        num_words_start = min(8, len(words))
        start_search_words = words[:num_words_start]

        start_candidates = self._find_word_sequence_candidates(
            all_words,
            start_search_words,
            min_score=0.7
        )

        if not start_candidates:
            self.logger.warning(f"❌ Aucun candidat de début trouvé pour: {clean_text[:80]}")
            return None, None

        self.logger.debug(f"🎯 {len(start_candidates)} candidat(s) de début trouvé(s)")

        # Choisir le meilleur candidat de début (score le plus proche de 1.0)
        best_start = max(start_candidates, key=lambda c: c['score'])
        start_time = best_start['start']
        start_index = best_start['index']

        self.logger.info(f"✅ Début: {start_time:.2f}s (score={best_start['score']:.2f}, {best_start['matched']}/{len(start_search_words)} mots)")

        # Si plusieurs candidats avec le même score, utiliser le contexte pour disambiguïser
        if len(start_candidates) > 1:
            top_score = best_start['score']
            top_candidates = [c for c in start_candidates if c['score'] == top_score]

            if len(top_candidates) > 1 and (context_before or context_after):
                self.logger.info(f"🔀 {len(top_candidates)} candidats avec score {top_score:.2f}, utilisation du contexte")

                # Convertir en format compatible avec _disambiguate_with_context
                candidate_dicts = []
                for c in top_candidates:
                    # Trouver le segment correspondant
                    seg_idx = 0
                    for i, seg in enumerate(segments):
                        if seg['start'] <= c['start'] <= seg.get('end', seg['start'] + 10):
                            seg_idx = i
                            break
                    candidate_dicts.append({
                        'time': c['start'],
                        'segment_idx': seg_idx,
                        'segment_text': segments[seg_idx].get('text', '') if seg_idx < len(segments) else ''
                    })

                def normalize_for_search(text):
                    text = re.sub(r'[,\.!?;:]', ' ', text)
                    return ' '.join(text.split()).lower().strip()

                disambiguated_time, _ = self._disambiguate_with_context(
                    candidate_dicts,
                    segments,
                    context_before,
                    context_after,
                    normalize_for_search
                )

                if disambiguated_time:
                    start_time = disambiguated_time
                    # Mettre à jour start_index
                    for c in start_candidates:
                        if c['start'] == start_time:
                            start_index = c['index']
                            break

        # ÉTAPE 3: Chercher la fin avec les 6 derniers mots
        num_words_end = min(6, len(words))
        end_search_words = words[-num_words_end:]

        # Chercher uniquement APRÈS le début
        words_after_start = all_words[start_index:]

        end_candidates = self._find_word_sequence_candidates(
            words_after_start,
            end_search_words,
            min_score=0.7
        )

        if not end_candidates:
            self.logger.warning(f"❌ Aucun candidat de fin trouvé")
            return None, None

        self.logger.debug(f"🎯 {len(end_candidates)} candidat(s) de fin trouvé(s)")

        # ÉTAPE 4: Choisir le meilleur candidat de fin en utilisant le ratio de couverture
        if len(end_candidates) == 1:
            end_time = end_candidates[0]['end']
            self.logger.info(f"✅ Fin: {end_time:.2f}s (score={end_candidates[0]['score']:.2f})")
        else:
            # Calculer le ratio de couverture pour chaque candidat
            self.logger.info(f"🔀 {len(end_candidates)} candidats de fin, calcul des ratios")

            best_candidate = None
            best_distance_from_1 = float('inf')

            for cand in end_candidates:
                # Compter les mots entre start et end
                end_index_abs = start_index + cand['index'] + cand['matched']
                words_in_range = all_words[start_index:end_index_abs]

                # Reconstruire le texte
                transcript_text = ' '.join([w['word'] for w in words_in_range])
                transcript_len = len(transcript_text)
                highlight_len = len(clean_text)

                coverage_ratio = transcript_len / highlight_len if highlight_len > 0 else 0

                self.logger.debug(f"  Candidat {cand['end']:.2f}s: ratio={coverage_ratio:.2f} (score={cand['score']:.2f})")

                # Le meilleur candidat est celui dont le ratio est le plus proche de 1.0
                if 0.7 <= coverage_ratio <= 1.5:
                    distance = abs(coverage_ratio - 1.0)
                    if distance < best_distance_from_1:
                        best_distance_from_1 = distance
                        best_candidate = cand

            if best_candidate:
                end_time = best_candidate['end']
                end_index_abs = start_index + best_candidate['index'] + best_candidate['matched']
                words_in_range = all_words[start_index:end_index_abs]
                transcript_len = len(' '.join([w['word'] for w in words_in_range]))
                final_ratio = transcript_len / len(clean_text) if len(clean_text) > 0 else 0

                self.logger.info(f"✅ Fin choisie: {end_time:.2f}s (ratio={final_ratio:.2f}, distance={best_distance_from_1:.2f})")
            else:
                # Fallback: prendre le premier candidat (le plus proche temporellement)
                end_time = end_candidates[0]['end']
                self.logger.warning(f"⚠️ Aucun candidat avec ratio 0.7-1.5, utilisation du premier: {end_time:.2f}s")

        # Ajouter une petite marge de sécurité à la fin
        end_time_with_margin = end_time + 0.4

        self.logger.info(f"🎬 Timestamps finaux: {start_time:.2f}s → {end_time_with_margin:.2f}s (marge +0.4s)")
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
