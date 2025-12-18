"""
Configuration module pour l'automation Whisper + Google Drive
"""
import os

# Google Drive Configuration
# Support pour credentials via variable d'environnement ou fichier
import json
import tempfile

def get_credentials_path():
    # 1. Essayer la variable d'environnement GOOGLE_CREDENTIALS (JSON)
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    if creds_json:
        # Créer un fichier temporaire avec le contenu JSON
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write(creds_json)
        temp_file.close()
        return temp_file.name
    
    # 2. Fichier monté comme secret Cloud Run
    cloud_run_path = '/app/secrets/credentials.json'
    if os.path.exists(cloud_run_path):
        return cloud_run_path
        
    # 3. Ancien emplacement secret Cloud Run
    old_cloud_run_path = '/app/config/credentials.json'
    if os.path.exists(old_cloud_run_path):
        return old_cloud_run_path
    
    # 4. Fichier local
    local_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    if os.path.exists(local_path):
        return local_path
    
    return None

CREDENTIALS_PATH = get_credentials_path()

# IDs des dossiers Google Drive
DRIVE_FOLDERS = {
    'input': '1A29pkQvrBodU_HxNS8deYt6T27AlmbSe',    # Dossier Files
    'output': '1yHcy9um2_We459w9I0cITwHBGXKTlOJa',   # Dossier Transcriptions
    'queue': '1yvN9VP0bAmZJGfyUlBFG4mzR22c5addV'     # Dossier Queue pour jobs VM
}

# Configuration Whisper
WHISPER_CONFIG = {
    'model': 'small',  # base, small, large - small = excellent compromis qualité/vitesse
    'language': 'fr',  # Auto-détection si None
    'device': 'cpu',   # cpu ou cuda
    'vocabulary': [     # Mots techniques à reconnaître
        'Guéshé Kelsang Gyatso',
        'Kadampa', 
        'Chakra Sambhara',
        'Rinpoche',
        'Vénérable',
        'Geshe',
        'Balado'
    ]
}

# Extensions de fichiers supportées
SUPPORTED_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.mp4', '.mov', '.avi', '.mkv']

# Configuration de sortie
OUTPUT_FORMATS = {
    'transcription': True,      # fichier_transcription.txt
    'srt': True,               # fichier_with_timestamps.srt
    'word_timestamps': True,    # fichier_word_timestamps.txt
    'paragraphs': True,        # fichier_paragraphs_timestamps.txt
    'complete_json': True      # fichier_complete_data.json
}

# Configuration des paragraphes
PARAGRAPH_CONFIG = {
    'pause_threshold': 3.0,    # Secondes de pause pour nouveau paragraphe
    'min_words': 5,            # Minimum de mots par paragraphe
    'max_duration': 30.0       # Durée maximale d'un paragraphe (secondes)
}

# Configuration des logs
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file': 'whisper_automation.log'
}

# Mode test (limitation à 10 minutes)
TEST_MODE = {
    'enabled': False,
    'duration_seconds': 600    # 10 minutes
}