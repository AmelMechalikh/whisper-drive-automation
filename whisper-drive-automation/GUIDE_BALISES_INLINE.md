# Guide Utilisateur - Système d'Extraits Vidéo avec Balises Inline

## 🎯 Nouvelle Méthode : Balises 🎬 dans le Texte

**Fini les commentaires tronqués !** Le système utilise maintenant des **balises inline** directement dans le document pour marquer les segments à extraire.

---

## 📋 Workflow Simplifié

### Étape 1 : Transcription automatique

1. Uploadez votre vidéo/audio dans **Google Drive > "Files"**
2. Attendez la transcription automatique
3. Récupérez le fichier `Votre_fichier_paragraphs_timestamps` dans **"Transcriptions"**

### Étape 2 : Copier et préparer

1. **Copiez** le fichier `_paragraphs_timestamps` dans **"Highlighted Files"**
2. **Ouvrez** le fichier copié dans Google Docs

### Étape 3 : Installer le menu (une seule fois)

📖 **Suivez le guide :** `google-apps-script/README_INSTALLATION.md`

**Résumé rapide :**
1. Dans Google Docs : **Extensions** → **Apps Script**
2. Copiez le code de `MarqueurSegments.gs`
3. Sauvegardez et rafraîchissez
4. Un menu **🎬 Extraits Vidéo** apparaît !

### Étape 4 : Marquer vos segments

1. **Sélectionnez** le texte du segment à extraire (du début à la fin exacte)
2. Cliquez sur **🎬 Extraits Vidéo** → **Marquer comme S1**
3. Les balises sont automatiquement insérées :

```
🎬 S1 🎬
(0:25) Texte de votre segment...
jusqu'à la fin exacte du segment
🎬 /S1 🎬
```

4. Répétez pour S2, S3, etc.

### Étape 5 : Laisser le système travailler

Le système détecte automatiquement :
- ✅ Les nouveaux fichiers avec balises dans "Highlighted Files"
- ✅ Génère l'Excel avec les timestamps précis
- ✅ Découpe la vidéo en extraits
- ✅ Upload tout dans "Segments Videos"

### Étape 6 : Récupérer vos extraits

Allez dans **"Segments Videos"** → Dossier de votre fichier → Vos extraits sont prêts !

---

## 🎬 Format des Balises

### Format standard
```
🎬 S1 🎬
... votre texte ...
🎬 /S1 🎬
```

### Règles importantes

✅ **À FAIRE :**
- Utilisez le menu pour insérer les balises (automatique et sans erreurs)
- Sélectionnez précisément du début à la fin du segment
- Numérotez logiquement : S1, S2, S3, etc.
- Vérifiez avec "Lister les segments" que tout est complet

❌ **À ÉVITER :**
- Ne modifiez PAS les balises manuellement
- Ne mettez PAS de balises imbriquées
- N'oubliez PAS la balise de fin `/S1`
- Ne sélectionnez PAS plusieurs segments en même temps

---

## 💡 Avantages de la Nouvelle Méthode

### Par rapport aux commentaires :

✅ **Pas de limite de taille**
- Les commentaires étaient tronqués à ~970 caractères
- Avec les balises : aucune limite !

✅ **Précision parfaite**
- Vous contrôlez exactement où commence et où finit le segment
- Le système trouve les timestamps précis

✅ **Visuel et clair**
- Vous voyez immédiatement ce qui sera extrait
- Pas de confusion avec des commentaires cachés

✅ **Facile à éditer**
- Modifiez facilement la sélection
- Retirez un marqueur en un clic

---

## 🔧 Fonctions du Menu

### Marquer comme S1 à S10
Marque rapidement les 10 premiers segments

### Marquer segment personnalisé
Pour S11, S20, etc. - vous choisissez le numéro

### Lister les segments
Affiche tous les segments et vérifie qu'ils sont complets :
- ✅ **S1: 2 marqueurs** → OK (début + fin)
- ⚠️ **S2: 1 marqueur** → Incomplet !

### Retirer les marqueurs
Supprime TOUS les marqueurs du document (avec confirmation)

---

## 📖 Exemple Complet

### Document original :
```
(0:00) Bonjour à tous, aujourd'hui nous allons parler de méditation.

(0:15) La méditation est une pratique ancestrale...

(1:30) Il existe plusieurs types de méditation...

(3:00) Pour commencer, asseyez-vous confortablement...
```

### Après marquage (S1 = intro, S2 = types) :
```
🎬 S1 🎬
(0:00) Bonjour à tous, aujourd'hui nous allons parler de méditation.

(0:15) La méditation est une pratique ancestrale...
🎬 /S1 🎬

(1:30) Il existe plusieurs types de méditation...

🎬 S2 🎬
(3:00) Pour commencer, asseyez-vous confortablement...
🎬 /S2 🎬
```

### Résultat :
- **Extrait 1 (S1)** : de 0:00 à ~1:30
- **Extrait 2 (S2)** : de 3:00 à la fin du segment

---

## 🆘 Dépannage

### Les balises ne s'insèrent pas
1. Vérifiez que vous avez **sélectionné du texte** avant de cliquer
2. Assurez-vous d'être dans un **paragraphe** (pas un titre)
3. Réinstallez le script si nécessaire

### Le système ne détecte pas mes segments
1. Vérifiez que le fichier est bien dans **"Highlighted Files"**
2. Utilisez "Lister les segments" pour vérifier que tout est complet
3. Attendez 5 minutes (le système vérifie toutes les 5 minutes)

### "Aucun segment trouvé"
1. Les balises doivent être exactement : `🎬 S1 🎬` (avec les espaces)
2. Chaque segment doit avoir un début ET une fin
3. Utilisez le menu au lieu de taper manuellement

---

## 🔄 Migration depuis les Commentaires

Si vous utilisiez l'ancienne méthode avec les commentaires :

1. **Rien à faire !** Les deux méthodes coexistent
2. La nouvelle méthode (balises) est activée par défaut
3. Pour revenir aux commentaires, modifiez `highlight_config.json` :
   ```json
   "extraction_method": "comments"
   ```

**Recommandation :** Utilisez les balises pour tous les nouveaux fichiers.

---

## 📊 Comparaison des Méthodes

| Critère | Commentaires (ancien) | Balises 🎬 (nouveau) |
|---------|---------------------|---------------------|
| **Limite de taille** | ❌ ~970 caractères | ✅ Illimitée |
| **Précision** | ⚠️ Moyenne | ✅ Parfaite |
| **Facilité d'utilisation** | ⚠️ Manuel | ✅ Menu automatique |
| **Visibilité** | ❌ Caché | ✅ Très visible |
| **Édition** | ⚠️ Difficile | ✅ Facile |

---

## ✅ Checklist Complète

### Installation (une fois)
- [ ] Script Google Apps Script installé
- [ ] Menu 🎬 visible dans Google Docs
- [ ] Test avec un petit segment

### Pour chaque vidéo
- [ ] Fichier uploadé dans "Files"
- [ ] Transcription terminée (fichiers dans "Transcriptions")
- [ ] Fichier copié dans "Highlighted Files"
- [ ] Segments marqués avec le menu
- [ ] Vérification avec "Lister les segments"
- [ ] Attente du traitement automatique (5-10 min)
- [ ] Extraits récupérés dans "Segments Videos"

---

## 🎓 Tutoriel Vidéo

*(À créer - capturer l'écran montrant :)*
1. Installation du script
2. Marquage d'un segment
3. Vérification
4. Récupération des extraits

---

## 📞 Support

**Questions fréquentes :** Voir ce guide
**Problèmes techniques :** `GUIDE_UTILISATEUR_COMPLET.md`
**Installation script :** `google-apps-script/README_INSTALLATION.md`

---

**Bonne extraction ! 🎬**
