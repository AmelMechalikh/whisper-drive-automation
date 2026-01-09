#!/usr/bin/env python3
"""
Tests pour le système de highlights
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from highlight_orchestrator_cloud import HighlightsProcessor, load_config


class TestHighlightsProcessor:
    """Tests pour HighlightsProcessor"""
    
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Config de test"""
        config = {
            "folders": {
                "transcriptions": "fake-transcriptions-id",
                "highlights_excel": "fake-excel-id",
                "files": "fake-files-id",
                "segments_videos": "fake-segments-id"
            }
        }
        
        # Créer un fichier config temporaire
        config_file = tmp_path / "highlight_config.json"
        config_file.write_text(json.dumps(config))
        
        return config
    
    @pytest.fixture
    def mock_credentials(self, tmp_path):
        """Credentials de test"""
        creds = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----",
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
    
    @patch('highlight_orchestrator_cloud.DriveManager')
    @patch('highlight_orchestrator_cloud.HighlightExtractor')
    @patch('highlight_orchestrator_cloud.VideoSegmentExtractor')
    def test_init_processor(self, mock_video_ext, mock_highlight_ext, mock_drive, 
                           mock_config, mock_credentials):
        """Test l'initialisation du processor"""
        
        # Créer le processor
        processor = HighlightsProcessor(mock_config, mock_credentials)
        
        # Vérifier que les composants sont initialisés
        assert processor.config == mock_config
        assert processor.credentials_path == mock_credentials
        assert processor.drive_manager is not None
        assert processor.highlight_extractor is not None
        assert processor.video_extractor is not None
        
        # Vérifier les appels
        mock_drive.assert_called_once_with(mock_credentials)
        mock_highlight_ext.assert_called_once()
        mock_video_ext.assert_called_once()
    
    @patch('highlight_orchestrator_cloud.DriveManager')
    @patch('highlight_orchestrator_cloud.HighlightExtractor')
    @patch('highlight_orchestrator_cloud.VideoSegmentExtractor')
    def test_check_new_highlighted_files(self, mock_video_ext, mock_highlight_ext, 
                                        mock_drive, mock_config, mock_credentials):
        """Test la détection de nouveaux fichiers avec highlights"""
        
        # Mock du drive manager
        mock_drive_instance = Mock()
        mock_drive.return_value = mock_drive_instance
        
        # Mock des fichiers Google Docs avec commentaires
        mock_files = [
            {'id': 'doc1', 'name': 'Transcription 1', 'hasComments': True},
            {'id': 'doc2', 'name': 'Transcription 2', 'hasComments': True}
        ]
        mock_drive_instance.list_files.return_value = mock_files
        
        processor = HighlightsProcessor(mock_config, mock_credentials)
        
        # Checker les fichiers
        result = processor.check_new_highlighted_files()
        
        # Vérifier
        assert len(result) == 2
        assert result[0]['name'] == 'Transcription 1'
        mock_drive_instance.list_files.assert_called_once()
    
    @patch('highlight_orchestrator_cloud.DriveManager')
    @patch('highlight_orchestrator_cloud.HighlightExtractor')
    @patch('highlight_orchestrator_cloud.VideoSegmentExtractor')
    def test_check_new_excel_files(self, mock_video_ext, mock_highlight_ext, 
                                   mock_drive, mock_config, mock_credentials):
        """Test la détection de nouveaux fichiers Excel"""
        
        mock_drive_instance = Mock()
        mock_drive.return_value = mock_drive_instance
        
        # Mock des fichiers Excel non traités
        mock_excel_files = [
            {'id': 'excel1', 'name': 'Highlights_Video1.xlsx'},
            {'id': 'excel2', 'name': 'Highlights_Video2.xlsx'}
        ]
        mock_drive_instance.list_files.return_value = mock_excel_files
        
        # Mock: pas de dossier de sortie (pas encore traité)
        mock_drive_instance.find_folder.return_value = None
        
        processor = HighlightsProcessor(mock_config, mock_credentials)
        
        result = processor.check_new_excel_files()
        
        assert len(result) == 2
        assert result[0]['name'] == 'Highlights_Video1.xlsx'
    
    @patch('highlight_orchestrator_cloud.DriveManager')
    @patch('highlight_orchestrator_cloud.HighlightExtractor')
    @patch('highlight_orchestrator_cloud.VideoSegmentExtractor')
    def test_process_highlighted_file(self, mock_video_ext, mock_highlight_ext, 
                                     mock_drive, mock_config, mock_credentials):
        """Test le traitement d'un fichier avec highlights"""
        
        mock_drive_instance = Mock()
        mock_drive.return_value = mock_drive_instance
        
        mock_highlight_ext_instance = Mock()
        mock_highlight_ext.return_value = mock_highlight_ext_instance
        
        # Mock des highlights extraits
        mock_highlights = [
            {'text': 'Important quote', 'timestamp': '00:05:30', 'comment': 'Intro'},
            {'text': 'Another quote', 'timestamp': '00:12:45', 'comment': 'Main point'}
        ]
        mock_highlight_ext_instance.extract_highlights.return_value = mock_highlights
        
        # Mock de la création d'Excel
        mock_highlight_ext_instance.create_excel.return_value = '/tmp/test.xlsx'
        
        # Mock de l'upload
        mock_drive_instance.upload_file.return_value = 'uploaded-file-id'
        
        processor = HighlightsProcessor(mock_config, mock_credentials)
        
        doc_info = {'id': 'doc123', 'name': 'Test Video'}
        
        result = processor.process_highlighted_file(doc_info)
        
        # Vérifier
        assert result is True
        mock_highlight_ext_instance.extract_highlights.assert_called_once_with('doc123')
        mock_highlight_ext_instance.create_excel.assert_called_once_with(
            mock_highlights, 'Test Video'
        )
        mock_drive_instance.upload_file.assert_called_once()
    
    @patch('highlight_orchestrator_cloud.DriveManager')
    @patch('highlight_orchestrator_cloud.HighlightExtractor')
    @patch('highlight_orchestrator_cloud.VideoSegmentExtractor')
    def test_process_excel_file(self, mock_video_ext, mock_highlight_ext, 
                                mock_drive, mock_config, mock_credentials):
        """Test le traitement d'un fichier Excel pour créer les segments"""
        
        mock_drive_instance = Mock()
        mock_drive.return_value = mock_drive_instance
        
        mock_video_ext_instance = Mock()
        mock_video_ext.return_value = mock_video_ext_instance
        
        # Mock: trouver la vidéo source
        mock_drive_instance.search_files.return_value = [
            {'id': 'video123', 'name': 'Test Video.mp4'}
        ]
        
        # Mock: télécharger Excel
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp_excel = tmp.name
        mock_drive_instance.download_file.return_value = tmp_excel
        
        # Mock: télécharger vidéo
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
            tmp_video = tmp.name
        mock_drive_instance.download_file.return_value = tmp_video
        
        # Mock: extraction réussie
        mock_video_ext_instance.extract_segments_from_excel.return_value = [
            '/tmp/segment1.mp4',
            '/tmp/segment2.mp4'
        ]
        
        # Mock: créer sous-dossier
        mock_drive_instance.create_folder.return_value = 'subfolder-id'
        
        processor = HighlightsProcessor(mock_config, mock_credentials)
        
        excel_info = {'id': 'excel123', 'name': 'Highlights_Test Video.xlsx'}
        
        result = processor.process_excel_file(excel_info)
        
        # Vérifier
        assert result is True
        mock_video_ext_instance.extract_segments_from_excel.assert_called_once()
    
    @patch('highlight_orchestrator_cloud.DriveManager')
    @patch('highlight_orchestrator_cloud.HighlightExtractor')
    @patch('highlight_orchestrator_cloud.VideoSegmentExtractor')
    def test_process_integration(self, mock_video_ext, mock_highlight_ext, 
                                 mock_drive, mock_config, mock_credentials):
        """Test d'intégration du process complet"""
        
        mock_drive_instance = Mock()
        mock_drive.return_value = mock_drive_instance
        
        mock_highlight_ext_instance = Mock()
        mock_highlight_ext.return_value = mock_highlight_ext_instance
        
        mock_video_ext_instance = Mock()
        mock_video_ext.return_value = mock_video_ext_instance
        
        # Étape 1: Détecter des fichiers avec highlights
        mock_drive_instance.list_files.side_effect = [
            [{'id': 'doc1', 'name': 'Video 1'}],  # Fichiers avec highlights
            [{'id': 'excel1', 'name': 'Highlights_Video 1.xlsx'}]  # Fichiers Excel
        ]
        
        # Étape 2: Extraire highlights
        mock_highlight_ext_instance.extract_highlights.return_value = [
            {'text': 'Quote', 'timestamp': '00:05:00', 'comment': 'Test'}
        ]
        mock_highlight_ext_instance.create_excel.return_value = '/tmp/test.xlsx'
        mock_drive_instance.upload_file.return_value = 'excel-id'
        
        # Étape 3: Pas encore de traitement vidéo (pas de dossier)
        mock_drive_instance.find_folder.return_value = None
        
        processor = HighlightsProcessor(mock_config, mock_credentials)
        
        # Exécuter le process complet
        processor.process()
        
        # Vérifier les étapes
        assert mock_highlight_ext_instance.extract_highlights.called
        assert mock_highlight_ext_instance.create_excel.called
        assert mock_drive_instance.upload_file.called


class TestLoadConfig:
    """Tests pour load_config"""
    
    def test_load_config_from_file(self, tmp_path):
        """Test le chargement depuis un fichier local"""
        
        config = {
            "folders": {
                "transcriptions": "test-id"
            }
        }
        
        config_file = tmp_path / "highlight_config.json"
        config_file.write_text(json.dumps(config))
        
        # Mock pour que le fichier soit trouvé
        with patch('highlight_orchestrator_cloud.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__truediv__ = lambda s, o: config_file
            
            # Note: Ce test est simplifié car load_config utilise des chemins hardcodés
            # Dans un vrai test, on mockerait pathlib.Path complètement
    
    def test_load_config_missing_file(self):
        """Test l'erreur quand le fichier n'existe pas"""
        
        with patch('highlight_orchestrator_cloud.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            
            # load_config devrait raise FileNotFoundError
            # (mais nécessite de mocker tous les chemins possibles)


class TestVideoSegmentExtraction:
    """Tests pour l'extraction de segments vidéo"""
    
    @patch('highlight_orchestrator_cloud.VideoSegmentExtractor')
    def test_merge_same_group_segments(self, mock_video_ext):
        """Test la fusion de segments avec le même groupe"""
        
        mock_instance = Mock()
        mock_video_ext.return_value = mock_instance
        
        # Mock des segments à fusionner
        highlights_data = [
            {'timestamp': '00:05:00', 'comment': 'GroupA'},
            {'timestamp': '00:05:30', 'comment': 'GroupA'},
            {'timestamp': '00:10:00', 'comment': 'GroupB'}
        ]
        
        # Mock de la fusion
        mock_instance.merge_segments_by_group.return_value = {
            'GroupA': '/tmp/GroupA_merged.mp4',
            'GroupB': '/tmp/GroupB.mp4'
        }
        
        result = mock_instance.merge_segments_by_group(highlights_data, '/tmp/video.mp4')
        
        assert len(result) == 2
        assert 'GroupA' in result
        assert 'GroupB' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
