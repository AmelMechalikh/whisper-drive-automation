#!/usr/bin/env python3
"""
Worker VM pour générer les sous-titres brûlés
Vérifie périodiquement le dossier queue_subtitles dans Google Drive
"""
import os
import json
import time
import logging
import tempfile
import re
import subprocess
from pathlib import Path
from datetime import datetime
import sys

# Ajouter les chemins au PYTHONPATH
current_dir = Path(__file__).parent
src_path = str(current_dir / 'src')
config_path = str(current_dir / 'config')
sys.path.insert(0, src_path)
sys.path.insert(0, config_path)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# FONCTIONS D'ALIGNEMENT ET DE SOUS-TITRAGE
# ============================================================================

def parse_srt(srt_path: str) -> list:
    """Parse un fichier SRT et retourne la liste des segments"""
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
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur extraction audio: {e.stderr.decode() if e.stderr else 'Erreur inconnue'}")
        return False


def align_segments_with_backend(audio_path: str, segments: list, backend) -> list:
    """
    Aligne chaque segment du SRT mot-par-mot en utilisant le backend configuré
    Retourne une liste de tous les mots avec timestamps
    """
    try:
        # Convertir segments SRT au format attendu par le backend
        backend_segments = []
        for seg in segments:
            backend_segments.append({
                "start": seg['start'],
                "end": seg['end'],
                "text": seg['text']
            })

        # Utiliser le backend pour aligner
        aligned_segments = backend.align_segments(
            audio_path=audio_path,
            segments=backend_segments,
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

        return all_words

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'alignement: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def generate_ass_subtitle(words: list, output_path: str):
    """Génère un fichier ASS style Instagram"""
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

    # Chunks de 5 mots (plus lisible que 3)
    chunk_size = 5
    sync_offset = 0.4  # Délai de synchronisation en secondes (ajusté pour compenserle décalage)
    min_duration = 0.8  # Durée minimale d'affichage en secondes
    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            text = " ".join([w["word"] for w in chunk_words])
            start_time = chunk_words[0]["start"] + sync_offset
            end_time = chunk_words[-1]["end"] + sync_offset

            # Assurer une durée minimale
            if (end_time - start_time) < min_duration:
                end_time = start_time + min_duration

            chunks.append({
                "text": text,
                "start": start_time,
                "end": end_time
            })

    for chunk in chunks:
        start_str = seconds_to_ass_time(chunk["start"])
        end_str = seconds_to_ass_time(chunk["end"])
        text = chunk["text"].replace("\n", " ")
        ass_content += f"Dialogue: 0,{start_str},{end_str},Instagram,,0,0,0,,{text}\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)


def seconds_to_ass_time(seconds: float) -> str:
    """Convertit secondes en format ASS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def burn_subtitles_into_video(video_path: str, ass_path: str, output_path: str) -> bool:
    """Brûle les sous-titres dans la vidéo"""
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
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Erreur brûlage sous-titres: {e.stderr.decode()}")
        return False


# ============================================================================
# WORKER PRINCIPAL
# ============================================================================

def main():
    """Boucle principale du worker sous-titres"""
    logger.info("=" * 60)
    logger.info("📺 Subtitles VM Worker démarré")
    logger.info("=" * 60)

    try:
        from drive_manager import DriveManager
        from transcription_backends import get_transcription_backend

        # Charger la config
        config_file = current_dir / 'config' / 'highlight_config.json'
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Initialiser le backend de transcription
        backend = get_transcription_backend(config)
        logger.info(f"🔧 Backend de transcription: {backend.get_backend_name()}")

        logger.info("🔧 Initialisation Drive Manager...")
        credentials_path = str(current_dir / 'config' / 'credentials.json')
        drive_manager = DriveManager(credentials_path=credentials_path)

        temp_dir = Path('/tmp/subtitles')
        temp_dir.mkdir(exist_ok=True)

        queue_folder = config['drive_folders'].get('queue_subtitles')
        if not queue_folder:
            logger.error("❌ Dossier queue_subtitles non configuré dans highlight_config.json")
            return 1

        logger.info(f"📂 Surveillance du dossier queue: {queue_folder}")
        logger.info("🔄 Démarrage de la boucle de traitement...")

        check_interval = 60
        idle_shutdown_minutes = 10
        consecutive_empty_checks = 0
        max_idle_checks = idle_shutdown_minutes * 60 // check_interval

        logger.info(f"⚙️  Auto-shutdown après {idle_shutdown_minutes} minutes d'inactivité")

        while True:
            try:
                logger.info("🔍 Recherche de nouveaux jobs sous-titres...")

                # Lister les fichiers .json dans le dossier queue
                job_files = drive_manager.list_files_in_folder(
                    queue_folder,
                    name_pattern='subtitles_job_*.json'
                )

                if not job_files:
                    consecutive_empty_checks += 1
                    logger.info(f"📭 Aucun job en attente ({consecutive_empty_checks}/{max_idle_checks} avant auto-shutdown)")

                    if consecutive_empty_checks >= max_idle_checks:
                        logger.info(f"💤 {idle_shutdown_minutes} minutes d'inactivité - arrêt automatique de la VM")
                        import subprocess
                        subprocess.run(['sudo', 'shutdown', '-h', 'now'])
                        break
                else:
                    consecutive_empty_checks = 0
                    logger.info(f"📥 {len(job_files)} job(s) trouvé(s)")

                    for job_file in job_files:
                        process_subtitles_job(
                            drive_manager,
                            job_file,
                            config,
                            temp_dir,
                            backend
                        )
                        consecutive_empty_checks = 0

                logger.info(f"⏳ Attente {check_interval}s avant la prochaine vérification...")
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("🛑 Arrêt demandé par l'utilisateur")
                break
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle principale: {e}")
                import traceback
                logger.error(traceback.format_exc())
                logger.info(f"⏳ Pause de 30s avant reprise...")
                time.sleep(30)

    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

    logger.info("👋 Subtitles VM Worker arrêté")
    return 0


def mark_doc_as_subtitles_done(drive_manager, doc_id):
    """Marque le document _paragraphs_timestamps comme SUBTITLES_DONE"""
    try:
        from googleapiclient.discovery import build

        docs_service = build('docs', 'v1', credentials=drive_manager.creds)
        doc = docs_service.documents().get(documentId=doc_id).execute()

        # Extraire le texte
        content = doc.get('body', {}).get('content', [])
        if not content:
            logger.warning(f"⚠️ Document vide")
            return

        # Le dernier élément contient l'index de fin
        end_index = content[-1].get('endIndex', 1) - 1

        # Insérer la balise à la fin
        requests = [{
            'insertText': {
                'location': {'index': end_index},
                'text': '\n\n🎬 SUBTITLES_DONE 🎬\n'
            }
        }]

        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()

        logger.info(f"✅ Balise SUBTITLES_DONE ajoutée au document")

    except Exception as e:
        logger.warning(f"⚠️ Erreur lors de l'ajout de la balise SUBTITLES_DONE: {e}")


def process_subtitles_job(drive_manager, job_file, config, temp_dir, backend):
    """Traite un job de sous-titrage avec le backend configuré"""
    job_name = job_file['name']
    job_id = job_file['id']

    logger.info("=" * 60)
    logger.info(f"🎯 Traitement du job: {job_name}")
    logger.info(f"🔧 Backend: {backend.get_backend_name()}")

    try:
        # Télécharger le fichier job
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        drive_manager.download_file(job_id, job_name, temp_path)

        # Lire le contenu du job
        with open(temp_path, 'r') as f:
            job_data = json.load(f)

        os.remove(temp_path)

        doc_id = job_data.get('doc_id')
        base_name = job_data.get('base_name')
        segments_folder_id = job_data.get('segments_folder_id')
        segments_folder_name = job_data.get('segments_folder_name')

        if not all([doc_id, base_name, segments_folder_id]):
            logger.error(f"❌ Job invalide: {job_name}")
            drive_manager.service.files().delete(fileId=job_id, supportsAllDrives=True).execute()
            return

        logger.info(f"📁 Dossier segments: {segments_folder_name}")

        # 1. Lister les fichiers dans le dossier segments
        all_files = drive_manager.list_files_in_folder(segments_folder_id)

        # Séparer vidéos et SRT
        video_files = [f for f in all_files if f['name'].endswith('.mp4')]
        srt_files = [f for f in all_files if f['name'].endswith('.srt')]

        logger.info(f"📹 {len(video_files)} vidéo(s) trouvée(s)")
        logger.info(f"📝 {len(srt_files)} SRT trouvé(s)")

        if not video_files:
            logger.error(f"❌ Aucune vidéo trouvée dans le dossier segments")
            return

        # 2. Créer dossier local pour les segments
        segments_local_dir = temp_dir / f"{base_name}_segments"
        segments_local_dir.mkdir(exist_ok=True)

        # 3. Télécharger les segments et SRT
        logger.info(f"📥 Téléchargement des segments et SRT...")
        for video_file in video_files:
            video_name = video_file['name']
            video_path = segments_local_dir / video_name
            drive_manager.download_file(video_file['id'], video_name, str(video_path))
            logger.info(f"   ✅ {video_name}")

        for srt_file in srt_files:
            srt_name = srt_file['name']
            srt_path = segments_local_dir / srt_name
            drive_manager.download_file(srt_file['id'], srt_name, str(srt_path))
            logger.info(f"   ✅ {srt_name}")

        # 4. Traiter chaque segment
        logger.info(f"🎬 Génération des sous-titres...")
        subtitled_videos = []

        for video_file in video_files:
            video_name = video_file['name']
            video_stem = Path(video_name).stem

            # Chercher le SRT correspondant
            srt_path = segments_local_dir / f"{video_stem}.srt"

            if not srt_path.exists():
                logger.warning(f"⚠️ SRT introuvable pour {video_name} - ignoré")
                continue

            logger.info(f"📹 Traitement: {video_name}")

            video_path = segments_local_dir / video_name

            # Extraire audio
            audio_path = segments_local_dir / f"{video_stem}_audio.wav"
            if not extract_audio_from_video(str(video_path), str(audio_path)):
                logger.warning(f"⚠️ Échec extraction audio - {video_name} ignoré")
                continue

            # Parser SRT
            segments = parse_srt(str(srt_path))
            logger.info(f"   📝 {len(segments)} segments SRT")

            # Aligner mot-par-mot avec le backend
            logger.info(f"   🎯 Alignement mot-par-mot avec {backend.get_backend_name()}...")
            words = align_segments_with_backend(str(audio_path), segments, backend)

            if not words:
                logger.warning(f"⚠️ Échec alignement - {video_name} ignoré")
                audio_path.unlink(missing_ok=True)
                continue

            logger.info(f"   ✅ {len(words)} mots alignés")

            # Générer ASS
            ass_path = segments_local_dir / f"{video_stem}.ass"
            generate_ass_subtitle(words, str(ass_path))
            logger.info(f"   📝 ASS généré")

            # Brûler sous-titres
            output_video = segments_local_dir / f"{video_stem}_SUBTITLED.mp4"
            logger.info(f"   🔥 Brûlage sous-titres...")

            if burn_subtitles_into_video(str(video_path), str(ass_path), str(output_video)):
                subtitled_videos.append(str(output_video))
                logger.info(f"   ✅ Vidéo avec sous-titres créée")
            else:
                logger.warning(f"⚠️ Échec brûlage - {video_name} ignoré")

            # Nettoyer fichiers temporaires
            audio_path.unlink(missing_ok=True)
            ass_path.unlink(missing_ok=True)

        logger.info(f"✅ {len(subtitled_videos)}/{len(video_files)} vidéo(s) sous-titrée(s)")

        if not subtitled_videos:
            logger.error(f"❌ Aucune vidéo sous-titrée créée")
            return

        # 5. Créer dossier de sortie sur Drive (dans le dossier segments)
        timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%Ss')
        output_folder_name = f"with_subtitles_{timestamp}"

        folder_metadata = {
            'name': output_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [segments_folder_id]
        }
        folder = drive_manager.service.files().create(
            body=folder_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        output_folder_id = folder['id']
        logger.info(f"📁 Dossier créé: {output_folder_name}")

        # 6. Upload les vidéos sous-titrées
        logger.info(f"📤 Upload des vidéos sous-titrées...")
        for video_path in subtitled_videos:
            video_name = Path(video_path).name
            drive_manager.upload_file(
                video_path,
                video_name,
                output_folder_id
            )
            logger.info(f"   ✅ {video_name}")

        logger.info(f"✅ {len(subtitled_videos)} vidéo(s) uploadée(s)")

        # 7. Marquer le document comme SUBTITLES_DONE
        logger.info(f"📝 Marquage du document comme SUBTITLES_DONE...")
        mark_doc_as_subtitles_done(drive_manager, doc_id)

        # 8. Nettoyer
        logger.info(f"🧹 Nettoyage...")
        import shutil
        for file in temp_dir.glob(f"{base_name}*"):
            try:
                if file.is_file():
                    file.unlink()
                elif file.is_dir():
                    shutil.rmtree(file)
            except Exception as e:
                logger.warning(f"Erreur nettoyage {file}: {e}")

        # 9. Archiver le job
        completed_folder = config['drive_folders'].get('completed_jobs')

        if completed_folder:
            logger.info(f"📦 Archivage du job dans completed_jobs...")
            completed_name = job_name.replace('subtitles_job_', 'completed_subtitles_')

            drive_manager.service.files().update(
                fileId=job_id,
                addParents=completed_folder,
                removeParents=config['drive_folders']['queue_subtitles'],
                body={'name': completed_name},
                supportsAllDrives=True
            ).execute()
            logger.info(f"✅ Job archivé: {completed_name}")
        else:
            logger.info(f"🗑️  Suppression du job: {job_name}")
            drive_manager.service.files().delete(
                fileId=job_id,
                supportsAllDrives=True
            ).execute()

        logger.info(f"✅ Job terminé avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur traitement job {job_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        # Renommer en erreur
        try:
            error_name = job_name.replace('subtitles_job_', 'subtitles_error_')
            drive_manager.service.files().update(
                fileId=job_id,
                body={'name': error_name},
                supportsAllDrives=True
            ).execute()
            logger.info(f"⚠️  Job renommé en erreur: {error_name}")
        except Exception as rename_error:
            logger.warning(f"⚠️  Impossible de renommer le job: {rename_error}")


if __name__ == '__main__':
    exit(main())
