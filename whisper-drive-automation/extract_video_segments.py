#!/usr/bin/env python3
"""
Script pour extraire les segments vidéo à partir du fichier Excel
"""
import sys
import logging
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import io

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from video_segment_extractor import VideoSegmentExtractor


def download_video_from_drive(drive_service, file_id: str, output_path: Path):
    """Télécharge une vidéo depuis Google Drive"""
    logger.info(f"📥 Téléchargement de la vidéo depuis Google Drive...")

    try:
        request = drive_service.files().get_media(fileId=file_id)

        with open(output_path, 'wb') as f:
            downloader = drive_service.files().get_media(fileId=file_id)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"   Téléchargement: {progress}%")

        logger.info(f"   ✅ Vidéo téléchargée: {output_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement: {e}")
        return False


def find_video_on_drive(drive_service, filename_pattern: str):
    """Cherche une vidéo sur Google Drive"""
    logger.info(f"🔍 Recherche de la vidéo '{filename_pattern}' sur Google Drive...")

    query = f"name contains '{filename_pattern}' and trashed=false and (mimeType contains 'video' or name contains '.mp4' or name contains '.mov')"

    try:
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, mimeType, size)",
            pageSize=10
        ).execute()

        files = results.get('files', [])

        if files:
            logger.info(f"   ✅ {len(files)} vidéo(s) trouvée(s):")
            for i, file in enumerate(files, 1):
                size_mb = int(file.get('size', 0)) / (1024 * 1024)
                logger.info(f"      {i}. {file['name']} ({size_mb:.1f} MB)")

            return files[0]  # Retourner la première
        else:
            logger.warning(f"   ❌ Aucune vidéo trouvée")
            return None
    except Exception as e:
        logger.error(f"❌ Erreur recherche: {e}")
        return None


def main():
    # Chemins
    excel_path = Path(__file__).parent / "test_seance3_timestamps.xlsx"
    output_folder = Path(__file__).parent / "segments_seance3"

    if not excel_path.exists():
        logger.error(f"❌ Fichier Excel non trouvé: {excel_path}")
        logger.info("   Exécutez d'abord test_seance3_local.py")
        return

    logger.info(f"📊 Fichier Excel: {excel_path}")

    # Chercher la vidéo source
    logger.info("\n" + "="*80)
    logger.info("🎥 RECHERCHE DE LA VIDÉO SOURCE")
    logger.info("="*80)

    # Option 1: Chercher en local
    video_path = None

    # Chercher dans Downloads
    downloads = Path.home() / "Downloads"
    possible_names = [
        "Séance 3 jour 1.mp4",
        "Seance 3 jour 1.mp4",
        "S3J1.mp4",
        "seance_3_jour_1.mp4"
    ]

    for name in possible_names:
        test_path = downloads / name
        if test_path.exists():
            video_path = test_path
            logger.info(f"✅ Vidéo trouvée en local: {video_path}")
            break

    # Option 2: Chercher sur Google Drive
    if not video_path:
        logger.info("❌ Vidéo non trouvée en local, recherche sur Google Drive...")

        creds_path = Path(__file__).parent / 'config' / 'credentials.json'
        creds = Credentials.from_service_account_file(
            str(creds_path),
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        drive_service = build('drive', 'v3', credentials=creds)

        video_file = find_video_on_drive(drive_service, "Séance 3 jour 1")

        if not video_file:
            video_file = find_video_on_drive(drive_service, "seance 3")

        if video_file:
            # Télécharger la vidéo
            video_path = Path(__file__).parent / "temp_video_source.mp4"

            logger.info(f"\n📥 Téléchargement de: {video_file['name']}")
            size_mb = int(video_file.get('size', 0)) / (1024 * 1024)
            logger.info(f"   Taille: {size_mb:.1f} MB")

            if size_mb > 500:
                logger.warning(f"⚠️  Vidéo volumineuse ({size_mb:.1f} MB), cela peut prendre du temps...")

            success = download_video_from_drive(drive_service, video_file['id'], video_path)

            if not success:
                logger.error("❌ Échec téléchargement")
                return

    if not video_path:
        logger.error("\n❌ Impossible de trouver la vidéo source")
        logger.info("\nOptions:")
        logger.info("1. Téléchargez manuellement la vidéo 'Séance 3 jour 1' dans ~/Downloads/")
        logger.info("2. Assurez-vous que la vidéo est partagée avec le service account sur Google Drive")
        return

    # Vérifier ffmpeg
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except FileNotFoundError:
        logger.error("❌ ffmpeg non installé")
        logger.info("   Installez avec: brew install ffmpeg")
        return

    # Extraire les segments
    logger.info("\n" + "="*80)
    logger.info("✂️  EXTRACTION DES SEGMENTS VIDÉO")
    logger.info("="*80)

    extractor = VideoSegmentExtractor(logger=logger)

    created_files = extractor.extract_segments(
        str(excel_path),
        str(video_path),
        str(output_folder)
    )

    if created_files:
        logger.info("\n" + "="*80)
        logger.info(f"✅ EXTRACTION TERMINÉE - {len(created_files)} fichier(s) créé(s)")
        logger.info("="*80)
        logger.info(f"\n📁 Dossier de sortie: {output_folder}")
        logger.info("\nFichiers créés:")
        for file_path in created_files:
            logger.info(f"   • {Path(file_path).name}")
    else:
        logger.error("\n❌ Aucun segment créé")


if __name__ == '__main__':
    main()
