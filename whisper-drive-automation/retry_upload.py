#!/usr/bin/env python3
"""
Script simple pour uploader les fichiers depuis le checkpoint
"""
import os
import sys
import json

# Setup Python path
sys.path.insert(0, 'src')
sys.path.insert(0, 'config')

# Maintenant on peut importer
from drive_manager import DriveManager
from output_generator import OutputGenerator
from whisper_transcriber import WhisperTranscriber
import whisper_config as config

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    checkpoint_file = '/tmp/whisper_checkpoints/Cours_45_mn_mercredi_14_janvier_avec_Guèn_Tonpa.MP4_transcription.json'
    file_name = 'Cours 45 mn mercredi 14 janvier avec Guèn Tonpa.MP4'

    # Charger le checkpoint
    logger.info(f"📂 Chargement du checkpoint...")
    with open(checkpoint_file, 'r') as f:
        whisper_result = json.load(f)

    logger.info(f"✅ {len(whisper_result['segments'])} segments chargés")

    # Initialiser les composants
    drive_manager = DriveManager(config.CREDENTIALS_PATH)
    transcriber = WhisperTranscriber(model='small')
    output_generator = OutputGenerator(
        drive_manager=drive_manager,
        output_folder_id=config.DRIVE_FOLDERS['output']
    )

    # Générer paragraphes
    logger.info("📝 Génération des paragraphes...")
    paragraphs = transcriber.group_segments_to_paragraphs(
        whisper_result['segments'],
        pause_threshold=config.PARAGRAPH_CONFIG['pause_threshold'],
        min_words=config.PARAGRAPH_CONFIG['min_words'],
        max_duration=config.PARAGRAPH_CONFIG['max_duration']
    )

    # Générer outputs
    logger.info("📄 Génération des fichiers...")
    base_filename = file_name.replace('.MP4', '').replace('.mp4', '')
    output_files = output_generator.generate_all_outputs(base_filename, whisper_result, paragraphs)

    logger.info(f"📤 Upload vers Drive...")
    output_folder_id = config.DRIVE_FOLDERS['output']

    # Upload chaque fichier
    for file_type, file_path in output_files.items():
        if not file_path:
            continue

        # Skip Google Docs (déjà uploadés)
        if isinstance(file_path, str) and file_path.startswith("gdoc:"):
            logger.info(f"✅ Google Doc déjà créé: {file_type}")
            continue

        # Upload fichier local
        if os.path.exists(file_path):
            drive_filename = os.path.basename(file_path)
            file_id = drive_manager.upload_file(file_path, drive_filename, output_folder_id)
            logger.info(f"✅ Uploadé: {drive_filename} (ID: {file_id})")
        else:
            logger.warning(f"⚠️  Fichier non trouvé: {file_path}")

    logger.info("🎉 Terminé !")
    return 0

if __name__ == '__main__':
    try:
        exit(main())
    except Exception as e:
        logger.error(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
