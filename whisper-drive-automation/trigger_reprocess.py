#!/usr/bin/env python3
"""
Script pour déclencher manuellement un reprocess d'un fichier Excel existant
"""
import sys
import json
import logging
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.insert(0, 'src')

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Charger la config
    config_file = 'config/highlight_config.json'
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Import après l'ajout au path
    sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
    from highlight_orchestrator_cloud import HighlightsProcessor

    # Créer le processor
    credentials_path = 'config/credentials.json'
    processor = HighlightsProcessor(config, credentials_path)

    # Excel à reprocesser
    excel_id = '19ka3PTEBPSJusz1FlylLsWQm2oDVvtdn'
    excel_name = 'Contempler au niveau du coeur_highlights.xlsx'

    logger.info("=" * 60)
    logger.info("🔄 DÉCLENCHEMENT REPROCESS")
    logger.info("=" * 60)
    logger.info(f"📄 Excel: {excel_name}")
    logger.info(f"🆔 ID: {excel_id}")
    logger.info("")

    # Déclencher le reprocess
    excel_info = {'id': excel_id, 'name': excel_name}
    result = processor.process_excel_file(excel_info)

    if result:
        logger.info("=" * 60)
        logger.info("✅ REPROCESS DÉCLENCHÉ AVEC SUCCÈS")
        logger.info("=" * 60)
        logger.info("📊 Actions effectuées:")
        logger.info("  1. Excel régénéré avec les nouveaux timestamps")
        logger.info("  2. Job créé dans queue_highlights")
        logger.info("  3. VM démarrée (si nécessaire)")
        logger.info("")
        logger.info("⏳ La VM va traiter le job et générer les segments vidéo avec sous-titres")
        logger.info("   Auto-shutdown de la VM après 10 min d'inactivité")
    else:
        logger.error("❌ ÉCHEC DU REPROCESS")
        logger.error("Voir les logs ci-dessus pour plus de détails")

    return 0 if result else 1

if __name__ == '__main__':
    sys.exit(main())
