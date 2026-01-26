#!/usr/bin/env python3
"""
Test de la logique de hash pour éviter les doublons
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

# Import des fonctions
from highlight_orchestrator_cloud import calculate_segments_hash, extract_hash_from_filename

def test_calculate_hash():
    """Test du calcul de hash"""
    print("🧪 Test: calculate_segments_hash()")

    # Test avec tuples
    segments1 = [(10.5, 20.3), (30.2, 45.7)]
    hash1 = calculate_segments_hash(segments1)
    print(f"  Segments: {segments1}")
    print(f"  Hash: {hash1}")
    assert len(hash1) == 8, "Hash devrait faire 8 caractères"
    assert hash1.isalnum(), "Hash devrait être alphanumérique"

    # Test avec dicts
    segments2 = [
        {'start': 10.5, 'end': 20.3},
        {'start': 30.2, 'end': 45.7}
    ]
    hash2 = calculate_segments_hash(segments2)
    print(f"  Segments (dict): {segments2}")
    print(f"  Hash: {hash2}")

    # Les deux devraient donner le même hash
    assert hash1 == hash2, "Hash devrait être identique pour mêmes timestamps"
    print(f"  ✅ Hash identique: {hash1} == {hash2}")

    # Test avec timestamps différents
    segments3 = [(10.5, 20.3), (30.2, 46.0)]  # Fin différente
    hash3 = calculate_segments_hash(segments3)
    print(f"  Segments modifiés: {segments3}")
    print(f"  Hash: {hash3}")
    assert hash3 != hash1, "Hash devrait être différent pour timestamps différents"
    print(f"  ✅ Hash différent: {hash3} != {hash1}")

    print("✅ Test calculate_segments_hash: OK\n")


def test_extract_hash():
    """Test de l'extraction de hash du nom de fichier"""
    print("🧪 Test: extract_hash_from_filename()")

    # Avec hash
    filename1 = "GSE_du_8_janvier_highlights_abc123de.xlsx"
    hash1 = extract_hash_from_filename(filename1)
    print(f"  Fichier: {filename1}")
    print(f"  Hash extrait: {hash1}")
    assert hash1 == "abc123de", f"Hash devrait être 'abc123de', obtenu '{hash1}'"
    print(f"  ✅ Hash extrait correctement")

    # Sans hash (ancien format)
    filename2 = "GSE_du_8_janvier_highlights.xlsx"
    hash2 = extract_hash_from_filename(filename2)
    print(f"  Fichier: {filename2}")
    print(f"  Hash extrait: {hash2}")
    assert hash2 is None, f"Hash devrait être None, obtenu '{hash2}'"
    print(f"  ✅ Ancien format détecté (pas de hash)")

    # Nom complexe avec hash
    filename3 = "Sagesse Bouddhiste 20 janvier_highlights_def456gh.xlsx"
    hash3 = extract_hash_from_filename(filename3)
    print(f"  Fichier: {filename3}")
    print(f"  Hash extrait: {hash3}")
    assert hash3 == "def456gh", f"Hash devrait être 'def456gh', obtenu '{hash3}'"
    print(f"  ✅ Hash extrait correctement")

    print("✅ Test extract_hash_from_filename: OK\n")


def test_hash_consistency():
    """Test de consistance: même contenu = même hash"""
    print("🧪 Test: Consistance du hash")

    segments = [(10.5, 20.3), (30.2, 45.7), (50.1, 60.9)]

    # Calculer 10 fois
    hashes = [calculate_segments_hash(segments) for _ in range(10)]

    # Tous devraient être identiques
    unique_hashes = set(hashes)
    print(f"  Segments: {segments}")
    print(f"  10 calculs: {len(unique_hashes)} hash(es) unique(s)")
    assert len(unique_hashes) == 1, "Tous les hashs devraient être identiques"
    print(f"  Hash: {hashes[0]}")
    print(f"  ✅ Hash consistant sur 10 calculs")

    print("✅ Test consistance: OK\n")


if __name__ == '__main__':
    print("=" * 60)
    print("Tests de la logique de hash")
    print("=" * 60)
    print()

    try:
        test_calculate_hash()
        test_extract_hash()
        test_hash_consistency()

        print("=" * 60)
        print("✅ TOUS LES TESTS PASSENT")
        print("=" * 60)
        sys.exit(0)

    except AssertionError as e:
        print(f"\n❌ ÉCHEC: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
