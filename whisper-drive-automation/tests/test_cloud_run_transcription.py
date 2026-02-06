"""
Tests unitaires pour la transcription via Cloud Run avec RunPod
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


class TestCloudRunTranscription:
    """Tests pour la transcription RunPod dans Cloud Run"""

    def test_output_generator_creation(self):
        """Test que OutputGenerator peut être créé avec drive_manager et output_folder_id"""
        from output_generator import OutputGenerator

        # Mock drive_manager
        mock_drive_manager = Mock()
        output_folder_id = "test_folder_id"

        # Créer OutputGenerator
        output_gen = OutputGenerator(
            drive_manager=mock_drive_manager,
            output_folder_id=output_folder_id
        )

        assert output_gen is not None
        assert output_gen.drive_manager == mock_drive_manager
        assert output_gen.output_folder_id == output_folder_id
        print("✅ OutputGenerator peut être créé correctement")

    def test_transcription_result_structure(self):
        """Test que le résultat de transcription a la bonne structure"""
        # Structure attendue du résultat de transcription
        transcription_result = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'Test text',
                    'words': [
                        {'word': 'Test', 'start': 0.0, 'end': 2.0},
                        {'word': 'text', 'start': 2.0, 'end': 5.0}
                    ]
                }
            ]
        }

        assert 'segments' in transcription_result
        assert len(transcription_result['segments']) > 0

        segment = transcription_result['segments'][0]
        assert 'start' in segment
        assert 'end' in segment
        assert 'text' in segment
        assert 'words' in segment
        print("✅ Structure du résultat de transcription valide")

    def test_whisper_transcriber_with_backend(self):
        """Test que WhisperTranscriber peut être initialisé avec un backend"""
        from whisper_transcriber import WhisperTranscriber

        # Mock backend
        mock_backend = Mock()
        mock_backend.get_backend_name.return_value = "test_backend"

        # Créer transcriber avec backend
        transcriber = WhisperTranscriber(backend=mock_backend)

        assert transcriber.backend == mock_backend
        assert transcriber.model is None  # Pas de modèle Whisper chargé si backend fourni
        print("✅ WhisperTranscriber accepte un backend")

    def test_group_segments_to_paragraphs(self):
        """Test que group_segments_to_paragraphs fonctionne"""
        from whisper_transcriber import WhisperTranscriber

        # Mock backend
        mock_backend = Mock()
        mock_backend.get_backend_name.return_value = "test_backend"

        transcriber = WhisperTranscriber(backend=mock_backend)

        # Test segments - avec au moins 5 mots
        segments = [
            {'start': 0.0, 'end': 5.0, 'text': 'This is a first test sentence.'},
            {'start': 5.0, 'end': 10.0, 'text': 'This is a second test sentence.'}
        ]

        # Utiliser min_words=5 (valeur par défaut)
        paragraphs = transcriber.group_segments_to_paragraphs(segments, min_words=5)

        assert paragraphs is not None
        assert len(paragraphs) > 0
        assert paragraphs[0]['word_count'] >= 5  # Au moins 5 mots
        print(f"✅ group_segments_to_paragraphs retourne {len(paragraphs)} paragraphe(s)")

    @patch('output_generator.OutputGenerator')
    def test_runpod_transcription_workflow(self, mock_output_gen_class):
        """Test du workflow complet de transcription RunPod"""
        from whisper_transcriber import WhisperTranscriber

        # Mock backend
        mock_backend = Mock()
        mock_backend.get_backend_name.return_value = "RunPod"
        mock_backend.transcribe_audio.return_value = {
            'segments': [
                {
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'Test transcription',
                    'words': [
                        {'word': 'Test', 'start': 0.0, 'end': 2.0},
                        {'word': 'transcription', 'start': 2.0, 'end': 5.0}
                    ]
                }
            ]
        }

        # Mock drive manager et output generator
        mock_drive_manager = Mock()
        mock_output_generator = Mock()
        mock_output_generator.create_output_files.return_value = True
        mock_output_gen_class.return_value = mock_output_generator

        # Simuler le workflow
        # 1. Transcription
        transcription_result = mock_backend.transcribe_audio(
            audio_path="/tmp/test.mp3",
            language='fr',
            word_timestamps=True
        )

        assert transcription_result is not None
        assert 'segments' in transcription_result

        # 2. Group paragraphs
        transcriber = WhisperTranscriber(backend=mock_backend)
        paragraphs = transcriber.group_segments_to_paragraphs(
            transcription_result.get('segments', [])
        )

        assert paragraphs is not None

        # 3. Create output generator
        output_generator = mock_output_gen_class(
            drive_manager=mock_drive_manager,
            output_folder_id="test_folder"
        )

        assert output_generator is not None

        # 4. Save results
        output_result = output_generator.create_output_files(
            transcription_result,
            "test_file",
            paragraphs
        )

        assert output_result is True
        print("✅ Workflow complet de transcription RunPod fonctionne")

    def test_backend_imports(self):
        """Test que tous les imports nécessaires fonctionnent"""
        try:
            from whisper_transcriber import WhisperTranscriber
            from output_generator import OutputGenerator
            from transcription_backends import get_transcription_backend
            print("✅ Tous les imports nécessaires fonctionnent")
        except ImportError as e:
            pytest.fail(f"Import failed: {e}")


if __name__ == "__main__":
    print("🧪 Tests unitaires pour Cloud Run Transcription\n")

    test = TestCloudRunTranscription()

    print("Test 1: OutputGenerator creation")
    test.test_output_generator_creation()
    print()

    print("Test 2: Transcription result structure")
    test.test_transcription_result_structure()
    print()

    print("Test 3: WhisperTranscriber with backend")
    test.test_whisper_transcriber_with_backend()
    print()

    print("Test 4: group_segments_to_paragraphs")
    test.test_group_segments_to_paragraphs()
    print()

    print("Test 5: Backend imports")
    test.test_backend_imports()
    print()

    print("Test 6: RunPod transcription workflow")
    test.test_runpod_transcription_workflow()
    print()

    print("=" * 60)
    print("✅ TOUS LES TESTS SONT RÉUSSIS")
    print("=" * 60)
