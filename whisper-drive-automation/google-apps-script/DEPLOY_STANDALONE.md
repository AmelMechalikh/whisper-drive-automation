# Déploiement du Script en Mode Standalone

## 🎯 Objectif

Déployer le script Google Apps Script comme un **script standalone partageable** que les utilisateurs peuvent ajouter à leurs documents via une bibliothèque.

---

## 📋 Prérequis

- Compte Google avec accès à Google Apps Script
- Node.js installé (pour clasp)
- Accès aux APIs Google activé

---

## 🚀 Déploiement (Administrateur)

### Étape 1 : Installer clasp

```bash
npm install -g @google/clasp
```

### Étape 2 : Se connecter à Google

```bash
clasp login
```

Une fenêtre de navigateur s'ouvre → Connectez-vous avec votre compte Google.

### Étape 3 : Créer le projet

```bash
cd google-apps-script
clasp create --type standalone --title "Marqueur Segments Vidéo"
```

**Résultat :** Un Script ID sera généré (ex: `1a2b3c4d5e6f7g8h9i0j`).

### Étape 4 : Pousser le code

```bash
clasp push
```

Cela uploade :
- `MarqueurSegments.gs`
- `appsscript.json`

### Étape 5 : Déployer une version

```bash
# Créer une version
clasp version "Version 1.0 - Initial release"

# Déployer
clasp deploy --description "Production v1.0"
```

**Résultat :** Vous obtenez un **Deployment ID** (ex: `AKfycbxXXXXXXXXXXXXXXXXXXX`).

### Étape 6 : Configurer les autorisations

1. Ouvrez le projet dans l'éditeur web :
   ```bash
   clasp open
   ```

2. Dans l'éditeur, cliquez sur **⚙️ Paramètres du projet**

3. Dans **Général**, notez le **Script ID**

4. Configurez le partage :
   - Cliquez sur **Déployer** → **Gérer les déploiements**
   - Sélectionnez le déploiement
   - Cliquez sur **Modifier les autorisations d'accès**
   - Changez de "Moi uniquement" à **"Toute personne"**
   - Cliquez sur **Terminer**

---

## 📤 Partager avec les Utilisateurs

### Option A : Via le Script ID (Recommandé)

Donnez aux utilisateurs le **Script ID** et ces instructions :

**Instructions pour l'utilisateur :**

1. Ouvrez votre Google Doc (fichier `_paragraphs_timestamps`)
2. Allez dans **Extensions** → **Apps Script**
3. Dans l'éditeur, cliquez sur **Bibliothèques** (à gauche, icône +)
4. Collez le **Script ID** : `[VOTRE_SCRIPT_ID]`
5. Cliquez sur **Rechercher**
6. Sélectionnez la dernière version
7. Cliquez sur **Ajouter**
8. Copiez ce code dans l'éditeur :

```javascript
/**
 * Charge le menu depuis la bibliothèque
 */
function onOpen() {
  MarqueurSegmentsVideo.onOpen();
}

function marquerS1() { MarqueurSegmentsVideo.marquerS1(); }
function marquerS2() { MarqueurSegmentsVideo.marquerS2(); }
function marquerS3() { MarqueurSegmentsVideo.marquerS3(); }
function marquerS4() { MarqueurSegmentsVideo.marquerS4(); }
function marquerS5() { MarqueurSegmentsVideo.marquerS5(); }
function marquerS6() { MarqueurSegmentsVideo.marquerS6(); }
function marquerS7() { MarqueurSegmentsVideo.marquerS7(); }
function marquerS8() { MarqueurSegmentsVideo.marquerS8(); }
function marquerS9() { MarqueurSegmentsVideo.marquerS9(); }
function marquerS10() { MarqueurSegmentsVideo.marquerS10(); }
function marquerPersonnalise() { MarqueurSegmentsVideo.marquerPersonnalise(); }
function retirerMarqueurs() { MarqueurSegmentsVideo.retirerMarqueurs(); }
function listerSegments() { MarqueurSegmentsVideo.listerSegments(); }
```

9. Sauvegardez et rafraîchissez le document

### Option B : Via URL directe

Créez un lien de partage :

```
https://script.google.com/d/[SCRIPT_ID]/edit?usp=sharing
```

Les utilisateurs peuvent :
1. Cliquer sur le lien
2. **Fichier** → **Faire une copie**
3. Utiliser leur copie dans leurs documents

---

## 🔄 Mises à jour

### Pousser une nouvelle version

```bash
# Modifier le code
cd google-apps-script

# Pousser les changements
clasp push

# Créer une nouvelle version
clasp version "Version 1.1 - Ajout fonctionnalité X"

# Déployer
clasp deploy --description "Production v1.1"
```

### Informer les utilisateurs

Les utilisateurs qui ont ajouté la bibliothèque peuvent mettre à jour :
1. Ouvrir Apps Script dans leur document
2. Cliquer sur **Bibliothèques**
3. Sélectionner la **nouvelle version** dans le menu déroulant
4. Sauvegarder

---

## 📊 Avantages du Mode Standalone

### ✅ Pour l'administrateur
- **Une seule source** : Vous modifiez à un seul endroit
- **Mises à jour centralisées** : Publiez une nouvelle version, les utilisateurs l'installent facilement
- **Suivi des versions** : Historique complet
- **Professionnel** : Ressemble à un vrai produit

### ✅ Pour les utilisateurs
- **Installation simple** : Juste un Script ID à copier
- **Mises à jour faciles** : Changement de version en 2 clics
- **Pas de copier-coller** : Moins d'erreurs
- **Toujours à jour** : Peuvent choisir quelle version utiliser

---

## 🔐 Sécurité et Permissions

### Permissions requises

Le script demande ces autorisations :
- **`documents`** : Lire et modifier le document actif
- **`script.container.ui`** : Créer le menu personnalisé

### OAuth Configuration

Lors de la première utilisation, chaque utilisateur doit :
1. Autoriser le script
2. Accepter les permissions
3. C'est tout !

**Note :** Comme le script est "non vérifié" par Google, un avertissement apparaît. C'est normal pour les scripts personnels.

---

## 📝 Template pour les Utilisateurs

Créez un document Word/PDF avec ces instructions :

```
═══════════════════════════════════════════════════
🎬 INSTALLATION DU MARQUEUR DE SEGMENTS VIDÉO
═══════════════════════════════════════════════════

📌 SCRIPT ID : [VOTRE_SCRIPT_ID_ICI]

🔧 INSTALLATION EN 5 ÉTAPES :

1. Ouvrez votre document Google Docs
2. Extensions → Apps Script
3. Bibliothèques → Coller le Script ID ci-dessus
4. Rechercher → Ajouter (dernière version)
5. Copiez le code ci-dessous dans l'éditeur

[CODE DU WRAPPER ICI]

✅ Sauvegardez et rafraîchissez votre document
✅ Le menu 🎬 Extraits Vidéo apparaît !

🆘 Support : [VOTRE EMAIL]
═══════════════════════════════════════════════════
```

---

## 🧪 Test du Déploiement

### Checklist de test

- [ ] Script déployé avec succès
- [ ] Script ID obtenu
- [ ] Permissions configurées (Toute personne)
- [ ] Test sur un nouveau document vierge
- [ ] Menu 🎬 apparaît correctement
- [ ] Toutes les fonctions marchent
- [ ] Documentation utilisateur à jour avec le Script ID

---

## 📞 Commandes Utiles

```bash
# Voir les infos du projet
clasp open

# Voir les logs d'exécution
clasp logs

# Voir les déploiements
clasp deployments

# Retirer un déploiement
clasp undeploy [DEPLOYMENT_ID]

# Cloner un projet existant
clasp clone [SCRIPT_ID]
```

---

## 🎓 Ressources

- [Documentation clasp](https://github.com/google/clasp)
- [Google Apps Script Guide](https://developers.google.com/apps-script)
- [Apps Script Best Practices](https://developers.google.com/apps-script/guides/support/best-practices)

---

## ✅ Prochaines Étapes

1. **Déployer** : Suivez les étapes ci-dessus
2. **Tester** : Sur un document de test
3. **Documenter** : Donnez le Script ID aux utilisateurs
4. **Former** : Mini-tutoriel vidéo (optionnel)
5. **Monitorer** : Vérifiez que tout fonctionne

**Besoin d'aide ?** Contactez le développeur.
