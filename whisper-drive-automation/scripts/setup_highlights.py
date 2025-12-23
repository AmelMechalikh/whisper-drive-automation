#!/usr/bin/env python3
"""
Script de déploiement du système de highlights sur VM
Crée les dossiers Drive nécessaires et configure le worker
"""

import json
import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from drive_manager import DriveManager


def create_drive_folders(drive_manager, transcriptions_folder_id):
    """Crée les dossiers nécessaires pour les highlights"""
    
    print("📁 Création des dossiers Drive...")
    
    # 1. Highlighted Files - sous-dossier de Transcriptions
    print(f"  - Création: Highlighted Files (sous Transcriptions)...")
    
    query = f"name='Highlighted Files' and mimeType='application/vnd.google-apps.folder' and '{transcriptions_folder_id}' in parents"
    results = drive_manager.service.files().list(
        q=query,
        fields='files(id, name)',
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    
    existing = results.get('files', [])
    
    if existing:
        highlighted_folder_id = existing[0]['id']
        print(f"    ✅ Dossier existant: {highlighted_folder_id}")
    else:
        file_metadata = {
            'name': 'Highlighted Files',
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [transcriptions_folder_id],
            'description': 'Fichiers de transcription annotés avec commentaires Google Docs'
        }
        
        folder = drive_manager.service.files().create(
            body=file_metadata,
            fields='id',
            supportsAllDrives=True
        ).execute()
        
        highlighted_folder_id = folder.get('id')
        print(f"    ✅ Dossier créé: {highlighted_folder_id}")
    
    # 2. Autres dossiers au même niveau que Transcriptions
    shared_drive_id = '0AJsxPbtOtogRUk9PVA'
    
    other_folders = {
        'Highlights Excel': 'Fichiers Excel avec timestamps des highlights',
        'Segments Videos': 'Segments vidéo extraits des highlights'
    }
    
    folder_ids = {'Highlighted Files': highlighted_folder_id}
    
    for folder_name, description in other_folders.items():
        print(f"  - Création: {folder_name}...")
        
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and '{shared_drive_id}' in parents"
        results = drive_manager.service.files().list(
            q=query,
            fields='files(id, name)',
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora='drive',
            driveId=shared_drive_id
        ).execute()
        
        existing = results.get('files', [])
        
        if existing:
            folder_id = existing[0]['id']
            print(f"    ✅ Dossier existant: {folder_id}")
        else:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [shared_drive_id],
                'description': description
            }
            
            folder = drive_manager.service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            print(f"    ✅ Dossier créé: {folder_id}")
        
        folder_ids[folder_name] = folder_id
    
    return folder_ids


def generate_config_file(folder_ids, output_path):
    """Génère le fichier de configuration pour l'orchestrateur"""
    
    config = {
        'drive_folders': {
            'highlighted_files': folder_ids['Highlighted Files'],
            'source_files': '1A29pkQvrBodU_HxNS8deYt6T27AlmbSe',
            'transcriptions': '1yHcy9um2_We459w9I0cITwHBGXKTlOJa',
            'excel_output': folder_ids['Highlights Excel'],
            'segments_output': folder_ids['Segments Videos']
        },
        'processing': {
            'watch_interval_seconds': 300,
            'temp_dir': './temp_highlights'
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Configuration sauvée: {output_path}")
    print("\nIDs des dossiers:")
    for name, folder_id in folder_ids.items():
        print(f"  - {name}: {folder_id}")


def main():
    """Point d'entrée principal"""
    print("🚀 Configuration du système de highlights\n")
    
    # Chemins
    script_dir = Path(__file__).parent.parent
    credentials_path = script_dir / 'config' / 'credentials.json'
    config_output = script_dir / 'config' / 'highlight_config.json'
    
    # IDs des dossiers
    TRANSCRIPTIONS_FOLDER_ID = '1yHcy9um2_We459w9I0cITwHBGXKTlOJa'
    
    # Initialiser Drive Manager
    print("🔧 Connexion à Google Drive...")
    drive_manager = DriveManager(str(credentials_path))
    print("✅ Connecté\n")
    
    # Créer les dossiers
    folder_ids = create_drive_folders(drive_manager, TRANSCRIPTIONS_FOLDER_ID)
    
    # Générer le fichier de config
    generate_config_file(folder_ids, config_output)
    
    print("\n" + "="*60)
    print("✅ Configuration terminée!")
    print("="*60)
    print("\nProchaines étapes:")
    print("1. Installer ffmpeg sur la VM: sudo apt-get install ffmpeg")
    print("2. Installer openpyxl: pip install openpyxl")
    print("3. Déployer le code sur la VM")
    print("4. Lancer le worker highlights: python3 scripts/highlight_worker.py")
    print("\nPour tester:")
    print(f"1. Téléchargez un fichier _paragraphs_timestamps.txt depuis Transcriptions")
    print("2. Convertissez-le en Google Doc et uploadez-le dans 'Highlighted Files'")
    print("3. Ajoutez des commentaires Google Docs sur les passages à extraire")
    print("4. Le système générera automatiquement l'Excel et les segments vidéo")


if __name__ == '__main__':
    main()
