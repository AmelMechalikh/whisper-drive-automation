#!/usr/bin/env python3
"""
Teste si S5 est détecté dans le document
"""
import sys
from pathlib import Path
import logging

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from inline_marker_extractor import InlineMarkerExtractor

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    # ID du document (depuis cleanup_and_reset.py)
    doc_id = "1xuSLj112Oz99P6l9JmoGeYLsPM7czQnoB0l6_vRGI1w"

    print("=" * 80)
    print("🔍 DÉTECTION DES SEGMENTS DANS LE DOCUMENT")
    print("=" * 80)
    print("")

    extractor = InlineMarkerExtractor(logger=logger)

    # Extraire les segments
    segments = extractor.extract_segments_from_document(
        document_id=doc_id,
        credentials_path='./config/credentials.json'
    )

    print("")
    print("=" * 80)
    print("📋 SEGMENTS DÉTECTÉS")
    print("=" * 80)
    print("")

    if not segments:
        print("❌ Aucun segment détecté")
        return

    # Afficher tous les segments
    for seg in segments:
        print(f"✅ {seg['segment_id']}: {seg['text'][:80]}...")

    print("")
    print(f"Total: {len(segments)} segment(s)")
    print("")

    # Vérifier spécifiquement S5
    s5_segments = [s for s in segments if s['segment_id'] == 'S5']

    if s5_segments:
        print("🎉 S5 EST DÉTECTÉ!")
        print("")
        for s5 in s5_segments:
            print(f"S5 - Texte: {s5['text'][:150]}...")
    else:
        print("❌ S5 N'EST PAS DÉTECTÉ")
        print("")
        print("Segments détectés:", [s['segment_id'] for s in segments])

if __name__ == '__main__':
    main()
