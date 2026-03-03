# 🚀 Setup Guide

## Étape 1: Installer les dépendances

```bash
cd transcription-desktop-app
npm install
```

## Étape 2: Configurer Google OAuth

### 2.1 Créer les credentials OAuth

1. Aller sur [Google Cloud Console](https://console.cloud.google.com)
2. Sélectionner le projet `transcription-project-435611`
3. Menu: **APIs & Services** → **Credentials**
4. Cliquer: **+ CREATE CREDENTIALS** → **OAuth client ID**
5. Application type: **Desktop app**
6. Name: `Transcription Desktop App`
7. Cliquer **CREATE**
8. Télécharger le JSON ou copier:
   - Client ID
   - Client Secret

### 2.2 Configurer dans l'app

Ouvrir `src/main.js` et remplacer lignes 14-16:

```javascript
const CLIENT_ID = 'YOUR_CLIENT_ID.apps.googleusercontent.com';
const CLIENT_SECRET = 'YOUR_CLIENT_SECRET';
```

Par vos vraies credentials.

### 2.3 Configurer le dossier Drive

1. Ouvrir Google Drive
2. Aller dans le dossier `source_files`
3. L'URL est: `https://drive.google.com/drive/folders/[ID]`
4. Copier l'ID

Dans `src/main.js`, remplacer ligne 144 et 155:

```javascript
'SOURCE_FILES_FOLDER_ID'
```

Par votre ID réel (entre guillemets).

## Étape 3: Installer FFmpeg (si pas déjà fait)

### Mac
```bash
brew install ffmpeg
```

### Windows
```bash
choco install ffmpeg
```

Ou télécharger sur [ffmpeg.org](https://ffmpeg.org/download.html)

## Étape 4: Lancer l'app en dev

```bash
npm start
```

## Étape 5: Tester

1. L'app s'ouvre
2. Cliquer "Se connecter avec Google"
3. Autoriser l'accès dans le navigateur
4. Glisser-déposer une petite vidéo de test
5. Vérifier que ça upload dans Drive

## Étape 6: Build pour distribution

### Windows (.exe)
```bash
npm run build:win
```

Le fichier sera dans: `dist/TranscriptionApp-Setup-1.0.0.exe`

### Mac (.dmg)
```bash
npm run build:mac
```

Le fichier sera dans: `dist/TranscriptionApp-1.0.0.dmg`

## 📝 Notes importantes

1. **Icônes manquantes**: Pour le build final, il faut des icônes:
   - Windows: `build/icon.ico` (256x256)
   - Mac: `build/icon.icns`

2. **Redirect URI OAuth**: Doit être `http://localhost:3000/oauth2callback`
   - Ajouter dans Google Cloud Console si pas déjà fait

3. **Scopes Drive**: L'app demande uniquement `drive.file`
   - Accès seulement aux fichiers créés par l'app
   - Pour accès complet: changer en `drive` dans main.js

4. **Distribution**: Les .exe et .dmg peuvent être:
   - Hébergés sur un site web
   - Partagés via Google Drive
   - Distribués par email

## 🐛 Troubleshooting

### Erreur: "FFmpeg not found"
→ FFmpeg pas installé ou pas dans PATH

### Erreur OAuth
→ Vérifier CLIENT_ID et CLIENT_SECRET

### Upload échoue
→ Vérifier FOLDER_ID et permissions Drive

### Build échoue
→ Vérifier que tous les modules sont installés: `npm install`
