#!/usr/bin/env python3
"""
Affiche tous les segments avec leurs timestamps
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
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def show_all_segments():
    """Affiche tous les segments avec leurs timestamps"""

    # Charger les données JSON
    json_path = Path.home() / 'Downloads' / 'Séance 3 jour 1 _complete_data.json'

    if not json_path.exists():
        logger.error(f"❌ Fichier non trouvé: {json_path}")
        return False

    with open(json_path, 'r', encoding='utf-8') as f:
        complete_data = json.load(f)

    # L'ID du document Google Docs (à extraire de l'URL ou du fichier de config)
    # Pour ce test, on va chercher les segments directement dans le document
    # Si tu as l'ID du doc, je peux extraire les segments marqués

    # Pour l'instant, affichons les segments qu'on connaît du test précédent
    # Tu peux me donner l'ID du document Google Docs pour extraire tous les segments automatiquement

    extractor = InlineMarkerExtractor(logger=logger)

    # Segments de test (basés sur les tests précédents)
    test_segments = [
        {
            'segment_id': 'S1',
            'text': "c'est comment créer un esprit beaucoup plus détendu"
        }
    ]

    logger.info("=" * 80)
    logger.info("📊 EXTRACTION DES TIMESTAMPS POUR TOUS LES SEGMENTS")
    logger.info("=" * 80)
    logger.info("")

    matched_segments = extractor.match_segments_with_transcript(
        test_segments,
        complete_data
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("📋 RÉSUMÉ DES SEGMENTS")
    logger.info("=" * 80)
    logger.info("")

    for seg in matched_segments:
        logger.info(f"🎬 {seg['segment_id']}")
        logger.info(f"   Start: {seg['start']:.2f}s ({_format_time(seg['start'])})")
        logger.info(f"   End:   {seg['end']:.2f}s ({_format_time(seg['end'])})")
        logger.info(f"   Durée: {seg['duration']:.2f}s")
        logger.info(f"   Texte: {seg['text'][:80]}...")
        logger.info("")

    return True

def _format_time(seconds):
    """Convertit secondes en MM:SS format"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

if __name__ == '__main__':
    print("\n🎬 Extraction des timestamps de tous les segments\n")

    # Pour extraire TOUS les segments du document Google Docs, j'ai besoin de:
    # 1. L'ID du document (dans l'URL: https://docs.google.com/document/d/DOCUMENT_ID/edit)
    # 2. Le chemin vers credentials.json

    print("⚠️  Pour extraire tous les segments du document Google Docs:")
    print("    Je peux mettre à jour ce script avec l'ID du document")
    print("    Ou tu peux me dire quels segments tu veux tester")
    print("")

    show_all_segments()
