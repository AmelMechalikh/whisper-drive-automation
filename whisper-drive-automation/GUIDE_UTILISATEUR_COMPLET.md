# Guide Utilisateur - Système d'Extraits Vidéo Automatiques

## 🎯 Qu'est-ce que ce système fait ?

**Vous donnez** : Une vidéo ou audio
**Vous obtenez** : Des extraits vidéo des passages que vous choisissez

**Simple en 5 étapes :**
1. Uploader votre fichier
2. Attendre la transcription automatique
3. Copier et annoter la transcription
4. Surligner les passages à extraire
5. Récupérer vos extraits vidéo !

---

## 📋 PARTIE 1 : TRANSCRIPTION

### Étape 1 : Uploader votre fichier audio/vidéo

**📁 Où ?** → Google Drive > Dossier **"Files"**

**Comment ?**
1. Ouvrir le dossier "Files"
2. Glisser-déposer votre fichier
   OU
   Cliquer sur "Nouveau" → "Importer un fichier"

**Formats acceptés :**
- 🎥 Vidéo : MP4, MOV, AVI, MKV
- 🎵 Audio : MP3, M4A, WAV, FLAC, AAC

**💡 Important :** Donnez un nom clair à votre fichier (ex: `Conference_Janvier_2024.mp4`)

---

### Étape 2 : Attendre la transcription automatique

**⏱️ Combien de temps ?**
- Fichier de 10 minutes → ~5-10 minutes de traitement
- Fichier de 1 heure → ~20-30 minutes de traitement

**🔍 Comment savoir si c'est prêt ?**

Allez dans **Google Drive > Dossier "Transcriptions"**

Vous verrez apparaître **5 nouveaux fichiers** :

```
✅ Votre_fichier_paragraphs_timestamps      ← Celui-ci est important !
   Votre_fichier_transcription.txt
   Votre_fichier_with_timestamps.srt
   Votre_fichier_word_timestamps.txt
   Votre_fichier_complete_data.json
```

**Le fichier `_paragraphs_timestamps` ressemble à ça :**
```
(0:25) Premier paragraphe de la transcription...

(2:30) Deuxième paragraphe...

(5:10) Troisième paragraphe...
```

---

### Étape 3 : Copier le fichier dans "Highlighted Files"

**⚠️ ÉTAPE IMPORTANTE - Ne pas sauter !**

**Pourquoi ?** Le système lit uniquement les fichiers dans "Highlighted Files" pour créer les extraits.

**Comment faire :**

1. **Ouvrir** le dossier "Transcriptions"
2. **Trouver** le fichier `Votre_fichier_paragraphs_timestamps`
3. **Clic droit** sur le fichier → "Faire une copie"
4. **Déplacer** la copie dans le dossier **"Highlighted Files"**

**OU (plus simple) :**

1. **Clic droit** sur `Votre_fichier_paragraphs_timestamps`
2. Choisir "Organiser" → "Déplacer"
3. Sélectionner le dossier "Highlighted Files"
4. Cliquer sur "Déplacer ici"

**✅ Vérification :** Votre fichier `_paragraphs_timestamps` doit maintenant être dans "Highlighted Files"

---

## 📋 PARTIE 2 : CRÉATION DES EXTRAITS

### Étape 4 : Ouvrir et annoter la transcription

**1. Ouvrir le fichier**
- Aller dans **Google Drive > "Highlighted Files"**
- Double-cliquer sur `Votre_fichier_paragraphs_timestamps`
- Le fichier s'ouvre dans Google Docs

**2. Lire et repérer les passages intéressants**
- Parcourez la transcription
- Notez mentalement les passages que vous voulez extraire
- Les timestamps (0:25), (2:30) indiquent les minutes dans la vidéo

---

### Étape 5 : Surligner les passages à extraire

**Pour chaque passage que vous voulez dans vos extraits :**

**A. Surligner le texte**
1. **Sélectionner** le texte avec votre souris (du début à la fin du passage)
2. Le texte se surligne en jaune automatiquement
3. Vous pouvez surligner plusieurs paragraphes d'un coup

**B. Ajouter un commentaire**
1. **Clic droit** sur le texte surligné
2. Cliquer sur **"Commenter"** (icône 💬)
3. Dans le commentaire, écrire :
   - `s1` pour le premier extrait vidéo
   - `s2` pour le deuxième extrait vidéo
   - `s3` pour le troisième extrait vidéo
   - etc.
4. Cliquer sur **"Commenter"** (bouton bleu)

**💡 ASTUCE IMPORTANTE : Fusionner des passages**

Si vous voulez **combiner plusieurs passages dans UNE SEULE vidéo**, utilisez le **même numéro** !

**Exemple :**
```
Passage A (2:30) → Surligner → Commenter "s1"
Passage B (5:10) → Surligner → Commenter "s1"  ← même numéro !
Passage C (10:00) → Surligner → Commenter "s2"

Résultat :
→ 1 vidéo "s1" qui fusionne A + B (3 minutes au total)
→ 1 vidéo "s2" avec C (1 minute)
```

---

### Exemple concret

**Situation :** Vous voulez créer 2 extraits d'une conférence

**Ce que vous faites :**

```
1. Surligner ce passage :
   "(2:30) Donc ça, on peut voir, ben, en fait, devenir
   un être éveillé... [3 paragraphes]"
   → Commenter "s1"

2. Surligner ce passage :
   "(4:11) Parce que c'est pour créer une connexion...
   [2 paragraphes]"
   → Commenter "s1"  (même numéro = fusion)

3. Surligner ce passage :
   "(10:03) Donc on imagine être ce boudin...
   [1 paragraphe]"
   → Commenter "s2"
```

**Résultat automatique :**
- ✅ Vidéo "s1" = Passages 2:30 + 4:11 fusionnés
- ✅ Vidéo "s2" = Passage 10:03

---

### Étape 6 : Fermer et attendre

**C'est terminé pour vous !**

1. **Fermer** le fichier Google Docs (vos modifications sont sauvegardées automatiquement)
2. **Attendre 5 à 10 minutes**

**Le système fait tout seul :**
- ✅ Lit vos commentaires
- ✅ Trouve les timestamps exacts
- ✅ Découpe la vidéo aux bons endroits
- ✅ Fusionne les segments si nécessaire
- ✅ Upload les vidéos sur Drive

**📧 Notification (optionnel) :** Vous pouvez demander une notification par email quand c'est prêt.

---

### Étape 7 : Récupérer vos extraits vidéo

**📁 Où les trouver ?**

**Google Drive > "Segments Videos" > [Nom de votre fichier]**

**Exemple :**
```
Segments Videos/
└── Conference_Janvier_2024/
    ├── s1_0230-0308_0411-0525.mp4  ← Votre premier extrait
    └── s2_1003-1116.mp4             ← Votre deuxième extrait
```

**Comprendre les noms de fichiers :**
- `s1` = Numéro du commentaire
- `0230-0308` = De 2:30 à 3:08
- `0411-0525` = De 4:11 à 5:25 (si fusion)
- `.mp4` = Format vidéo

**Que faire ensuite ?**
- ✅ Télécharger les vidéos sur votre ordinateur
- ✅ Les partager directement depuis Drive
- ✅ Les utiliser dans un montage
- ✅ Les publier sur les réseaux sociaux

---

## ❓ Questions Fréquentes

### Combien d'extraits je peux créer ?
**Autant que vous voulez !** Utilisez `s1`, `s2`, `s3`, `s4`, etc.

### Je peux surligner un long passage ?
**Oui !** Vous pouvez surligner plusieurs paragraphes (même 5-10 minutes de vidéo).

### Je peux surligner juste une phrase ?
**Oui**, mais c'est mieux de surligner au moins quelques phrases pour avoir du contexte.

### Combien de temps pour avoir mes extraits ?
**5 à 10 minutes** après avoir ajouté vos commentaires.

### Je veux modifier mes choix, que faire ?
**Option 1 - Avant génération :**
- Modifier vos commentaires dans Google Docs
- Attendre la génération

**Option 2 - Après génération :**
1. Supprimer le dossier de vidéos dans "Segments Videos"
2. Supprimer le fichier Excel dans "Excel Output"
3. Modifier vos commentaires
4. Attendre 5-10 minutes

### Ça ne marche pas, que vérifier ?

**✅ Checklist de vérification :**
- [ ] Le fichier `_paragraphs_timestamps` est bien dans "Highlighted Files"
- [ ] Vous avez bien ajouté des commentaires (s1, s2, etc.)
- [ ] Les commentaires sont bien écrits (`s1` pas `S1` ou `s 1`)
- [ ] La vidéo source est toujours dans "Files"
- [ ] Vous avez attendu au moins 10-15 minutes
- [ ] Le nom du fichier transcription correspond au nom de la vidéo

**Si ça ne marche toujours pas :** Contactez le support technique avec le nom du fichier.

---

## 💡 Conseils pour de meilleurs extraits

### ✅ À FAIRE

**Pour la transcription :**
- Uploader des fichiers avec du son clair
- Nommer vos fichiers clairement
- Éviter les noms avec caractères spéciaux (é, à, ç, espaces)

**Pour les extraits :**
- Surligner des passages complets avec du contexte
- Fusionner les passages sur le même thème (même numéro)
- Vérifier que les timestamps correspondent bien
- Mettre les numéros dans l'ordre (s1, s2, s3...)

### ❌ À ÉVITER

**Pour éviter les problèmes :**
- Ne pas surligner juste 1-2 mots (trop court)
- Ne pas oublier de copier le fichier dans "Highlighted Files"
- Ne pas utiliser de majuscules (S1 → utiliser s1)
- Ne pas ajouter d'espaces (s 1 → utiliser s1)
- Ne pas modifier pendant le traitement
- Ne pas supprimer la vidéo source

---

## 📁 Récapitulatif des dossiers

**Où sont vos fichiers à chaque étape :**

```
📁 Google Drive/
│
├── 📁 Files/
│   └── 🎬 Conference_2024.mp4       ← ÉTAPE 1 : Vous uploadez ici
│
├── 📁 Transcriptions/
│   ├── 📄 Conference_2024_transcription.txt
│   ├── 📄 Conference_2024_paragraphs_timestamps  ← ÉTAPE 2 : Généré automatiquement
│   ├── 📄 Conference_2024_with_timestamps.srt
│   └── 📄 Conference_2024_complete_data.json
│
├── 📁 Highlighted Files/
│   └── 📄 Conference_2024_paragraphs_timestamps  ← ÉTAPE 3 : Vous copiez ici
│                                                    ÉTAPE 4-5 : Vous annotez ici
│
├── 📁 Excel Output/
│   └── 📄 Conference_2024_highlights.xlsx        ← ÉTAPE 6 : Généré automatiquement
│
└── 📁 Segments Videos/
    └── 📁 Conference_2024/
        ├── 🎬 s1_0230-0525.mp4      ← ÉTAPE 7 : Vos extraits finaux ici !
        └── 🎬 s2_1003-1116.mp4
```

**👉 Vous utilisez seulement 3 dossiers :**
1. **"Files"** → Vous uploadez votre vidéo/audio
2. **"Highlighted Files"** → Vous copiez et annotez la transcription
3. **"Segments Videos"** → Vous récupérez vos extraits

---

## 🎓 Exemple complet pas à pas

### Scénario
Vous avez enregistré une conférence de 1 heure et vous voulez extraire 3 passages clés.

### Actions détaillées

**JOUR 1 - Matin**

**9h00** - Uploader la vidéo
- Fichier : `Conference_Leadership_Jan2024.mp4`
- Emplacement : Drive > "Files"
- Action : Glisser-déposer

**9h30** - La transcription est prête
- 5 fichiers créés dans "Transcriptions"
- Fichier important : `Conference_Leadership_Jan2024_paragraphs_timestamps`

**9h35** - Copier le fichier
- Copier `_paragraphs_timestamps` vers "Highlighted Files"

**JOUR 1 - Après-midi**

**14h00** - Annoter la transcription
- Ouvrir le fichier dans "Highlighted Files"
- Lire la transcription
- Surligner 3 passages :
  * Passage 1 (3:25) → Commenter "s1"
  * Passage 2 (18:40) → Commenter "s2"
  * Passage 3 (52:10) → Commenter "s3"
- Fermer le fichier

**14h10** - Les extraits sont créés !
- Aller dans "Segments Videos/Conference_Leadership_Jan2024"
- 3 vidéos disponibles :
  * `s1_0325-0405.mp4` (40 secondes)
  * `s2_1840-1920.mp4` (40 secondes)
  * `s3_5210-5330.mp4` (80 secondes)

**14h15** - Utiliser les extraits
- Télécharger les 3 vidéos
- Créer un montage pour LinkedIn
- Publier ! 🎉

---

## 🔧 Informations techniques (optionnel)

### Système de vérification automatique
Le système vérifie automatiquement **toutes les 5 minutes** :
- S'il y a de nouvelles transcriptions à traiter
- S'il y a de nouveaux extraits à créer

### Qualité de la transcription
- **Modèle IA** : Whisper AI (OpenAI)
- **Langue** : Français
- **Précision** : 90-95% selon la qualité audio
- **Vocabulaire** : Mots techniques pré-entraînés

### Format des vidéos
- **Codec** : H.264 (compatible partout)
- **Qualité** : Copie directe (pas de réencodage = qualité originale)
- **Format** : MP4

---

## 🆘 Support

**Problème technique ?**

Envoyer un message avec :
- Le nom exact du fichier
- La date et l'heure
- Une description du problème
- Une capture d'écran si possible

**Email support :** [à définir]

---

**🎉 C'est tout ! Profitez de vos extraits vidéo automatiques ! 🎉**

---

*Version 1.0 - Janvier 2024*
*Système opérationnel et testé ✅*
