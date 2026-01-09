# Icônes pour l'extension Chrome

## 🎨 Générer les icônes

Les icônes PNG doivent être générées à partir du fichier `icon.svg`.

### Option 1 : Convertisseur en ligne (Plus simple)

1. Allez sur https://cloudconvert.com/svg-to-png
2. Uploadez `icon.svg`
3. Générez 3 versions aux tailles suivantes :
   - **16x16** pixels → `icon16.png`
   - **48x48** pixels → `icon48.png`
   - **128x128** pixels → `icon128.png`
4. Téléchargez et placez les fichiers dans ce dossier

### Option 2 : ImageMagick (Ligne de commande)

```bash
# Installer ImageMagick si nécessaire
brew install imagemagick  # macOS
# sudo apt-get install imagemagick  # Linux

# Générer les icônes
cd icons/
convert -background none icon.svg -resize 16x16 icon16.png
convert -background none icon.svg -resize 48x48 icon48.png
convert -background none icon.svg -resize 128x128 icon128.png
```

### Option 3 : Inkscape

1. Ouvrez `icon.svg` dans Inkscape
2. Fichier → Exporter PNG
3. Définissez la largeur/hauteur : 16, 48, puis 128
4. Exportez chaque version

### Option 4 : Figma/Canva

1. Ouvrez `icon.svg` dans Figma ou Canva
2. Exportez en PNG aux tailles requises
3. Sauvegardez dans ce dossier

---

## 📏 Spécifications

- **icon16.png** : 16x16 px (barre d'outils Chrome)
- **icon48.png** : 48x48 px (page extensions)
- **icon128.png** : 128x128 px (Chrome Web Store)

Format : PNG avec transparence

---

## 🎬 Design actuel

L'icône actuelle montre :
- Fond bleu (#4285f4 - couleur Google)
- Emoji 🎬 au centre
- Coins arrondis (radius 16px)

N'hésitez pas à personnaliser !

---

## ⚠️ Note importante

L'extension fonctionnera même sans les icônes PNG, mais elles sont **fortement recommandées** pour une meilleure apparence dans Chrome.

Sans icônes, Chrome utilisera des icônes par défaut génériques.
