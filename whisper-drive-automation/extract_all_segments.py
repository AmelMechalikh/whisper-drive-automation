#!/usr/bin/env python3
"""
Extrait tous les segments d'un document Google Docs avec inline markers
et affiche leurs timestamps
"""
import json
import logging
import sys
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from inline_marker_extractor import InlineMarkerExtractor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_all_segments(document_id: str, complete_data_path: str, credentials_path: str = None):
    """
    Extrait tous les segments et affiche leurs timestamps

    Args:
        document_id: ID du document Google Docs (depuis l'URL)
        complete_data_path: Chemin vers le fichier _complete_data.json
        credentials_path: Chemin vers credentials.json (optionnel si sur VM/Cloud Run)
    """

    # Charger les données de transcription
    with open(complete_data_path, 'r', encoding='utf-8') as f:
        complete_data = json.load(f)

    # Créer l'extracteur
    extractor = InlineMarkerExtractor(logger=logger)

    print("=" * 80)
    print("📄 EXTRACTION DES SEGMENTS DEPUIS GOOGLE DOCS")
    print("=" * 80)
    print(f"Document ID: {document_id}")
    print(f"Transcription: {complete_data_path}")
    print("")

    # Extraire les segments depuis le document
    segments = extractor.extract_segments_from_document(
        document_id=document_id,
        credentials_path=credentials_path
    )

    if not segments:
        print("❌ Aucun segment trouvé dans le document")
        return

    print(f"✅ {len(segments)} segment(s) trouvé(s) dans le document")
    print("")

    # Matcher avec les timestamps
    print("=" * 80)
    print("🔍 RECHERCHE DES TIMESTAMPS")
    print("=" * 80)
    print("")

    matched_segments = extractor.match_segments_with_transcript(
        segments,
        complete_data
    )

    # Afficher les résultats
    print("")
    print("=" * 80)
    print("📋 RÉSUMÉ DE TOUS LES SEGMENTS")
    print("=" * 80)
    print("")

    if not matched_segments:
        print("❌ Aucun segment n'a pu être matché avec le transcript")
        return

    for seg in matched_segments:
        print(f"🎬 {seg['segment_id']}")
        print(f"   Start:  {seg['start']:.2f}s  ({_format_time(seg['start'])})")
        print(f"   End:    {seg['end']:.2f}s  ({_format_time(seg['end'])})")
        print(f"   Durée:  {seg['duration']:.2f}s")
        print(f"   Texte:  {seg['text'][:100]}...")
        print("")

    # Résumé statistiques
    print("=" * 80)
    print("📊 STATISTIQUES")
    print("=" * 80)
    total_duration = sum(s['duration'] for s in matched_segments)
    print(f"Nombre de segments: {len(matched_segments)}")
    print(f"Durée totale: {total_duration:.2f}s ({_format_time(total_duration)})")
    print(f"Durée moyenne: {total_duration/len(matched_segments):.2f}s")
    print("")

def _format_time(seconds):
    """Convertit secondes en HH:MM:SS format"""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Extrait tous les segments avec timestamps')
    parser.add_argument('--doc-id', required=True, help='ID du document Google Docs')
    parser.add_argument('--complete-data', required=True, help='Chemin vers _complete_data.json')
    parser.add_argument('--credentials', default='./config/credentials.json', help='Chemin vers credentials.json')

    args = parser.parse_args()

    print("\n🎬 Extraction de tous les segments\n")

    extract_all_segments(
        document_id=args.doc_id,
        complete_data_path=args.complete_data,
        credentials_path=args.credentials
    )
