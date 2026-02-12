#!/usr/bin/env python3
"""
Script de test pour le client RunPod

Usage:
    export RUNPOD_API_KEY="your_api_key"
    python test_runpod_client.py
"""

import os
import sys
from pathlib import Path

# Add src to path
current_dir = Path(__file__).parent
src_path = str(current_dir / 'src')
sys.path.insert(0, src_path)

from runpod_client import RunPodClient


def test_runpod_client():
    """Test basique du client RunPod"""

    # Vérifier que l'API key est définie
    api_key = os.environ.get('RUNPOD_API_KEY')
    if not api_key:
        print("❌ RUNPOD_API_KEY non définie")
        print("Exécutez: export RUNPOD_API_KEY='votre_cle'")
        return 1

    # Configuration (à modifier selon votre endpoint)
    endpoint_id = input("Entrez votre RunPod Endpoint ID: ").strip()
    if not endpoint_id:
        print("❌ Endpoint ID requis")
        return 1

    endpoint = f"https://api.runpod.ai/v2/{endpoint_id}"

    print(f"\n🔧 Configuration:")
    print(f"   API Key: {api_key[:8]}...")
    print(f"   Endpoint: {endpoint}")

    # Créer le client
    client = RunPodClient(api_key=api_key, endpoint=endpoint)

    # URL d'un fichier audio de test
    # Option 1: Utiliser un fichier déjà sur GCS
    # Option 2: Uploader un fichier local d'abord
    audio_url = input("\nEntrez l'URL de l'audio de test (GCS ou public): ").strip()

    if not audio_url:
        print("❌ URL audio requise")
        return 1

    print(f"\n🎤 Audio: {audio_url}")
    print("\n🚀 Envoi de la requête de transcription...")

    try:
        result = client.transcribe_audio(
            audio_url=audio_url,
            model="large-v3-turbo",
            language="fr"
        )

        print("\n✅ Transcription réussie!")
        print(f"\n📝 Résultat:")
        print(f"   Segments: {len(result.get('segments', []))}")

        # Afficher les premiers segments
        segments = result.get('segments', [])
        if segments:
            print(f"\n   Premiers segments:")
            for i, seg in enumerate(segments[:3]):
                print(f"   [{i+1}] {seg.get('start', 0):.2f}s - {seg.get('end', 0):.2f}s")
                print(f"       {seg.get('text', '').strip()}")

                # Vérifier les word timestamps
                words = seg.get('words', [])
                if words:
                    print(f"       Mots: {len(words)} word-level timestamps")
                else:
                    print(f"       ⚠️  Pas de word-level timestamps!")

        return 0

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(test_runpod_client())
