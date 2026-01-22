#!/usr/bin/env python3
"""
Liste tous les fichiers dans les dossiers Drive
"""

import sys
import json
import logging
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drive_manager import DriveManager


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('ListDrive')

    # Chemins
    script_dir = Path(__file__).parent.parent
    credentials_path = script_dir / 'config' / 'credentials.json'
    config_path = script_dir / 'config' / 'highlight_config.json'

    # Charger la configuration
    with open(config_path) as f:
        config = json.load(f)

    folders = config['drive_folders']

    # Initialiser Drive Manager
    drive = DriveManager(str(credentials_path))

    print("\n" + "="*80)
    print("📊 FICHIERS EXCEL (excel_output)")
    print("="*80)
    excel_files = drive.list_files_in_folder(folders['excel_output'])
    for f in excel_files:
        print(f"  - {f['name']}")

    print("\n" + "="*80)
    print("🎬 FICHIERS SOURCE (source_files)")
    print("="*80)
    source_files = drive.list_files_in_folder(folders['source_files'])
    for f in source_files:
        print(f"  - {f['name']}")

    print("\n" + "="*80)
    print("📁 SEGMENTS OUTPUT")
    print("="*80)
    segment_files = drive.list_files_in_folder(folders['segments_output'])
    for f in segment_files:
        mime = f.get('mimeType', '')
        is_folder = 'folder' in mime
        icon = "📁" if is_folder else "📄"
        print(f"  {icon} {f['name']}")


if __name__ == '__main__':
    main()
