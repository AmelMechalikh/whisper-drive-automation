# Guide Simple - Créer des extraits vidéo à partir de transcriptions

## 🎯 En résumé

Ce guide vous explique comment créer automatiquement des extraits vidéo à partir d'une transcription, simplement en surlignant du texte dans Google Docs.

---

## ✅ Ce dont vous avez besoin

1. Un fichier de transcription dans Google Drive (se termine par `_paragraphs_timestamps`)
2. La vidéo complète correspondante dans le dossier "Files"
3. Un accès à Google Docs

---

## 📝 Les étapes (c'est simple !)

### Étape 1 : Ouvrir votre transcription

Allez dans Google Drive, dossier **"Highlighted Files"**, et ouvrez votre fichier de transcription.

Le fichier ressemble à ça :
```
(0:25) Premier paragraphe de texte...

(2:30) Deuxième paragraphe...

(5:10) Troisième paragraphe...
```

---

### Étape 2 : Surligner les passages que vous voulez extraire

**👉 Avec votre souris :**
1. Sélectionnez le texte que vous voulez dans votre vidéo
2. Le texte se surligne en jaune
3. Vous pouvez surligner plusieurs passages

**💡 Conseil :** Vous pouvez surligner un long passage (plusieurs paragraphes) ou plusieurs petits passages séparés.

---

### Étape 3 : Ajouter un numéro à chaque passage

**Pour chaque passage surligné :**

1. **Clic droit** sur le texte surligné
2. Cliquer sur **"Commenter"** (💬)
3. Dans le commentaire, écrire simplement :
   - `s1` pour le premier extrait vidéo
   - `s2` pour le deuxième extrait vidéo
   - `s3` pour le troisième, etc.

**Important :** Si vous voulez fusionner plusieurs passages dans UNE SEULE vidéo, mettez le même numéro !

---

### Exemple concret

**Vous voulez créer 2 vidéos :**

**Vidéo 1** : Deux passages sur le même sujet
```
Passage A (2:30-3:00) → Surligner + Commenter "s1"
Passage B (5:10-6:00) → Surligner + Commenter "s1"
```

**Vidéo 2** : Un passage différent
```
Passage C (10:00-11:00) → Surligner + Commenter "s2"
```

**Résultat automatique :**
- 1 vidéo "s1" qui combine les passages A + B
- 1 vidéo "s2" avec le passage C

---

### Étape 4 : Attendre (5-10 minutes)

C'est tout ! **Le système fait le reste automatiquement** :

✅ Il lit vos commentaires
✅ Il trouve les timestamps exacts
✅ Il découpe la vidéo
✅ Il fusionne les segments si nécessaire
✅ Il enregistre les vidéos dans Drive

**Où trouver vos vidéos ?**
→ Google Drive > Dossier **"Segments Videos"** > Un sous-dossier avec le nom de votre fichier

---

## 🎬 Vos vidéos sont prêtes !

Vous y trouverez des fichiers comme :
- `s1_0230-0300_0510-0600.mp4` (votre première vidéo)
- `s2_1000-1100.mp4` (votre deuxième vidéo)

Les noms indiquent les timestamps des passages extraits.

---

## ❓ Questions fréquentes

### Combien de temps ça prend ?
**5 à 10 minutes** maximum après avoir ajouté vos commentaires.

### Je peux surligner combien de passages ?
**Autant que vous voulez !** Utilisez `s1`, `s2`, `s3`, etc.

### Je peux surligner un long passage ?
**Oui !** Vous pouvez surligner plusieurs paragraphes d'un coup.

### Je veux modifier mes extraits, comment faire ?
1. Supprimer les fichiers générés dans Drive (Excel + vidéos)
2. Modifier vos surlignages/commentaires
3. Attendre 5-10 minutes pour la nouvelle génération

### Ça marche pas, que faire ?
Vérifier que :
- ✅ Le nom du fichier transcription correspond à la vidéo
- ✅ La vidéo est bien dans le dossier "Files"
- ✅ Les commentaires sont bien `s1`, `s2`, etc. (pas d'espaces, pas de majuscules)
- ✅ Vous avez attendu au moins 10 minutes

---

## 💡 Astuces pour de meilleurs résultats

### ✅ À FAIRE

- Surligner des **phrases complètes** avec du contexte
- Utiliser le **même numéro** pour des passages sur le même thème
- Vérifier que le **texte surligné** correspond exactement à la transcription
- Attendre que les vidéos soient créées **avant de modifier**

### ❌ À ÉVITER

- Ne pas surligner juste 1 ou 2 mots (trop court)
- Ne pas utiliser de commentaires fantaisie (restez sur `s1`, `s2`, etc.)
- Ne pas modifier les commentaires pendant le traitement
- Ne pas supprimer le fichier de transcription original

---

## 📁 Où se trouvent mes fichiers ?

```
Google Drive/
│
├── Highlighted Files/           ← VOUS : Vos transcriptions ici
│   └── Ma_conference_paragraphs_timestamps
│
├── Files/                       ← SYSTÈME : Vidéo source ici
│   └── Ma_conference.mp4
│
├── Excel Output/                ← SYSTÈME : Fichier technique généré
│   └── Ma_conference_highlights.xlsx
│
└── Segments Videos/             ← VOUS : VOS EXTRAITS VIDÉO ICI ! 🎬
    └── Ma_conference/
        ├── s1_0230-0525.mp4    ← Votre première vidéo
        └── s2_1003-1116.mp4    ← Votre deuxième vidéo
```

**👉 Vous n'avez besoin que de 2 dossiers :**
- **"Highlighted Files"** → Vous y travaillez (surlignage + commentaires)
- **"Segments Videos"** → Vous y récupérez vos vidéos finales

---

## 🎓 Exemple pas à pas

### Situation
Vous avez une vidéo de conférence de 1 heure et vous voulez extraire 3 passages intéressants.

### Actions

**1. Ouvrir la transcription**
- `Conference_2024_paragraphs_timestamps` dans "Highlighted Files"

**2. Surligner et commenter**
- Passage minute 2:30 → Surligner → Commenter `s1`
- Passage minute 15:20 → Surligner → Commenter `s2`
- Passage minute 45:00 → Surligner → Commenter `s3`

**3. Fermer le fichier**

**4. Attendre 10 minutes**

**5. Aller dans "Segments Videos/Conference_2024"**

### Résultat
```
✅ s1_0230-0308.mp4 (38 secondes)
✅ s2_1520-1605.mp4 (45 secondes)
✅ s3_4500-4630.mp4 (1m30)
```

### Utiliser vos vidéos
- Téléchargez-les
- Partagez-les
- Montez-les dans un éditeur vidéo
- Publiez-les sur les réseaux sociaux

---

## 🆘 Besoin d'aide ?

**Le système vérifie automatiquement toutes les 5 minutes.**
Si après 15 minutes vos vidéos ne sont pas là, contactez le support technique avec :
- Le nom exact de votre fichier
- La date et l'heure où vous avez ajouté les commentaires

---

**C'est tout ! Profitez de vos extraits vidéo automatiques ! 🎉**
