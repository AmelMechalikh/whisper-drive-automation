# 👁️ Guide Watch Folder

## Nouvelle fonctionnalité ajoutée ! ✅

L'app peut maintenant **surveiller automatiquement** un dossier et traiter les vidéos dès qu'elles apparaissent.

## 🎯 Comment ça marche

### Pour l'utilisateur final

1. **Ouvrir l'app**
2. **Cliquer sur "Activer"** dans la section "Surveillance automatique"
3. **Choisir un dossier** à surveiller (ex: `~/Videos/To_Transcribe/`)
4. **C'est tout !** 🎉

Dès qu'une vidéo apparaît dans le dossier → traitement automatique

### Interface

```
┌─────────────────────────────────────┐
│  👁️ Surveillance automatique       │
│  [● Actif]                          │
│                                     │
│  📁 /Users/amel/Videos/             │
│  [Choisir un dossier]               │
│                                     │
│  🔄 Nouveau: video1.mp4             │
│  ✅ Terminé: video2.mp4             │
└─────────────────────────────────────┘
```

## 🔧 Fonctionnalités

### Surveillance intelligente
- ✅ Détecte les nouvelles vidéos instantanément
- ✅ Attend que le fichier soit complètement écrit (pas de fichiers corrompus)
- ✅ Évite de traiter 2 fois le même fichier
- ✅ Supporte tous les formats: `.mp4`, `.mov`, `.avi`, `.mkv`, `.flv`, `.wmv`, `.m4v`

### Traitement automatique
1. **Extraction audio** (FFmpeg local)
2. **Upload vidéo** → Drive `source_files/`
3. **Upload audio** → Drive `source_files/`
4. **Notification** dans l'activité

### Activité en temps réel
- 🔄 Fichier en cours de traitement
- ✅ Fichier traité avec succès
- ❌ Erreur avec détails

### Persistance
- Le dossier surveillé est **sauvegardé**
- Au prochain lancement → surveillance reprend automatiquement

## 📝 Use Cases

### Use Case 1: Utilisateur non-tech
```
1. Installer l'app (.exe ou .dmg)
2. Premier lancement → Se connecter avec Google
3. Activer surveillance → Choisir dossier Desktop
4. Déposer vidéos sur le Desktop → automatique !
```

### Use Case 2: Dossier Dropbox/OneDrive
```
1. Activer surveillance → Choisir dossier Dropbox
2. Quelqu'un partage une vidéo → Dropbox sync
3. Vidéo apparaît → traitement automatique
```

### Use Case 3: Export depuis autre app
```
1. Activer surveillance → Choisir dossier Export
2. App d'édition vidéo export vers ce dossier
3. Traitement automatique
```

## 🚀 Upload manuel toujours disponible

L'upload manuel (drag & drop) reste disponible !

Deux modes au choix :
- **Watch Folder** → Automatique
- **Drag & Drop** → Manuel

## 🔒 Sécurité

- ✅ Surveillance locale uniquement (pas de données externes)
- ✅ Fichiers traités uploadés via OAuth (connexion sécurisée)
- ✅ Aucune donnée stockée en dehors de Drive

## 📊 Performances

- **Overhead minimal** : chokidar est très léger
- **Pas de polling** : événements système natifs
- **Un seul fichier à la fois** : évite de surcharger le système

## 🐛 Troubleshooting

### La surveillance ne démarre pas
→ Vérifier que le dossier existe et est accessible

### Les fichiers ne sont pas détectés
→ Vérifier l'extension (doit être .mp4, .mov, etc.)
→ Attendre 2 secondes après copie (stabilityThreshold)

### L'app se ferme, la surveillance s'arrête
→ Normal. Au prochain lancement, cliquer "Activer" à nouveau
→ Le dossier est déjà sauvegardé, pas besoin de le re-sélectionner

## 🎨 Personnalisation future

Ideas pour améliorer :
- [ ] Lancer l'app au démarrage système
- [ ] Mode "minimized to tray" (surveillance en arrière-plan)
- [ ] Notifications système (macOS/Windows native)
- [ ] Historique des fichiers traités
- [ ] Statistiques (nombre de fichiers, taille totale)

## 📦 Inclus dans le build

Tout est inclus, pas de config supplémentaire :
- `chokidar` packagé avec l'app
- Settings sauvegardés dans electron-store
- Compatible Windows & Mac

## ✅ Prêt à tester !

Après ton test en cours, tu peux :

1. **Relancer l'app** : `npm start`
2. **Activer le watch folder**
3. **Tester avec quelques vidéos**

Puis builder pour distribution :
```bash
npm run build:win  # ou build:mac
```

L'app complète avec watch folder sera dans `dist/` ! 🎉
