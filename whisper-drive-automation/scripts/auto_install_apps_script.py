#!/usr/bin/env python3
"""
Script pour installer automatiquement le menu Apps Script
sur tous les fichiers _paragraphs_timestamps du dossier transcriptions
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Ajouter le chemin du projet au PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.drive_manager import DriveManager

# Script ID de la bibliothèque standalone
LIBRARY_SCRIPT_ID = "1R6unJ92rXrhGwzneC1r1uT1t668ljf68fXJAchSBY_kEnADcoIyuoUTT"

# Code du wrapper à injecter
WRAPPER_CODE = """/**
 * Wrapper pour utiliser la bibliothèque Marqueur Segments Vidéo
 * Installé automatiquement par le système backend
 */

function onOpen() {
  MarqueurSegmentsVideo.onOpen();
}

function marquerS1() { MarqueurSegmentsVideo.marquerS1(); }
function marquerS2() { MarqueurSegmentsVideo.marquerS2(); }
function marquerS3() { MarqueurSegmentsVideo.marquerS3(); }
function marquerS4() { MarqueurSegmentsVideo.marquerS4(); }
function marquerS5() { MarqueurSegmentsVideo.marquerS5(); }
function marquerS6() { MarqueurSegmentsVideo.marquerS6(); }
function marquerS7() { MarqueurSegmentsVideo.marquerS7(); }
function marquerS8() { MarqueurSegmentsVideo.marquerS8(); }
function marquerS9() { MarqueurSegmentsVideo.marquerS9(); }
function marquerS10() { MarqueurSegmentsVideo.marquerS10(); }
function marquerPersonnalise() { MarqueurSegmentsVideo.marquerPersonnalise(); }
function retirerMarqueurs() { MarqueurSegmentsVideo.retirerMarqueurs(); }
function listerSegments() { MarqueurSegmentsVideo.listerSegments(); }
function marquerCommePret() { MarqueurSegmentsVideo.marquerCommePret(); }
function verifierStatut() { MarqueurSegmentsVideo.verifierStatut(); }
"""

APPSSCRIPT_JSON = """{
  "timeZone": "Europe/Paris",
  "dependencies": {
    "libraries": [{
      "userSymbol": "MarqueurSegmentsVideo",
      "libraryId": "%s",
      "version": "3"
    }]
  },
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8"
}
""" % LIBRARY_SCRIPT_ID


class AppsScriptInstaller:
    """Installe automatiquement le menu Apps Script sur les documents"""

    def __init__(self, credentials_path: str, transcriptions_folder_name: str = "transcriptions"):
        """
        Initialise l'installateur

        Args:
            credentials_path: Chemin vers les credentials du service account
            transcriptions_folder_name: Nom du dossier contenant les transcriptions
        """
        self.credentials_path = Path(credentials_path)
        self.transcriptions_folder_name = transcriptions_folder_name

        # Créer les services Google API
        creds = ServiceAccountCredentials.from_service_account_file(
            str(self.credentials_path),
            scopes=[
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/script.projects'
            ]
        )

        self.drive_service = build('drive', 'v3', credentials=creds)
        self.docs_service = build('docs', 'v1', credentials=creds)
        self.script_service = build('script', 'v1', credentials=creds)

        self.drive_manager = DriveManager(str(self.credentials_path))

    def find_transcriptions_folder(self) -> str:
        """Trouve le dossier transcriptions dans Drive"""
        folder_id = self.drive_manager.get_or_create_folder(self.transcriptions_folder_name)
        print(f"✅ Dossier transcriptions trouvé: {folder_id}")
        return folder_id

    def find_paragraphs_files(self, folder_id: str) -> List[Dict]:
        """
        Trouve tous les fichiers _paragraphs_timestamps dans le dossier

        Args:
            folder_id: ID du dossier transcriptions

        Returns:
            Liste des fichiers trouvés
        """
        query = f"'{folder_id}' in parents and name contains '_paragraphs_timestamps' and trashed=false"

        try:
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)',
                pageSize=1000
            ).execute()

            files = results.get('files', [])
            print(f"📁 {len(files)} fichier(s) _paragraphs_timestamps trouvé(s)")
            return files

        except HttpError as e:
            print(f"❌ Erreur lors de la recherche des fichiers: {e}")
            return []

    def has_apps_script(self, document_id: str) -> bool:
        """
        Vérifie si un document a déjà un script Apps Script attaché

        Args:
            document_id: ID du document Google Docs

        Returns:
            True si le document a déjà un script
        """
        try:
            # Tenter de récupérer le script du document
            # Les scripts container-bound ont le même ID que leur document parent
            self.script_service.projects().get(scriptId=document_id).execute()
            return True
        except HttpError as e:
            if e.resp.status == 404:
                return False
            else:
                print(f"⚠️  Erreur lors de la vérification du script pour {document_id}: {e}")
                return False

    def install_apps_script(self, document_id: str, document_name: str) -> bool:
        """
        Installe le script Apps Script sur un document

        Args:
            document_id: ID du document Google Docs
            document_name: Nom du document

        Returns:
            True si l'installation a réussi
        """
        try:
            print(f"  📝 Installation du script sur '{document_name}'...")

            # Créer le projet Apps Script container-bound
            # Note: L'API Apps Script ne supporte pas directement la création de container-bound scripts
            # Il faut le faire via l'API Drive en créant un fichier de type application/vnd.google-apps.script

            # Créer le contenu du script
            script_content = {
                'title': f'Marqueur Segments - {document_name}',
                'parentId': document_id
            }

            # Créer le fichier Apps Script
            file_metadata = {
                'name': 'Code',
                'mimeType': 'application/vnd.google-apps.script+json',
                'parents': [document_id]
            }

            # Créer les fichiers du projet
            files = [
                {
                    'name': 'Code',
                    'type': 'SERVER_JS',
                    'source': WRAPPER_CODE
                },
                {
                    'name': 'appsscript',
                    'type': 'JSON',
                    'source': APPSSCRIPT_JSON
                }
            ]

            # L'API Apps Script ne supporte pas la création de container-bound scripts programmatically
            # On doit utiliser une approche alternative

            print(f"  ⚠️  L'API Apps Script ne supporte pas la création automatique de container-bound scripts")
            print(f"  💡 Solution: Les utilisateurs doivent ajouter le script manuellement")
            return False

        except HttpError as e:
            print(f"  ❌ Erreur lors de l'installation: {e}")
            return False

    def process_all_files(self) -> Dict[str, int]:
        """
        Traite tous les fichiers _paragraphs_timestamps

        Returns:
            Statistiques: {'total': x, 'already_installed': y, 'newly_installed': z, 'failed': w}
        """
        stats = {
            'total': 0,
            'already_installed': 0,
            'newly_installed': 0,
            'failed': 0
        }

        # Trouver le dossier transcriptions
        folder_id = self.find_transcriptions_folder()

        # Trouver tous les fichiers _paragraphs_timestamps
        files = self.find_paragraphs_files(folder_id)
        stats['total'] = len(files)

        if not files:
            print("ℹ️  Aucun fichier à traiter")
            return stats

        print(f"\n🔧 Traitement de {len(files)} fichier(s)...\n")

        for file in files:
            doc_id = file['id']
            doc_name = file['name']

            print(f"📄 {doc_name}")

            # Vérifier si le script est déjà installé
            if self.has_apps_script(doc_id):
                print(f"  ✅ Script déjà installé")
                stats['already_installed'] += 1
            else:
                # Installer le script
                if self.install_apps_script(doc_id, doc_name):
                    print(f"  ✅ Script installé avec succès")
                    stats['newly_installed'] += 1
                else:
                    stats['failed'] += 1

            print()

        return stats

    def print_stats(self, stats: Dict[str, int]):
        """Affiche les statistiques finales"""
        print("\n" + "="*60)
        print("📊 RÉSUMÉ DE L'INSTALLATION")
        print("="*60)
        print(f"Total de fichiers: {stats['total']}")
        print(f"✅ Déjà installés: {stats['already_installed']}")
        print(f"🆕 Nouvellement installés: {stats['newly_installed']}")
        print(f"❌ Échecs: {stats['failed']}")
        print("="*60)


def main():
    """Point d'entrée principal"""
    # Chemins
    project_root = Path(__file__).parent.parent
    credentials_path = project_root / "credentials" / "service-account.json"

    if not credentials_path.exists():
        print(f"❌ Fichier de credentials non trouvé: {credentials_path}")
        sys.exit(1)

    print("🚀 Installation automatique du menu Apps Script")
    print("="*60)

    # Créer l'installateur
    installer = AppsScriptInstaller(str(credentials_path))

    # Traiter tous les fichiers
    stats = installer.process_all_files()

    # Afficher les statistiques
    installer.print_stats(stats)

    # Message d'information sur la limitation
    if stats['failed'] > 0 or stats['total'] > stats['already_installed']:
        print("\n⚠️  LIMITATION DE L'API GOOGLE")
        print("L'API Apps Script ne permet pas de créer automatiquement des")
        print("container-bound scripts (scripts liés à un document).")
        print("\n💡 SOLUTION:")
        print("Les utilisateurs doivent installer le script manuellement UNE FOIS")
        print("en suivant les instructions dans le README.")
        print(f"\nScript ID à utiliser: {LIBRARY_SCRIPT_ID}")


if __name__ == "__main__":
    main()
