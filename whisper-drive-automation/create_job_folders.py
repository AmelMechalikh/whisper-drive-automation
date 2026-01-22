#!/usr/bin/env python3
"""
Script pour créer les dossiers completed_jobs et failed_jobs sur Drive
et mettre à jour la config automatiquement
"""
import sys
import json
sys.path.insert(0, 'src')
sys.path.insert(0, 'config')

from drive_manager import DriveManager
import whisper_config as config

def create_folder(drive_manager, folder_name, parent_id=None):
    """Crée un dossier sur Drive"""
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }

    if parent_id:
        folder_metadata['parents'] = [parent_id]

    folder = drive_manager.service.files().create(
        body=folder_metadata,
        fields='id, name',
        supportsAllDrives=True
    ).execute()

    return folder

def main():
    print("🚀 Création des dossiers pour l'archivage des jobs...")

    # Initialiser Drive Manager
    dm = DriveManager(config.CREDENTIALS_PATH)

    # Lire la config highlights
    with open('config/highlight_config.json', 'r') as f:
        hl_config = json.load(f)

    queue_folder_id = hl_config['drive_folders']['queue_highlights']

    # Vérifier si les dossiers existent déjà
    existing_folders = dm.list_files_in_folder(queue_folder_id)

    completed_folder = None
    failed_folder = None

    for folder in existing_folders:
        if folder['name'] == 'completed_jobs' and folder.get('mimeType') == 'application/vnd.google-apps.folder':
            completed_folder = folder
            print(f"✅ Dossier 'completed_jobs' existe déjà: {folder['id']}")
        elif folder['name'] == 'failed_jobs' and folder.get('mimeType') == 'application/vnd.google-apps.folder':
            failed_folder = folder
            print(f"✅ Dossier 'failed_jobs' existe déjà: {folder['id']}")

    # Créer completed_jobs si nécessaire
    if not completed_folder:
        print("📁 Création du dossier 'completed_jobs'...")
        completed_folder = create_folder(dm, 'completed_jobs', parent_id=queue_folder_id)
        print(f"✅ Dossier créé: {completed_folder['name']} (ID: {completed_folder['id']})")

    # Créer failed_jobs si nécessaire
    if not failed_folder:
        print("📁 Création du dossier 'failed_jobs'...")
        failed_folder = create_folder(dm, 'failed_jobs', parent_id=queue_folder_id)
        print(f"✅ Dossier créé: {failed_folder['name']} (ID: {failed_folder['id']})")

    # Mettre à jour la config
    print("\n📝 Mise à jour de highlight_config.json...")
    hl_config['drive_folders']['completed_jobs'] = completed_folder['id']
    hl_config['drive_folders']['failed_jobs'] = failed_folder['id']

    with open('config/highlight_config.json', 'w') as f:
        json.dump(hl_config, f, indent=2)

    print("✅ Configuration mise à jour!")
    print(f"\n📊 IDs des dossiers:")
    print(f"   - completed_jobs: {completed_folder['id']}")
    print(f"   - failed_jobs: {failed_folder['id']}")
    print("\n✅ Configuration terminée!")

if __name__ == '__main__':
    main()
