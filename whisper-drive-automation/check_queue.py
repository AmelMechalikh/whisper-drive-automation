#!/usr/bin/env python3
"""
Script pour vérifier les doublons dans la queue
"""
import sys
sys.path.insert(0, 'src')
sys.path.insert(0, 'config')

from drive_manager import DriveManager
import whisper_config as config
import json

drive_manager = DriveManager(config.CREDENTIALS_PATH)
queue_folder = config.DRIVE_FOLDERS['queue']

# Lister tous les jobs
query = f"'{queue_folder}' in parents and name contains 'job_' and name contains '.json' and trashed=false"
results = drive_manager.service.files().list(
    q=query,
    fields="files(id, name, createdTime)",
    orderBy='createdTime',
    supportsAllDrives=True,
    includeItemsFromAllDrives=True
).execute()

job_files = results.get('files', [])

print(f"📋 Total jobs dans la queue: {len(job_files)}\n")

# Grouper par file_id
from collections import defaultdict
jobs_by_file = defaultdict(list)

for job in job_files:
    # Télécharger le contenu du job
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
        temp_path = f.name

    drive_manager.download_file(job['id'], job['name'], temp_path)

    with open(temp_path, 'r') as f:
        job_data = json.load(f)

    import os
    os.remove(temp_path)

    file_id = job_data.get('file_id')
    file_name = job_data.get('file_name')

    jobs_by_file[file_id].append({
        'job_id': job['id'],
        'job_name': job['name'],
        'file_name': file_name,
        'created': job['createdTime']
    })

# Afficher les doublons
print("🔍 Analyse des doublons:\n")
duplicates_found = False

for file_id, jobs in jobs_by_file.items():
    if len(jobs) > 1:
        duplicates_found = True
        print(f"⚠️  DOUBLON: {jobs[0]['file_name']}")
        print(f"   File ID: {file_id}")
        print(f"   Nombre de jobs: {len(jobs)}")
        for i, job in enumerate(jobs, 1):
            print(f"   {i}. {job['job_name']} (créé: {job['created']})")
        print()

if not duplicates_found:
    print("✅ Aucun doublon trouvé")
else:
    print(f"\n❌ Total fichiers avec doublons: {sum(1 for jobs in jobs_by_file.values() if len(jobs) > 1)}")
