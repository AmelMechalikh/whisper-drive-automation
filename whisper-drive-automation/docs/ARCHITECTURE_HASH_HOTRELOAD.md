# Architecture : Hash-based deduplication + Hot Reload

## 📅 Date : 2026-01-23
## 🎯 Statut : À IMPLÉMENTER PLUS TARD

---

## 🔴 Problème actuel

L'utilisateur peut remettre la balise `🎬 READY 🎬` plusieurs fois, ce qui crée des jobs en doublon même si le contenu (timestamps) n'a pas changé.

**Cas observé :**
- Job "Sagesse Bouddhiste" traité 3 fois avec les mêmes segments
- Gaspillage de ressources (temps, bande passante, coûts)

---

## 💡 Solution proposée : Hash des timestamps

### Principe

Calculer un **hash MD5 (8 caractères)** basé uniquement sur les **timestamps des segments** :

```python
def calculate_segments_hash(segments: List[Dict]) -> str:
    """
    Calcule un hash basé uniquement sur les timestamps
    segments = [{'start': 10.5, 'end': 20.3}, ...]
    """
    import hashlib
    hash_input = "|".join([f"{s['start']},{s['end']}" for s in segments])
    return hashlib.md5(hash_input.encode()).hexdigest()[:8]
```

**Exemple :**
- Segments : `[(10.5, 20.3), (30.2, 45.7)]`
- Hash input : `"10.5,20.3|30.2,45.7"`
- Hash : `abc123de`
- Nom Excel : `GSE_du_8_janvier_highlights_abc123de.xlsx`

---

## 🏗️ Architecture

### 1. Cloud Run Orchestrator

**Modifications dans `highlight_orchestrator_cloud.py` :**

```python
def process_highlighted_file(self, file_info: dict):
    """Génère Excel avec hash"""

    # 1. Extraire les highlights comme actuellement
    excel_path = self.highlight_extractor.extract_highlights_from_drive_file(...)

    # 2. Lire l'Excel pour calculer le hash
    df = pd.read_excel(excel_path)
    segments = []
    for _, row in df.iterrows():
        segments.append({
            'start': row['Début (secondes)'],
            'end': row['Fin (secondes)']
        })

    # 3. Calculer le hash
    new_hash = calculate_segments_hash(segments)

    # 4. Vérifier si Excel avec ce hash existe déjà
    existing_excels = self.drive_manager.list_files_in_folder(
        self.config['drive_folders']['excel_output'],
        name_pattern=f"{base_name}_highlights_*.xlsx"
    )

    for excel in existing_excels:
        existing_hash = extract_hash_from_filename(excel['name'])
        if existing_hash == new_hash:
            logger.info(f"⏭️ Segments identiques (hash: {new_hash}) - pas de nouveau job")
            return None  # Ne pas créer de job

    # 5. Renommer l'Excel avec le hash
    excel_filename = f"{base_name}_highlights_{new_hash}.xlsx"

    # 6. Uploader avec le nouveau nom
    excel_id = self.drive_manager.upload_file(excel_path, excel_filename, ...)

    # 7. Créer le job
    self._create_video_job(base_name, excel_id, excel_filename)
```

**Fonction utilitaire :**
```python
def extract_hash_from_filename(filename: str) -> str:
    """
    Extrait le hash du nom de fichier Excel
    Ex: "GSE_du_8_janvier_highlights_abc123de.xlsx" → "abc123de"
    """
    import re
    match = re.search(r'_highlights_([a-f0-9]{8})\.xlsx$', filename)
    return match.group(1) if match else None
```

---

### 2. VM Worker (Hot Reload - OPTIONNEL)

**Si on veut le hot reload (détection pendant traitement) :**

```python
def extract_segments(self, excel_path, source_video_path, output_folder):
    """Découpe les segments avec hot reload"""

    # Extraire le hash de l'Excel actuel
    current_hash = extract_hash_from_filename(Path(excel_path).name)
    base_name = extract_base_name(Path(excel_path).name)

    # Lire l'Excel
    df = pd.read_excel(excel_path)
    grouped = df.groupby('Numéro')

    last_check_time = time.time()

    for segment_num, group in grouped:
        # Checker toutes les 30s si nouvel Excel
        if time.time() - last_check_time > 30:
            newer_excel = self._check_for_newer_excel(base_name, current_hash)
            if newer_excel:
                logger.warning(f"⚠️ Nouvel Excel détecté (hash différent) - restart")
                # Nettoyer les fichiers temporaires
                self._cleanup_temp_files(output_folder)
                # Re-télécharger le nouvel Excel
                new_excel_path = self._download_excel(newer_excel['id'], newer_excel['name'])
                # Recommencer le découpage (vidéo déjà en cache)
                return self.extract_segments(new_excel_path, source_video_path, output_folder)
            last_check_time = time.time()

        # Découper le segment normalement
        self._extract_segment(...)

def _check_for_newer_excel(self, base_name: str, current_hash: str) -> Optional[Dict]:
    """Vérifie s'il existe un Excel avec hash différent"""
    excel_files = self.drive_manager.list_files_in_folder(
        self.config['drive_folders']['excel_output'],
        name_pattern=f"{base_name}_highlights_*.xlsx"
    )

    for excel in excel_files:
        hash_in_file = extract_hash_from_filename(excel['name'])
        if hash_in_file and hash_in_file != current_hash:
            logger.info(f"🔄 Nouvel Excel détecté : {excel['name']} (hash: {hash_in_file})")
            return excel

    return None
```

---

## ✅ Avantages

1. **Pas de jobs dupliqués** : Si user remet READY 10 fois sans changer les timestamps → 1 seul job
2. **Historique préservé** : Tous les Excel avec différents hashs restent sur Drive
3. **Hot reload (optionnel)** : La VM peut détecter les changements en temps réel
4. **Économies** : Moins de téléchargements vidéo, moins de découpage inutile

---

## ⚠️ Considérations

### Hash collision ?
- MD5 8 caractères = 4.3 milliards de combinaisons
- Pour ce use case (quelques vidéos par jour) : risque négligeable

### Ancien comportement
- **Avant** : Changer le TEXTE d'un commentaire = nouveau job
- **Après** : Changer le TEXTE = pas de nouveau job (seuls les timestamps comptent)
- Si l'user veut forcer un retraitement → Modifier légèrement un timestamp (ex: 10.5 → 10.6)

### Hot reload complexité
- ✅ Simple : Check Drive toutes les 30s
- ✅ Vidéo déjà en cache (/tmp)
- ⚠️ Doit nettoyer proprement les fichiers temporaires
- ⚠️ Gestion des erreurs pendant l'interruption

---

## 📝 Checklist d'implémentation

### Phase 1 : Hash seulement (sans hot reload)
- [ ] Ajouter fonction `calculate_segments_hash()` dans utils
- [ ] Modifier `process_highlighted_file()` pour calculer hash
- [ ] Modifier upload Excel pour inclure hash dans le nom
- [ ] Ajouter vérification hash avant création job
- [ ] Tester avec Excel existant et nouveau contenu
- [ ] Déployer sur Cloud Run

### Phase 2 : Hot reload (optionnel)
- [ ] Ajouter `_check_for_newer_excel()` dans VM worker
- [ ] Modifier boucle d'extraction pour checker périodiquement
- [ ] Ajouter nettoyage propre des temp files
- [ ] Tester interruption et restart
- [ ] Gérer les cas d'erreur (Excel corrompu, Drive indisponible, etc.)
- [ ] Déployer sur VM

---

## 🧪 Tests requis

1. **Cas nominal** : User met READY → Excel créé avec hash → Job traité
2. **Doublon** : User remet READY sans changer timestamps → Pas de nouveau job
3. **Modification** : User change timestamps → Nouveau hash → Nouveau job créé
4. **Historique** : Vérifier que les anciens Excel restent sur Drive
5. **Hot reload** : User modifie pendant traitement → VM détecte et redémarre

---

## 📊 Impact estimé

- **Développement** : 2-3 heures (hash) + 2-3 heures (hot reload)
- **Tests** : 1-2 heures
- **Économies** : ~50-80% de jobs dupliqués évités
- **Risques** : Faibles si bien testé

---

## 📚 Références

- Code actuel : `scripts/highlight_orchestrator_cloud.py`
- VM worker : `scripts/highlights_vm_worker.py`
- Config : `config/highlight_config.json`
