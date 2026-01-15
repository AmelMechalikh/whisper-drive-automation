#!/usr/bin/env python3
"""
Parser robuste pour les segments - tolérant aux erreurs humaines
"""
import re
from collections import defaultdict

def parse_segments_robust(text):
    """
    Parse les segments de manière robuste, tolérant aux erreurs:
    - Espaces manquants/en trop
    - Balises mal ordonnées
    - Balises multiples
    """
    segments = []

    # Pattern flexible: tolérant sur les espaces
    # 🎬 S1 🎬 ou 🎬S1🎬 ou 🎬 S1🎬 etc.
    open_pattern = r'🎬\s*([A-Z]\d+)\s*🎬'
    close_pattern = r'🎬\s*/([A-Z]\d+)\s*🎬'

    # Trouver toutes les balises d'ouverture
    open_matches = list(re.finditer(open_pattern, text))
    # Trouver toutes les balises de fermeture
    close_matches = list(re.finditer(close_pattern, text))

    # Créer un index des fermetures par segment ID
    closes_by_id = defaultdict(list)
    for match in close_matches:
        segment_id = match.group(1)
        closes_by_id[segment_id].append(match)

    # Pour chaque ouverture, trouver la fermeture correspondante
    for open_match in open_matches:
        segment_id = open_match.group(1)
        open_pos = open_match.end()

        # Chercher la première fermeture de ce segment APRÈS cette ouverture
        matching_close = None
        for close_match in closes_by_id.get(segment_id, []):
            if close_match.start() > open_pos:
                matching_close = close_match
                break

        if matching_close:
            close_pos = matching_close.start()
            segment_text = text[open_pos:close_pos].strip()

            # Nettoyer le texte (retirer timestamps, etc.)
            clean_text = re.sub(r'\(\d{1,2}:\d{2}\)', '', segment_text)
            clean_text = ' '.join(clean_text.split())

            segments.append({
                'segment_id': segment_id,
                'text': clean_text,
                'raw_text': segment_text
            })

    return segments

def test_parser(docx_path):
    """Teste le parser sur un fichier docx"""
    import subprocess
    import tempfile
    import shutil
    from pathlib import Path

    # Extraire le texte du docx
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_docx = Path(tmpdir) / "temp.docx"
        shutil.copy(docx_path, temp_docx)
        subprocess.run(['unzip', '-q', str(temp_docx)], cwd=tmpdir, check=True)
        xml_path = Path(tmpdir) / 'word' / 'document.xml'
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        text = re.sub(r'<[^>]+>', ' ', xml_content)
        text = re.sub(r'\s+', ' ', text)

    # Parser les segments
    segments = parse_segments_robust(text)

    print(f"🎬 Parser robuste: {len(segments)} segments trouvés\n")
    print("=" * 80)

    # Compter par ID
    from collections import Counter
    counts = Counter([s['segment_id'] for s in segments])

    for seg_id in sorted(counts.keys(), key=lambda x: (x[0], int(re.findall(r'\d+', x)[0]))):
        count = counts[seg_id]
        print(f"{seg_id}: {count}x")
        # Afficher les aperçus
        for i, seg in enumerate([s for s in segments if s['segment_id'] == seg_id], 1):
            print(f"  #{i}: {seg['text'][:80]}...")

    print("\n" + "=" * 80)
    print(f"✅ Total: {len(segments)} segments")

    return segments

if __name__ == '__main__':
    import sys

    docx_path = sys.argv[1] if len(sys.argv) > 1 else "/Users/amel/Downloads/Séance 3 jour 1_paragraphs_timestamps (1).docx"

    print("🔍 Test du parser robuste")
    print("=" * 80)
    print()

    segments = test_parser(docx_path)
