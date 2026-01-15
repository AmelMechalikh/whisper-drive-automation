#!/usr/bin/env python3
"""
Vérifie le nouvel Excel créé
"""
import sys
from pathlib import Path
import openpyxl

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from drive_manager import DriveManager

# Nouvel ID Excel (depuis les logs : 1zs4q5sAPsB3UEVtp4VmoXJ3iB4tY4Tc1)
EXCEL_ID = "1zs4q5sAPsB3UEVtp4VmoXJ3iB4tY4Tc1"

def main():
    manager = DriveManager(credentials_path='./config/credentials.json')

    # Télécharger l'Excel
    file_name = 'new_excel.xlsx'
    full_path = '/tmp/new_excel.xlsx'
    print(f"📥 Téléchargement du nouvel Excel...")

    manager.download_file(EXCEL_ID, file_name, full_path)
    print(f"✅ Téléchargé")
    print("")

    # Lire l'Excel
    wb = openpyxl.load_workbook(full_path)
    ws = wb.active

    print("=" * 80)
    print("📊 TOUS LES SEGMENTS DANS LE NOUVEL EXCEL")
    print("=" * 80)
    print("")

    # Données
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        numero = row[0]
        groupe = row[1]  # S1, S2, etc.
        sous_segment = row[2]
        start_seconds = row[4]
        end_seconds = row[5]
        start_time = row[6]
        end_time = row[7]

        print(f"{groupe} (sous-segment {sous_segment}): {start_seconds}s → {end_seconds}s ({start_time} → {end_time})")

if __name__ == '__main__':
    main()
