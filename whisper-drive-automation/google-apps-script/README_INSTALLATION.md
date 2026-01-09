# Installation du Marqueur de Segments Google Apps Script

## 📋 Introduction

Ce script ajoute un menu personnalisé dans Google Docs pour marquer facilement les segments vidéo à extraire avec le format : `🎬 S1 🎬`.

## 🚀 Installation (5 minutes)

### Étape 1 : Ouvrir Apps Script

1. Ouvrez votre document Google Docs (le fichier `_paragraphs_timestamps`)
2. Dans le menu, cliquez sur **Extensions** → **Apps Script**
3. Une nouvelle fenêtre s'ouvre avec l'éditeur Apps Script

### Étape 2 : Copier le code

1. Supprimez tout le code existant dans l'éditeur (généralement `function myFunction() {...}`)
2. Ouvrez le fichier `MarqueurSegments.gs`
3. Copiez TOUT le code
4. Collez-le dans l'éditeur Apps Script

### Étape 3 : Sauvegarder

1. Donnez un nom au projet (ex: "Marqueur Segments Vidéo")
2. Cliquez sur l'icône **Disquette** ou appuyez sur `Ctrl+S` (Cmd+S sur Mac)

### Étape 4 : Activer

1. Fermez l'onglet Apps Script
2. Retournez sur votre document Google Docs
3. **Rafraîchissez la page** (F5 ou Cmd+R)
4. Un nouveau menu **"🎬 Extraits Vidéo"** apparaît dans la barre de menu !

### Première utilisation

La **première fois** que vous utilisez une fonction du menu, Google vous demandera d'autoriser le script :

1. Cliquez sur "Examiner les autorisations"
2. Choisissez votre compte Google
3. Cliquez sur "Paramètres avancés" → "Accéder à Marqueur Segments Vidéo (non sécurisé)"
4. Cliquez sur "Autoriser"

⚠️ **C'est normal !** Google affiche cet avertissement pour tous les scripts personnels. Le script ne modifie que votre document.

---

## 📖 Utilisation

### Marquer un segment

1. **Sélectionnez** le texte du segment à extraire (début → fin)
2. Cliquez sur **🎬 Extraits Vidéo** → **Marquer comme S1** (ou S2, S3, etc.)
3. Les balises `🎬 S1 🎬` et `🎬 /S1 🎬` sont automatiquement insérées !

**Exemple :**

Avant :
```
(0:25) Premier paragraphe de la transcription...

(2:30) Deuxième paragraphe...
```

Après avoir sélectionné et marqué comme S1 :
```
🎬 S1 🎬
(0:25) Premier paragraphe de la transcription...

(2:30) Deuxième paragraphe...
🎬 /S1 🎬
```

### Fonctionnalités disponibles

**Menu "🎬 Extraits Vidéo" :**

- ✅ **Marquer comme S1 à S10** : Marque rapidement les 10 premiers segments
- ✅ **Marquer segment personnalisé** : Pour S11, S20, etc.
- ✅ **Retirer les marqueurs** : Supprime tous les marqueurs du document
- ✅ **Lister les segments** : Affiche tous les segments et vérifie qu'ils sont complets

### Vérifier les segments

Cliquez sur **"Lister les segments"** pour voir :
- ✅ **S1: 2 marqueurs** → Complet (début + fin)
- ⚠️ **S2: 1 marqueur** → Incomplet (manque début ou fin)

---

## 💡 Conseils

### ✅ Bonnes pratiques

- **Sélectionnez précisément** : Commencez au début exact et finissez à la fin exacte du passage
- **Utilisez des noms logiques** : S1 pour le premier segment, S2 pour le deuxième, etc.
- **Vérifiez régulièrement** : Utilisez "Lister les segments" pour vérifier que tout est correct
- **Sauvegardez régulièrement** : Google Docs sauvegarde automatiquement, mais vérifiez que tout est bien enregistré

### ❌ À éviter

- Ne pas mettre de balises à l'intérieur d'autres balises
- Ne pas modifier manuellement les balises (utilisez le menu)
- Ne pas oublier de marquer la fin d'un segment

---

## 🔧 Dépannage

### Le menu n'apparaît pas

1. Vérifiez que le script est bien sauvegardé
2. Rafraîchissez la page (F5)
3. Fermez et rouvrez le document
4. Si le problème persiste, réinstallez le script

### Erreur "Autorisations requises"

C'est normal la première fois ! Suivez les étapes dans "Première utilisation" ci-dessus.

### Les balises ne s'insèrent pas correctement

1. Assurez-vous de bien sélectionner du texte AVANT de cliquer sur le menu
2. Vérifiez que vous êtes dans un paragraphe (pas dans un titre ou une image)
3. Si le problème persiste, utilisez "Retirer les marqueurs" et recommencez

---

## 🆘 Support

En cas de problème :
1. Vérifiez cette documentation
2. Regardez le fichier `GUIDE_UTILISATEUR_COMPLET.md`
3. Contactez le support technique

---

## 🎬 Workflow complet

1. **Transcription** → Le système transcrit votre vidéo automatiquement
2. **Copie** → Copiez `_paragraphs_timestamps` dans "Highlighted Files"
3. **Installation** → Installez ce script (une seule fois)
4. **Marquage** → Sélectionnez et marquez les segments avec le menu
5. **Traitement** → Le système détecte automatiquement les segments et génère les extraits vidéo
6. **Récupération** → Vos extraits sont dans "Segments Videos" !
