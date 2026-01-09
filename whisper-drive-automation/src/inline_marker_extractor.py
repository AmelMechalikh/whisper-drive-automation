#!/usr/bin/env python3
"""
Extracteur de segments basé sur des balises inline dans le texte
Alternative à l'extraction par commentaires
"""

import re
import json
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build


class InlineMarkerExtractor:
    """Extrait les segments marqués par des balises 🎬 dans le texte"""

    # Format des balises : 🎬 S1 🎬 ... texte ... 🎬 /S1 🎬
    MARKER_START_PATTERN = r'🎬\s*([A-Z]\d+)\s*🎬'
    MARKER_END_PATTERN = r'🎬\s*/([A-Z]\d+)\s*🎬'

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(__name__)

    def extract_segments_from_document(
        self,
        document_id: str,
        credentials_path: str
    ) -> List[Dict]:
        """
        Extrait les segments marqués depuis un Google Doc

        Args:
            document_id: ID du document Google Docs
            credentials_path: Chemin vers credentials.json

        Returns:
            Liste de dict avec 'segment_id', 'text', 'start_pos', 'end_pos'
        """
        # Initialiser l'API Docs
        creds = Credentials.from_service_account_file(
            credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/drive.readonly',
                'https://www.googleapis.com/auth/documents.readonly'
            ]
        )

        docs_service = build('docs', 'v1', credentials=creds)

        # Récupérer le document
        try:
            document = docs_service.documents().get(documentId=document_id).execute()
        except Exception as e:
            self.logger.error(f"Erreur récupération document: {e}")
            return []

        # Extraire le texte complet
        full_text = self._extract_full_text(document)

        if not full_text:
            self.logger.warning("Document vide ou impossible à lire")
            return []

        self.logger.info(f"📄 Document récupéré: {len(full_text)} caractères")

        # Parser les segments
        segments = self._parse_segments(full_text)

        self.logger.info(f"✅ {len(segments)} segment(s) trouvé(s)")

        return segments

    def _extract_full_text(self, document: Dict) -> str:
        """
        Extrait le texte complet d'un document Google Docs

        Args:
            document: Document récupéré via l'API Docs

        Returns:
            Texte complet du document
        """
        body = document.get('body', {})
        content = body.get('content', [])

        text_parts = []

        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                elements = paragraph.get('elements', [])

                for elem in elements:
                    if 'textRun' in elem:
                        text = elem['textRun'].get('content', '')
                        text_parts.append(text)

        return ''.join(text_parts)

    def _parse_segments(self, text: str) -> List[Dict]:
        """
        Parse le texte pour trouver les segments marqués

        Args:
            text: Texte complet du document

        Returns:
            Liste de segments avec leur ID et contenu
        """
        segments = []

        # Trouver toutes les balises de début
        start_matches = list(re.finditer(self.MARKER_START_PATTERN, text))

        for start_match in start_matches:
            segment_id = start_match.group(1)  # Ex: S1, S2, etc.
            start_pos = start_match.end()  # Position après la balise de début

            # Chercher la balise de fin correspondante
            end_pattern = r'🎬\s*/' + re.escape(segment_id) + r'\s*🎬'
            end_match = re.search(end_pattern, text[start_pos:])

            if end_match:
                end_pos = start_pos + end_match.start()
                segment_text = text[start_pos:end_pos].strip()

                # Nettoyer le texte (retirer timestamps au format (XX:XX))
                clean_text = self._clean_text(segment_text)

                segments.append({
                    'segment_id': segment_id,
                    'text': clean_text,
                    'raw_text': segment_text,
                    'start_pos': start_match.start(),
                    'end_pos': start_pos + end_match.end()
                })

                self.logger.debug(f"Segment {segment_id}: {len(clean_text)} caractères")
            else:
                self.logger.warning(f"⚠️  Balise de fin manquante pour {segment_id}")

        return segments

    def _clean_text(self, text: str) -> str:
        """
        Nettoie le texte du segment

        Args:
            text: Texte brut du segment

        Returns:
            Texte nettoyé
        """
        # Retirer les timestamps au format (XX:XX) ou (X:XX:XX)
        text = re.sub(r'\(\d{1,2}:\d{2}(?::\d{2})?\)', '', text)

        # Normaliser les espaces
        text = ' '.join(text.split())

        return text.strip()

    def match_segments_with_transcript(
        self,
        segments: List[Dict],
        complete_data: Dict
    ) -> List[Dict]:
        """
        Matche les segments avec le transcript pour trouver les timestamps

        Args:
            segments: Liste des segments extraits du document
            complete_data: Données JSON du transcript (_complete_data.json)

        Returns:
            Liste de segments avec timestamps ajoutés
        """
        from highlight_extractor import HighlightExtractor

        extractor = HighlightExtractor(logger=self.logger)

        matched_segments = []

        for segment in segments:
            segment_id = segment['segment_id']
            text = segment['text']

            self.logger.info(f"🔍 Recherche timestamps pour {segment_id}...")

            # Utiliser la méthode existante pour trouver les timestamps
            start_time, end_time = extractor._find_exact_timestamps(
                text,
                complete_data,
                context_before="",
                context_after=""
            )

            if start_time is not None and end_time is not None:
                matched_segments.append({
                    'segment_id': segment_id,
                    'text': text,
                    'start': start_time,
                    'end': end_time,
                    'duration': round(end_time - start_time, 2)
                })

                self.logger.info(f"  ✅ {segment_id}: {start_time:.2f}s → {end_time:.2f}s")
            else:
                self.logger.warning(f"  ❌ {segment_id}: Timestamps non trouvés")

        return matched_segments
