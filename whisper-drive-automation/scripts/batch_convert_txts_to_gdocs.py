#!/usr/bin/env python3
"""
Script pour convertir tous les fichiers .txt d'un dossier Google Drive en Google Docs
Usage: python3 batch_convert_txts_to_gdocs.py
"""

from pathlib import Path
import json
import sys
import time

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

from drive_manager import DriveManager

# Charger la config
config_path = Path(__file__).parent.parent / 'config' / 'highlight_config.json'
with open(config_path) as f:
    config = json.load(f)

folder_id = config['drive_folders']['highlighted_files']

# Initialiser DriveManager
credentials_path = Path(__file__).parent.parent / 'config' / 'credentials.json'
drive_manager = DriveManager(str(credentials_path))

# Lister tous les fichiers .txt dans le dossier
query = f"mimeType='text/plain' and '{folder_id}' in parents and trashed=false"
results = drive_manager.service.files().list(
    q=query,
    fields="files(id, name, mimeType)",
    supportsAllDrives=True,
    includeItemsFromAllDrives=True
).execute()

files = results.get('files', [])
print(f"{len(files)} fichier(s) .txt trouvé(s) dans le dossier.")

from convert_txt_to_gdoc import convert_txt_to_gdoc

for file in files:
    print(f"\nTraitement: {file['name']} (ID: {file['id']})")
    convert_txt_to_gdoc(drive_manager, file['id'])
    time.sleep(1)  # Pour éviter les quotas API

print("\n✅ Conversion batch terminée !")
