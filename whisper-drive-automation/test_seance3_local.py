#!/usr/bin/env python3
"""
Script de test pour extraire les timestamps de Séance 3 jour 1
Avec fichier JSON local
"""
import sys
import json
import logging
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from highlight_extractor import HighlightExtractor
from inline_marker_extractor import InlineMarkerExtractor


def main():
    # Document ID fourni
    DOCUMENT_ID = "1jxJi6WQj_gCU6t_ZHj7DtZefEb1NgUyJr3KczfkUeEk"

    # Chemin du fichier JSON local
    JSON_PATH = Path.home() / "Downloads" / "Séance 3 jour 1 _complete_data.json"

    logger.info(f"📥 Chargement du fichier JSON local: {JSON_PATH}")

    if not JSON_PATH.exists():
        logger.error(f"❌ Fichier non trouvé: {JSON_PATH}")
        return

    # Charger le complete_data.json
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            complete_data = json.load(f)

        logger.info(f"   ✅ {len(complete_data.get('segments', []))} segments chargés")
    except Exception as e:
        logger.error(f"❌ Erreur lecture JSON: {e}")
        return

    # Credentials pour accéder au document
    creds_path = Path(__file__).parent / 'config' / 'credentials.json'

    creds = Credentials.from_service_account_file(
        str(creds_path),
        scopes=[
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/documents.readonly'
        ]
    )

    # Extraire les segments avec marqueurs inline
    logger.info(f"\n🎬 Extraction des marqueurs inline du document ID: {DOCUMENT_ID}...")

    marker_extractor = InlineMarkerExtractor(logger=logger)

    try:
        segments = marker_extractor.extract_segments_from_document(
            DOCUMENT_ID,
            str(creds_path)
        )
    except Exception as e:
        logger.error(f"❌ Erreur extraction document: {e}")
        logger.info("\nLe document n'est peut-être pas encore partagé avec le service account.")
        logger.info("Veuillez attendre quelques minutes que les permissions se propagent.")
        return

    if not segments:
        logger.warning("❌ Aucun segment trouvé dans le document")
        logger.info("\nVérifiez que le document contient des marqueurs au format:")
        logger.info("   🎬 S1 🎬 ... texte ... 🎬 /S1 🎬")
        return

    # Matcher avec le transcript
    logger.info(f"\n🔍 Matching avec le transcript...")
    matched_segments = marker_extractor.match_segments_with_transcript(
        segments,
        complete_data
    )

    if not matched_segments:
        logger.warning("❌ Aucun segment matché avec le transcript")
        return

    # Afficher les résultats
    logger.info(f"\n" + "="*80)
    logger.info(f"📊 RÉSULTATS - {len(matched_segments)} segment(s) trouvé(s)")
    logger.info("="*80)

    for seg in matched_segments:
        duration = seg['end'] - seg['start']
        logger.info(f"\n🎬 {seg['segment_id']}")
        logger.info(f"   Début:  {seg['start']:.2f}s  ({format_timestamp(seg['start'])})")
        logger.info(f"   Fin:    {seg['end']:.2f}s    ({format_timestamp(seg['end'])})")
        logger.info(f"   Durée:  {duration:.2f}s")
        logger.info(f"   Texte:  {seg['text'][:150]}...")

    # Sauvegarder dans un fichier Excel
    output_path = Path(__file__).parent / "test_seance3_timestamps.xlsx"

    logger.info(f"\n💾 Sauvegarde des résultats dans: {output_path}")

    try:
        import pandas as pd

        rows = []
        for i, seg in enumerate(matched_segments, 1):
            rows.append({
                'Numéro': i,
                'Segment ID': seg['segment_id'],
                'Début (secondes)': seg['start'],
                'Fin (secondes)': seg['end'],
                'Début (HH:MM:SS)': format_timestamp(seg['start']),
                'Fin (HH:MM:SS)': format_timestamp(seg['end']),
                'Durée (secondes)': seg['duration'],
                'Texte': seg['text'][:500]
            })

        df = pd.DataFrame(rows)
        df.to_excel(output_path, index=False, engine='openpyxl')

        logger.info(f"   ✅ Excel créé avec succès: {output_path}")
        logger.info(f"\n🎉 Test terminé! Vérifiez les timestamps dans le fichier Excel.")
    except Exception as e:
        logger.error(f"❌ Erreur création Excel: {e}")


def format_timestamp(seconds):
    """Convertit secondes en HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


if __name__ == '__main__':
    main()
