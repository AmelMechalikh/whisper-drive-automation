# 🚀 Quick Start Guide

## ✅ Ce qui est déjà fait

- ✅ Dépendances npm installées
- ✅ ID du dossier Drive configuré (`source_files`)
- ✅ Structure de l'app créée

## 🔐 Étape 1: Configurer OAuth (5 minutes)

### Option A: Script automatique (recommandé)

```bash
cd /Users/amel/Documents/Transcription-Project/transcription-desktop-app
node scripts/setup-oauth.js
```

Le script va te guider pour:
1. Ouvrir Google Cloud Console
2. Créer un OAuth client ID (Desktop app)
3. Copier-coller CLIENT_ID et CLIENT_SECRET
4. Tout configurer automatiquement

### Option B: Manuel

1. Ouvrir: https://console.cloud.google.com/apis/credentials?project=transcription-project-435611

2. Cliquer: **+ CREATE CREDENTIALS** → **OAuth client ID**

3. Choisir:
   - Application type: **Desktop app**
   - Name: **Transcription Desktop App**

4. Cliquer **CREATE**

5. Copier CLIENT_ID et CLIENT_SECRET

6. Ouvrir `src/main.js` et remplacer lignes 13-14:
   ```javascript
   const CLIENT_ID = 'TON_CLIENT_ID.apps.googleusercontent.com';
   const CLIENT_SECRET = 'TON_CLIENT_SECRET';
   ```

## 🎬 Étape 2: Lancer l'app

```bash
npm start
```

L'app va s'ouvrir → Cliquer "Se connecter avec Google" → Autoriser → C'est parti!

## 🧪 Étape 3: Tester avec un petit fichier

1. Glisser-déposer une **petite vidéo** (< 100 MB pour le test)
2. Observer:
   - Extraction audio
   - Upload vidéo vers Drive
   - Upload audio vers Drive
3. Vérifier dans Drive que les fichiers sont bien uploadés

## 📦 Étape 4: Build pour distribution

### Windows
```bash
npm run build:win
```
→ Génère: `dist/TranscriptionApp-Setup-1.0.0.exe`

### Mac
```bash
npm run build:mac
```
→ Génère: `dist/TranscriptionApp-1.0.0.dmg`

## 🔧 Troubleshooting

### Erreur: "FFmpeg not found"
```bash
# Mac
brew install ffmpeg

# Windows
choco install ffmpeg
```

### L'app ne démarre pas
```bash
# Réinstaller les dépendances
rm -rf node_modules
npm install
npm start
```

### OAuth ne fonctionne pas
- Vérifier que CLIENT_ID se termine par `.apps.googleusercontent.com`
- Vérifier que le redirect URI est: `http://localhost:3000/oauth2callback`
- Dans Google Cloud Console, vérifier que le client OAuth est bien de type "Desktop app"

## 📝 Notes

- **Port 3000**: L'app utilise le port 3000 pour OAuth callback. Si occupé, changer dans `main.js` ligne 15.

- **Gros fichiers (50GB+)**: L'upload peut prendre du temps. L'app gère automatiquement les uploads resumables.

- **Tokens sauvegardés**: Après la première auth, pas besoin de se reconnecter. Les tokens sont dans:
  - Mac: `~/Library/Application Support/transcription-app/`
  - Windows: `%APPDATA%/transcription-app/`
