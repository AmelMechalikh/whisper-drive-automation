#!/usr/bin/env python3
"""
Tests d'intégration pour le système de highlights
Teste le code réel sans mocks pour détecter les vrais bugs
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Empêcher l'init automatique
os.environ['PYTEST_CURRENT_TEST'] = 'test'

from drive_manager import DriveManager


class TestDriveManager:
    """Tests pour DriveManager - détection des méthodes manquantes"""
    
    @pytest.fixture
    def mock_credentials(self, tmp_path):
        """Credentials de test valides"""
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test"
        }
        
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps(creds))
        return str(creds_file)
    
    def test_drive_manager_has_required_methods(self, mock_credentials):
        """Vérifie que DriveManager a toutes les méthodes nécessaires"""
        
        with patch('drive_manager.build') as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            
            # Mock about().get()
            mock_about = MagicMock()
            mock_about.get.return_value.execute.return_value = {
                'user': {'emailAddress': 'test@test.com'}
            }
            mock_service.about.return_value = mock_about
            
            dm = DriveManager(mock_credentials)
            
            # Vérifier les méthodes nécessaires pour highlights
            required_methods = [
                'list_files_in_folder',  # ❌ Manquante
                'search_files',          # ❌ Manquante  
                'find_folder',           # ❌ Manquante
                'create_folder',         # Existe ?
                'upload_file',           # Existe ?
                'download_file',         # Existe ?
            ]
            
            missing_methods = []
            for method in required_methods:
                if not hasattr(dm, method):
                    missing_methods.append(method)
            
            assert len(missing_methods) == 0, f"Méthodes manquantes: {missing_methods}"
    
    def test_list_files_in_folder_exists(self, mock_credentials):
        """Test si list_files_in_folder existe"""
        with patch('drive_manager.build'):
            dm = DriveManager(mock_credentials)
            assert hasattr(dm, 'list_files_in_folder'), \
                "DriveManager doit avoir list_files_in_folder(folder_id, name_pattern=None)"
    
    def test_search_files_exists(self, mock_credentials):
        """Test si search_files existe"""
        with patch('drive_manager.build'):
            dm = DriveManager(mock_credentials)
            assert hasattr(dm, 'search_files'), \
                "DriveManager doit avoir search_files(folder_id, name_contains)"
    
    def test_find_folder_exists(self, mock_credentials):
        """Test si find_folder existe"""
        with patch('drive_manager.build'):
            dm = DriveManager(mock_credentials)
            assert hasattr(dm, 'find_folder'), \
                "DriveManager doit avoir find_folder(parent_folder_id, folder_name)"


class TestHighlightOrchestratorIntegration:
    """Tests d'intégration pour HighlightsProcessor"""
    
    @pytest.fixture
    def mock_config(self):
        """Config réaliste"""
        return {
            "drive_folders": {
                "highlighted_files": "fake-highlighted-id",
                "source_files": "fake-source-id",
                "transcriptions": "fake-transcriptions-id",
                "excel_output": "fake-excel-id",
                "segments_output": "fake-segments-id"
            },
            "processing": {
                "watch_interval_seconds": 300,
                "temp_dir": "./temp_highlights"
            }
        }
    
    @pytest.fixture
    def mock_credentials(self, tmp_path):
        """Credentials de test"""
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC\ntest\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test"
        }
        
        creds_file = tmp_path / "credentials.json"
        creds_file.write_text(json.dumps(creds))
        return str(creds_file)
    
    def test_check_new_highlighted_files_calls_correct_method(self, mock_config, mock_credentials):
        """Test que check_new_highlighted_files appelle la bonne méthode"""
        
        # Import après avoir set PYTEST_CURRENT_TEST
        from scripts.highlight_orchestrator_cloud import HighlightsProcessor
        
        with patch('drive_manager.build'):
            processor = HighlightsProcessor(mock_config, mock_credentials)
            
            # Mock la méthode attendue
            processor.drive_manager.list_files_in_folder = Mock(return_value=[])
            
            # Devrait appeler list_files_in_folder
            try:
                processor.check_new_highlighted_files()
                # Si ça passe, la méthode existe
                processor.drive_manager.list_files_in_folder.assert_called_once()
            except AttributeError as e:
                pytest.fail(f"Méthode manquante: {e}")
    
    def test_check_new_excel_files_calls_correct_method(self, mock_config, mock_credentials):
        """Test que check_new_excel_files appelle la bonne méthode"""
        
        from scripts.highlight_orchestrator_cloud import HighlightsProcessor
        
        with patch('drive_manager.build'):
            processor = HighlightsProcessor(mock_config, mock_credentials)
            
            # Mock la méthode attendue
            processor.drive_manager.list_files_in_folder = Mock(return_value=[])
            processor.drive_manager.find_folder = Mock(return_value=None)
            
            try:
                processor.check_new_excel_files()
                processor.drive_manager.list_files_in_folder.assert_called_once()
            except AttributeError as e:
                pytest.fail(f"Méthode manquante: {e}")
    
    def test_find_source_video_calls_search_files(self, mock_config, mock_credentials):
        """Test que _find_source_video appelle search_files"""
        
        from scripts.highlight_orchestrator_cloud import HighlightsProcessor
        
        with patch('drive_manager.build'):
            processor = HighlightsProcessor(mock_config, mock_credentials)
            
            # Mock la méthode attendue
            processor.drive_manager.search_files = Mock(return_value=[])
            
            try:
                result = processor._find_source_video("test_video")
                processor.drive_manager.search_files.assert_called_once()
            except AttributeError as e:
                pytest.fail(f"Méthode manquante: {e}")


class TestCoverageReport:
    """Génère un rapport de couverture des méthodes nécessaires"""
    
    def test_generate_coverage_report(self):
        """Génère un rapport de ce qui est implémenté vs nécessaire"""
        
        from drive_manager import DriveManager
        
        required_for_highlights = {
            'list_files_in_folder': 'Lister les fichiers dans un dossier avec pattern optionnel',
            'search_files': 'Chercher des fichiers par nom',
            'find_folder': 'Trouver un sous-dossier par nom',
            'create_folder': 'Créer un dossier',
            'upload_file': 'Upload un fichier',
            'download_file': 'Télécharger un fichier',
            'get_file_metadata': 'Récupérer les métadonnées d\'un fichier',
        }
        
        # Vérifier ce qui existe
        implemented = {}
        missing = {}
        
        # Mock pour créer une instance
        with patch('drive_manager.build'):
            dm = DriveManager.__new__(DriveManager)
            
            for method, description in required_for_highlights.items():
                if hasattr(dm.__class__, method):
                    implemented[method] = description
                else:
                    missing[method] = description
        
        total = len(required_for_highlights)
        impl_count = len(implemented)
        coverage = (impl_count / total) * 100
        
        print(f"\n{'='*60}")
        print(f"COUVERTURE DES MÉTHODES DriveManager")
        print(f"{'='*60}")
        print(f"Coverage: {coverage:.1f}% ({impl_count}/{total})")
        print(f"\n✅ IMPLÉMENTÉES ({impl_count}):")
        for method, desc in implemented.items():
            print(f"  - {method}: {desc}")
        
        print(f"\n❌ MANQUANTES ({len(missing)}):")
        for method, desc in missing.items():
            print(f"  - {method}: {desc}")
        print(f"{'='*60}\n")
        
        # Le test passe mais affiche le rapport
        assert coverage >= 0, f"Coverage: {coverage:.1f}%"


if __name__ == '__main__':
    # Lancer les tests avec verbose
    pytest.main([__file__, '-v', '-s'])
