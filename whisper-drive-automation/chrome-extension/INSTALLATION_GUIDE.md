# 🚀 Guide d'Installation - Extension Chrome

Guide rapide pour installer l'extension **Marqueur Segments Vidéo** sur Chrome.

---

## ⚡ Installation Rapide (5 minutes)

### Étape 1 : Générer les icônes (Obligatoire)

L'extension a besoin d'icônes PNG. Voici 2 options :

#### Option A : Convertisseur en ligne (Plus rapide) ⭐

1. **Allez sur** https://cloudconvert.com/svg-to-png

2. **Uploadez** le fichier `chrome-extension/icons/icon.svg`

3. **Générez 3 versions** :
   - **16x16** pixels → Télécharger → Renommer en `icon16.png`
   - **48x48** pixels → Télécharger → Renommer en `icon48.png`
   - **128x128** pixels → Télécharger → Renommer en `icon128.png`

4. **Déplacez** les 3 fichiers dans `chrome-extension/icons/`

#### Option B : ImageMagick (Si installé)

```bash
cd chrome-extension/icons/
convert -background none icon.svg -resize 16x16 icon16.png
convert -background none icon.svg -resize 48x48 icon48.png
convert -background none icon.svg -resize 128x128 icon128.png
```

---

### Étape 2 : Installer l'extension dans Chrome

1. **Ouvrez Chrome** et tapez dans la barre d'adresse :
   ```
   chrome://extensions/
   ```

2. **Activez le "Mode développeur"** (coin supérieur droit)

   ![Mode développeur](https://i.imgur.com/XYZ.png)

3. **Cliquez sur "Charger l'extension non empaquetée"**

4. **Sélectionnez le dossier** `chrome-extension`

5. **L'extension est installée !** 🎉

   Vous devriez voir :
   ```
   🎬 Marqueur Segments Vidéo
   Version 1.0.0
   ✅ Activée
   ```

---

### Étape 3 : Tester l'extension

1. **Ouvrez Google Docs** : https://docs.google.com

2. **Ouvrez un document** qui contient `_paragraphs_timestamps` dans le nom

3. **La barre d'outils apparaît automatiquement** en haut à droite ! 🎬

   ```
   ┌─────────────────────────┐
   │ 🎬 Extraits Vidéo    −  │
   ├─────────────────────────┤
   │ S1  S2  S3  S4  S5     │
   │ S6  S7  S8  S9  S10    │
   │ ...                     │
   └─────────────────────────┘
   ```

4. **Testez :**
   - Sélectionnez du texte
   - Cliquez sur **S1**
   - Les balises `🎬 S1 🎬` et `🎬 /S1 🎬` sont ajoutées !

---

## 🎯 Utilisation

### Marquer un segment

1. **Sélectionnez** le texte dans le document
2. **Cliquez** sur S1, S2, S3... dans la barre d'outils
3. **Les balises sont insérées** automatiquement

### Marquer comme PRÊT

Une fois tous les segments marqués :

1. **Cliquez** sur **"✅ Marquer comme PRÊT"**
2. **La balise est copiée** dans le presse-papiers
3. **Allez à la fin** du document
4. **Collez** (Ctrl+V ou Cmd+V)

La balise `🎬 READY 🎬` indique au système backend que le document est prêt à être traité.

---

## 🔧 Dépannage

### ❌ La barre d'outils n'apparaît pas

**Causes possibles :**
- Vous n'êtes pas sur Google Docs
- Le document n'est pas ouvert en mode édition
- L'extension est désactivée

**Solutions :**
1. Vérifiez que vous êtes sur `docs.google.com/document/...`
2. Rafraîchissez la page (F5)
3. Allez dans `chrome://extensions/` et vérifiez que l'extension est activée
4. Regardez la console (F12) pour les erreurs

### ❌ Les balises ne s'insèrent pas

**Note** : Google Docs a des limitations pour l'insertion programmatique.

**Solution de secours** :
1. La balise est automatiquement **copiée dans le presse-papiers**
2. **Collez-la** manuellement (Ctrl+V)

### ❌ L'extension ne se charge pas

**Erreur possible :** "Les icônes sont manquantes"

**Solution :**
- Assurez-vous d'avoir généré les icônes PNG (Étape 1)
- Vérifiez que `icon16.png`, `icon48.png`, `icon128.png` existent dans `icons/`

### ❌ Message "Manifest version is invalid"

**Solution :**
- Assurez-vous d'utiliser **Chrome 88+** ou **Edge 88+**
- Si vous utilisez une version plus ancienne, contactez l'administrateur

---

## 🔄 Mise à jour de l'extension

Si le code de l'extension est modifié :

1. **Allez dans** `chrome://extensions/`
2. **Trouvez** "🎬 Marqueur Segments Vidéo"
3. **Cliquez** sur le bouton **🔄 Recharger**
4. **Rafraîchissez** la page Google Docs (F5)

---

## 📤 Partager avec l'équipe

### Option 1 : Dossier partagé

1. **Compressez** le dossier `chrome-extension/` en ZIP
2. **Partagez** le fichier ZIP avec l'équipe
3. Chacun suit le guide d'installation ci-dessus

### Option 2 : Chrome Web Store (Production)

Pour publier l'extension officiellement :

1. **Créez un compte** Chrome Web Store Developer ($5 unique)
2. **Empaquetez** l'extension
3. **Soumettez** pour review (1-2 jours)
4. **Publiez** sur le store

**Avantage :** Installation en 1 clic pour tout le monde.

---

## 📊 Statut d'installation

Vérifiez que tout fonctionne :

- [ ] Icônes PNG générées (icon16.png, icon48.png, icon128.png)
- [ ] Extension chargée dans Chrome
- [ ] Extension activée (switch ON)
- [ ] Testée sur un Google Doc
- [ ] Barre d'outils visible
- [ ] Marquage de segment fonctionne
- [ ] Balise READY peut être ajoutée

---

## 🆘 Support

**Problème avec l'extension ?**

1. **Vérifiez** que vous avez suivi toutes les étapes
2. **Consultez** le README.md pour plus de détails
3. **Regardez** la console Chrome (F12) pour les erreurs
4. **Contactez** l'administrateur système

---

## 🎓 Ressources

- [Documentation complète](../chrome-extension/README.md)
- [Google Chrome Extensions Docs](https://developer.chrome.com/docs/extensions/)
- [Guide des balises inline](../GUIDE_BALISES_INLINE.md)

---

**Prêt à marquer des segments ! 🎬**
