#!/usr/bin/env python3
"""
Script pour convertir un fichier .txt en Google Doc
Usage: python3 convert_txt_to_gdoc.py <file_id_or_name>
"""

import sys
from pathlib import Path

# Ajouter le chemin parent pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

from drive_manager import DriveManager
import json

def convert_txt_to_gdoc(drive_manager, file_id):
    """
    Convertit un fichier texte en Google Doc
    
    Args:
        drive_manager: Instance de DriveManager
        file_id: ID du fichier à convertir
    """
    try:
        # Récupérer les infos du fichier
        file_info = drive_manager.service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,parents',
            supportsAllDrives=True
        ).execute()
        
        print(f"📄 Fichier trouvé: {file_info['name']}")
        print(f"   Type actuel: {file_info['mimeType']}")
        
        if file_info['mimeType'] == 'application/vnd.google-apps.document':
            print("✅ Le fichier est déjà un Google Doc !")
            return file_id
        
        # Télécharger le contenu
        print("📥 Téléchargement du contenu...")
        import io
        request = drive_manager.service.files().get_media(
            fileId=file_id,
            supportsAllDrives=True
        )
        content = io.BytesIO()
        from googleapiclient.http import MediaIoBaseDownload
        downloader = MediaIoBaseDownload(content, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        
        text_content = content.getvalue().decode('utf-8')
        
        # Créer un nouveau Google Doc
        print("📝 Création du Google Doc...")
        doc_metadata = {
            'name': file_info['name'].replace('.txt', ''),
            'mimeType': 'application/vnd.google-apps.document',
            'parents': file_info.get('parents', [])
        }
        
        doc = drive_manager.service.files().create(
            body=doc_metadata,
            supportsAllDrives=True
        ).execute()
        
        doc_id = doc['id']
        print(f"✅ Google Doc créé: {doc['name']} (ID: {doc_id})")
        
        # Insérer le contenu dans le Google Doc
        print("📝 Insertion du contenu...")
        from googleapiclient.discovery import build
        docs_service = build('docs', 'v1', credentials=drive_manager.service._http.credentials)
        
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': text_content
                }
            }
        ]
        
        docs_service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()
        
        print(f"✅ Conversion réussie !")
        print(f"   Ancien fichier: {file_info['name']} (ID: {file_id})")
        print(f"   Nouveau Doc: {doc['name']} (ID: {doc_id})")
        print(f"   URL: https://docs.google.com/document/d/{doc_id}/edit")
        
        # Suppression automatique gérée par le batch, rien ici
        
        return doc_id
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return None

def find_file_by_name(drive_manager, name, folder_id):
    """Cherche un fichier par nom dans un dossier"""
    try:
        escaped_name = name.replace("'", "\\'")
        query = f"name='{escaped_name}' and '{folder_id}' in parents and trashed=false"
        
        results = drive_manager.service.files().list(
            q=query,
            fields="files(id, name, mimeType)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True
        ).execute()
        
        files = results.get('files', [])
        return files[0] if files else None
        
    except Exception as e:
        print(f"❌ Erreur recherche: {e}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 convert_txt_to_gdoc.py <file_id_or_name>")
        print("\nExemple:")
        print("  python3 convert_txt_to_gdoc.py 1ABC123...")
        print("  python3 convert_txt_to_gdoc.py 'Mon fichier.txt'")
        sys.exit(1)
    
    # Initialiser DriveManager
    credentials_path = Path(__file__).parent.parent / 'config' / 'credentials.json'
    config_path = Path(__file__).parent.parent / 'config' / 'highlight_config.json'
    
    with open(config_path) as f:
        config = json.load(f)
    
    drive_manager = DriveManager(str(credentials_path))
    
    file_input = sys.argv[1]
    
    # Si c'est un nom de fichier, le chercher
    if not file_input.startswith('1'):
        print(f"🔍 Recherche du fichier '{file_input}'...")
        folder_id = config['drive_folders']['highlighted_files']
        file_info = find_file_by_name(drive_manager, file_input, folder_id)
        
        if not file_info:
            print(f"❌ Fichier '{file_input}' non trouvé dans le dossier highlighted_files")
            sys.exit(1)
        
        file_id = file_info['id']
        print(f"✅ Trouvé: {file_info['name']} (ID: {file_id})")
    else:
        file_id = file_input
    
    # Convertir
    convert_txt_to_gdoc(drive_manager, file_id)
