#!/usr/bin/env python3
"""
Script pour convertir les fichiers _paragraphs_timestamps de l'ancien format au nouveau format
Sans avoir à retranscrire - utilise les données du _complete_data.json

Ancien format:
=== Paragraphe 1 ===
Temps: 0:00 - 1:30
Mots: 150
[texte]

Nouveau format:
(0:00) Premier segment. (0:15) Deuxième segment.

(1:30) Nouveau paragraphe ici.
"""
import sys
from pathlib import Path
from datetime import datetime
import logging
import json
import tempfile

# Ajouter le chemin du projet
sys.path.insert(0, str(Path(__file__).parent))

from src.drive_manager import DriveManager
from config import whisper_config as config
from googleapiclient.discovery import build

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Date de déploiement du nouveau format sur Cloud Run
# On exclut janvier 2026 - donc seulement les fichiers de 2025 et avant
NEW_FORMAT_DATE = datetime(2026, 1, 1, 0, 0, 0)


def _seconds_to_simple_timestamp(seconds):
    """Convertit secondes en format M:SS (sans zéros inutiles)"""
    minutes, seconds_remainder = divmod(seconds, 60)
    return f"{int(minutes)}:{int(seconds_remainder):02d}"


def check_document_format(drive_manager, file_id, mime_type):
    """
    Vérifie si un document a l'ancien ou le nouveau format

    Returns:
        str: 'old' si ancien format, 'new' si nouveau format, 'unknown' si indéterminé
    """
    try:
        if 'google-apps.document' in mime_type:
            # C'est un Google Doc - utiliser l'API Docs
            from google.oauth2.service_account import Credentials
            from google.auth import default as get_default_credentials

            if drive_manager.credentials_path:
                creds = Credentials.from_service_account_file(
                    drive_manager.credentials_path,
                    scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
                )
            else:
                creds, _ = get_default_credentials(
                    scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
                )

            docs_service = build('docs', 'v1', credentials=creds)
            doc = docs_service.documents().get(documentId=file_id).execute()

            # Extraire le texte
            content = doc.get('body', {}).get('content', [])
            full_text = []

            for element in content:
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    for text_run in paragraph.get('elements', []):
                        if 'textRun' in text_run:
                            full_text.append(text_run['textRun']['content'])

            text = ''.join(full_text)

        else:
            # C'est un fichier .txt - le télécharger
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False, encoding='utf-8') as f:
                temp_path = f.name

            drive_manager.download_file(file_id, 'temp.txt', temp_path)

            with open(temp_path, 'r', encoding='utf-8') as f:
                text = f.read()

            import os
            os.remove(temp_path)

        # Vérifier le format
        if "=== Paragraphe" in text:
            return 'old'
        elif "Temps:" in text and "Mots:" in text:
            return 'old'
        elif text.strip().startswith("(") and ":" in text.split("\n")[0][:10]:
            # Format nouveau: commence par (M:SS)
            return 'new'
        else:
            return 'unknown'

    except Exception as e:
        logger.error(f"   ❌ Erreur vérification format: {e}")
        return 'unknown'


def list_old_paragraphs_files(drive_manager, output_folder_id):
    """
    Liste tous les fichiers _paragraphs_timestamps qui ont l'ancien format
    Exclut les fichiers de janvier 2026

    Returns:
        list: Liste de fichiers à convertir
    """
    logger.info(f"🔍 Recherche des fichiers _paragraphs_timestamps avec ancien format (avant {NEW_FORMAT_DATE.strftime('%Y-%m-%d')})")

    # Lister TOUS les fichiers dans le dossier de sortie avec pagination
    query = f"'{output_folder_id}' in parents and trashed = false"

    all_files = []
    page_token = None

    while True:
        kwargs = {
            'q': query,
            'fields': 'nextPageToken, files(id, name, createdTime, mimeType)',
            'supportsAllDrives': True,
            'includeItemsFromAllDrives': True,
            'pageSize': 1000
        }

        if page_token:
            kwargs['pageToken'] = page_token

        results = drive_manager.service.files().list(**kwargs).execute()
        all_files.extend(results.get('files', []))

        page_token = results.get('nextPageToken')
        if not page_token:
            break

    files = all_files
    logger.info(f"📁 Total de fichiers dans le dossier: {len(files)}")
    old_files = []
    skipped_new_format = 0
    skipped_january = 0

    for file in files:
        # Ne garder que les fichiers _paragraphs_timestamps
        if '_paragraphs_timestamps' in file['name']:
            created_time_str = file['createdTime']
            # Format: 2025-01-15T10:30:00.000Z
            created_time = datetime.strptime(created_time_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')

            # Exclure les fichiers de janvier 2026
            if created_time >= NEW_FORMAT_DATE:
                skipped_january += 1
                logger.info(f"   ⏭️  Ignoré (janvier 2026): {file['name']}")
                continue

            # Vérifier le format du document
            logger.info(f"   🔍 Vérification: {file['name']}")
            doc_format = check_document_format(drive_manager, file['id'], file['mimeType'])

            if doc_format == 'old':
                old_files.append({
                    'name': file['name'],
                    'id': file['id'],
                    'created_time': created_time,
                    'mime_type': file['mimeType']
                })
                logger.info(f"      🔴 ANCIEN FORMAT - à convertir")
            elif doc_format == 'new':
                skipped_new_format += 1
                logger.info(f"      ✅ Déjà au nouveau format - ignoré")
            else:
                logger.info(f"      ⚠️  Format inconnu - ignoré")

    logger.info("")
    logger.info(f"📊 Résumé de la recherche:")
    logger.info(f"   🔴 Fichiers à convertir (ancien format): {len(old_files)}")
    logger.info(f"   ✅ Déjà au nouveau format: {skipped_new_format}")
    logger.info(f"   ⏭️  Ignorés (janvier 2026): {skipped_january}")

    return old_files


def extract_base_filename(transcription_name):
    """
    Extrait le nom de base du fichier depuis le nom de transcription

    Args:
        transcription_name: ex: "mon_audio_paragraphs_timestamps"

    Returns:
        str: ex: "mon_audio"
    """
    # Enlever "_paragraphs_timestamps" et toute extension
    base = transcription_name.replace('_paragraphs_timestamps', '')
    base = base.replace('.txt', '')
    return base


def find_complete_data_json(drive_manager, output_folder_id, base_filename):
    """
    Trouve le fichier _complete_data.json correspondant

    Returns:
        dict: file_info ou None si non trouvé
    """
    json_name = f"{base_filename}_complete_data.json"
    # Échapper les apostrophes pour la requête Drive
    json_name_escaped = json_name.replace("'", "\\'")
    query = f"'{output_folder_id}' in parents and name = '{json_name_escaped}' and trashed = false"

    results = drive_manager.service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get('files', [])
    if files:
        return files[0]
    return None


def download_and_parse_json(drive_manager, file_id):
    """
    Télécharge et parse le fichier JSON

    Returns:
        dict: Données du JSON
    """
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
        temp_path = f.name

    drive_manager.download_file(file_id, 'temp.json', temp_path)

    with open(temp_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    import os
    os.remove(temp_path)

    return data


def generate_new_format_content(paragraphs):
    """
    Génère le contenu au nouveau format à partir des paragraphes

    Args:
        paragraphs: Liste de paragraphes depuis complete_data.json

    Returns:
        str: Contenu formaté
    """
    content_lines = []

    for paragraph in paragraphs:
        line_parts = []

        if 'segments' in paragraph:
            # Format avec segments multiples
            for segment in paragraph['segments']:
                timestamp = _seconds_to_simple_timestamp(segment['start'])
                text = segment['text'].strip()
                line_parts.append(f"({timestamp}) {text}")
        else:
            # Format simple avec un seul timestamp
            timestamp = _seconds_to_simple_timestamp(paragraph['start'])
            text = paragraph['text'].strip()
            line_parts.append(f"({timestamp}) {text}")

        # Joindre les segments avec un espace
        content_lines.append(' '.join(line_parts))

    # Joindre les paragraphes avec double saut de ligne
    return '\n\n'.join(content_lines)


def update_google_doc(drive_manager, doc_id, new_content):
    """
    Met à jour le contenu d'un Google Doc existant

    Args:
        drive_manager: Instance de DriveManager
        doc_id: ID du document à mettre à jour
        new_content: Nouveau contenu
    """
    from google.oauth2.service_account import Credentials
    from google.auth import default as get_default_credentials

    # Obtenir les credentials
    if drive_manager.credentials_path:
        creds = Credentials.from_service_account_file(
            drive_manager.credentials_path,
            scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
        )
    else:
        creds, _ = get_default_credentials(
            scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
        )

    docs_service = build('docs', 'v1', credentials=creds)

    # Récupérer le document pour obtenir la longueur du contenu
    doc = docs_service.documents().get(documentId=doc_id).execute()

    # Calculer la longueur du contenu existant
    content = doc.get('body', {}).get('content', [])
    end_index = 1
    for element in content:
        if 'endIndex' in element:
            end_index = max(end_index, element['endIndex'])

    # Créer les requêtes pour remplacer tout le contenu
    requests = [
        # Supprimer tout le contenu existant (sauf le premier caractère qui est protégé)
        {
            'deleteContentRange': {
                'range': {
                    'startIndex': 1,
                    'endIndex': end_index - 1
                }
            }
        },
        # Insérer le nouveau contenu
        {
            'insertText': {
                'location': {'index': 1},
                'text': new_content
            }
        }
    ]

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests}
    ).execute()


def convert_paragraphs_file(drive_manager, old_file, output_folder_id):
    """
    Convertit un fichier _paragraphs_timestamps au nouveau format

    Args:
        drive_manager: Instance de DriveManager
        old_file: Info du fichier à convertir
        output_folder_id: ID du dossier de sortie

    Returns:
        bool: True si succès
    """
    base_filename = extract_base_filename(old_file['name'])
    logger.info(f"\n📝 Traitement: {base_filename}")

    # Trouver le fichier _complete_data.json
    json_file = find_complete_data_json(drive_manager, output_folder_id, base_filename)

    if not json_file:
        logger.warning(f"   ⚠️  Fichier _complete_data.json non trouvé pour {base_filename}")
        return False

    logger.info(f"   ✅ Fichier JSON trouvé: {json_file['name']}")

    # Télécharger et parser le JSON
    try:
        data = download_and_parse_json(drive_manager, json_file['id'])
    except Exception as e:
        logger.error(f"   ❌ Erreur lecture JSON: {e}")
        return False

    # Vérifier qu'il y a des paragraphes
    if 'paragraphs' not in data or not data['paragraphs']:
        logger.warning(f"   ⚠️  Pas de paragraphes dans le JSON")
        return False

    logger.info(f"   📊 {len(data['paragraphs'])} paragraphe(s) trouvé(s)")

    # Générer le nouveau contenu
    new_content = generate_new_format_content(data['paragraphs'])

    # Vérifier si c'est un Google Doc
    is_gdoc = 'google-apps.document' in old_file['mime_type']

    if is_gdoc:
        # Mettre à jour le Google Doc existant
        logger.info(f"   🔄 Mise à jour du Google Doc...")
        try:
            update_google_doc(drive_manager, old_file['id'], new_content)
            logger.info(f"   ✅ Google Doc mis à jour: {old_file['name']}")
            return True
        except Exception as e:
            logger.error(f"   ❌ Erreur mise à jour Google Doc: {e}")
            return False
    else:
        # C'est un fichier .txt - créer un nouveau Google Doc et supprimer l'ancien
        logger.info(f"   🔄 Conversion .txt → Google Doc...")
        try:
            # Créer le nouveau Google Doc
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials
            from google.auth import default as get_default_credentials

            if drive_manager.credentials_path:
                creds = Credentials.from_service_account_file(
                    drive_manager.credentials_path,
                    scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
                )
            else:
                creds, _ = get_default_credentials(
                    scopes=['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive']
                )

            docs_service = build('docs', 'v1', credentials=creds)

            # Créer le document vide
            doc_name = base_filename + '_paragraphs_timestamps'
            doc_metadata = {
                'name': doc_name,
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [output_folder_id]
            }

            doc = drive_manager.service.files().create(
                body=doc_metadata,
                supportsAllDrives=True
            ).execute()

            doc_id = doc['id']

            # Insérer le contenu
            requests = [{
                'insertText': {
                    'location': {'index': 1},
                    'text': new_content
                }
            }]

            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

            logger.info(f"   ✅ Google Doc créé: {doc_name}")

            # Supprimer l'ancien fichier .txt
            drive_manager.service.files().update(
                fileId=old_file['id'],
                body={'trashed': True},
                supportsAllDrives=True
            ).execute()

            logger.info(f"   🗑️  Ancien fichier .txt supprimé")
            return True

        except Exception as e:
            logger.error(f"   ❌ Erreur conversion: {e}")
            return False


def main():
    logger.info("="*80)
    logger.info("🚀 CONVERSION DES FICHIERS _paragraphs_timestamps AU NOUVEAU FORMAT")
    logger.info("="*80)
    logger.info("")

    # Initialiser le DriveManager
    drive_manager = DriveManager(config.CREDENTIALS_PATH)

    output_folder_id = config.DRIVE_FOLDERS['output']

    # 1. Lister les anciens fichiers
    old_files = list_old_paragraphs_files(drive_manager, output_folder_id)

    if not old_files:
        logger.info("✅ Aucun fichier à convertir!")
        return 0

    # 2. Afficher le résumé et demander confirmation
    logger.info("\n" + "="*80)
    logger.info(f"📊 RÉSUMÉ: {len(old_files)} fichier(s) à convertir")
    logger.info("="*80)

    for item in old_files:
        logger.info(f"   • {item['name']} (créé le {item['created_time'].strftime('%Y-%m-%d %H:%M')})")

    logger.info("\n⚠️  Cette opération va:")
    logger.info("   1. Lire les données depuis _complete_data.json")
    logger.info("   2. Régénérer les fichiers _paragraphs_timestamps au nouveau format")
    logger.info("   3. Mettre à jour les Google Docs existants (ou convertir .txt en Google Docs)")
    logger.info("\n💡 Aucune retranscription ne sera effectuée - seul le format change")

    response = input("\n❓ Continuer? (oui/non): ").strip().lower()

    if response not in ['oui', 'yes', 'o', 'y']:
        logger.info("❌ Opération annulée")
        return 0

    # 3. Convertir les fichiers
    logger.info("\n🔄 Conversion en cours...")
    logger.info("="*80)

    success_count = 0
    failed_count = 0

    for old_file in old_files:
        if convert_paragraphs_file(drive_manager, old_file, output_folder_id):
            success_count += 1
        else:
            failed_count += 1

    # 4. Résumé final
    logger.info("\n" + "="*80)
    logger.info("✅ CONVERSION TERMINÉE")
    logger.info("="*80)
    logger.info(f"✅ Fichiers convertis avec succès: {success_count}")
    logger.info(f"❌ Échecs: {failed_count}")
    logger.info("")

    if success_count > 0:
        logger.info("💡 Les fichiers ont été convertis au nouveau format:")
        logger.info("   Format: (M:SS) texte du segment")
        logger.info("   Les timestamps sont maintenant plus lisibles et compacts")

    return 0


if __name__ == '__main__':
    sys.exit(main())
