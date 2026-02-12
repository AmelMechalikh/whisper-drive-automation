#!/usr/bin/env python3
"""
Test local du système de sous-titrage avec RunPod
Permet de tester sans redéployer sur Cloud Run

Usage:
    python test_runpod_subtitles_local.py <video_path> [srt_path]

Si srt_path n'est pas fourni, un SRT sera généré automatiquement.
"""
import sys
import os
import json
import logging
import subprocess
import re
from pathlib import Path

# Ajouter les chemins au PYTHONPATH
current_dir = Path(__file__).parent
src_path = str(current_dir / 'src')
config_path = str(current_dir / 'config')
sys.path.insert(0, src_path)
sys.path.insert(0, config_path)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# FONCTIONS UTILITAIRES (copiées du worker)
# ============================================================================

def parse_srt(srt_path: str) -> list:
    """Parse un fichier SRT et retourne la liste des segments"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

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

    return segments


def parse_timestamp(ts: str) -> float:
    """Convertit un timestamp SRT (HH:MM:SS,mmm) en secondes"""
    match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3})', ts)
    if not match:
        return 0.0

    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000.0


def extract_audio_from_video(video_path: str, output_audio: str) -> bool:
    """Extrait l'audio d'une vidéo"""
    logger.info(f"🎵 Extraction audio: {video_path}")

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
        logger.info(f"✅ Audio extrait: {output_audio}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur extraction audio: {e.stderr.decode() if e.stderr else 'Erreur inconnue'}")
        return False


def generate_srt_with_runpod(audio_path: str, backend) -> list:
    """Génère un SRT en utilisant RunPod pour la transcription"""
    logger.info("🎤 Génération SRT avec RunPod...")

    try:
        # Utiliser le backend pour transcrire
        result = backend.transcribe_audio(
            audio_path=audio_path,
            language="fr"
        )

        segments = result.get("segments", [])
        logger.info(f"✅ {len(segments)} segments transcrits")

        return segments

    except Exception as e:
        logger.error(f"❌ Erreur transcription: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def align_segments_with_backend(audio_path: str, segments: list, backend) -> list:
    """
    Aligne chaque segment du SRT mot-par-mot en utilisant le backend RunPod
    Retourne une liste de tous les mots avec timestamps
    """
    logger.info(f"🎯 Alignement mot-par-mot avec {backend.get_backend_name()}...")

    try:
        aligned_segments = backend.align_segments(
            audio_path=audio_path,
            segments=segments,
            language="fr"
        )

        # Extraire les mots de tous les segments alignés
        all_words = []
        for segment in aligned_segments:
            for word_info in segment.get("words", []):
                all_words.append({
                    "word": word_info["word"],
                    "start": word_info["start"],
                    "end": word_info["end"]
                })

        logger.info(f"✅ {len(all_words)} mots alignés")
        return all_words

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'alignement: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def generate_ass_subtitle(words: list, output_path: str):
    """Génère un fichier ASS style Instagram"""
    logger.info(f"📝 Génération ASS: {output_path}")

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

    # Chunks de 5 mots
    chunk_size = 5
    sync_offset = 0.4
    min_duration = 0.8
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            text = " ".join([w["word"] for w in chunk_words])
            start_time = chunk_words[0]["start"] + sync_offset
            end_time = chunk_words[-1]["end"] + sync_offset

            if (end_time - start_time) < min_duration:
                end_time = start_time + min_duration

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
        result = subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✅ Vidéo créée: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur: {e.stderr.decode() if e.stderr else 'Erreur inconnue'}")
        return False


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main():
    """Test local du système de sous-titrage RunPod"""

    if len(sys.argv) < 2:
        print("Usage: python test_runpod_subtitles_local.py <video_path> [srt_path]")
        print("")
        print("Si srt_path n'est pas fourni, un SRT sera généré avec RunPod.")
        sys.exit(1)

    video_path = sys.argv[1]
    srt_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(video_path):
        logger.error(f"❌ Fichier vidéo introuvable: {video_path}")
        sys.exit(1)

    if srt_path and not os.path.exists(srt_path):
        logger.error(f"❌ Fichier SRT introuvable: {srt_path}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("🧪 TEST LOCAL - SOUS-TITRAGE AVEC RUNPOD")
    logger.info("=" * 70)
    logger.info(f"📹 Vidéo: {video_path}")
    if srt_path:
        logger.info(f"📝 SRT fourni: {srt_path}")
    else:
        logger.info(f"📝 SRT: sera généré automatiquement")

    # Charger la configuration
    try:
        from transcription_backends import get_transcription_backend

        config_file = current_dir / 'config' / 'highlight_config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)

        backend = get_transcription_backend(config)
        logger.info(f"🔧 Backend: {backend.get_backend_name()}")

    except Exception as e:
        logger.error(f"❌ Erreur chargement backend: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Créer dossier de sortie
    output_dir = Path('./test_subtitles_local')
    output_dir.mkdir(exist_ok=True)
    video_name = Path(video_path).stem

    # 1. Extraire audio
    logger.info("")
    logger.info("🎵 ÉTAPE 1: Extraction audio")
    logger.info("-" * 70)
    audio_path = output_dir / f"{video_name}_audio.wav"
    if not extract_audio_from_video(video_path, str(audio_path)):
        sys.exit(1)

    # 2. Obtenir les segments (soit du SRT, soit par transcription)
    logger.info("")
    logger.info("📝 ÉTAPE 2: Obtention des segments")
    logger.info("-" * 70)

    if srt_path:
        logger.info(f"📖 Lecture du SRT: {srt_path}")
        segments = parse_srt(srt_path)
        logger.info(f"✅ {len(segments)} segments chargés")
    else:
        segments = generate_srt_with_runpod(str(audio_path), backend)
        if not segments:
            logger.error("❌ Échec génération SRT")
            sys.exit(1)

        # Sauvegarder le SRT généré
        srt_output = output_dir / f"{video_name}_generated.srt"
        with open(srt_output, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                start = seg['start']
                end = seg['end']
                text = seg['text']

                start_str = f"{int(start//3600):02d}:{int((start%3600)//60):02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
                end_str = f"{int(end//3600):02d}:{int((end%3600)//60):02d}:{int(end%60):02d},{int((end%1)*1000):03d}"

                f.write(f"{i}\n{start_str} --> {end_str}\n{text}\n\n")

        logger.info(f"💾 SRT sauvegardé: {srt_output}")

    # 3. Aligner mot-par-mot avec RunPod
    logger.info("")
    logger.info("🎯 ÉTAPE 3: Alignement mot-par-mot")
    logger.info("-" * 70)
    words = align_segments_with_backend(str(audio_path), segments, backend)

    if not words:
        logger.error("❌ Échec alignement")
        sys.exit(1)

    # 4. Générer ASS
    logger.info("")
    logger.info("📄 ÉTAPE 4: Génération ASS")
    logger.info("-" * 70)
    ass_path = output_dir / f"{video_name}.ass"
    generate_ass_subtitle(words, str(ass_path))

    # 5. Brûler sous-titres
    logger.info("")
    logger.info("🔥 ÉTAPE 5: Brûlage sous-titres")
    logger.info("-" * 70)
    output_video = output_dir / f"{video_name}_SUBTITLED.mp4"

    if not burn_subtitles_into_video(video_path, str(ass_path), str(output_video)):
        sys.exit(1)

    # Résumé
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ TEST TERMINÉ")
    logger.info("=" * 70)
    logger.info(f"📁 Dossier: {output_dir}")
    logger.info(f"🎵 Audio: {audio_path.name}")
    if not srt_path:
        logger.info(f"📝 SRT généré: {srt_output.name}")
    logger.info(f"📄 ASS: {ass_path.name}")
    logger.info(f"🎬 Vidéo: {output_video.name}")
    logger.info(f"📊 Mots alignés: {len(words)}")
    logger.info("")
    logger.info(f"🎥 Visionner: open '{output_video}'")


if __name__ == '__main__':
    main()
