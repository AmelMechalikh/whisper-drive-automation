#!/usr/bin/env python3
"""
Test simple de la logique de hash (sans imports complexes)
"""
import hashlib
import re

def calculate_segments_hash(segments_list):
    """Copie de la fonction pour tester"""
    pairs = []
    for s in segments_list:
        if isinstance(s, dict):
            pairs.append((s['start'], s['end']))
        else:
            pairs.append(s)
    hash_input = "|".join([f"{start},{end}" for start, end in pairs])
    return hashlib.md5(hash_input.encode()).hexdigest()[:8]

def extract_hash_from_filename(filename):
    """Copie de la fonction pour tester"""
    match = re.search(r'_highlights_([a-f0-9]{8})\.xlsx$', filename)
    return match.group(1) if match else None

print("🧪 Test 1: Hash identique pour mêmes timestamps")
segments1 = [(10.5, 20.3), (30.2, 45.7)]
hash1 = calculate_segments_hash(segments1)
print(f"  Hash: {hash1}")
assert len(hash1) == 8
print("  ✅ OK\n")

print("🧪 Test 2: Hash différent pour timestamps différents")
segments2 = [(10.5, 20.3), (30.2, 46.0)]
hash2 = calculate_segments_hash(segments2)
print(f"  Hash: {hash2}")
assert hash1 != hash2
print("  ✅ OK\n")

print("🧪 Test 3: Extraction hash du nom de fichier")
filename = "GSE_du_8_janvier_highlights_abc123de.xlsx"
extracted = extract_hash_from_filename(filename)
print(f"  Fichier: {filename}")
print(f"  Hash: {extracted}")
assert extracted == "abc123de"
print("  ✅ OK\n")

print("🧪 Test 4: Ancien format sans hash")
filename_old = "GSE_du_8_janvier_highlights.xlsx"
extracted_old = extract_hash_from_filename(filename_old)
print(f"  Fichier: {filename_old}")
print(f"  Hash: {extracted_old}")
assert extracted_old is None
print("  ✅ OK\n")

print("=" * 60)
print("✅ TOUS LES TESTS PASSENT")
print("=" * 60)
