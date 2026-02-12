#!/usr/bin/env python3
"""
Test de génération de sous-titres style Instagram avec WhisperX
Usage: python test_subtitle_generation.py <video_path> <text>
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


def align_text_with_whisperx(audio_path: str, text: str):
    """
    Aligne le texte avec l'audio en utilisant WhisperX
    Retourne une liste de mots avec timestamps
    """
    logger.info("🔤 Chargement de WhisperX...")

    try:
        import whisperx
        import torch

        # Fix pour torch 2.8+ : autoriser le chargement non-sécurisé des modèles pyannote
        torch.serialization.add_safe_globals([
            'omegaconf.listconfig.ListConfig',
            'omegaconf.dictconfig.DictConfig'
        ])
    except ImportError:
        logger.error("❌ WhisperX non installé. Install: pip install whisperx")
        return None

    # Déterminer le device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"

    logger.info(f"🖥️  Device: {device}")
    logger.info(f"📊 Compute type: {compute_type}")

    # 1. Charger le modèle de transcription
    logger.info("📥 Chargement du modèle Whisper...")
    model = whisperx.load_model("base", device, compute_type=compute_type)

    # 2. Transcrire pour obtenir les segments de base
    logger.info("🎤 Transcription de l'audio...")
    audio = whisperx.load_audio(audio_path)
    result = model.transcribe(audio, batch_size=16)

    logger.info(f"✅ Transcription: {len(result['segments'])} segments")

    # 3. Aligner avec le modèle d'alignement
    logger.info("🎯 Alignement forcé avec WhisperX...")

    # Détecter la langue (ou utiliser celle de la transcription)
    language_code = result.get("language", "fr")
    logger.info(f"🌍 Langue détectée: {language_code}")

    # Charger le modèle d'alignement
    model_a, metadata = whisperx.load_align_model(
        language_code=language_code,
        device=device
    )

    # Faire l'alignement
    result_aligned = whisperx.align(
        result["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False
    )

    # 4. Extraire les mots avec timestamps
    words = []
    for segment in result_aligned.get("segments", []):
        for word_info in segment.get("words", []):
            words.append({
                "word": word_info["word"],
                "start": word_info["start"],
                "end": word_info["end"]
            })

    logger.info(f"✅ Alignement terminé: {len(words)} mots")

    # Nettoyer
    del model
    del model_a
    if device == "cuda":
        torch.cuda.empty_cache()

    return words


def generate_ass_subtitle(words: list, output_path: str, video_duration: float):
    """
    Génère un fichier ASS avec style Instagram (Indivisible Bold, fond blanc, texte noir)
    """
    logger.info(f"📝 Génération ASS: {output_path}")

    # Header ASS avec style Instagram
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

    # Grouper les mots par chunks de 2-4 mots pour style dynamique Instagram
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

    logger.info(f"📦 {len(chunks)} chunks créés (groups de ~{chunk_size} mots)")

    # Ajouter les dialogues
    for chunk in chunks:
        start_str = seconds_to_ass_time(chunk["start"])
        end_str = seconds_to_ass_time(chunk["end"])
        text = chunk["text"].replace("\n", " ")
        ass_content += f"Dialogue: 0,{start_str},{end_str},Instagram,,0,0,0,,{text}\n"

    # Écrire le fichier
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    logger.info(f"✅ Fichier ASS créé: {output_path}")


def seconds_to_ass_time(seconds: float) -> str:
    """Convertit secondes en format ASS: H:MM:SS.CS (centiseconds)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def burn_subtitles_into_video(video_path: str, ass_path: str, output_path: str) -> bool:
    """Brûle les sous-titres ASS dans la vidéo avec ffmpeg"""
    import subprocess

    logger.info(f"🔥 Brûlage des sous-titres dans la vidéo...")

    # Convertir les chemins absolus pour ffmpeg
    video_path_abs = os.path.abspath(video_path)
    ass_path_abs = os.path.abspath(ass_path)
    output_path_abs = os.path.abspath(output_path)

    # Échapper les caractères spéciaux pour le filtre subtitles
    # Windows/Unix: remplacer \ par / et échapper :
    ass_path_filter = ass_path_abs.replace('\\', '/').replace(':', '\\:')

    cmd = [
        'ffmpeg',
        '-i', video_path_abs,
        '-vf', f"subtitles='{ass_path_filter}'",
        '-c:a', 'copy',  # Copier l'audio sans réencodage
        '-y',
        output_path_abs
    ]

    logger.info(f"🎬 Commande ffmpeg: {' '.join(cmd)}")

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✅ Vidéo avec sous-titres créée: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur brûlage sous-titres: {e.stderr.decode()}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_subtitle_generation.py <video_path>")
        print("Exemple: python test_subtitle_generation.py ~/Downloads/S9_4201-4455.mp4")
        sys.exit(1)

    video_path = sys.argv[1]

    if not os.path.exists(video_path):
        logger.error(f"❌ Fichier vidéo introuvable: {video_path}")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("🎬 TEST GÉNÉRATION SOUS-TITRES INSTAGRAM")
    logger.info("=" * 70)
    logger.info(f"📹 Vidéo: {video_path}")

    # Créer dossier de sortie
    output_dir = Path('./test_subtitles_local')
    output_dir.mkdir(exist_ok=True)

    video_name = Path(video_path).stem

    # 1. Extraire l'audio
    audio_path = output_dir / f"{video_name}_audio.wav"
    if not extract_audio_from_video(video_path, str(audio_path)):
        logger.error("❌ Échec extraction audio")
        sys.exit(1)

    # 2. Aligner avec WhisperX
    logger.info("")
    logger.info("🎯 Étape 2: Alignement avec WhisperX")
    logger.info("-" * 70)
    words = align_text_with_whisperx(str(audio_path), "")

    if not words:
        logger.error("❌ Échec alignement WhisperX")
        sys.exit(1)

    # 3. Générer ASS
    logger.info("")
    logger.info("📝 Étape 3: Génération fichier ASS")
    logger.info("-" * 70)
    ass_path = output_dir / f"{video_name}.ass"

    # Calculer durée vidéo
    import subprocess
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
        capture_output=True,
        text=True
    )
    video_duration = float(result.stdout.strip())

    generate_ass_subtitle(words, str(ass_path), video_duration)

    # 4. Brûler dans la vidéo
    logger.info("")
    logger.info("🔥 Étape 4: Brûlage sous-titres dans vidéo")
    logger.info("-" * 70)
    output_video = output_dir / f"{video_name}_with_subtitles.mp4"

    if not burn_subtitles_into_video(video_path, str(ass_path), str(output_video)):
        logger.error("❌ Échec brûlage sous-titres")
        sys.exit(1)

    # Résumé
    logger.info("")
    logger.info("=" * 70)
    logger.info("✅ GÉNÉRATION TERMINÉE")
    logger.info("=" * 70)
    logger.info(f"📁 Dossier de sortie: {output_dir}")
    logger.info(f"📝 Fichier ASS: {ass_path.name}")
    logger.info(f"🎬 Vidéo avec sous-titres: {output_video.name}")
    logger.info(f"📊 Mots alignés: {len(words)}")
    logger.info("")
    logger.info("🎥 Pour visionner:")
    logger.info(f"   open {output_video}")


if __name__ == '__main__':
    main()
