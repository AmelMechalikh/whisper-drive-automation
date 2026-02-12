#!/usr/bin/env python3
"""
Test rapide pour vérifier que video_segment_extractor fonctionne sans erreur
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from video_segment_extractor import VideoSegmentExtractor
import logging

def test_init():
    """Test d'initialisation"""
    logger = logging.getLogger(__name__)
    extractor = VideoSegmentExtractor(logger)

    # Vérifier que add_subtitles est bien désactivé
    assert extractor.add_subtitles == False, "add_subtitles devrait être False"

    print("✅ Test init: OK")

def test_method_signatures():
    """Test que les méthodes ont les bonnes signatures"""
    logger = logging.getLogger(__name__)
    extractor = VideoSegmentExtractor(logger)

    # Vérifier la signature de _extract_and_merge_segments
    import inspect
    sig = inspect.signature(extractor._extract_and_merge_segments)
    params = list(sig.parameters.keys())

    print(f"Paramètres de _extract_and_merge_segments: {params}")

    # La fonction devrait avoir: self, input_path, output_path, segments, temp_dir
    # SANS subtitles_dir
    expected = ['input_path', 'output_path', 'segments', 'temp_dir']

    if 'subtitles_dir' in params:
        print("❌ ERREUR: subtitles_dir est encore dans la signature!")
        return False

    for param in expected:
        if param not in params:
            print(f"❌ ERREUR: {param} manquant dans la signature!")
            return False

    print("✅ Test signatures: OK")
    return True

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print("🧪 Tests rapides de video_segment_extractor")
    print("=" * 50)

    try:
        test_init()
        if test_method_signatures():
            print("\n✅ TOUS LES TESTS PASSENT")
            sys.exit(0)
        else:
            print("\n❌ CERTAINS TESTS ÉCHOUENT - CORRIGER AVANT DÉPLOIEMENT")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
