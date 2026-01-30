"""
Utilitaires pour le calcul et l'extraction de hash MD5 des segments
"""
import hashlib
import re
from typing import List, Tuple, Union, Dict, Optional


def calculate_segments_hash(segments_list: List[Union[Tuple[float, float], Dict]]) -> str:
    """
    Calcule un hash MD5 (8 caractères) basé uniquement sur les timestamps

    Args:
        segments_list: Liste de tuples (start, end) ou dicts avec 'start'/'end'

    Returns:
        Hash de 8 caractères (ex: "abc123de")

    Examples:
        >>> calculate_segments_hash([(10.5, 20.3), (30.2, 45.7)])
        'e8f3a2b1'
        >>> calculate_segments_hash([{'start': 10.5, 'end': 20.3}])
        '7c9d1e4f'
    """
    # Normaliser en liste de tuples (start, end)
    pairs = []
    for seg in segments_list:
        if isinstance(seg, dict):
            pairs.append((seg['start'], seg['end']))
        else:
            pairs.append(seg)

    # Créer chaîne : "10.5,20.3|30.2,45.7"
    hash_input = "|".join([f"{start},{end}" for start, end in pairs])
    return hashlib.md5(hash_input.encode()).hexdigest()[:8]


def extract_hash_from_filename(filename: str) -> Optional[str]:
    """
    Extrait le hash du nom de fichier Excel

    Args:
        filename: "GSE_du_8_janvier_highlights_abc123de.xlsx"

    Returns:
        Hash de 8 caractères ou None

    Examples:
        >>> extract_hash_from_filename("test_highlights_abc123de.xlsx")
        'abc123de'
        >>> extract_hash_from_filename("test_highlights.xlsx")
        None
    """
    match = re.search(r'_highlights_([a-f0-9]{8})\.xlsx$', filename)
    return match.group(1) if match else None
