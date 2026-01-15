#!/usr/bin/env python3
"""
Vérifie les dates de création des fichiers sources
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))
from drive_manager import DriveManager

dm = DriveManager('./config/credentials.json')

# Lister tous les fichiers sources
source_files_folder = '1A29pkQvrBodU_HxNS8deYt6T27AlmbSe'
source_files = dm.list_files_in_folder(source_files_folder)

# Trier par date de création (du plus récent au plus ancien)
source_files.sort(key=lambda x: x.get('createdTime', ''), reverse=True)

print('=== FICHIERS SOURCES (AUDIO/VIDEO) ===')
print(f'Total: {len(source_files)} fichiers\n')
print('DATE CREATION       | DATE MODIFICATION  | FICHIER')
print('-' * 100)

for f in source_files:
    created = f.get('createdTime', 'N/A')
    modified = f.get('modifiedTime', 'N/A')

    # Formater les dates
    if created != 'N/A':
        created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
        created_str = created_dt.strftime('%Y-%m-%d %H:%M')
    else:
        created_str = 'N/A'.ljust(16)

    if modified != 'N/A':
        modified_dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
        modified_str = modified_dt.strftime('%Y-%m-%d %H:%M')
    else:
        modified_str = 'N/A'.ljust(16)

    print(f'{created_str} | {modified_str} | {f["name"]}')
