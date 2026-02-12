#!/usr/bin/env python3
"""
Test simple: vérifier que l'audio extrait n'est pas vide
et peut être streamé correctement vers RunPod
"""
import sys
import os
import subprocess
import tempfile
from pathlib import Path

def extract_audio_from_video(video_path: str, output_audio: str) -> bool:
    """Extrait l'audio d'une vidéo"""
    print(f"🎵 Extraction audio: {video_path}")

    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        '-y',
        output_audio
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Audio extrait: {output_audio}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur extraction audio:")
        print(e.stderr.decode() if e.stderr else 'Erreur inconnue')
        return False


def check_audio_file(audio_path: str):
    """Vérifie que le fichier audio est valide"""
    if not os.path.exists(audio_path):
        print(f"❌ Fichier audio introuvable: {audio_path}")
        return False

    file_size = os.path.getsize(audio_path)
    print(f"📊 Taille fichier audio: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

    if file_size == 0:
        print(f"❌ Fichier audio vide!")
        return False

    # Obtenir les infos avec ffprobe
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration,size,bit_rate',
        '-show_entries', 'stream=codec_name,sample_rate,channels',
        '-of', 'default=noprint_wrappers=1',
        audio_path
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("\n📋 Informations audio:")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur ffprobe: {e.stderr}")
        return False


def simulate_stream_to_runpod(audio_path: str):
    """Simule ce qui serait envoyé à RunPod"""
    print("\n🚀 Simulation du stream vers RunPod...")

    # Lire le fichier par chunks comme on le ferait pour l'upload
    chunk_size = 1024 * 1024  # 1MB chunks
    total_bytes = 0
    chunks_count = 0

    with open(audio_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            chunks_count += 1

    print(f"✅ Total bytes qui seraient envoyés: {total_bytes:,} bytes")
    print(f"✅ Nombre de chunks (1MB): {chunks_count}")
    print(f"✅ Le fichier audio est prêt pour RunPod!")

    return total_bytes > 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_audio_extraction_stream.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]

    if not os.path.exists(video_path):
        print(f"❌ Fichier vidéo introuvable: {video_path}")
        sys.exit(1)

    print("=" * 70)
    print("🧪 TEST EXTRACTION AUDIO + STREAM")
    print("=" * 70)
    print(f"📹 Vidéo: {video_path}\n")

    # Créer dossier de sortie
    output_dir = Path('./test_subtitles_local')
    output_dir.mkdir(exist_ok=True)

    video_name = Path(video_path).stem
    audio_path = output_dir / f"{video_name}_audio.wav"

    # 1. Extraire audio
    print("🎵 ÉTAPE 1: Extraction audio")
    print("-" * 70)
    if not extract_audio_from_video(video_path, str(audio_path)):
        sys.exit(1)

    # 2. Vérifier le fichier
    print("\n🔍 ÉTAPE 2: Vérification du fichier audio")
    print("-" * 70)
    if not check_audio_file(str(audio_path)):
        sys.exit(1)

    # 3. Simuler le stream
    print("\n📤 ÉTAPE 3: Simulation stream vers RunPod")
    print("-" * 70)
    if not simulate_stream_to_runpod(str(audio_path)):
        print("❌ Le fichier ne peut pas être streamé!")
        sys.exit(1)

    # Résumé
    print("\n" + "=" * 70)
    print("✅ TOUS LES TESTS PASSÉS!")
    print("=" * 70)
    print(f"📁 Fichier audio: {audio_path}")
    print(f"✅ L'audio peut être envoyé à RunPod sans problème")


if __name__ == '__main__':
    main()
