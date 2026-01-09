# Google Apps Script - Marqueur Segments Vidéo 🎬

## 📁 Contenu du dossier

```
google-apps-script/
├── MarqueurSegments.gs          # Code principal du script
├── appsscript.json              # Configuration du projet
├── WrapperTemplate.gs           # Template pour les utilisateurs
├── .clasp.json                  # Configuration clasp
├── deploy.sh                    # Script de déploiement automatique
├── README.md                    # Ce fichier
├── README_INSTALLATION.md       # Guide d'installation manuelle
└── DEPLOY_STANDALONE.md         # Guide de déploiement standalone
```

---

## 🎯 Deux Méthodes de Déploiement

### **Méthode 1 : Installation Manuelle** ⚡ (Rapide)

Pour quelques utilisateurs ou usage personnel.

**Guide :** `README_INSTALLATION.md`

**Résumé :**
1. Copier le code de `MarqueurSegments.gs`
2. Le coller dans Extensions → Apps Script
3. Ça marche immédiatement !

**Avantages :**
- ✅ Rapide (5 minutes)
- ✅ Pas de configuration
- ✅ Fonctionne tout de suite

**Inconvénient :**
- ❌ À refaire pour chaque document

---

### **Méthode 2 : Déploiement Standalone** 🚀 (Recommandé pour équipe)

Pour partager avec plusieurs utilisateurs.

**Guide :** `DEPLOY_STANDALONE.md`

**Déploiement rapide :**

```bash
# Installation de clasp (une fois)
npm install -g @google/clasp

# Connexion à Google (une fois)
clasp login

# Déploiement
cd google-apps-script
./deploy.sh 1.0.0 "Première version"
```

**Résultat :**
- Vous obtenez un **Script ID**
- Les utilisateurs l'ajoutent via Bibliothèques
- Une seule source de code à maintenir

**Avantages :**
- ✅ Centralisé
- ✅ Mises à jour faciles
- ✅ Professionnel
- ✅ Suivi des versions

---

## 🔧 Fonctionnalités du Script

### Menu 🎬 Extraits Vidéo

- **Marquer comme S1 à S10** : Marquage rapide des segments
- **Marquer segment personnalisé** : Pour S11, S20, etc.
- **Lister les segments** : Vérification des segments
- **Retirer les marqueurs** : Nettoyage du document

### Format des Balises

```
🎬 S1 🎬
Votre texte ici...
🎬 /S1 🎬
```

---

## 📖 Guide Utilisateur Final

Une fois le script déployé/installé :

1. **Sélectionner** le texte à extraire
2. **Menu 🎬 Extraits Vidéo** → Marquer comme S1
3. Les balises sont insérées automatiquement
4. Le système backend traite automatiquement

**Documentation complète :** `../GUIDE_BALISES_INLINE.md`

---

## 🔄 Workflow Complet

```
┌─────────────────────────────────────────────────────────┐
│  ADMINISTRATEUR                                         │
├─────────────────────────────────────────────────────────┤
│  1. Déploie le script (une fois)                       │
│     $ ./deploy.sh 1.0.0                                │
│                                                         │
│  2. Obtient le Script ID                               │
│     Script ID: 1a2b3c4d5e6f7g8h9i0j                   │
│                                                         │
│  3. Partage le Script ID avec les utilisateurs         │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  UTILISATEURS                                           │
├─────────────────────────────────────────────────────────┤
│  1. Ouvrent leur Google Doc                            │
│  2. Extensions → Apps Script                           │
│  3. Ajoutent la bibliothèque (Script ID)              │
│  4. Copient le WrapperTemplate.gs                      │
│  5. Menu 🎬 disponible !                               │
│                                                         │
│  6. Sélectionnent du texte                             │
│  7. Cliquent sur "Marquer comme S1"                    │
│  8. Balises insérées automatiquement                   │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│  SYSTÈME BACKEND                                        │
├─────────────────────────────────────────────────────────┤
│  1. Détecte les fichiers avec balises                  │
│  2. Parse les segments                                 │
│  3. Matche avec le transcript                          │
│  4. Génère les extraits vidéo                          │
│  5. Upload sur Drive                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ Développement

### Structure du Code

**MarqueurSegments.gs :**
```javascript
function onOpen() { ... }           // Crée le menu
function marquerSegment(numero) { ... }  // Insère les balises
function listerSegments() { ... }   // Liste tous les segments
function retirerMarqueurs() { ... } // Nettoie le document
```

### Tester Localement

```bash
# Cloner le projet
clasp clone [SCRIPT_ID]

# Modifier le code
vim MarqueurSegments.gs

# Pousser les changements
clasp push

# Tester dans l'éditeur web
clasp open
```

### Publier une Nouvelle Version

```bash
./deploy.sh 1.1.0 "Ajout fonctionnalité X"
```

---

## 📝 Checklist de Déploiement

### Avant le premier déploiement

- [ ] Node.js installé
- [ ] clasp installé (`npm install -g @google/clasp`)
- [ ] Connexion Google configurée (`clasp login`)
- [ ] Code testé localement

### Déploiement

- [ ] Exécuter `./deploy.sh [version] [description]`
- [ ] Noter le Script ID
- [ ] Tester l'ajout en tant que bibliothèque
- [ ] Vérifier que le menu apparaît
- [ ] Tester toutes les fonctions

### Après déploiement

- [ ] Mettre à jour la documentation avec le Script ID
- [ ] Créer un document template d'instructions
- [ ] Former les premiers utilisateurs
- [ ] Monitorer les erreurs

---

## 🆘 Dépannage

### `clasp: command not found`
```bash
npm install -g @google/clasp
```

### `User has not enabled the Apps Script API`
1. Allez sur https://script.google.com/home/usersettings
2. Activez "Google Apps Script API"

### `No valid credentials found`
```bash
clasp login
```

### Le menu n'apparaît pas pour les utilisateurs
1. Vérifier que le Script ID est correct
2. Vérifier que la bibliothèque est bien ajoutée
3. Vérifier que le WrapperTemplate.gs est copié
4. Rafraîchir le document

---

## 📊 Comparaison des Méthodes

| Critère | Manuel | Standalone |
|---------|--------|-----------|
| **Setup initial** | 5 min | 15 min |
| **Par utilisateur** | 5 min | 2 min |
| **Mises à jour** | Copier-coller | 2 clics |
| **Source unique** | ❌ | ✅ |
| **Versions** | ❌ | ✅ |
| **Professionnel** | ⚠️ | ✅ |

**Recommandation :**
- **1-5 utilisateurs** : Manuel
- **5+ utilisateurs** : Standalone

---

## 🔐 Sécurité

### Permissions Requises

- `documents` : Lire et modifier le document actif
- `script.container.ui` : Créer le menu

### OAuth

- Première utilisation : autorisation requise
- Avertissement "application non vérifiée" normal
- Scope limité au document actif seulement

---

## 📞 Support

- **Documentation** : Voir les guides dans ce dossier
- **Issues** : Créer une issue GitHub
- **Email** : [À configurer]

---

## 🎓 Ressources

- [Google Apps Script Docs](https://developers.google.com/apps-script)
- [Clasp Documentation](https://github.com/google/clasp)
- [Apps Script Best Practices](https://developers.google.com/apps-script/guides/support/best-practices)

---

**Prêt à déployer ? Suivez `DEPLOY_STANDALONE.md` ! 🚀**
