#!/usr/bin/env python3
"""
Vérifie le format d'un Google Doc spécifique
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.drive_manager import DriveManager
from config import whisper_config as config
from googleapiclient.discovery import build

drive_manager = DriveManager(config.CREDENTIALS_PATH)

# Document à vérifier
DOC_ID = "1DVX3sSEyGhfYZCaJI91upYf1KtQON_RLUVo9KwKX8K4"  # Apprendre de tout_paragraphs_timestamps

print("📄 Lecture du contenu du Google Doc...")

# Créer le service Docs API
docs_service = build('docs', 'v1', credentials=drive_manager.creds)

# Lire le document
doc = docs_service.documents().get(documentId=DOC_ID).execute()

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

print("\n" + "="*80)
print("CONTENU DU DOCUMENT (premiers 1500 caractères):")
print("="*80)
print(text[:1500])
print("\n" + "="*80)

# Vérifier le format
if "=== Paragraphe" in text:
    print("\n🔴 ANCIEN FORMAT DÉTECTÉ!")
    print("   Le document contient '=== Paragraphe'")
elif "Temps:" in text and "Mots:" in text:
    print("\n🔴 ANCIEN FORMAT DÉTECTÉ!")
    print("   Le document contient 'Temps:' et 'Mots:'")
elif text.strip().startswith("(") and ":" in text.split("\n")[0]:
    print("\n🟢 NOUVEAU FORMAT DÉTECTÉ!")
    print("   Le document commence par un timestamp (M:SS)")
else:
    print("\n⚠️  FORMAT INCONNU ou vide")

print(f"\n📊 Longueur totale: {len(text)} caractères")
