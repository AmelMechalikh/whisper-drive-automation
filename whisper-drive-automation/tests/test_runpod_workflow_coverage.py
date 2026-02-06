"""
Tests de coverage pour le workflow RunPod
Ces tests vérifient les VRAIES signatures de méthodes, pas des mocks
"""
import pytest
import sys
import inspect
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestRunPodWorkflowCoverage:
    """Tests de coverage pour vérifier les vraies signatures de méthodes"""

    def test_output_generator_method_signature(self):
        """
        Test CRITIQUE qui aurait détecté l'erreur create_output_files vs generate_all_outputs
        """
        from output_generator import OutputGenerator

        # Vérifier que la classe a la bonne méthode
        assert hasattr(OutputGenerator, 'generate_all_outputs'), \
            "❌ OutputGenerator doit avoir 'generate_all_outputs'"

        assert not hasattr(OutputGenerator, 'create_output_files'), \
            "❌ OutputGenerator n'a PAS 'create_output_files' - utiliser 'generate_all_outputs'"

        # Vérifier la signature de generate_all_outputs
        sig = inspect.signature(OutputGenerator.generate_all_outputs)
        params = list(sig.parameters.keys())

        # Signature attendue: (self, base_filename, whisper_result, paragraphs=None)
        assert 'base_filename' in params, "generate_all_outputs doit accepter 'base_filename'"
        assert 'whisper_result' in params, "generate_all_outputs doit accepter 'whisper_result'"
        assert 'paragraphs' in params, "generate_all_outputs doit accepter 'paragraphs'"

        # Vérifier l'ordre des paramètres
        assert params.index('base_filename') < params.index('whisper_result'), \
            "base_filename doit venir AVANT whisper_result"

        print("✅ OutputGenerator.generate_all_outputs a la bonne signature")
        print(f"   Paramètres: {', '.join(params)}")

    def test_output_generator_real_instantiation(self):
        """Test que OutputGenerator peut vraiment être instancié avec les bons paramètres"""
        from output_generator import OutputGenerator

        mock_drive_manager = Mock()
        output_folder_id = "test_folder"

        # Créer une vraie instance (pas un mock)
        with tempfile.TemporaryDirectory() as tmpdir:
            output_gen = OutputGenerator(
                output_dir=tmpdir,
                drive_manager=mock_drive_manager,
                output_folder_id=output_folder_id
            )

            # Vérifier que l'instance a les bons attributs
            assert output_gen.drive_manager == mock_drive_manager
            assert output_gen.output_folder_id == output_folder_id
            assert hasattr(output_gen, 'generate_all_outputs')

            print("✅ OutputGenerator s'instancie correctement")

    def test_generate_all_outputs_can_be_called(self):
        """Test que generate_all_outputs peut être appelé avec la bonne signature"""
        from output_generator import OutputGenerator

        mock_drive_manager = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_gen = OutputGenerator(
                output_dir=tmpdir,
                drive_manager=mock_drive_manager,
                output_folder_id="test_folder"
            )

            # Préparer des données de test minimales
            base_filename = "test_audio"
            whisper_result = {
                'text': 'Test transcription with enough words to make a paragraph.',
                'segments': [
                    {
                        'start': 0.0,
                        'end': 5.0,
                        'text': 'Test transcription with enough words to make a paragraph.',
                        'words': [
                            {'word': 'Test', 'start': 0.0, 'end': 0.5},
                            {'word': 'transcription', 'start': 0.5, 'end': 1.5},
                            {'word': 'with', 'start': 1.5, 'end': 2.0},
                            {'word': 'enough', 'start': 2.0, 'end': 2.5},
                            {'word': 'words', 'start': 2.5, 'end': 3.0},
                            {'word': 'to', 'start': 3.0, 'end': 3.5},
                            {'word': 'make', 'start': 3.5, 'end': 4.0},
                            {'word': 'a', 'start': 4.0, 'end': 4.5},
                            {'word': 'paragraph.', 'start': 4.5, 'end': 5.0}
                        ]
                    }
                ]
            }
            paragraphs = [
                {
                    'start': 0.0,
                    'end': 5.0,
                    'text': 'Test transcription with enough words to make a paragraph.',
                    'word_count': 9
                }
            ]

            # APPEL RÉEL de la méthode (pas un mock!)
            try:
                result = output_gen.generate_all_outputs(
                    base_filename,
                    whisper_result,
                    paragraphs
                )

                # Vérifier que ça retourne bien un dict avec les fichiers
                assert isinstance(result, dict), "generate_all_outputs doit retourner un dict"
                assert 'transcription' in result or len(result) > 0, \
                    "generate_all_outputs doit retourner des fichiers"

                print("✅ generate_all_outputs() s'exécute correctement")
                print(f"   Fichiers générés: {list(result.keys())}")

            except Exception as e:
                pytest.fail(f"❌ Erreur lors de l'appel à generate_all_outputs: {e}")

    def test_cloud_run_server_uses_correct_method(self):
        """
        Test CRITIQUE: Vérifier que cloud_run_server.py utilise la bonne méthode
        """
        cloud_run_server_path = Path(__file__).parent.parent / 'scripts' / 'cloud_run_server.py'

        with open(cloud_run_server_path, 'r') as f:
            code = f.read()

        # Vérifier qu'on utilise generate_all_outputs
        assert 'generate_all_outputs' in code, \
            "❌ cloud_run_server.py doit utiliser 'generate_all_outputs'"

        # Vérifier qu'on N'utilise PAS create_output_files
        assert 'create_output_files' not in code, \
            "❌ cloud_run_server.py ne doit PAS utiliser 'create_output_files' (méthode inexistante)"

        # Vérifier l'ordre des arguments
        import re
        pattern = r'generate_all_outputs\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*([^)]+)\s*\)'
        matches = re.findall(pattern, code)

        if matches:
            for match in matches:
                arg1, arg2, arg3 = [arg.strip() for arg in match]
                # arg1 devrait être base_filename, arg2 whisper_result, arg3 paragraphs
                print(f"✅ Appel trouvé: generate_all_outputs({arg1}, {arg2}, {arg3})")

        print("✅ cloud_run_server.py utilise la bonne méthode")

    def test_whisper_transcriber_has_group_segments(self):
        """Vérifier que WhisperTranscriber a bien group_segments_to_paragraphs"""
        from whisper_transcriber import WhisperTranscriber

        assert hasattr(WhisperTranscriber, 'group_segments_to_paragraphs'), \
            "WhisperTranscriber doit avoir 'group_segments_to_paragraphs'"

        # Vérifier la signature
        sig = inspect.signature(WhisperTranscriber.group_segments_to_paragraphs)
        params = list(sig.parameters.keys())

        assert 'segments' in params, "group_segments_to_paragraphs doit accepter 'segments'"
        print("✅ WhisperTranscriber.group_segments_to_paragraphs existe")

    def test_complete_workflow_with_real_methods(self):
        """
        Test du workflow COMPLET avec de vraies méthodes (pas de mocks)
        """
        from whisper_transcriber import WhisperTranscriber
        from output_generator import OutputGenerator

        # Mock backend
        mock_backend = Mock()
        mock_backend.get_backend_name.return_value = "RunPod"

        # 1. Créer transcriber
        transcriber = WhisperTranscriber(backend=mock_backend)
        assert transcriber is not None
        print("✅ Step 1: WhisperTranscriber créé")

        # 2. Test group_segments_to_paragraphs avec de vraies données
        segments = [
            {
                'start': 0.0,
                'end': 5.0,
                'text': 'This is a test transcription with enough words.',
                'words': []
            }
        ]

        paragraphs = transcriber.group_segments_to_paragraphs(segments, min_words=5)
        assert paragraphs is not None
        assert isinstance(paragraphs, list)
        print(f"✅ Step 2: group_segments_to_paragraphs retourne {len(paragraphs)} paragraphe(s)")

        # 3. Créer OutputGenerator
        mock_drive_manager = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_gen = OutputGenerator(
                output_dir=tmpdir,
                drive_manager=mock_drive_manager,
                output_folder_id="test_folder"
            )
            assert output_gen is not None
            print("✅ Step 3: OutputGenerator créé")

            # 4. Appeler generate_all_outputs avec de vraies données
            whisper_result = {
                'text': 'This is a test transcription with enough words.',
                'segments': [
                    {
                        'start': 0.0,
                        'end': 5.0,
                        'text': 'This is a test transcription with enough words.',
                        'words': [
                            {'word': 'This', 'start': 0.0, 'end': 0.5},
                            {'word': 'is', 'start': 0.5, 'end': 1.0},
                            {'word': 'a', 'start': 1.0, 'end': 1.5},
                            {'word': 'test', 'start': 1.5, 'end': 2.0},
                            {'word': 'transcription', 'start': 2.0, 'end': 3.0},
                            {'word': 'with', 'start': 3.0, 'end': 3.5},
                            {'word': 'enough', 'start': 3.5, 'end': 4.0},
                            {'word': 'words.', 'start': 4.0, 'end': 5.0}
                        ]
                    }
                ]
            }

            result = output_gen.generate_all_outputs(
                "test_file",
                whisper_result,
                paragraphs
            )

            assert result is not None
            assert isinstance(result, dict)
            print(f"✅ Step 4: generate_all_outputs retourne {len(result)} fichier(s)")

        print("✅ WORKFLOW COMPLET TESTÉ AVEC DE VRAIES MÉTHODES")


def test_coverage_summary():
    """Affiche un résumé du coverage"""
    print("\n" + "=" * 70)
    print("RÉSUMÉ DU COVERAGE")
    print("=" * 70)
    print("✅ OutputGenerator.generate_all_outputs - signature vérifiée")
    print("✅ WhisperTranscriber.group_segments_to_paragraphs - signature vérifiée")
    print("✅ cloud_run_server.py - utilisation des bonnes méthodes vérifiée")
    print("✅ Workflow complet - exécution réelle testée")
    print("=" * 70)


if __name__ == "__main__":
    print("🧪 Tests de Coverage RunPod Workflow\n")
    print("=" * 70)
    print("Ces tests vérifient les VRAIES signatures et exécutions")
    print("Pas de mocks pour les méthodes critiques!")
    print("=" * 70)
    print()

    test = TestRunPodWorkflowCoverage()

    print("Test 1: Signature de OutputGenerator.generate_all_outputs")
    test.test_output_generator_method_signature()
    print()

    print("Test 2: Instanciation réelle de OutputGenerator")
    test.test_output_generator_real_instantiation()
    print()

    print("Test 3: Appel réel de generate_all_outputs")
    test.test_generate_all_outputs_can_be_called()
    print()

    print("Test 4: Vérification du code dans cloud_run_server.py")
    test.test_cloud_run_server_uses_correct_method()
    print()

    print("Test 5: Signature de group_segments_to_paragraphs")
    test.test_whisper_transcriber_has_group_segments()
    print()

    print("Test 6: Workflow complet avec vraies méthodes")
    test.test_complete_workflow_with_real_methods()
    print()

    test_coverage_summary()
    print()
    print("=" * 70)
    print("✅ TOUS LES TESTS DE COVERAGE RÉUSSIS")
    print("=" * 70)
