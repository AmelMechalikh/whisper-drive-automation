# Résumé: Nettoyage automatique des images Docker

## 🎯 Problème résolu

Vos crédits GCP fondaient à cause de **188 GB d'images Docker** accumulées (~$37/mois en stockage).

## ✅ Solutions mises en place

### 1. Nettoyage manuel effectué

**210 anciennes images supprimées:**
- Artifact Registry: 64 images
- Container Registry: 146 images (dont 107 versions de whisper-transcription)

**Économies immédiates: ~$27-29/mois**

### 2. Automatisation configurée

#### a) Cloud Scheduler
- **Fréquence**: Chaque dimanche à 3h du matin
- **Timezone**: Europe/Paris
- **Status**: ✅ Actif

#### b) Cloud Function
- **Nom**: `docker-cleanup-function`
- **Région**: europe-west1
- **Trigger**: Pub/Sub topic `docker-cleanup`
- **Status**: ✅ Déployée

#### c) Scripts locaux
- **`cleanup_docker_images.sh`**: Nettoyage manuel en local
- **`cloudbuild-cleanup.yaml`**: Configuration Cloud Build

### 3. Configuration

Le système garde automatiquement les **3 dernières versions** de chaque image et supprime le reste.

## 💰 Coûts finaux

### Avant nettoyage
- Stockage Docker: **188 GB** = $37/mois
- Disques VMs: **300 GB** = $25/mois
- VMs + Cloud Run: $3/mois
- **TOTAL: ~$65/mois**

### Après nettoyage + automatisation
- Stockage Docker: **~40-50 GB** = $8-10/mois
- Disques VMs: **300 GB** = $25/mois
- VMs + Cloud Run: $3/mois
- Cloud Function: ~$0.40/mois (très peu d'exécutions)
- **TOTAL: ~$36-38/mois**

### 💵 Économies: ~$27-29/mois

## 📋 Commandes utiles

### Nettoyage manuel
```bash
# Depuis votre machine locale
./cleanup_docker_images.sh

# Ou via Cloud Build
gcloud builds submit \
  --config=cloudbuild-cleanup.yaml \
  --no-source \
  --project=artificial-intelligence-cmk
```

### Vérifier l'espace de stockage
```bash
gcloud artifacts repositories list \
  --project=artificial-intelligence-cmk \
  --format='table(name,format,sizeBytes)'
```

### Voir les logs du nettoyage automatique
```bash
gcloud functions logs read docker-cleanup-function \
  --region=europe-west1 \
  --limit=50
```

### Tester le scheduler manuellement
```bash
gcloud scheduler jobs run docker-cleanup-weekly \
  --location=europe-west1 \
  --project=artificial-intelligence-cmk
```

### Désactiver temporairement l'automatisation
```bash
gcloud scheduler jobs pause docker-cleanup-weekly \
  --location=europe-west1 \
  --project=artificial-intelligence-cmk
```

### Réactiver l'automatisation
```bash
gcloud scheduler jobs resume docker-cleanup-weekly \
  --location=europe-west1 \
  --project=artificial-intelligence-cmk
```

## 🔍 Surveillance

### Vérifier le statut du scheduler
```bash
gcloud scheduler jobs describe docker-cleanup-weekly \
  --location=europe-west1 \
  --project=artificial-intelligence-cmk
```

### Voir l'historique des builds de nettoyage
```bash
gcloud builds list \
  --filter='steps.name:cloudsdktool' \
  --limit=10 \
  --project=artificial-intelligence-cmk
```

## 📊 Images nettoyées automatiquement

### Artifact Registry (cloud-run-source-deploy)
- `highlights-orchestrator`
- `highlights-processor`
- `whisper-automation`

### Container Registry (gcr.io)
- `highlights-orchestrator`
- `highlights-processor`
- `whisper-automation`
- `whisper-transcription`

## ⚙️ Modifier la configuration

Pour changer le nombre de versions à garder (actuellement 3):

**Script local:**
```bash
# Éditer cleanup_docker_images.sh
KEEP_VERSIONS=5  # Changer cette ligne
```

**Cloud Build:**
```bash
# Éditer cloudbuild-cleanup.yaml
KEEP=5  # Changer cette ligne
```

**Cloud Function:**
```bash
# Éditer /tmp/cleanup-pubsub-function/main.py
KEEP=5  # Changer dans le script bash inline
```

## 🚨 Alertes recommandées

Configurez des alertes si le stockage Docker dépasse 100 GB:

```bash
# À faire via la console GCP > Monitoring > Alerting
# Métrique: storage.googleapis.com/storage/object_count
# Condition: > 100 GB
```

## 📝 Notes importantes

1. **Les VMs coûtent toujours ~$25/mois** même arrêtées (disques persistants)
   - whisper-cpu-worker: 100 GB SSD (~$17/mois)
   - highlights-worker-vm: 200 GB standard (~$8/mois)

2. **Pour réduire encore les coûts**, envisagez de:
   - Réduire la taille des disques VMs
   - Supprimer les snapshots inutiles
   - Utiliser des disques standard au lieu de SSD

3. **Le nettoyage automatique**:
   - S'exécute chaque dimanche à 3h
   - Prend 2-5 minutes
   - Coûte ~$0.01 par exécution
   - Économise ~$25-30/mois

## ✅ Prochaines étapes (optionnel)

1. **Réduire la taille des disques VMs** (économie: ~$15/mois)
2. **Configurer des alertes de coût** dans GCP Billing
3. **Vérifier mensuellement** l'espace de stockage

## 📞 Support

Voir la documentation complète: `README-DOCKER-CLEANUP.md`

---

**Date de configuration**: 2026-02-05
**Économies totales**: ~$300-350/an
