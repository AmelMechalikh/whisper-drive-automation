#!/usr/bin/env python3
"""
Test script pour valider le nouveau système de timestamps basé sur mots
"""
import json
import logging
import sys
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from highlight_extractor import HighlightExtractor

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_seance3():
    """Test avec Séance 3 jour 1 - cas problématique du 2ème S1"""

    # Charger les données JSON
    json_path = Path.home() / 'Downloads' / 'Séance 3 jour 1 _complete_data.json'

    if not json_path.exists():
        logger.error(f"❌ Fichier non trouvé: {json_path}")
        return False

    with open(json_path, 'r', encoding='utf-8') as f:
        complete_data = json.load(f)

    # Créer l'extracteur
    extractor = HighlightExtractor(logger=logger)

    # Test 1: Le texte problématique qui devrait commencer à 849.22s (pas 847.36s)
    # "c'est comment créer un esprit beaucoup plus détendu"
    highlight_text = "c'est comment créer un esprit beaucoup plus détendu"

    logger.info("=" * 80)
    logger.info("TEST 1: Segment S1 problématique")
    logger.info("=" * 80)
    logger.info(f"Highlight: '{highlight_text}'")
    logger.info("Attendu: start_time ≈ 849.22s (pas 847.36s)")

    start_time, end_time = extractor._find_exact_timestamps(
        highlight_text,
        complete_data,
        context_before="",
        context_after=""
    )

    logger.info("")
    logger.info(f"🎬 Résultat: start={start_time:.2f}s, end={end_time:.2f}s")

    # Vérifier que le start_time est correct
    # Devrait être autour de 849.22s, pas 847.36s
    if start_time:
        if 849.0 <= start_time <= 850.0:
            logger.info("✅ TEST RÉUSSI: Le timestamp commence bien au bon mot!")
            return True
        elif 847.0 <= start_time <= 848.0:
            logger.error("❌ TEST ÉCHOUÉ: Le timestamp commence au segment (847.36s) au lieu du mot (849.22s)")
            return False
        else:
            logger.warning(f"⚠️  TEST INCERTAIN: Timestamp inattendu {start_time:.2f}s")
            return False
    else:
        logger.error("❌ TEST ÉCHOUÉ: Aucun timestamp trouvé")
        return False

if __name__ == '__main__':
    print("\n🧪 Test du nouveau système de timestamps basé sur mots\n")

    success = test_seance3()

    print("\n" + "=" * 80)
    if success:
        print("✅ TOUS LES TESTS SONT RÉUSSIS")
        sys.exit(0)
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        sys.exit(1)
