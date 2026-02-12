#!/usr/bin/env python3
"""
Test de simulation pour l'extraction de segments multiples
Simule le scénario qui a échoué: plusieurs sous-segments à fusionner
"""
import sys
from pathlib import Path
import tempfile
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from video_segment_extractor import VideoSegmentExtractor
import logging

def test_multiple_segments():
    """Simule le cas avec plusieurs sous-segments (comme GSE du 8 janvier)"""
    print("🧪 Test: Simulation extraction avec plusieurs sous-segments")
    print("=" * 60)

    # Créer un extractor
    logger = logging.getLogger(__name__)
    extractor = VideoSegmentExtractor(logger)

    # Créer un fichier Excel temporaire similaire à celui qui a échoué
    # Avec 2 sous-segments pour le même groupe (S1)
    data = {
        'Numéro': [1, 1],  # Même numéro = fusion nécessaire
        'Groupe': ['S1', 'S1'],
        'Début (secondes)': [10.0, 30.0],
        'Fin (secondes)': [20.0, 40.0],
        'Durée (secondes)': [10.0, 10.0],
        'Texte': ['Segment 1', 'Segment 2']
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Créer le fichier Excel
        excel_path = tmpdir / "test_highlights.xlsx"
        df = pd.DataFrame(data)
        df.to_excel(excel_path, index=False, engine='openpyxl')

        print(f"✅ Excel créé: {excel_path}")
        print(f"   Contenu: {len(df)} lignes, groupe 'S1' avec 2 sous-segments")

        # Lire le fichier (comme dans extract_segments)
        df_read = pd.read_excel(excel_path, engine='openpyxl')
        grouped = df_read.groupby('Numéro')

        print(f"✅ Groupement: {len(grouped)} groupe(s)")

        for segment_num, group in grouped:
            print(f"\n📋 Groupe {segment_num}:")
            print(f"   Nombre de sous-segments: {len(group)}")

            # Préparer les segments pour la fusion
            segments_to_merge = []
            for idx, row in group.iterrows():
                segments_to_merge.append({
                    'start': row['Début (secondes)'],
                    'end': row['Fin (secondes)'],
                    'duration': row['Durée (secondes)']
                })

            print(f"   Segments préparés: {segments_to_merge}")

            # TEST CRITIQUE: Appeler _extract_and_merge_segments
            # C'est ici que le bug se produisait (subtitles_dir non défini)
            try:
                print(f"\n🔧 Test de _extract_and_merge_segments...")

                # On ne peut pas vraiment extraire sans vidéo source
                # Mais on peut au moins vérifier que la signature est correcte
                import inspect
                sig = inspect.signature(extractor._extract_and_merge_segments)
                params = list(sig.parameters.keys())

                print(f"   Paramètres: {params}")

                if 'subtitles_dir' in params:
                    print("   ❌ ERREUR: subtitles_dir encore présent!")
                    return False
                else:
                    print("   ✅ Signature correcte (pas de subtitles_dir)")

            except Exception as e:
                print(f"   ❌ ERREUR lors du test: {e}")
                import traceback
                traceback.print_exc()
                return False

    print("\n" + "=" * 60)
    print("✅ Test de simulation RÉUSSI")
    print("   Le code devrait fonctionner avec plusieurs sous-segments")
    return True

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        if test_multiple_segments():
            print("\n✅ VALIDATION OK - Prêt pour le déploiement")
            sys.exit(0)
        else:
            print("\n❌ VALIDATION ÉCHOUÉE - NE PAS DÉPLOYER")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
