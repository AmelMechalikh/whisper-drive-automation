#!/usr/bin/env python3
"""
Script pour reprendre l'upload à partir d'un checkpoint de transcription
"""
import os
import json
import sys
from pathlib import Path

# Ajouter les chemins au PYTHONPATH
current_dir = Path(__file__).parent.parent
src_path = str(current_dir / 'src')
config_path = str(current_dir / 'config')
sys.path.insert(0, src_path)
sys.path.insert(0, config_path)

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import whisper_config as config
from processor import WhisperDriveProcessor

def main():
    checkpoint_file = '/tmp/whisper_checkpoints/Cours_45_mn_mercredi_14_janvier_avec_Guèn_Tonpa.MP4_transcription.json'
    file_name = 'Cours 45 mn mercredi 14 janvier avec Guèn Tonpa.MP4'

    logger.info(f"🔄 Reprise depuis checkpoint: {checkpoint_file}")

    # Charger le checkpoint
    with open(checkpoint_file, 'r', encoding='utf-8') as f:
        whisper_result = json.load(f)

    logger.info(f"✅ Checkpoint chargé: {len(whisper_result.get('segments', []))} segments")

    # Initialiser le processeur
    processor = WhisperDriveProcessor(config)

    # Générer les paragraphes
    paragraph_config = config.PARAGRAPH_CONFIG
    paragraphs = processor.transcriber.group_segments_to_paragraphs(
        whisper_result['segments'],
        pause_threshold=paragraph_config['pause_threshold'],
        min_words=paragraph_config['min_words'],
        max_duration=paragraph_config['max_duration']
    )

    # Générer tous les outputs
    base_filename = Path(file_name).stem
    output_files = processor.output_generator.generate_all_outputs(
        base_filename, whisper_result, paragraphs
    )

    logger.info(f"📄 Fichiers générés: {list(output_files.keys())}")

    # Upload vers Drive
    uploaded_types = processor._upload_results(output_files)

    logger.info(f"✅ Upload réussi: {uploaded_types}")

    # Vérification
    output_folder_id = config.DRIVE_FOLDERS['output']
    if processor._verify_upload_complete(base_filename, output_folder_id):
        logger.info("✅ Vérification réussie - tous les fichiers sont sur Drive")

        # Nettoyer le checkpoint
        processor.checkpoint_manager.clear_checkpoints(file_name)
        logger.info("🗑️ Checkpoint supprimé")
    else:
        logger.error("❌ Vérification échouée")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
