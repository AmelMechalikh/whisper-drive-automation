#!/usr/bin/env python3
"""
Script pour tester le highlights processor localement
Usage: python3 test_highlights_local.py
"""

import sys
import os
from pathlib import Path

# Ajouter les chemins pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent))

# Simuler l'environnement Cloud Run
os.environ['PYTEST_CURRENT_TEST'] = ''  # Désactiver le mode test

import json
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from highlight_orchestrator_cloud import HighlightsProcessor

def test_local():
    """Test local du processor"""
    
    print("=" * 60)
    print("🧪 TEST LOCAL - Highlights Processor")
    print("=" * 60)
    
    # Charger la config
    config_path = Path(__file__).parent.parent / 'config' / 'highlight_config.json'
    with open(config_path) as f:
        config = json.load(f)
    
    print(f"\n📋 Configuration chargée:")
    print(f"   highlighted_files: {config['drive_folders']['highlighted_files']}")
    print(f"   transcriptions: {config['drive_folders']['transcriptions']}")
    print(f"   excel_output: {config['drive_folders']['excel_output']}")
    
    # Initialiser le processor
    credentials_path = Path(__file__).parent.parent / 'config' / 'credentials.json'
    
    print(f"\n🚀 Initialisation du processor...")
    processor = HighlightsProcessor(config, str(credentials_path))
    
    print(f"\n✅ Processor initialisé")
    print(f"   DriveManager: {processor.drive_manager}")
    print(f"   HighlightExtractor: {processor.highlight_extractor}")
    
    # Test 1: Vérifier les fichiers avec commentaires
    print("\n" + "=" * 60)
    print("TEST 1: Détection des fichiers avec commentaires")
    print("=" * 60)
    
    highlighted_files = processor.check_new_highlighted_files()
    print(f"\n📊 Résultat: {len(highlighted_files)} fichier(s) trouvé(s)")
    
    for file_info in highlighted_files:
        print(f"\n📄 Fichier: {file_info['name']}")
        print(f"   ID: {file_info['id']}")
        print(f"   Type: {file_info.get('mimeType', 'unknown')}")
    
    # Test 2: Traiter un fichier
    if highlighted_files:
        print("\n" + "=" * 60)
        print("TEST 2: Traitement d'un fichier")
        print("=" * 60)
        
        file_to_test = highlighted_files[0]
        print(f"\n🎯 Traitement de: {file_to_test['name']}")
        
        try:
            result = processor.process_highlighted_file(file_to_test)
            
            if result:
                print(f"\n✅ Traitement réussi !")
                print(f"   Excel généré: {result}")
            else:
                print(f"\n⚠️  Traitement terminé sans résultat")
                
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    
    # Test 3: Vérifier les fichiers Excel
    print("\n" + "=" * 60)
    print("TEST 3: Détection des fichiers Excel")
    print("=" * 60)
    
    excel_files = processor.check_new_excel_files()
    print(f"\n📊 Résultat: {len(excel_files)} fichier(s) Excel non traité(s)")
    
    for file_info in excel_files:
        print(f"\n📄 Fichier: {file_info['name']}")
        print(f"   ID: {file_info['id']}")
    
    print("\n" + "=" * 60)
    print("✅ Tests terminés")
    print("=" * 60)

if __name__ == '__main__':
    try:
        test_local()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
