#!/usr/bin/env python3
"""
Script pour copier un document dans le dossier queue_highlights
et déclencher le traitement
"""
import sys
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Document à traiter
DOCUMENT_ID = "1jxJi6WQj_gCU6t_ZHj7DtZefEb1NgUyJr3KczfkUeEk"
QUEUE_FOLDER_ID = "1Dc5kkTvBOSYXuB103vAwYHTpPAsW8G9Q"

# Credentials
creds_path = Path(__file__).parent / 'config' / 'credentials.json'
creds = Credentials.from_service_account_file(
    str(creds_path),
    scopes=['https://www.googleapis.com/auth/drive']
)

drive_service = build('drive', 'v3', credentials=creds)

print("📋 Copie du document dans le dossier queue_highlights...")

# Copier le fichier dans le dossier queue
try:
    # Récupérer les infos du fichier source
    file_info = drive_service.files().get(
        fileId=DOCUMENT_ID,
        fields='name'
    ).execute()

    print(f"   Document: {file_info['name']}")

    # Copier le fichier
    copied_file = drive_service.files().copy(
        fileId=DOCUMENT_ID,
        body={
            'name': file_info['name'],
            'parents': [QUEUE_FOLDER_ID]
        }
    ).execute()

    print(f"✅ Document copié dans queue_highlights")
    print(f"   ID de la copie: {copied_file['id']}")
    print(f"\n🎬 Le worker va le détecter dans ~60 secondes...")
    print(f"\n📊 Pour suivre les logs en temps réel:")
    print(f"   gcloud compute ssh highlights-worker-vm --zone=europe-west1-b --command='sudo journalctl -u highlights-worker -f'")

except Exception as e:
    print(f"❌ Erreur: {e}")
    sys.exit(1)
