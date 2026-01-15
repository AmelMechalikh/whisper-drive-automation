#!/usr/bin/env python3
"""
Nettoie et réinitialise pour un nouveau traitement
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from drive_manager import DriveManager
from googleapiclient.discovery import build

def main():
    manager = DriveManager(credentials_path='./config/credentials.json')

    print("🧹 Nettoyage pour nouveau traitement")
    print("=" * 80)
    print("")

    # 1. Supprimer l'ancien Excel
    excel_id = "1Bo6c06DLfQbiAk60lw-z3MEEE92dH-um"
    print(f"🗑️  Suppression de l'ancien Excel (ID: {excel_id})...")
    try:
        manager.service.files().delete(fileId=excel_id, supportsAllDrives=True).execute()
        print("   ✅ Excel supprimé")
    except Exception as e:
        print(f"   ⚠️  Erreur suppression Excel: {e}")
    print("")

    # 2. Supprimer les anciens jobs
    print("🗑️  Suppression des anciens jobs dans queue_highlights...")
    queue_folder = "1Dc5kkTvBOSYXuB103vAwYHTpPAsW8G9Q"

    try:
        files = manager.list_files_in_folder(queue_folder)
        job_files = [f for f in files if 'highlight_job_' in f['name'] and 'Séance 3 jour 1' in f['name']]

        for job in job_files:
            print(f"   🗑️  Suppression: {job['name']}")
            manager.service.files().delete(fileId=job['id'], supportsAllDrives=True).execute()

        print(f"   ✅ {len(job_files)} job(s) supprimé(s)")
    except Exception as e:
        print(f"   ⚠️  Erreur suppression jobs: {e}")
    print("")

    # 3. Trouver le document _paragraphs_timestamps
    print("📄 Recherche du document _paragraphs_timestamps...")
    transcriptions_folder = "1yHcy9um2_We459w9I0cITwHBGXKTlOJa"

    try:
        files = manager.list_files_in_folder(transcriptions_folder)
        doc_files = [f for f in files if 'Séance 3 jour 1' in f['name'] and '_paragraphs_timestamps' in f['name']]

        if not doc_files:
            print("   ❌ Document non trouvé")
            return

        doc = doc_files[0]
        doc_id = doc['id']
        print(f"   ✅ Document trouvé: {doc['name']} (ID: {doc_id})")
        print("")

        # 4. Modifier le document: retirer PROCESSED, ajouter READY
        print("✏️  Mise à jour des balises dans le document...")

        # Construire le service Docs
        from google.oauth2.service_account import Credentials

        creds = Credentials.from_service_account_file(
            './config/credentials.json',
            scopes=['https://www.googleapis.com/auth/documents']
        )
        docs_service = build('docs', 'v1', credentials=creds)

        # Récupérer le document
        document = docs_service.documents().get(documentId=doc_id).execute()
        content = document.get('content', [])

        # Trouver et remplacer PROCESSED par READY
        requests = []

        # Chercher "🎬 PROCESSED 🎬" et le remplacer par "🎬 READY 🎬"
        requests.append({
            'replaceAllText': {
                'containsText': {
                    'text': '🎬 PROCESSED 🎬',
                    'matchCase': False
                },
                'replaceText': '🎬 READY 🎬'
            }
        })

        # Exécuter les modifications
        if requests:
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            print("   ✅ Balise READY ajoutée")
        else:
            print("   ℹ️  Aucune modification nécessaire")

    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    print("")
    print("=" * 80)
    print("✅ Nettoyage terminé!")
    print("")
    print("⏳ Le scheduler va retraiter le fichier dans les 5 prochaines minutes")
    print("")

if __name__ == '__main__':
    main()
