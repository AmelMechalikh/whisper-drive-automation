"""
Module d'initialisation du package whisper-drive-automation
"""

from .drive_manager import DriveManager
from .whisper_transcriber import WhisperTranscriber
from .output_generator import OutputGenerator
from .processor import WhisperDriveProcessor
from .orchestrator import DriveOrchestrator

__version__ = "1.0.0"
__author__ = "Whisper Drive Automation"
__description__ = "Système automatisé de transcription audio utilisant Google Drive et OpenAI Whisper"

__all__ = [
    'DriveManager',
    'WhisperTranscriber', 
    'OutputGenerator',
    'WhisperDriveProcessor',
    'DriveOrchestrator'
]