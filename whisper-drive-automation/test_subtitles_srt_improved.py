#!/usr/bin/env python3
"""
Script de test - Solution 2: Améliorer la génération du SRT avec découpage intelligent
"""
import sys
from pathlib import Path
import subprocess
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def format_timestamp(seconds: float) -> str:
    """Convertit secondes en format SRT HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def group_words_intelligently(words: list, max_words: int = 10, min_words: int = 4) -> list:
    """
    Regroupe les mots en segments intelligents selon les ponctuations et pauses

    Args:
        words: Liste de dicts avec 'word', 'start', 'end'
        max_words: Nombre max de mots par segment
        min_words: Nombre min de mots avant de chercher une coupure

    Returns:
        Liste de segments avec 'text', 'start', 'end'
    """
    # Mots qui marquent une pause naturelle
    connector_words = {'et', 'mais', 'donc', 'or', 'car', 'puis', 'alors', 'ainsi', 'ensuite', 'ou', 'ni'}

    segments = []
    current_segment = []

    for i, word_info in enumerate(words):
        word = word_info['word'].strip()
        current_segment.append(word_info)

        should_break = False

        # 1. Si on a atteint le max, on DOIT couper
        if len(current_segment) >= max_words:
            should_break = True

        # 2. Si on a au moins min_words
        elif len(current_segment) >= min_words:
            word_lower = word.lower().rstrip('.,!?;:')
            has_strong_punct = any(p in word for p in '.!?')  # Ponctuation forte
            has_comma = ',' in word

            # Couper sur ponctuation forte
            if has_strong_punct:
                should_break = True
            # Couper sur virgule si on a assez de mots
            elif has_comma and len(current_segment) >= min_words + 1:
                should_break = True
            # Ne PAS couper si le mot actuel est une conjonction
            elif word_lower not in connector_words:
                # Regarder le prochain mot
                if i + 1 < len(words):
                    next_word = words[i + 1]['word'].strip().lower().rstrip('.,!?;:')
                    # Si le prochain mot est une conjonction, couper maintenant
                    if next_word in connector_words:
                        should_break = True

        # 3. Dernier mot
        if i == len(words) - 1:
            should_break = True

        if should_break and current_segment:
            text = ' '.join([w['word'] for w in current_segment])
            segments.append({
                'text': text,
                'start': current_segment[0]['start'],
                'end': current_segment[-1]['end']
            })
            current_segment = []

    return segments

def generate_srt_improved(video_path: str, output_srt: str) -> bool:
    """
    Génère un SRT avec découpage intelligent (word timestamps + regroupement)
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        logger.error("❌ faster-whisper non installé")
        return False

    # Extraire audio
    audio_path = str(Path(video_path).with_suffix('.wav'))
    if not extract_audio_from_video(video_path, audio_path):
        return False

    try:
        # Charger le modèle Whisper
        logger.info("🔧 Chargement du modèle Whisper...")
        device = "cpu"
        compute_type = "int8"
        model = WhisperModel("base", device=device, compute_type=compute_type)

        # Transcrire AVEC word timestamps
        logger.info("🎤 Transcription avec word timestamps...")
        segments, info = model.transcribe(audio_path, language="fr", word_timestamps=True)
        segments_list = list(segments)

        if not segments_list:
            logger.warning(f"⚠️ Aucun segment transcrit")
            return False

        # Extraire tous les mots avec leurs timestamps
        logger.info("📝 Extraction des mots...")
        all_words = []
        for segment in segments_list:
            if hasattr(segment, 'words') and segment.words:
                for word_info in segment.words:
                    all_words.append({
                        'word': word_info.word.strip(),
                        'start': word_info.start,
                        'end': word_info.end
                    })

        if not all_words:
            logger.warning(f"⚠️ Pas de word timestamps")
            return False

        logger.info(f"✅ {len(all_words)} mots extraits")

        # Regrouper intelligemment
        logger.info("🎯 Regroupement intelligent des mots...")
        intelligent_segments = group_words_intelligently(all_words, max_words=10, min_words=4)

        logger.info(f"✅ {len(intelligent_segments)} segments créés")

        # Générer SRT
        with open(output_srt, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(intelligent_segments, 1):
                start_time = format_timestamp(seg['start'])
                end_time = format_timestamp(seg['end'])
                text = seg['text'].strip()

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n")
                f.write("\n")

        logger.info(f"✅ SRT amélioré généré: {output_srt}")

        # Nettoyer l'audio temporaire
        Path(audio_path).unlink(missing_ok=True)

        return True

    except Exception as e:
        logger.error(f"❌ Erreur génération SRT: {e}")
        import traceback
        logger.error(traceback.format_exc())
        Path(audio_path).unlink(missing_ok=True)
        return False

def main():
    logger.info("=" * 60)
    logger.info("🎬 Test Solution 2: SRT amélioré avec découpage intelligent")
    logger.info("=" * 60)

    # Chemins
    base_dir = Path(__file__).parent / "test_subtitles_local"
    video_path = base_dir / "S9_4201-4455.mp4"
    srt_output = base_dir / "S9_4201-4455_IMPROVED.srt"

    # Vérifier que le fichier existe
    if not video_path.exists():
        logger.error(f"❌ Vidéo non trouvée: {video_path}")
        return 1

    logger.info(f"📹 Vidéo: {video_path}")
    logger.info(f"📝 SRT de sortie: {srt_output}")

    # Générer le SRT amélioré
    if not generate_srt_improved(str(video_path), str(srt_output)):
        return 1

    logger.info("=" * 60)
    logger.info(f"✅ SRT amélioré généré avec succès!")
    logger.info(f"📄 Fichier: {srt_output}")
    logger.info("=" * 60)
    logger.info("\nProchaine étape: utiliser ce SRT avec test_subtitles_local_s9.py")

    return 0

if __name__ == "__main__":
    sys.exit(main())
