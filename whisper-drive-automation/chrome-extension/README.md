# Extension Chrome - Marqueur Segments Vidéo 🎬

Extension Chrome pour marquer facilement les segments vidéo dans Google Docs avec des balises inline.

## 🎯 Fonctionnalités

- ✅ **Menu contextuel** : Clic droit sur texte sélectionné → Marquage direct (NOUVEAU!)
- ✅ Barre d'outils flottante dans Google Docs
- ✅ Marquage rapide S1 à S10
- ✅ Segment personnalisé (S11, S20, etc.)
- ✅ Marquer comme PRÊT pour le découpage
- ✅ Interface drag & drop
- ✅ Notifications visuelles
- ✅ Aucune configuration requise

---

## 📦 Installation

### Option 1 : Mode Développeur (Recommandé pour test)

1. **Ouvrez Chrome** et allez à `chrome://extensions/`

2. **Activez le "Mode développeur"** (coin supérieur droit)

3. **Cliquez sur "Charger l'extension non empaquetée"**

4. **Sélectionnez le dossier** `chrome-extension`

5. **L'extension est installée !** 🎉

### Option 2 : Empaqueter l'extension (Pour distribution)

1. Dans `chrome://extensions/`, cliquez sur **"Empaqueter l'extension"**

2. Sélectionnez le dossier `chrome-extension`

3. Chrome génère un fichier `.crx` que vous pouvez distribuer

---

## 🚀 Utilisation

### 1. Ouvrir un Google Doc

Allez sur https://docs.google.com et ouvrez un document avec `_paragraphs_timestamps` dans le nom.

### 2. La barre d'outils apparaît automatiquement

Une barre flottante **"🎬 Extraits Vidéo"** apparaît en haut à droite.

### 3. Marquer des segments

**Méthode 1 (Recommandée) : Menu contextuel**
1. **Sélectionnez** le texte à extraire
2. **Clic droit** → "🎬 Marquer segment" → S1, S2, S3...
3. Les balises sont insérées automatiquement :
   ```
   🎬 S1 🎬
   Votre texte sélectionné...
   🎬 /S1 🎬
   ```

**Méthode 2 : Barre d'outils**
1. **Sélectionnez** le texte à extraire
2. **Copiez** (Ctrl+C)
3. **Cliquez** sur S1, S2, S3... dans la barre d'outils

### 4. Marquer comme PRÊT

Une fois tous les segments marqués :
1. Cliquez sur **"✅ Marquer comme PRÊT"**
2. La balise `🎬 READY 🎬` est copiée dans le presse-papiers
3. Collez-la à la fin du document (Ctrl+V)

### 5. Le backend traite automatiquement

Le système backend détecte le fichier PRÊT et génère les extraits vidéo.

---

## 🎨 Interface

### Barre d'outils flottante

```
┌─────────────────────────────┐
│ 🎬 Extraits Vidéo        −  │ ← Drag pour déplacer
├─────────────────────────────┤
│ SEGMENTS RAPIDES            │
│ ┌────┬────┬────┬────┬────┐ │
│ │ S1 │ S2 │ S3 │ S4 │ S5 │ │
│ ├────┼────┼────┼────┼────┤ │
│ │ S6 │ S7 │ S8 │ S9 │ S10│ │
│ └────┴────┴────┴────┴────┘ │
│                             │
│ ACTIONS                     │
│ [✏️ Segment personnalisé]   │
│ [📋 Lister les segments]    │
│ [🗑️ Retirer les marqueurs]  │
│                             │
│ FINITION                    │
│ [✅ Marquer comme PRÊT]     │
│ [📊 Vérifier le statut]     │
└─────────────────────────────┘
```

### Notifications

Des notifications apparaissent en haut de l'écran :
- ✅ **Succès** : Fond vert
- ⚠️ **Avertissement** : Fond jaune
- ❌ **Erreur** : Fond rouge
- 💡 **Info** : Fond bleu

---

## ⚙️ Configuration

### Personnaliser la position

La barre d'outils est **draggable** :
- Cliquez sur l'en-tête bleu
- Glissez pour repositionner

La position est sauvegardée pour votre session.

### Réduire/Étendre

Cliquez sur le bouton **−** / **+** pour réduire/étendre la barre.

---

## 🔧 Développement

### Structure des fichiers

```
chrome-extension/
├── manifest.json           # Configuration de l'extension
├── content.js             # Script injecté dans Google Docs
├── styles.css             # Styles de la barre d'outils
├── popup.html             # Popup de l'extension
├── icons/                 # Icônes de l'extension
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md              # Ce fichier
```

### Modifier l'extension

1. **Éditez les fichiers** dans `chrome-extension/`

2. **Rechargez l'extension** dans `chrome://extensions/`
   - Cliquez sur le bouton "Recharger" (🔄)

3. **Rafraîchissez** la page Google Docs

### Ajouter des fonctionnalités

**Dans `content.js`** :
- `markSegment(code)` : Marque un segment
- `showNotification(msg, type)` : Affiche une notification
- Ajoutez vos propres fonctions

**Dans `styles.css`** :
- Personnalisez les couleurs, tailles, etc.

---

## 🐛 Dépannage

### La barre d'outils n'apparaît pas

1. **Vérifiez** que vous êtes sur `docs.google.com/document/`
2. **Rafraîchissez** la page (F5)
3. **Vérifiez** que l'extension est activée dans `chrome://extensions/`
4. **Regardez la console** (F12) pour les erreurs

### Les balises ne s'insèrent pas

**Note** : L'insertion directe dans Google Docs est limitée par l'API.

**Solution de secours** :
- Les balises sont copiées dans le presse-papiers
- Collez-les manuellement (Ctrl+V)

### L'extension ne se charge pas après update

1. Allez dans `chrome://extensions/`
2. Cliquez sur **"Recharger"** sur l'extension
3. Rafraîchissez la page Google Docs

---

## 📊 Compatibilité

- ✅ Chrome 88+
- ✅ Edge 88+
- ✅ Brave
- ✅ Opera (avec adaptation)
- ❌ Firefox (nécessite manifest v2)

---

## 🔐 Permissions

L'extension demande uniquement :
- **activeTab** : Pour accéder à l'onglet Google Docs actif
- **identity** : Pour s'authentifier avec Google Docs API
- **contextMenus** : Pour ajouter le menu clic droit
- **docs.googleapis.com** : Pour lire/modifier les Google Docs
- Aucune donnée n'est envoyée à des serveurs externes

---

## 📝 Notes importantes

### Limitations de Google Docs

Google Docs utilise une interface complexe (Canvas + DOM virtuel).

**Ce qui fonctionne** :
- ✅ Insertion de texte via le presse-papiers
- ✅ Interface overlay
- ✅ Détection de sélection

**Ce qui ne fonctionne pas directement** :
- ❌ Manipulation DOM directe du contenu
- ❌ Styling programmatique du texte

**Solution** : L'extension copie les balises dans le presse-papiers, l'utilisateur colle.

---

## 🚀 Prochaines étapes

### Pour les utilisateurs

1. Installez l'extension (5 minutes)
2. Testez sur un document
3. Partagez avec l'équipe

### Pour l'administrateur

1. Générez les icônes PNG (voir ci-dessous)
2. Testez l'extension
3. Distribuez le dossier ou le fichier .crx

---

## 🎨 Générer les icônes PNG

Les icônes sont actuellement en SVG. Pour générer les PNG :

### Option 1 : Utiliser un convertisseur en ligne

1. Allez sur https://cloudconvert.com/svg-to-png
2. Uploadez `icons/icon.svg`
3. Générez 3 tailles : 16x16, 48x48, 128x128
4. Sauvegardez comme `icon16.png`, `icon48.png`, `icon128.png`

### Option 2 : Utiliser Inkscape/GIMP

1. Ouvrez `icon.svg` dans Inkscape ou GIMP
2. Exportez en PNG aux tailles requises
3. Sauvegardez dans le dossier `icons/`

### Option 3 : Utiliser ImageMagick

```bash
cd icons/
convert -background none icon.svg -resize 16x16 icon16.png
convert -background none icon.svg -resize 48x48 icon48.png
convert -background none icon.svg -resize 128x128 icon128.png
```

---

## 💬 Support

- **Issues** : Créer une issue GitHub
- **Email** : [À configurer]
- **Documentation** : Voir ce README

---

## 📄 Licence

[À définir]

---

**Prêt à utiliser ! 🎉**
