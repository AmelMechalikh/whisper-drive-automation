#!/usr/bin/env python3
"""
Test de génération de sous-titres style Instagram avec WhisperX
Version simplifiée sans VAD
"""
import sys
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_audio_from_video(video_path: str, output_audio: str) -> bool:
    """Extrait l'audio d'une vidéo avec ffmpeg"""
    import subprocess

    logger.info(f"🎵 Extraction audio: {video_path}")

    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-vn',  # Pas de vidéo
        '-acodec', 'pcm_s16le',  # WAV 16-bit
        '-ar', '16000',  # 16kHz (optimal pour Whisper)
        '-ac', '1',  # Mono
        '-y',
        output_audio
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✅ Audio extrait: {output_audio}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur extraction audio: {e.stderr.decode()}")
        return False


def transcribe_and_align(audio_path: str):
    """
    Transcrit et aligne avec faster-whisper + WhisperX alignment
    """
    logger.info("🔤 Transcription avec faster-whisper...")

    try:
        from faster_whisper import WhisperModel
        import whisperx
        import torch
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return None

    device = "cpu"  # ou "cuda" si GPU
    compute_type = "int8"

    logger.info(f"🖥️  Device: {device}")

    # 1. Transcrire avec faster-whisper (pas de VAD)
    logger.info("📥 Chargement faster-whisper...")
    model = WhisperModel("base", device=device, compute_type=compute_type)

    logger.info("🎤 Transcription...")
    segments, info = model.transcribe(audio_path, language="fr", word_timestamps=True)

    # Convertir les segments en format liste
    segments_list = []
    for segment in segments:
        seg_dict = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text,
            "words": []
        }
        for word in segment.words:
            seg_dict["words"].append({
                "word": word.word,
                "start": word.start,
                "end": word.end
            })
        segments_list.append(seg_dict)

    logger.info(f"✅ Transcription: {len(segments_list)} segments")

    # 2. Aligner avec WhisperX pour plus de précision
    logger.info("🎯 Alignement forcé avec WhisperX...")

    # Charger audio avec whisperx
    audio = whisperx.load_audio(audio_path)

    # Charger modèle d'alignement
    try:
        model_a, metadata = whisperx.load_align_model(
            language_code="fr",
            device=device
        )

        # Aligner
        result_aligned = whisperx.align(
            segments_list,
            model_a,
            metadata,
            audio,
            device,
            return_char_alignments=False
        )

        # Extraire les mots
        words = []
        for segment in result_aligned.get("segments", []):
            for word_info in segment.get("words", []):
                words.append({
                    "word": word_info["word"],
                    "start": word_info["start"],
                    "end": word_info["end"]
                })

        logger.info(f"✅ Alignement: {len(words)} mots")

        del model_a
        return words

    except Exception as e:
        logger.warning(f"⚠️ Alignement WhisperX échoué: {e}")
        logger.info("📝 Utilisation timestamps de faster-whisper...")

        # Fallback: utiliser les timestamps de faster-whisper
        words = []
        for segment in segments_list:
            for word in segment["words"]:
                words.append(word)

        return words


def generate_ass_subtitle(words: list, output_path: str, video_duration: float):
    """
    Génère un fichier ASS avec style Instagram
    """
    logger.info(f"📝 Génération ASS: {output_path}")

    # Header ASS
    ass_content = """[Script Info]
Title: Instagram Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Instagram,Arial,80,&H00000000,&H000000FF,&H00FFFFFF,&H00FFFFFF,-1,0,0,0,100,100,0,0,3,8,0,2,10,10,180,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Grouper par chunks de 3 mots
    chunk_size = 3
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            text = " ".join([w["word"] for w in chunk_words])
            start_time = chunk_words[0]["start"]
            end_time = chunk_words[-1]["end"]
            chunks.append({
                "text": text,
                "start": start_time,
                "end": end_time
            })

    logger.info(f"📦 {len(chunks)} chunks créés")

    # Ajouter dialogues
    for chunk in chunks:
        start_str = seconds_to_ass_time(chunk["start"])
        end_str = seconds_to_ass_time(chunk["end"])
        text = chunk["text"].replace("\n", " ")
        ass_content += f"Dialogue: 0,{start_str},{end_str},Instagram,,0,0,0,,{text}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    logger.info(f"✅ ASS créé: {output_path}")


def seconds_to_ass_time(seconds: float) -> str:
    """Convertit secondes en format ASS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def burn_subtitles_into_video(video_path: str, ass_path: str, output_path: str) -> bool:
    """Brûle les sous-titres dans la vidéo"""
    import subprocess

    logger.info(f"🔥 Brûlage sous-titres...")

    video_path_abs = os.path.abspath(video_path)
    ass_path_abs = os.path.abspath(ass_path)
    output_path_abs = os.path.abspath(output_path)

    ass_path_filter = ass_path_abs.replace('\\', '/').replace(':', '\\:')

    cmd = [
        'ffmpeg',
        '-i', video_path_abs,
        '-vf', f"subtitles='{ass_path_filter}'",
        '-c:a', 'copy',
        '-y',
        output_path_abs
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✅ Vidéo créée: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur: {e.stderr.decode()}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_subtitle_generation_simple.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]

    if not os.path.exists(video_path):
        logger.error(f"❌ Fichier introuvable: {video_path}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("🎬 TEST SOUS-TITRES INSTAGRAM (VERSION SIMPLE)")
    logger.info("=" * 70)
    logger.info(f"📹 Vidéo: {video_path}")

    output_dir = Path('./test_subtitles_local')
    output_dir.mkdir(exist_ok=True)

    video_name = Path(video_path).stem

    # 1. Extraire audio
    audio_path = output_dir / f"{video_name}_audio.wav"
    if not extract_audio_from_video(video_path, str(audio_path)):
        sys.exit(1)

    # 2. Transcrire et aligner
    logger.info("")
    logger.info("🎯 Étape 2: Transcription + Alignement")
    logger.info("-" * 70)
    words = transcribe_and_align(str(audio_path))

    if not words:
        logger.error("❌ Échec transcription")
        sys.exit(1)

    # 3. Générer ASS
    logger.info("")
    logger.info("📝 Étape 3: Génération ASS")
    logger.info("-" * 70)
    ass_path = output_dir / f"{video_name}.ass"

    import subprocess
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
        capture_output=True,
        text=True
    )
    video_duration = float(result.stdout.strip())

    generate_ass_subtitle(words, str(ass_path), video_duration)

    # 4. Brûler dans vidéo
    logger.info("")
    logger.info("🔥 Étape 4: Brûlage dans vidéo")
    logger.info("-" * 70)
    output_video = output_dir / f"{video_name}_with_subtitles.mp4"

    if not burn_subtitles_into_video(video_path, str(ass_path), str(output_video)):
        sys.exit(1)

    # Résumé
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ TERMINÉ")
    logger.info("=" * 70)
    logger.info(f"📁 Dossier: {output_dir}")
    logger.info(f"📝 ASS: {ass_path.name}")
    logger.info(f"🎬 Vidéo: {output_video.name}")
    logger.info(f"📊 Mots: {len(words)}")
    logger.info("")
    logger.info(f"🎥 Visionner: open {output_video}")


if __name__ == '__main__':
    main()
