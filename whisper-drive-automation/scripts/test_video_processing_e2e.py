#!/usr/bin/env python3
"""
Script de test end-to-end pour le système de découpage vidéo
Teste l'extraction et la fusion de segments vidéo depuis un fichier Excel
"""

import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drive_manager import DriveManager
from video_segment_extractor import VideoSegmentExtractor


class VideoProcessingTester:
    """Testeur pour le système de découpage vidéo"""

    def __init__(self, credentials_path: str, config_path: str):
        self.logger = self._setup_logger()

        # Charger la configuration
        with open(config_path) as f:
            self.config = json.load(f)

        # Initialiser les composants
        self.drive_manager = DriveManager(credentials_path)
        self.video_extractor = VideoSegmentExtractor(self.logger)

        # Dossier temporaire
        self.temp_dir = Path('./temp_test_video')
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("✅ VideoProcessingTester initialisé")

    def _setup_logger(self):
        """Configure le logger"""
        logger = logging.getLogger('VideoProcessingTester')
        logger.setLevel(logging.INFO)

        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def check_dependencies(self) -> bool:
        """Vérifie que ffmpeg et ffprobe sont installés"""
        self.logger.info("\n" + "="*80)
        self.logger.info("🔍 VÉRIFICATION DES DÉPENDANCES")
        self.logger.info("="*80)

        # Vérifier ffmpeg
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            version_line = result.stdout.split('\n')[0]
            self.logger.info(f"✅ ffmpeg trouvé: {version_line}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.logger.error("❌ ffmpeg non trouvé. Installez-le avec: brew install ffmpeg")
            return False

        # Vérifier ffprobe
        try:
            result = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                text=True,
                check=True
            )
            version_line = result.stdout.split('\n')[0]
            self.logger.info(f"✅ ffprobe trouvé: {version_line}")
        except (FileNotFoundError, subprocess.CalledProcessError):
            self.logger.error("❌ ffprobe non trouvé")
            return False

        return True

    def list_available_excel_files(self) -> List[Dict]:
        """Liste les fichiers Excel disponibles dans Drive"""
        self.logger.info("\n" + "="*80)
        self.logger.info("📋 FICHIERS EXCEL DISPONIBLES")
        self.logger.info("="*80)

        excel_folder_id = self.config['drive_folders']['excel_output']
        files = self.drive_manager.list_files_in_folder(
            excel_folder_id,
            name_pattern='_highlights.xlsx'
        )

        if not files:
            self.logger.warning("❌ Aucun fichier Excel trouvé")
            return []

        self.logger.info(f"\n{len(files)} fichier(s) trouvé(s):\n")
        for i, f in enumerate(files, 1):
            size_mb = int(f.get('size', 0)) / 1024 / 1024
            self.logger.info(f"{i}. {f['name']}")
            self.logger.info(f"   ID: {f['id']}")
            self.logger.info(f"   Taille: {size_mb:.2f} MB")
            self.logger.info(f"   Créé: {f.get('createdTime', 'N/A')}\n")

        return files

    def test_local_extraction(self, excel_file_info: Dict) -> bool:
        """
        Test l'extraction locale (sans upload Drive)

        Args:
            excel_file_info: Info du fichier Excel depuis Drive

        Returns:
            True si succès
        """
        self.logger.info("\n" + "="*80)
        self.logger.info("🧪 TEST D'EXTRACTION LOCALE")
        self.logger.info("="*80)

        file_name = excel_file_info['name']
        file_id = excel_file_info['id']
        base_name = file_name.replace('_highlights.xlsx', '')

        try:
            # 1. Télécharger le fichier Excel
            self.logger.info(f"\n📥 Téléchargement Excel: {file_name}")
            excel_path = self.temp_dir / file_name
            self.drive_manager.download_file(file_id, file_name, str(excel_path))
            self.logger.info(f"   ✅ Téléchargé: {excel_path}")

            # 2. Chercher la vidéo source
            self.logger.info(f"\n🎬 Recherche de la vidéo source: {base_name}")
            source_file = self._find_source_video(base_name)

            if not source_file:
                self.logger.error(f"   ❌ Vidéo source non trouvée")
                self.logger.info(f"   Vérifiez que le fichier existe dans le dossier 'Medias'")
                return False

            self.logger.info(f"   ✅ Trouvée: {source_file['name']}")

            # 3. Télécharger la vidéo source
            self.logger.info(f"\n📥 Téléchargement vidéo source...")
            source_ext = Path(source_file['name']).suffix
            source_path = self.temp_dir / f"{base_name}{source_ext}"
            self.drive_manager.download_file(source_file['id'], source_file['name'], str(source_path))

            source_size_mb = source_path.stat().st_size / 1024 / 1024
            self.logger.info(f"   ✅ Téléchargé: {source_path}")
            self.logger.info(f"   Taille: {source_size_mb:.1f} MB")

            # 4. Créer dossier pour les segments
            segments_folder = self.temp_dir / f"{base_name}_segments"
            segments_folder.mkdir(exist_ok=True)

            # 5. Extraire et fusionner les segments
            self.logger.info(f"\n✂️  DÉCOUPAGE ET FUSION DES SEGMENTS")
            self.logger.info("="*80)

            created_segments = self.video_extractor.extract_segments(
                str(excel_path),
                str(source_path),
                str(segments_folder)
            )

            if not created_segments:
                self.logger.error("❌ Aucun segment créé")
                return False

            # 6. Valider les segments créés
            self.logger.info(f"\n✅ {len(created_segments)} segment(s) créé(s) avec succès!")
            self.validate_segments(created_segments)

            return True

        except Exception as e:
            self.logger.error(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            return False

    def validate_segments(self, segment_files: List[str]):
        """Valide les segments créés avec ffprobe"""
        self.logger.info("\n" + "="*80)
        self.logger.info("🔍 VALIDATION DES SEGMENTS")
        self.logger.info("="*80 + "\n")

        for i, segment_path in enumerate(segment_files, 1):
            segment_name = Path(segment_path).name

            # Obtenir les infos du segment
            info = self.video_extractor.get_segment_info(segment_path)

            if not info:
                self.logger.warning(f"{i}. {segment_name}")
                self.logger.warning("   ⚠️  Impossible d'obtenir les infos")
                continue

            # Afficher les infos
            size_mb = info['size_bytes'] / 1024 / 1024

            self.logger.info(f"{i}. {segment_name}")
            self.logger.info(f"   ⏱️  Durée: {info['duration']:.2f}s")
            self.logger.info(f"   🎥 Codec: {info['video_codec']}")
            self.logger.info(f"   📐 Résolution: {info['width']}x{info['height']}")
            self.logger.info(f"   💾 Taille: {size_mb:.2f} MB")
            self.logger.info(f"   📊 Bitrate: {info['bitrate'] / 1000:.0f} kbps\n")

    def _find_source_video(self, base_name: str) -> Dict:
        """Cherche la vidéo source correspondante"""
        video_extensions = ['.mp4', '.mp3', '.wav', '.m4a', '.mov', '.avi']
        source_folder_id = self.config['drive_folders']['source_files']

        for ext in video_extensions:
            search_name = f"{base_name}{ext}"
            files = self.drive_manager.list_files_in_folder(
                source_folder_id,
                name_pattern=base_name
            )

            # Chercher le fichier exact
            for f in files:
                if f['name'] == search_name:
                    return f

        return None

    def cleanup(self):
        """Nettoie les fichiers temporaires"""
        self.logger.info("\n" + "="*80)
        self.logger.info("🧹 NETTOYAGE")
        self.logger.info("="*80)

        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.logger.info("✅ Fichiers temporaires nettoyés")
        except Exception as e:
            self.logger.warning(f"⚠️  Erreur nettoyage: {e}")

    def run_interactive(self):
        """Mode interactif: choisir un fichier Excel"""
        print("\n" + "="*80)
        print("🎬 TEST SYSTÈME DE DÉCOUPAGE VIDÉO - MODE INTERACTIF")
        print("="*80)

        # 1. Vérifier dépendances
        if not self.check_dependencies():
            print("\n❌ Dépendances manquantes. Installez ffmpeg et réessayez.")
            return

        # 2. Lister les fichiers Excel
        files = self.list_available_excel_files()

        if not files:
            print("\n❌ Aucun fichier Excel disponible")
            return

        # 3. Demander à l'utilisateur de choisir
        print("\n" + "="*80)
        try:
            choice = int(input(f"Choisissez un fichier à tester (1-{len(files)}): "))
            if choice < 1 or choice > len(files):
                print("❌ Choix invalide")
                return
        except (ValueError, KeyboardInterrupt):
            print("\n❌ Annulé")
            return

        selected_file = files[choice - 1]

        # 4. Lancer le test
        success = self.test_local_extraction(selected_file)

        # 5. Cleanup
        print("\n" + "="*80)
        cleanup_choice = input("Nettoyer les fichiers temporaires? (o/n): ").lower()
        if cleanup_choice == 'o':
            self.cleanup()
        else:
            print(f"📁 Fichiers conservés dans: {self.temp_dir}")

        # 6. Résultat final
        print("\n" + "="*80)
        if success:
            print("✅ TEST RÉUSSI!")
        else:
            print("❌ TEST ÉCHOUÉ")
        print("="*80)


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description='Test du système de découpage vidéo')
    parser.add_argument(
        '--excel-id',
        help='ID du fichier Excel à tester (optionnel, sinon mode interactif)'
    )
    args = parser.parse_args()

    # Chemins
    script_dir = Path(__file__).parent.parent
    credentials_path = script_dir / 'config' / 'credentials.json'
    config_path = script_dir / 'config' / 'highlight_config.json'

    # Vérifier que les fichiers existent
    if not credentials_path.exists():
        print(f"❌ Fichier credentials.json non trouvé: {credentials_path}")
        return

    if not config_path.exists():
        print(f"❌ Fichier highlight_config.json non trouvé: {config_path}")
        return

    # Initialiser le testeur
    tester = VideoProcessingTester(
        credentials_path=str(credentials_path),
        config_path=str(config_path)
    )

    # Mode interactif ou direct
    if args.excel_id:
        # Mode direct avec ID spécifique
        print("\n" + "="*80)
        print("🎬 TEST SYSTÈME DE DÉCOUPAGE VIDÉO - MODE DIRECT")
        print("="*80)

        # Vérifier dépendances
        if not tester.check_dependencies():
            print("\n❌ Dépendances manquantes. Installez ffmpeg et réessayez.")
            return

        # Chercher le fichier
        files = tester.list_available_excel_files()
        excel_file = next((f for f in files if f['id'] == args.excel_id), None)

        if not excel_file:
            print(f"\n❌ Fichier Excel non trouvé avec ID: {args.excel_id}")
            return

        print(f"\n📄 Fichier sélectionné: {excel_file['name']}")

        # Lancer le test
        success = tester.test_local_extraction(excel_file)

        # Cleanup
        print("\n" + "="*80)
        tester.cleanup()

        # Résultat final
        print("\n" + "="*80)
        if success:
            print("✅ TEST RÉUSSI!")
        else:
            print("❌ TEST ÉCHOUÉ")
        print("="*80)
    else:
        # Mode interactif
        tester.run_interactive()


if __name__ == '__main__':
    main()
