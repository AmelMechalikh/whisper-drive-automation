#!/usr/bin/env python3
"""
Test génération sous-titres avec texte corrigé depuis Drive
"""
import sys
import os
import re
from pathlib import Path
import logging

# Setup paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent / 'config'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def download_paragraphs_file(base_name: str, drive_manager):
    """Télécharge le fichier _paragraphs_timestamps depuis Drive"""
    logger.info(f"🔍 Recherche du fichier: {base_name}_paragraphs_timestamps")

    # Chercher dans le dossier transcriptions
    import json
    config_path = Path(__file__).parent / 'config' / 'highlight_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)

    transcriptions_folder = config['drive_folders']['transcriptions']

    # Liste les fichiers
    files = drive_manager.list_files_in_folder(
        transcriptions_folder,
        name_pattern=f"{base_name}_paragraphs_timestamps"
    )

    if not files:
        logger.error(f"❌ Fichier non trouvé: {base_name}_paragraphs_timestamps")
        return None

    file_info = files[0]
    logger.info(f"✅ Fichier trouvé: {file_info['name']}")

    # Télécharger
    output_path = Path('./test_subtitles_local') / file_info['name']
    output_path.parent.mkdir(exist_ok=True)

    logger.info(f"📥 Téléchargement...")
    drive_manager.download_file(file_info['id'], str(output_path))

    logger.info(f"✅ Téléchargé: {output_path}")
    return output_path


def extract_segment_text(paragraphs_file: Path, segment_num: int) -> str:
    """Extrait le texte d'un segment depuis le fichier _paragraphs_timestamps"""
    logger.info(f"📖 Extraction du texte du segment S{segment_num}")

    with open(paragraphs_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Chercher entre les balises 🎬 SX 🎬 et 🎬 /SX 🎬
    pattern = rf'🎬 S{segment_num} 🎬(.*?)🎬 /S{segment_num} 🎬'
    match = re.search(pattern, content, re.DOTALL)

    if not match:
        logger.error(f"❌ Segment S{segment_num} non trouvé dans le fichier")
        return None

    text = match.group(1).strip()

    # Nettoyer: enlever les timestamps (XX:XX) et lignes vides
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Enlever les timestamps au début de ligne
        line = re.sub(r'^\(\d+:\d+\)\s*', '', line)
        line = line.strip()
        if line:
            cleaned_lines.append(line)

    cleaned_text = ' '.join(cleaned_lines)

    logger.info(f"✅ Texte extrait: {len(cleaned_text)} caractères")
    logger.info(f"📝 Aperçu: {cleaned_text[:100]}...")

    return cleaned_text


def extract_audio_from_video(video_path: str, output_audio: str) -> bool:
    """Extrait l'audio d'une vidéo"""
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


def align_text_with_audio(audio_path: str, text: str):
    """Aligne le texte corrigé avec l'audio en utilisant WhisperX"""
    logger.info("🎯 Alignement forcé du texte corrigé avec l'audio...")

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

    # Créer un segment artificiel avec le texte complet
    segments = [{
        "start": 0.0,
        "end": len(audio) / 16000,  # durée approximative
        "text": text
    }]

    logger.info(f"📝 Texte à aligner: {len(text)} caractères")

    # Charger le modèle d'alignement
    logger.info("📥 Chargement du modèle d'alignement français...")
    model_a, metadata = whisperx.load_align_model(
        language_code="fr",
        device=device
    )

    # Aligner
    logger.info("⚙️  Alignement en cours...")
    result_aligned = whisperx.align(
        segments,
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

    logger.info(f"✅ Alignement terminé: {len(words)} mots alignés")

    del model_a
    return words


def generate_ass_subtitle(words: list, output_path: str, video_duration: float):
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
    if len(sys.argv) < 4:
        print("Usage: python test_subtitle_with_corrected_text.py <base_name> <segment_num> <video_path>")
        print("Exemple: python test_subtitle_with_corrected_text.py 'Copie de Seance 3 jour 1' 9 ~/Downloads/S9_4201-4455.mp4")
        sys.exit(1)

    base_name = sys.argv[1]
    segment_num = int(sys.argv[2])
    video_path = sys.argv[3]

    if not os.path.exists(video_path):
        logger.error(f"❌ Vidéo introuvable: {video_path}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("🎬 SOUS-TITRES AVEC TEXTE CORRIGÉ")
    logger.info("=" * 70)
    logger.info(f"📄 Base: {base_name}")
    logger.info(f"🔢 Segment: S{segment_num}")
    logger.info(f"📹 Vidéo: {video_path}")

    # 1. Connexion Drive
    logger.info("")
    logger.info("🔑 Connexion à Drive...")
    from drive_manager import DriveManager

    credentials_path = Path(__file__).parent / 'config' / 'credentials.json'
    drive_manager = DriveManager(credentials_path=str(credentials_path))

    # 2. Télécharger le fichier _paragraphs_timestamps
    logger.info("")
    logger.info("📥 Étape 1: Téléchargement du texte corrigé")
    logger.info("-" * 70)
    paragraphs_file = download_paragraphs_file(base_name, drive_manager)

    if not paragraphs_file:
        sys.exit(1)

    # 3. Extraire le texte du segment
    logger.info("")
    logger.info("📖 Étape 2: Extraction du segment")
    logger.info("-" * 70)
    text = extract_segment_text(paragraphs_file, segment_num)

    if not text:
        sys.exit(1)

    # 4. Extraire l'audio
    logger.info("")
    logger.info("🎵 Étape 3: Extraction audio")
    logger.info("-" * 70)
    output_dir = Path('./test_subtitles_local')
    output_dir.mkdir(exist_ok=True)

    video_name = Path(video_path).stem
    audio_path = output_dir / f"{video_name}_audio.wav"

    if not extract_audio_from_video(video_path, str(audio_path)):
        sys.exit(1)

    # 5. Aligner le texte avec l'audio
    logger.info("")
    logger.info("🎯 Étape 4: Alignement forcé")
    logger.info("-" * 70)
    words = align_text_with_audio(str(audio_path), text)

    if not words:
        sys.exit(1)

    # 6. Générer ASS
    logger.info("")
    logger.info("📝 Étape 5: Génération ASS")
    logger.info("-" * 70)
    ass_path = output_dir / f"{video_name}_corrected.ass"

    import subprocess
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
        capture_output=True,
        text=True
    )
    video_duration = float(result.stdout.strip())

    generate_ass_subtitle(words, str(ass_path), video_duration)

    # 7. Brûler dans vidéo
    logger.info("")
    logger.info("🔥 Étape 6: Brûlage dans vidéo")
    logger.info("-" * 70)
    output_video = output_dir / f"{video_name}_with_corrected_subtitles.mp4"

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
