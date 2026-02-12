#!/usr/bin/env python3
"""
Étape 1: Générer un SRT automatique pour un segment vidéo
Le user pourra ensuite le corriger manuellement
"""
import sys
import os
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_audio: str) -> bool:
    """Extrait l'audio de la vidéo"""
    import subprocess

    logger.info(f"🎵 Extraction audio...")

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
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✅ Audio extrait")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur: {e.stderr.decode()}")
        return False


def transcribe_to_srt(audio_path: str, output_srt: str):
    """Transcrit l'audio et génère un SRT"""
    logger.info("🎤 Transcription avec faster-whisper...")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.error("❌ faster-whisper non installé")
        return False

    device = "cpu"
    compute_type = "int8"

    logger.info(f"🖥️  Device: {device}")
    logger.info("📥 Chargement du modèle...")

    model = WhisperModel("base", device=device, compute_type=compute_type)

    logger.info("⚙️  Transcription en cours...")
    segments, info = model.transcribe(audio_path, language="fr", word_timestamps=False)

    # Convertir en liste
    segments_list = list(segments)
    logger.info(f"✅ Transcription: {len(segments_list)} segments")

    # Générer SRT
    logger.info("📝 Génération du SRT...")

    with open(output_srt, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments_list, 1):
            start_time = format_timestamp(segment.start)
            end_time = format_timestamp(segment.end)
            text = segment.text.strip()

            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{text}\n")
            f.write("\n")

    logger.info(f"✅ SRT créé: {output_srt}")
    logger.info(f"📊 {len(segments_list)} segments")

    return True


def format_timestamp(seconds: float) -> str:
    """Convertit secondes en format SRT: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python step1_generate_srt.py <video_path>")
        print("Exemple: python step1_generate_srt.py ~/Downloads/S9_4201-4455.mp4")
        sys.exit(1)

    video_path = sys.argv[1]

    if not os.path.exists(video_path):
        logger.error(f"❌ Vidéo introuvable: {video_path}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("📝 ÉTAPE 1: GÉNÉRATION SRT")
    logger.info("=" * 70)
    logger.info(f"📹 Vidéo: {video_path}")

    # Créer dossier de sortie
    output_dir = Path('./test_subtitles_local')
    output_dir.mkdir(exist_ok=True)

    video_name = Path(video_path).stem

    # 1. Extraire audio
    audio_path = output_dir / f"{video_name}_audio.wav"
    if not extract_audio(video_path, str(audio_path)):
        sys.exit(1)

    # 2. Transcrire et générer SRT
    logger.info("")
    logger.info("📝 Transcription et génération SRT")
    logger.info("-" * 70)

    srt_path = output_dir / f"{video_name}_AUTO.srt"

    if not transcribe_to_srt(str(audio_path), str(srt_path)):
        sys.exit(1)

    # Résumé
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ ÉTAPE 1 TERMINÉE")
    logger.info("=" * 70)
    logger.info(f"📁 Fichier SRT: {srt_path}")
    logger.info("")
    logger.info("📝 PROCHAINES ÉTAPES:")
    logger.info(f"   1. Ouvrir et corriger: {srt_path}")
    logger.info(f"   2. Sauvegarder sous: {output_dir}/{video_name}_CORRECTED.srt")
    logger.info(f"   3. Lancer: python step2_align_from_srt.py {video_path} {output_dir}/{video_name}_CORRECTED.srt")


if __name__ == '__main__':
    main()
