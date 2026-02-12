#!/usr/bin/env python3
"""
Test extraction audio WAV + vérification intégrité + envoi RunPod
Pour les gros fichiers (15+ GB)
"""
import os
import sys
import subprocess
import tempfile
from pathlib import Path
import json

def extract_audio_wav(video_path: str, output_path: str) -> bool:
    """Extrait l'audio en WAV (comme le nouveau code)"""
    print(f"🎬 Extraction audio WAV: {video_path}")

    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # WAV PCM 16-bit
        '-ar', '16000',  # Sample rate
        '-ac', '1',  # Mono
        '-y',  # Overwrite
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600)
        if result.returncode != 0:
            print(f"❌ Erreur: {result.stderr.decode()}")
            return False
        print(f"✅ Audio extrait: {Path(output_path).stat().st_size / 1024 / 1024:.1f} MB")
        return True
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout après 600s")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def verify_audio_integrity(audio_path: str) -> bool:
    """Vérifie l'intégrité avec ffprobe"""
    print(f"🔍 Vérification intégrité...")

    try:
        probe_result = subprocess.run([
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration,size',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ], capture_output=True, text=True, timeout=30)

        if probe_result.returncode != 0:
            print(f"❌ Fichier audio corrompu: {probe_result.stderr}")
            return False

        probe_lines = probe_result.stdout.strip().split('\n')
        if len(probe_lines) >= 2:
            duration = float(probe_lines[0])
            size_bytes = int(probe_lines[1])
            print(f"✅ Audio valide: {size_bytes / 1024 / 1024:.1f} MB, durée: {duration:.1f}s")
            return True

        return False

    except Exception as e:
        print(f"❌ Erreur vérification: {e}")
        return False


def upload_to_gcs_and_runpod(audio_path: str):
    """Upload sur GCS et envoie à RunPod"""
    print(f"☁️  Upload GCS + RunPod...")

    sys.path.insert(0, 'src')
    from transcription_backends import get_transcription_backend

    # Charger config
    config_file = Path('config/highlight_config.json')
    with open(config_file, 'r') as f:
        config = json.load(f)

    # Initialiser backend RunPod
    backend = get_transcription_backend(config)
    print(f"🔧 Backend: {backend.get_backend_name()}")

    # Transcrire (va uploader sur GCS et appeler RunPod)
    print(f"🚀 Envoi à RunPod...")
    result = backend.transcribe_audio(
        audio_path=audio_path,
        language="fr"
    )

    if result:
        segments = result.get("segments", [])
        print(f"✅ RunPod terminé: {len(segments)} segments")
        return True
    else:
        print(f"❌ Échec RunPod")
        return False


def main():
    video_path = "/Users/amel/Downloads/Cours avec Myriam.MP4"

    if not os.path.exists(video_path):
        print(f"❌ Fichier introuvable: {video_path}")
        sys.exit(1)

    print("=" * 70)
    print("🧪 TEST GROS FICHIER - WAV + INTÉGRITÉ + RUNPOD")
    print("=" * 70)
    print(f"📹 Vidéo: {video_path}")
    print(f"📊 Taille: {Path(video_path).stat().st_size / 1024 / 1024 / 1024:.1f} GB")
    print()

    # Créer fichier audio temporaire
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        audio_path = f.name

    try:
        # 1. Extraction audio WAV
        print("📥 ÉTAPE 1: Extraction audio WAV")
        print("-" * 70)
        if not extract_audio_wav(video_path, audio_path):
            sys.exit(1)

        print()

        # 2. Vérification intégrité
        print("🔍 ÉTAPE 2: Vérification intégrité")
        print("-" * 70)
        if not verify_audio_integrity(audio_path):
            sys.exit(1)

        print()

        # 3. Upload GCS + RunPod
        print("☁️  ÉTAPE 3: Upload GCS + RunPod")
        print("-" * 70)

        # Demander confirmation avant d'envoyer à RunPod (coûteux)
        response = input("Envoyer à RunPod ? (o/n): ")
        if response.lower() == 'o':
            if not upload_to_gcs_and_runpod(audio_path):
                sys.exit(1)
        else:
            print("⏭️  RunPod skippé")

        print()
        print("=" * 70)
        print("✅ TOUS LES TESTS PASSÉS")
        print("=" * 70)

    finally:
        # Nettoyer
        if os.path.exists(audio_path):
            os.remove(audio_path)
            print(f"🧹 Fichier temporaire nettoyé")


if __name__ == '__main__':
    main()
