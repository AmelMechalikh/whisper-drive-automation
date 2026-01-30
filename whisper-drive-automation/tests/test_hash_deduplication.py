#!/usr/bin/env python3
"""
Tests unitaires pour le système de hash et déduplication d'Excel
"""
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys
from pathlib import Path
import tempfile
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestHashDeduplication(unittest.TestCase):
    """Tests pour vérifier le système de hash et régénération"""

    def setUp(self):
        """Setup pour chaque test"""
        # Import du module hash_utils (pas de dépendances Cloud)
        from hash_utils import calculate_segments_hash

        self.calculate_hash = calculate_segments_hash

        # Mock des dépendances
        self.mock_drive = Mock()
        self.mock_config = {
            'drive_folders': {
                'transcriptions': 'folder_transcriptions',
                'excel_output': 'folder_excel',
                'videos_source': 'folder_videos',
                'queue_highlights': 'folder_queue'
            }
        }

    def test_hash_calculation_same_segments(self):
        """Test 1: Même segments = même hash (déduplication)"""
        segments_v1 = [
            (202.56, 291.98)  # S2 seulement
        ]

        segments_v2 = [
            (202.56, 291.98)  # Toujours S2 seulement
        ]

        hash_v1 = self.calculate_hash(segments_v1)
        hash_v2 = self.calculate_hash(segments_v2)

        self.assertEqual(hash_v1, hash_v2, "Même segments doivent avoir le même hash")
        self.assertEqual(hash_v1, "28b64263", "Hash devrait être 28b64263 pour ces segments")

    def test_hash_calculation_different_segments(self):
        """Test 2: Segments différents = hash différent"""
        segments_v1 = [
            (202.56, 291.98)  # S2 seulement
        ]

        segments_v3 = [
            (31.60, 120.10),   # S1 ajouté
            (202.56, 291.98)   # S2
        ]

        hash_v1 = self.calculate_hash(segments_v1)
        hash_v3 = self.calculate_hash(segments_v3)

        self.assertNotEqual(hash_v1, hash_v3, "Segments différents doivent avoir des hash différents")
        self.assertEqual(hash_v1, "28b64263", "Hash V1 (S2 seulement)")
        self.assertEqual(hash_v3, "8c51d3e9", "Hash V3 (S1+S2)")

    def test_hash_order_matters(self):
        """Test 3: L'ordre des segments change le hash"""
        segments_normal = [(10.0, 20.0), (30.0, 40.0)]
        segments_reversed = [(30.0, 40.0), (10.0, 20.0)]

        hash_normal = self.calculate_hash(segments_normal)
        hash_reversed = self.calculate_hash(segments_reversed)

        self.assertNotEqual(hash_normal, hash_reversed, "L'ordre doit changer le hash")

    def test_hash_precision(self):
        """Test 4: Petites différences de timestamps = hash différent"""
        segments_v1 = [(202.56, 291.98)]
        segments_v2 = [(202.57, 291.98)]  # +0.01s sur le début

        hash_v1 = self.calculate_hash(segments_v1)
        hash_v2 = self.calculate_hash(segments_v2)

        self.assertNotEqual(hash_v1, hash_v2, "Même 0.01s de différence doit changer le hash")

    # NOTE: Tests 5 et 6 nécessitent trop de mocks (Drive, Docs API, etc.)
    # Ils sont mieux testés en intégration ou avec le script test_hash_regeneration.py

    def test_hash_length(self):
        """Test 7: Hash doit faire exactement 8 caractères"""
        segments = [(10.5, 20.3), (30.2, 45.7)]
        hash_result = self.calculate_hash(segments)

        self.assertEqual(len(hash_result), 8, "Hash doit faire 8 caractères")
        self.assertTrue(hash_result.isalnum(), "Hash doit être alphanumérique")
        # MD5 en hex utilise seulement 0-9 et a-f
        self.assertTrue(all(c in '0123456789abcdef' for c in hash_result), "Hash doit être en hex")


class TestExcelFilenameExtraction(unittest.TestCase):
    """Tests pour l'extraction de hash depuis les noms de fichiers"""

    def setUp(self):
        from hash_utils import extract_hash_from_filename
        self.extract_hash = extract_hash_from_filename

    def test_extract_hash_with_hash(self):
        """Test 8: Extraction de hash depuis nom avec hash"""
        filename = "test_amel_27_01_highlights_28b64263.xlsx"
        hash_result = self.extract_hash(filename)

        self.assertEqual(hash_result, "28b64263", "Doit extraire le hash correctement")

    def test_extract_hash_without_hash(self):
        """Test 9: Nom sans hash retourne None"""
        filename = "test_amel_27_01_highlights.xlsx"
        hash_result = self.extract_hash(filename)

        self.assertIsNone(hash_result, "Fichier sans hash doit retourner None")

    def test_extract_hash_invalid_format(self):
        """Test 10: Format invalide retourne None"""
        filename = "random_file.xlsx"
        hash_result = self.extract_hash(filename)

        self.assertIsNone(hash_result, "Format invalide doit retourner None")

    def test_extract_hash_wrong_length(self):
        """Test 11: Hash de mauvaise longueur (pas 8 chars)"""
        filename = "test_highlights_abc123.xlsx"  # 6 chars au lieu de 8
        hash_result = self.extract_hash(filename)

        self.assertIsNone(hash_result, "Hash de mauvaise longueur doit retourner None")


if __name__ == '__main__':
    # Créer le dossier tests s'il n'existe pas
    Path(__file__).parent.mkdir(exist_ok=True)

    # Lancer les tests avec verbose
    unittest.main(verbosity=2)
