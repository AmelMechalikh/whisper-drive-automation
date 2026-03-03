# Transcription Desktop App

Application desktop cross-platform pour upload et transcription de vidéos.

## 🎯 Fonctionnalités

- ✅ Interface glisser-déposer simple
- ✅ Extraction audio locale (FFmpeg)
- ✅ Upload vers Google Drive (vidéo + audio)
- ✅ Authentification Google OAuth
- ✅ Barres de progression en temps réel
- ✅ Cross-platform (Windows .exe / Mac .dmg)

## 📋 Prérequis

1. **Node.js** (v16 ou supérieur)
2. **FFmpeg** installé sur le système
   - Windows: `choco install ffmpeg`
   - Mac: `brew install ffmpeg`

## 🚀 Installation (développement)

```bash
cd transcription-desktop-app
npm install
```

## ⚙️ Configuration

Avant de lancer l'app, configurez les credentials Google OAuth dans `src/main.js`:

```javascript
const CLIENT_ID = 'YOUR_CLIENT_ID.apps.googleusercontent.com';
const CLIENT_SECRET = 'YOUR_CLIENT_SECRET';
```

**Obtenir les credentials:**
1. Aller sur [Google Cloud Console](https://console.cloud.google.com)
2. Créer un projet (ou utiliser celui existant)
3. Activer l'API Google Drive
4. Créer des credentials OAuth 2.0
   - Type: Desktop App
   - Redirect URI: `http://localhost:3000/oauth2callback`
5. Télécharger le fichier JSON avec CLIENT_ID et CLIENT_SECRET

**Configurer le dossier Drive:**
Dans `src/main.js`, remplacer `SOURCE_FILES_FOLDER_ID` par l'ID du dossier `source_files` dans Drive:

```javascript
'SOURCE_FILES_FOLDER_ID' // Remplacer par l'ID réel
```

Pour obtenir l'ID d'un dossier Drive:
- Ouvrir le dossier dans Drive
- L'URL est: `https://drive.google.com/drive/folders/[ID_ICI]`

## 🎬 Lancer l'application

```bash
npm start
```

## 📦 Build pour distribution

### Windows (.exe)
```bash
npm run build:win
```
Génère: `dist/TranscriptionApp-Setup-1.0.0.exe`

### Mac (.dmg)
```bash
npm run build:mac
```
Génère: `dist/TranscriptionApp-1.0.0.dmg`

### Les deux
```bash
npm run build:all
```

## 📖 Utilisation pour utilisateurs finaux

1. **Installation**
   - Windows: Double-clic sur `.exe` → Next → Install
   - Mac: Ouvrir `.dmg` → Glisser dans Applications

2. **Premier lancement**
   - Cliquer sur "Se connecter avec Google"
   - Autoriser l'accès à Drive dans le navigateur
   - Retourner à l'app

3. **Upload de vidéo**
   - Glisser-déposer une vidéo dans la zone
   - Attendre la fin de l'upload
   - La transcription démarre automatiquement

## 🔧 Architecture

```
transcription-desktop-app/
├── src/
│   ├── main.js          # Process principal Electron
│   ├── preload.js       # Bridge sécurisé
│   ├── index.html       # Interface utilisateur
│   ├── styles.css       # Styles
│   └── renderer.js      # Logique UI
├── build/               # Icônes (.ico, .icns)
├── dist/                # Builds générés
└── package.json         # Config npm & electron-builder
```

## 🛠️ Technologies

- **Electron** - Framework desktop
- **FFmpeg** - Extraction audio
- **Google APIs** - Upload vers Drive
- **electron-builder** - Packaging
- **electron-store** - Storage local des tokens

## 📝 TODO

- [ ] Ajouter icônes (.ico pour Windows, .icns pour Mac)
- [ ] Tester build sur Windows et Mac
- [ ] Ajouter auto-update
- [ ] Gérer les erreurs réseau (retry)
- [ ] Ajouter historique des uploads
