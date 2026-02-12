# Nettoyage automatique des images Docker

## Problème

Les images Docker s'accumulent dans GCP et coûtent ~$35-40/mois en stockage inutile.

## Solution

### Option 1: Nettoyage manuel (recommandé pour commencer)

Exécutez ce script une fois par mois:

```bash
./cleanup_docker_images.sh
```

Ou via Cloud Build (nettoyage depuis GCP directement):

```bash
gcloud builds submit \
  --config=cloudbuild-cleanup.yaml \
  --no-source \
  --project=artificial-intelligence-cmk
```

### Option 2: Automatisation hebdomadaire via Cloud Scheduler

Pour configurer un nettoyage automatique chaque dimanche à 3h du matin:

#### Étape 1: Créer un topic Pub/Sub

```bash
gcloud pubsub topics create docker-cleanup \
  --project=artificial-intelligence-cmk
```

#### Étape 2: Créer un trigger Cloud Build

```bash
gcloud builds triggers create pubsub \
  --name=docker-cleanup-trigger \
  --topic=docker-cleanup \
  --build-config=cloudbuild-cleanup.yaml \
  --project=artificial-intelligence-cmk \
  --region=europe-west1
```

#### Étape 3: Créer le Cloud Scheduler

```bash
gcloud scheduler jobs create pubsub docker-cleanup-weekly \
  --location=europe-west1 \
  --schedule='0 3 * * 0' \
  --topic=docker-cleanup \
  --message-body='{"action":"cleanup"}' \
  --time-zone='Europe/Paris' \
  --description='Nettoyage hebdomadaire des images Docker' \
  --project=artificial-intelligence-cmk
```

#### Tester immédiatement

```bash
gcloud scheduler jobs run docker-cleanup-weekly \
  --location=europe-west1 \
  --project=artificial-intelligence-cmk
```

## Configuration

Le script garde les **3 dernières versions** de chaque image et supprime le reste.

Pour changer ce nombre, éditez les fichiers:
- `cleanup_docker_images.sh` → ligne `KEEP_VERSIONS=3`
- `cloudbuild-cleanup.yaml` → ligne `KEEP=3`

## Économies

- **Avant**: ~188 GB de stockage Docker = $37/mois
- **Après**: ~40-50 GB = $8-10/mois
- **Économies**: ~$27-29/mois

## Images nettoyées

### Artifact Registry
- `highlights-orchestrator`
- `highlights-processor`
- `whisper-automation`

### Container Registry (gcr.io)
- `highlights-orchestrator`
- `highlights-processor`
- `whisper-automation`
- `whisper-transcription`

## Logs

Pour voir les logs du dernier nettoyage:

```bash
gcloud builds list \
  --filter='buildTriggerId=docker-cleanup-trigger' \
  --limit=1 \
  --project=artificial-intelligence-cmk
```

## Surveillance

Vérifiez l'espace de stockage actuel:

```bash
gcloud artifacts repositories list \
  --project=artificial-intelligence-cmk \
  --format='table(name,format,sizeBytes)'
```

## Désactivation

Pour désactiver le nettoyage automatique:

```bash
gcloud scheduler jobs pause docker-cleanup-weekly \
  --location=europe-west1 \
  --project=artificial-intelligence-cmk
```

Pour le réactiver:

```bash
gcloud scheduler jobs resume docker-cleanup-weekly \
  --location=europe-west1 \
  --project=artificial-intelligence-cmk
```
