#!/usr/bin/env python3
"""
Script de test pour transcrire le fichier WhatsApp Audio
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.insert(0, str(Path(__file__).parent / 'config'))

import whisper_config as config
from src.processor import WhisperDriveProcessor

# Initialiser le processeur
print("🔧 Initialisation du processeur...")
processor = WhisperDriveProcessor(config)

# ID du fichier WhatsApp Audio
file_id = "1JBsckpoM3uYArjYMYPY2-o0agnJqQeI-"
file_name = "WhatsApp Audio 2026-01-13 at 17.49.57.mp4"

file_info = {
    'id': file_id,
    'name': file_name,
    'mimeType': 'video/mp4'
}

print(f"🎯 Test de transcription: {file_name}")
print("=" * 80)

# Traiter le fichier
success = processor.process_single_file(file_id)

print("=" * 80)
if success:
    print("✅ Test réussi !")
else:
    print("❌ Test échoué")
