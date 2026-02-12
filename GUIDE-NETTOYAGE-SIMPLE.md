# Guide de nettoyage des images Docker GCP

## 🎯 Problème

Vos images Docker s'accumulent sur GCP et coûtent ~$35-40/mois en stockage inutile.

## ✅ Solution (2 options)

### Option 1: Nettoyage manuel mensuel (RECOMMANDÉ)

**Le plus simple et gratuit:**

```bash
cd /Users/amel/Documents/Transcription-Project
./cleanup_docker_images.sh
```

**Fréquence recommandée:** Une fois par mois

**Durée:** 2-3 minutes

**Coût:** $0

### Option 2: Automatisation locale (optionnel)

Si vous voulez automatiser sur votre Mac:

```bash
cd /Users/amel/Documents/Transcription-Project
./setup_crontab_cleanup.sh
```

Cela ajoutera une tâche cron qui exécute le nettoyage automatiquement le 1er dimanche de chaque mois à 3h du matin.

## 💰 Économies

- **Avant:** 188 GB de stockage Docker = ~$37/mois
- **Après:** 40-50 GB = ~$8-10/mois  
- **Économies:** ~$27-29/mois = **~$300-350/an**

## 📊 Vérifier l'espace de stockage

```bash
gcloud artifacts repositories list \
  --project=artificial-intelligence-cmk \
  --format='table(name,format,sizeBytes)'
```

## 🔍 Images nettoyées

Le script garde les **3 dernières versions** de chaque image et supprime le reste:

- `highlights-orchestrator`
- `highlights-processor`  
- `whisper-automation`
- `whisper-transcription`

## ⚙️ Configuration

Pour changer le nombre de versions à garder (actuellement 3):

Éditez `cleanup_docker_images.sh` et changez:
```bash
KEEP_VERSIONS=5  # Au lieu de 3
```

## 📝 Résultats du nettoyage

Lors du dernier nettoyage:
- **210 images supprimées** au total
  - Artifact Registry: 64 images
  - Container Registry: 146 images

## ⚠️ Notes importantes

1. Le nettoyage ne supprime jamais les 3 versions les plus récentes
2. Vos services Cloud Run continuent de fonctionner normalement
3. L'exécution prend 2-3 minutes
4. Aucun risque de casser vos déploiements actuels

## 🚀 Utilisation

### Première fois
```bash
cd /Users/amel/Documents/Transcription-Project
chmod +x cleanup_docker_images.sh
./cleanup_docker_images.sh
```

### Ensuite
```bash
./cleanup_docker_images.sh
```

## 📅 Rappel

Ajoutez un rappel mensuel dans votre calendrier pour exécuter le script.

**Ou** configurez l'automatisation locale avec:
```bash
./setup_crontab_cleanup.sh
```

---

**Économies annuelles:** ~$300-350
**Temps requis:** 5 minutes/mois
**Difficulté:** ⭐ Très facile
