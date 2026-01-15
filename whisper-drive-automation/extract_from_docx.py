#!/usr/bin/env python3
"""
Extrait tous les segments du fichier .docx et affiche leurs timestamps
"""
import json
import re
import logging
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from highlight_extractor import HighlightExtractor

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def extract_text_from_docx(docx_path):
    """Extrait le texte d'un fichier .docx"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copier le docx
        temp_docx = Path(tmpdir) / "temp.docx"
        shutil.copy(docx_path, temp_docx)

        # Unzip
        subprocess.run(['unzip', '-q', str(temp_docx)], cwd=tmpdir, check=True)

        # Lire le XML
        xml_path = Path(tmpdir) / 'word' / 'document.xml'
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()

        # Extraire le texte (retirer les balises XML)
        text = re.sub(r'<[^>]+>', ' ', xml_content)
        text = re.sub(r'\s+', ' ', text)

        return text

def parse_segments(text):
    """Parse les segments depuis le texte"""
    segments = []

    # Pattern pour trouver les segments: 🎬 S1 🎬 ... 🎬 /S1 🎬
    pattern = r'🎬\s*([A-Z]\d+)\s*🎬(.*?)🎬\s*/\1\s*🎬'

    for match in re.finditer(pattern, text, re.DOTALL):
        segment_id = match.group(1)
        segment_text = match.group(2).strip()

        # Nettoyer le texte (retirer les timestamps (XX:XX))
        clean_text = re.sub(r'\(\d{1,2}:\d{2}\)', '', segment_text)
        clean_text = ' '.join(clean_text.split())

        segments.append({
            'segment_id': segment_id,
            'text': clean_text
        })

    return segments

def main():
    docx_path = "/Users/amel/Downloads/Séance 3 jour 1_paragraphs_timestamps.docx"
    json_path = "/Users/amel/Downloads/Séance 3 jour 1 _complete_data (1).json"

    logger.info("=" * 80)
    logger.info("📄 EXTRACTION DES SEGMENTS DEPUIS LE DOCX")
    logger.info("=" * 80)
    logger.info("")

    # Extraire le texte
    logger.info("📖 Extraction du texte depuis le .docx...")
    text = extract_text_from_docx(docx_path)
    logger.info(f"   {len(text)} caractères extraits")
    logger.info("")

    # Parser les segments
    logger.info("🔍 Parsing des segments...")
    segments = parse_segments(text)
    logger.info(f"   {len(segments)} segment(s) trouvé(s)")
    logger.info("")

    # Afficher les segments trouvés
    logger.info("📋 Segments détectés:")
    for seg in segments:
        logger.info(f"   - {seg['segment_id']}: {seg['text'][:60]}...")
    logger.info("")

    # Charger les données de transcription
    logger.info("📊 Chargement de la transcription...")
    with open(json_path, 'r', encoding='utf-8') as f:
        complete_data = json.load(f)
    logger.info("   ✅ Transcription chargée")
    logger.info("")

    # Matcher avec les timestamps
    logger.info("=" * 80)
    logger.info("🔍 RECHERCHE DES TIMESTAMPS")
    logger.info("=" * 80)
    logger.info("")

    extractor = HighlightExtractor(logger=logging.getLogger('HighlightExtractor'))

    matched_segments = []
    for seg in segments:
        logger.info(f"🎬 {seg['segment_id']}: {seg['text'][:80]}...")

        start_time, end_time = extractor._find_exact_timestamps(
            seg['text'],
            complete_data,
            context_before="",
            context_after=""
        )

        if start_time and end_time:
            matched_segments.append({
                'segment_id': seg['segment_id'],
                'text': seg['text'],
                'start': start_time,
                'end': end_time,
                'duration': round(end_time - start_time, 2)
            })
            logger.info(f"   ✅ {_format_time(start_time)} → {_format_time(end_time)} ({end_time - start_time:.2f}s)")
        else:
            logger.info(f"   ❌ Timestamps non trouvés")

        logger.info("")

    # Résumé final
    logger.info("")
    logger.info("=" * 80)
    logger.info("📋 RÉSUMÉ DE TOUS LES SEGMENTS")
    logger.info("=" * 80)
    logger.info("")

    for seg in matched_segments:
        logger.info(f"🎬 {seg['segment_id']}")
        logger.info(f"   Start:  {seg['start']:.2f}s  ({_format_time(seg['start'])})")
        logger.info(f"   End:    {seg['end']:.2f}s  ({_format_time(seg['end'])})")
        logger.info(f"   Durée:  {seg['duration']:.2f}s")
        logger.info(f"   Texte:  {seg['text'][:100]}...")
        logger.info("")

    # Statistiques
    if matched_segments:
        logger.info("=" * 80)
        logger.info("📊 STATISTIQUES")
        logger.info("=" * 80)
        total_duration = sum(s['duration'] for s in matched_segments)
        logger.info(f"Nombre de segments: {len(matched_segments)}/{len(segments)}")
        logger.info(f"Durée totale: {total_duration:.2f}s ({_format_time(total_duration)})")
        logger.info(f"Durée moyenne: {total_duration/len(matched_segments):.2f}s")
        logger.info("")

def _format_time(seconds):
    """Convertit secondes en HH:MM:SS format"""
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    else:
        return f"{mins:02d}:{secs:02d}"

if __name__ == '__main__':
    print("\n🎬 Extraction de tous les segments depuis le DOCX\n")
    main()
