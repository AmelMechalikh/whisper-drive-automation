#!/usr/bin/env python3
"""
Worker pour le traitement des highlights
Tourne sur la VM et surveille les nouveaux fichiers
"""

import sys
import json
import logging
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from highlight_orchestrator import HighlightOrchestrator


def setup_logging():
    """Configure le logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('highlight_worker.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('HighlightWorker')


def load_config(config_path):
    """Charge la configuration"""
    with open(config_path) as f:
        return json.load(f)


def main():
    """Point d'entrée principal"""
    logger = setup_logging()
    
    logger.info("🚀 Démarrage du Highlight Worker")
    
    # Chemins
    script_dir = Path(__file__).parent.parent
    credentials_path = script_dir / 'config' / 'credentials.json'
    config_path = script_dir / 'config' / 'highlight_config.json'
    
    # Charger la configuration
    logger.info("📖 Chargement de la configuration...")
    config = load_config(config_path)
    folders = config['drive_folders']
    processing = config['processing']
    
    # Initialiser l'orchestrateur
    logger.info("🔧 Initialisation de l'orchestrateur...")
    orchestrator = HighlightOrchestrator(
        credentials_path=str(credentials_path),
        highlighted_folder_id=folders['highlighted_files'],
        source_files_folder_id=folders['source_files'],
        transcriptions_folder_id=folders['transcriptions'],
        excel_output_folder_id=folders['excel_output'],
        segments_output_folder_id=folders['segments_output'],
        temp_dir=processing['temp_dir'],
        logger=logger
    )
    
    # Mode one-shot : traiter une fois puis s'arrêter
    logger.info("🎯 Traitement des fichiers (mode one-shot)...")
    stats = orchestrator.process_files()
    
    logger.info(f"📊 Statistiques finales: {stats}")
    logger.info("✅ Traitement terminé - VM prête à s'éteindre")


if __name__ == '__main__':
    main()
