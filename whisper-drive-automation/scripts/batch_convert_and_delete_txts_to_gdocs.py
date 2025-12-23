#!/usr/bin/env python3
"""
Script pour convertir tous les fichiers .txt d'un dossier Google Drive en Google Docs et supprimer les .txt après conversion.
Usage: python3 batch_convert_and_delete_txts_to_gdocs.py
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

folder_id = config['drive_folders']['transcriptions']

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


import re

def escape_for_drive_query(s):
    # Échappe les apostrophes pour la requête Drive (utilisation de name = ...)
    return s.replace("'", "\\'")

for file in files:
    print(f"\nTraitement: {file['name']} (ID: {file['id']})")
    # Chercher un Google Doc du même nom (sans extension)
    base_name = file['name'].rsplit('.', 1)[0]
    base_name_escaped = escape_for_drive_query(base_name)
    gdoc_query = f"name = '{base_name_escaped}' and mimeType='application/vnd.google-apps.document' and '{folder_id}' in parents and trashed=false"
    try:
        gdoc_results = drive_manager.service.files().list(
            q=gdoc_query,
            fields="files(id, name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        gdocs = gdoc_results.get('files', [])
    except Exception as e:
        print(f"❌ Erreur requête Google Drive pour {base_name}: {e}")
        continue
    if gdocs:
        print(f"⚠️ Google Doc déjà présent pour {base_name}, on saute.")
        continue
    doc_id = convert_txt_to_gdoc(drive_manager, file['id'])
    if doc_id:
        try:
            drive_manager.service.files().delete(
                fileId=file['id'],
                supportsAllDrives=True
            ).execute()
            print(f"✅ Fichier .txt supprimé: {file['name']}")
        except Exception as e:
            print(f"❌ Erreur suppression {file['name']}: {e}")
    time.sleep(1)  # Pour éviter les quotas API

print("\n✅ Conversion et suppression batch terminées !")
