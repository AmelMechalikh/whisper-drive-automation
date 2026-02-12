#!/usr/bin/env python3
"""
Script de test local pour générer les sous-titres sur S9_4201-4455
avec les nouveaux paramètres (5 mots, offset 0.4s, min_duration 0.8s)
"""
import sys
from pathlib import Path
import subprocess
import re
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ajouter le dossier scripts au path
sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

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

def align_segments_with_whisperx(audio_path: str, segments: list) -> list:
    """Aligne chaque segment du SRT mot-par-mot avec WhisperX"""
    try:
        import whisperx
    except ImportError as e:
        logger.error(f"❌ whisperx non installé: {e}")
        return None

    device = "cpu"

    # Charger l'audio
    logger.info("📥 Chargement de l'audio...")
    audio = whisperx.load_audio(audio_path)

    # Convertir segments SRT au format WhisperX
    whisperx_segments = []
    for seg in segments:
        whisperx_segments.append({
            "start": seg['start'],
            "end": seg['end'],
            "text": seg['text']
        })

    logger.info(f"📝 {len(whisperx_segments)} segments SRT à aligner")

    # Charger le modèle d'alignement
    logger.info("🔧 Chargement du modèle d'alignement...")
    model_a, metadata = whisperx.load_align_model(
        language_code="fr",
        device=device
    )

    # Aligner
    logger.info("🎯 Alignement mot-par-mot...")
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

def generate_ass_subtitle_from_srt_segments(segments: list, words: list, output_path: str):
    """
    Génère un fichier ASS en respectant exactement les segments du SRT
    Utilise les mots alignés uniquement pour ajuster les timestamps précis
    """
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

    sync_offset = 0.4  # Délai de synchronisation
    min_duration = 0.8  # Durée minimale

    logger.info(f"📊 Mode: Fidèle au SRT - {len(segments)} segments, sync_offset={sync_offset}s")

    for segment in segments:
        text = segment['text']
        start_time = segment['start'] + sync_offset
        end_time = segment['end'] + sync_offset

        # Assurer une durée minimale
        if (end_time - start_time) < min_duration:
            end_time = start_time + min_duration

        start_str = seconds_to_ass_time(start_time)
        end_str = seconds_to_ass_time(end_time)
        text_clean = text.replace("\n", " ")
        ass_content += f"Dialogue: 0,{start_str},{end_str},Instagram,,0,0,0,,{text_clean}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    logger.info(f"✅ ASS généré avec {len(segments)} segments (fidèle au SRT)")

def generate_ass_subtitle(words: list, output_path: str):
    """Génère un fichier ASS style Instagram avec découpage intelligent"""
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

    # NOUVEAUX PARAMÈTRES
    max_chunk_size = 7  # Maximum 7 mots par chunk
    min_chunk_size = 3  # Minimum 3 mots par chunk
    sync_offset = 0.4  # Délai de synchronisation en secondes
    min_duration = 0.8  # Durée minimale d'affichage en secondes

    # Mots qui marquent une pause naturelle (ne pas les mettre en fin de chunk)
    connector_words = {
        'et', 'mais', 'donc', 'or', 'car',  # Conjonctions de coordination
        'puis', 'alors', 'ainsi', 'ensuite',  # Transitions
        'ou', 'ni',  # Alternatives
    }

    logger.info(f"📊 Paramètres: max={max_chunk_size} mots, min={min_chunk_size}, sync_offset={sync_offset}s")
    logger.info(f"🎯 Découpage intelligent - évite de couper après conjonctions")

    chunks = []
    current_chunk = []

    for i, word_info in enumerate(words):
        word = word_info["word"].strip()
        current_chunk.append(word_info)

        # Vérifier si on doit couper ici
        should_break = False

        # 1. Si on a atteint la taille max, on DOIT couper
        if len(current_chunk) >= max_chunk_size:
            should_break = True

        # 2. Si on a au moins min_chunk_size mots
        elif len(current_chunk) >= min_chunk_size:
            # Vérifier le mot actuel et le suivant
            word_lower = word.lower().rstrip('.,!?;:')
            has_punct = any(p in word for p in '.,!?;:')

            # Couper si ponctuation forte
            if has_punct:
                should_break = True
            # Ne PAS couper si le mot actuel est une conjonction (et, mais, donc...)
            # SAUF si on est au max ou si c'est le dernier mot
            elif word_lower not in connector_words:
                # Regarder le prochain mot
                if i + 1 < len(words):
                    next_word = words[i + 1]["word"].strip().lower().rstrip('.,!?;:')
                    # Si le prochain mot est une conjonction, couper maintenant
                    if next_word in connector_words:
                        should_break = True

        # 3. Dernier mot
        if i == len(words) - 1:
            should_break = True

        if should_break and current_chunk:
            text = " ".join([w["word"] for w in current_chunk])
            start_time = current_chunk[0]["start"] + sync_offset
            end_time = current_chunk[-1]["end"] + sync_offset

            # Assurer une durée minimale
            if (end_time - start_time) < min_duration:
                end_time = start_time + min_duration

            chunks.append({
                "text": text,
                "start": start_time,
                "end": end_time
            })

            current_chunk = []

    for chunk in chunks:
        start_str = seconds_to_ass_time(chunk["start"])
        end_str = seconds_to_ass_time(chunk["end"])
        text = chunk["text"].replace("\n", " ")
        ass_content += f"Dialogue: 0,{start_str},{end_str},Instagram,,0,0,0,,{text}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    logger.info(f"✅ ASS généré avec {len(chunks)} chunks")

def seconds_to_ass_time(seconds: float) -> str:
    """Convertit secondes en format ASS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

def burn_subtitles_into_video(video_path: str, ass_path: str, output_path: str) -> bool:
    """Brûle les sous-titres dans la vidéo"""
    import os
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
        logger.info("🔥 Brûlage des sous-titres...")
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"✅ Vidéo avec sous-titres créée: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur brûlage sous-titres: {e.stderr.decode()}")
        return False

def main():
    logger.info("=" * 60)
    logger.info("🎬 Test sous-titres S9_4201-4455")
    logger.info("=" * 60)

    # Chemins
    base_dir = Path(__file__).parent / "test_subtitles_local"
    video_path = base_dir / "S9_4201-4455.mp4"
    srt_path = base_dir / "S9_4201-4455_IMPROVED.srt"  # Utiliser le SRT amélioré
    audio_path = base_dir / "S9_4201-4455_test_audio.wav"
    ass_path = base_dir / "S9_4201-4455_test.ass"
    output_path = base_dir / "S9_4201-4455_TEST_OUTPUT.mp4"

    # Vérifier que les fichiers existent
    if not video_path.exists():
        logger.error(f"❌ Vidéo non trouvée: {video_path}")
        return 1

    if not srt_path.exists():
        logger.error(f"❌ SRT non trouvé: {srt_path}")
        return 1

    logger.info(f"📹 Vidéo: {video_path}")
    logger.info(f"📝 SRT: {srt_path}")

    # 1. Extraire l'audio
    if not extract_audio_from_video(str(video_path), str(audio_path)):
        return 1

    # 2. Parser le SRT
    logger.info("📖 Parsing du SRT...")
    segments = parse_srt(str(srt_path))
    logger.info(f"📝 {len(segments)} segments SRT")

    # 3. Aligner avec WhisperX
    words = align_segments_with_whisperx(str(audio_path), segments)
    if not words:
        logger.error("❌ Échec de l'alignement")
        return 1

    # 4. Générer ASS (fidèle au SRT, sans recouper)
    logger.info("📝 Génération du fichier ASS...")
    generate_ass_subtitle_from_srt_segments(segments, words, str(ass_path))

    # 5. Brûler les sous-titres
    if not burn_subtitles_into_video(str(video_path), str(ass_path), str(output_path)):
        return 1

    logger.info("=" * 60)
    logger.info(f"✅ SUCCÈS! Vidéo de sortie: {output_path}")
    logger.info("=" * 60)

    # Nettoyer l'audio temporaire
    audio_path.unlink(missing_ok=True)

    return 0

if __name__ == "__main__":
    sys.exit(main())
