#!/usr/bin/env python3
"""
Script pour lister TOUS les fichiers de transcription sur Drive
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from src.drive_manager import DriveManager
from config import whisper_config as config

drive_manager = DriveManager(config.CREDENTIALS_PATH)
output_folder_id = config.DRIVE_FOLDERS['output']

print(f"📁 Listing des fichiers dans le dossier Transcriptions (ID: {output_folder_id})\n")

# Lister tous les fichiers
query = f"'{output_folder_id}' in parents and trashed = false"

results = drive_manager.service.files().list(
    q=query,
    fields="files(id, name, createdTime, mimeType, modifiedTime)",
    supportsAllDrives=True,
    includeItemsFromAllDrives=True,
    pageSize=100
).execute()

files = results.get('files', [])

print(f"✅ Trouvé {len(files)} fichiers\n")

# Chercher spécifiquement les fichiers _paragraphs_timestamps
para_files = [f for f in files if '_paragraphs_timestamps' in f['name']]

print(f"📝 Trouvé {len(para_files)} fichiers _paragraphs_timestamps\n")
print("="*80)

for f in sorted(para_files, key=lambda x: x['createdTime'], reverse=True):
    created = datetime.strptime(f['createdTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
    mime = "Google Doc" if 'google-apps.document' in f['mimeType'] else f['mimeType']

    # Date limite du nouveau format
    new_format_date = datetime(2025, 12, 18, 16, 43, 9)
    status = "🟢 NOUVEAU FORMAT" if created >= new_format_date else "🔴 ANCIEN FORMAT"

    print(f"{status}")
    print(f"  Nom: {f['name']}")
    print(f"  ID: {f['id']}")
    print(f"  Type: {mime}")
    print(f"  Créé: {created.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
