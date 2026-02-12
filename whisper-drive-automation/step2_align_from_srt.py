#!/usr/bin/env python3
"""
Étape 2: Aligner le SRT corrigé mot-par-mot et générer sous-titres Instagram
"""
import sys
import os
import re
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_srt(srt_path: str) -> list:
    """Parse un fichier SRT et retourne la liste des segments"""
    logger.info(f"📖 Lecture du SRT: {srt_path}")

    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern pour parser les segments SRT
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)

    segments = []
    for match in matches:
        num, start_str, end_str, text = match
        segments.append({
            'num': int(num),
            'start': parse_timestamp(start_str),
            'end': parse_timestamp(end_str),
            'text': text.strip()
        })

    logger.info(f"✅ {len(segments)} segments trouvés")
    return segments


def parse_timestamp(ts: str) -> float:
    """Convertit un timestamp SRT (HH:MM:SS,mmm) en secondes"""
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', ts)
    if not match:
        return 0.0

    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000.0


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


def align_segments_with_whisperx(audio_path: str, segments: list) -> list:
    """
    Aligne chaque segment du SRT mot-par-mot avec WhisperX
    Retourne une liste de tous les mots avec timestamps
    """
    logger.info("🎯 Alignement mot-par-mot avec WhisperX...")

    try:
        import whisperx
        import torch
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return None

    device = "cpu"
    logger.info(f"🖥️  Device: {device}")

    # Charger l'audio
    audio = whisperx.load_audio(audio_path)

    # Convertir segments SRT au format WhisperX
    whisperx_segments = []
    for seg in segments:
        whisperx_segments.append({
            "start": seg['start'],
            "end": seg['end'],
            "text": seg['text']
        })

    logger.info(f"📝 {len(whisperx_segments)} segments à aligner")

    # Charger le modèle d'alignement
    logger.info("📥 Chargement du modèle d'alignement français...")
    model_a, metadata = whisperx.load_align_model(
        language_code="fr",
        device=device
    )

    # Aligner
    logger.info("⚙️  Alignement en cours...")
    result_aligned = whisperx.align(
        whisperx_segments,
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False
    )

    # Extraire les mots
    all_words = []
    for segment in result_aligned.get("segments", []):
        for word_info in segment.get("words", []):
            all_words.append({
                "word": word_info["word"],
                "start": word_info["start"],
                "end": word_info["end"]
            })

    logger.info(f"✅ {len(all_words)} mots alignés")

    del model_a
    return all_words


def generate_ass_subtitle(words: list, output_path: str):
    """Génère un fichier ASS style Instagram"""
    logger.info(f"📝 Génération ASS...")

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

    # Chunks de 3 mots
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

    for chunk in chunks:
        start_str = seconds_to_ass_time(chunk["start"])
        end_str = seconds_to_ass_time(chunk["end"])
        text = chunk["text"].replace("\n", " ")
        ass_content += f"Dialogue: 0,{start_str},{end_str},Instagram,,0,0,0,,{text}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    logger.info(f"✅ ASS créé")


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
        logger.info(f"✅ Vidéo créée")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur: {e.stderr.decode()}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python step2_align_from_srt.py <video_path> <corrected_srt>")
        print("Exemple: python step2_align_from_srt.py ~/Downloads/S9_4201-4455.mp4 ./test_subtitles_local/S9_4201-4455_CORRECTED.srt")
        sys.exit(1)

    video_path = sys.argv[1]
    srt_path = sys.argv[2]

    if not os.path.exists(video_path):
        logger.error(f"❌ Vidéo introuvable: {video_path}")
        sys.exit(1)

    if not os.path.exists(srt_path):
        logger.error(f"❌ SRT introuvable: {srt_path}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("🎯 ÉTAPE 2: ALIGNEMENT DEPUIS SRT CORRIGÉ")
    logger.info("=" * 70)
    logger.info(f"📹 Vidéo: {video_path}")
    logger.info(f"📝 SRT: {srt_path}")

    output_dir = Path('./test_subtitles_local')
    output_dir.mkdir(exist_ok=True)

    video_name = Path(video_path).stem

    # 1. Parser le SRT
    logger.info("")
    logger.info("📖 Étape 1: Lecture du SRT")
    logger.info("-" * 70)
    segments = parse_srt(srt_path)

    if not segments:
        logger.error("❌ Aucun segment trouvé dans le SRT")
        sys.exit(1)

    # 2. Extraire audio
    logger.info("")
    logger.info("🎵 Étape 2: Extraction audio")
    logger.info("-" * 70)
    audio_path = output_dir / f"{video_name}_audio.wav"

    if not extract_audio(video_path, str(audio_path)):
        sys.exit(1)

    # 3. Aligner mot-par-mot
    logger.info("")
    logger.info("🎯 Étape 3: Alignement mot-par-mot")
    logger.info("-" * 70)
    words = align_segments_with_whisperx(str(audio_path), segments)

    if not words:
        sys.exit(1)

    # 4. Générer ASS
    logger.info("")
    logger.info("📝 Étape 4: Génération ASS")
    logger.info("-" * 70)
    ass_path = output_dir / f"{video_name}_FINAL.ass"

    generate_ass_subtitle(words, str(ass_path))

    # 5. Brûler dans vidéo
    logger.info("")
    logger.info("🔥 Étape 5: Brûlage dans vidéo")
    logger.info("-" * 70)
    output_video = output_dir / f"{video_name}_FINAL.mp4"

    if not burn_subtitles_into_video(video_path, str(ass_path), str(output_video)):
        sys.exit(1)

    # Résumé
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ ÉTAPE 2 TERMINÉE")
    logger.info("=" * 70)
    logger.info(f"📁 Dossier: {output_dir}")
    logger.info(f"📝 ASS: {ass_path.name}")
    logger.info(f"🎬 Vidéo: {output_video.name}")
    logger.info(f"📊 Mots: {len(words)}")
    logger.info("")
    logger.info(f"🎥 Visionner: open {output_video}")


if __name__ == '__main__':
    main()
