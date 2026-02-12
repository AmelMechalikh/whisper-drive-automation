# RunPod Backend - Checklist d'implémentation

## ✅ Phase 1: Préparation (avant déploiement)

### 1.1 RunPod Setup
- [ ] Créer un compte RunPod (https://www.runpod.io)
- [ ] Ajouter du crédit au compte
- [ ] Créer un endpoint Serverless:
  - [ ] Template: "Whisper Large-v3"
  - [ ] GPU: RTX 4090
  - [ ] Min workers: 0
  - [ ] Max workers: 5
  - [ ] Idle timeout: 60s
- [ ] Noter l'Endpoint ID: `____________________`
- [ ] Créer une API Key dans Settings
- [ ] Noter l'API Key: `____________________`

### 1.2 Google Cloud Storage
- [ ] Créer le bucket GCS:
  ```bash
  gsutil mb -l europe-west1 gs://whisper-temp-audio
  ```
- [ ] Configurer lifecycle policy (auto-delete après 1 jour):
  ```bash
  cat > lifecycle.json << EOF
  {
    "lifecycle": {
      "rule": [{
        "action": {"type": "Delete"},
        "condition": {"age": 1}
      }]
    }
  }
  EOF
  gsutil lifecycle set lifecycle.json gs://whisper-temp-audio
  ```
- [ ] Configurer les permissions IAM:
  ```bash
  SERVICE_ACCOUNT="id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com"
  gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:roles/storage.objectAdmin \
    gs://whisper-temp-audio
  ```

### 1.3 Configuration locale
- [ ] Mettre à jour `config/highlight_config.json`:
  - [ ] Remplacer `<YOUR_ENDPOINT_ID>` par votre endpoint ID
  - [ ] Vérifier `"provider": "gpu_runpod"`
  - [ ] Vérifier `"subtitles_vm_enabled": false`
  - [ ] Vérifier `"gcs_temp_bucket": "whisper-temp-audio"`
- [ ] Commiter les changements:
  ```bash
  git add config/highlight_config.json
  git commit -m "feat: add RunPod backend configuration"
  ```

## ✅ Phase 2: Tests locaux (recommandé)

### 2.1 Test du client RunPod
- [ ] Définir la variable d'environnement:
  ```bash
  export RUNPOD_API_KEY="votre_cle"
  ```
- [ ] Installer les dépendances:
  ```bash
  pip install -r requirements-runpod.txt
  ```
- [ ] Tester le client:
  ```bash
  python test_runpod_client.py
  ```
- [ ] Vérifier que la transcription fonctionne
- [ ] Vérifier les word-level timestamps

### 2.2 Test du backend abstraction
- [ ] Tester la sélection du backend:
  ```python
  from transcription_backends import get_transcription_backend
  import json

  with open('config/highlight_config.json') as f:
      config = json.load(f)

  backend = get_transcription_backend(config)
  print(f"Backend: {backend.get_backend_name()}")
  # Devrait afficher: "gpu_runpod"
  ```

## ✅ Phase 3: Build & déploiement

### 3.1 Build de l'image Docker
- [ ] Option A - Cloud Build (recommandé):
  ```bash
  gcloud builds submit \
    --config cloudbuild-runpod.yaml \
    --substitutions=_RUNPOD_API_KEY="votre_cle"
  ```
- [ ] Option B - Build local:
  ```bash
  docker build -f Dockerfile.runpod-worker \
    -t gcr.io/artificial-intelligence-cmk/runpod-transcription-worker .
  docker push gcr.io/artificial-intelligence-cmk/runpod-transcription-worker
  ```

### 3.2 Déploiement Cloud Run Worker
- [ ] Déployer le worker RunPod:
  ```bash
  gcloud run deploy runpod-transcription-worker \
    --image gcr.io/artificial-intelligence-cmk/runpod-transcription-worker \
    --region europe-west1 \
    --memory 2Gi \
    --timeout 3600 \
    --max-instances 5 \
    --set-env-vars RUNPOD_API_KEY="votre_cle" \
    --service-account id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com \
    --no-allow-unauthenticated
  ```
- [ ] Noter l'URL du service: `____________________`

### 3.3 Upload de la configuration
- [ ] Upload config sur GCS:
  ```bash
  gsutil cp config/highlight_config.json \
    gs://artificial-intelligence-cmk/config/
  ```
- [ ] Vérifier que le fichier est bien uploadé:
  ```bash
  gsutil cat gs://artificial-intelligence-cmk/config/highlight_config.json | \
    jq '.transcription_backend.provider'
  ```

### 3.4 Redéploiement de l'orchestrator
- [ ] Redéployer l'orchestrator pour lire la nouvelle config:
  ```bash
  gcloud run deploy highlights-orchestrator \
    --source . \
    --region europe-west1
  ```

## ✅ Phase 4: Vérification

### 4.1 Vérifications de base
- [ ] Vérifier que le worker RunPod est déployé:
  ```bash
  gcloud run services list --region europe-west1 | grep runpod
  ```
- [ ] Vérifier les variables d'environnement:
  ```bash
  gcloud run services describe runpod-transcription-worker \
    --region europe-west1 \
    --format="value(spec.template.spec.containers[0].env)"
  ```
- [ ] Vérifier que la VM CPU est arrêtée:
  ```bash
  gcloud compute instances describe highlights-worker-vm \
    --zone europe-west1-b --format="value(status)"
  # Devrait afficher: TERMINATED
  ```

### 4.2 Logs et monitoring
- [ ] Vérifier les logs du worker RunPod:
  ```bash
  gcloud run services logs read runpod-transcription-worker \
    --region europe-west1 --limit 20
  ```
- [ ] Vérifier les logs de l'orchestrator:
  ```bash
  gcloud run services logs read highlights-orchestrator \
    --region europe-west1 --limit 20
  ```

## ✅ Phase 5: Test end-to-end

### 5.1 Préparation du test
- [ ] Créer un document Google Docs de test
- [ ] Ajouter un court texte (1-2 paragraphes)
- [ ] Ajouter une vidéo courte (~1 minute)
- [ ] Marquer avec la balise `🎬 READY 🎬`

### 5.2 Exécution du test
- [ ] Option A - Attendre le Cloud Scheduler (prochain cycle)
- [ ] Option B - Déclencher manuellement:
  ```bash
  gcloud scheduler jobs run highlights-automation-scheduler \
    --location=europe-west1
  ```

### 5.3 Vérification des résultats
- [ ] Vérifier que l'orchestrator a traité le document:
  ```bash
  gcloud run services logs read highlights-orchestrator \
    --region europe-west1 --limit 50 | grep "READY"
  ```
- [ ] Vérifier qu'un job a été créé dans Drive:
  - Dossier: `queue_subtitles/`
  - Fichier: `subtitles_job_*.json`
- [ ] Vérifier que le worker RunPod traite le job:
  ```bash
  gcloud run services logs read runpod-transcription-worker \
    --region europe-west1 --limit 50 | grep "Traitement du job"
  ```
- [ ] Vérifier que la VM CPU n'a PAS démarré:
  ```bash
  gcloud compute instances describe highlights-worker-vm \
    --zone europe-west1-b --format="value(status)"
  # Devrait toujours être: TERMINATED
  ```
- [ ] Vérifier la sortie dans Drive:
  - Dossier: `segments_output/<dossier_segments>/with_subtitles_<timestamp>/`
  - Fichiers: `*_SUBTITLED.mp4`
- [ ] Télécharger une vidéo sous-titrée et vérifier:
  - [ ] Les sous-titres sont présents
  - [ ] Les sous-titres sont synchronisés
  - [ ] La qualité de transcription est bonne
- [ ] Vérifier que le document est marqué `🎬 SUBTITLES_DONE 🎬`

## ✅ Phase 6: Monitoring (première semaine)

### 6.1 Métriques à surveiller
- [ ] Nombre de jobs traités avec succès: `____`
- [ ] Nombre d'erreurs: `____`
- [ ] Temps moyen de transcription: `____ secondes`
- [ ] Coût RunPod quotidien: `____ $`

### 6.2 Vérifications quotidiennes
- [ ] Jour 1: Vérifier les logs pour erreurs
- [ ] Jour 2: Vérifier les coûts RunPod
- [ ] Jour 3: Comparer qualité CPU vs GPU
- [ ] Jour 4: Vérifier les timeouts (si > 10%, augmenter timeout)
- [ ] Jour 5: Vérifier les cold starts RunPod
- [ ] Jour 6: Optimiser si nécessaire
- [ ] Jour 7: Bilan de la semaine

### 6.3 Dashboard RunPod
- [ ] Ouvrir https://www.runpod.io/console/serverless
- [ ] Vérifier les métriques:
  - [ ] Nombre de requêtes
  - [ ] Temps d'exécution moyen
  - [ ] Taux d'erreur
  - [ ] Cold starts
- [ ] Ajuster la configuration si nécessaire:
  - [ ] Si cold starts > 30s: augmenter min_workers à 1
  - [ ] Si coûts trop élevés: réduire max_workers
  - [ ] Si qualité insuffisante: passer à "large-v3" (non-turbo)

## ✅ Phase 7: Validation finale

### 7.1 Checklist de validation
- [ ] ✅ RunPod endpoint fonctionne correctement
- [ ] ✅ Jobs de sous-titres sont traités automatiquement
- [ ] ✅ VM CPU ne démarre plus pour les sous-titres
- [ ] ✅ Qualité de transcription améliorée vs CPU
- [ ] ✅ Coûts dans le budget prévu (~$6/mois)
- [ ] ✅ Aucune erreur dans les logs depuis 48h
- [ ] ✅ Temps de transcription < 1 min pour 5 min audio

### 7.2 Documentation mise à jour
- [ ] Mettre à jour le README si nécessaire
- [ ] Documenter les coûts réels observés
- [ ] Documenter les temps de transcription réels
- [ ] Partager les résultats avec l'équipe

## ✅ Phase 8: Rollback (si nécessaire)

### 8.1 Critères de rollback
Rollback si:
- [ ] Taux d'erreur > 10%
- [ ] Coûts > 2× prévision
- [ ] Timeouts fréquents (> 20% des jobs)
- [ ] Qualité de transcription dégradée

### 8.2 Procédure de rollback
- [ ] Modifier la config:
  ```bash
  jq '.transcription_backend.provider = "cpu_local" |
      .vm_workers.subtitles_vm_enabled = true |
      .vm_workers.auto_start_subtitles_vm = true' \
    config/highlight_config.json > temp.json
  mv temp.json config/highlight_config.json
  ```
- [ ] Upload sur GCS:
  ```bash
  gsutil cp config/highlight_config.json \
    gs://artificial-intelligence-cmk/config/
  ```
- [ ] Redéployer l'orchestrator:
  ```bash
  gcloud run deploy highlights-orchestrator --source .
  ```
- [ ] Vérifier que le système fonctionne avec CPU
- [ ] Investiguer la cause du problème RunPod

## 📊 Résumé des changements

### Fichiers créés (9)
1. `src/transcription_backends.py` - Backend abstraction
2. `src/runpod_client.py` - Client API RunPod
3. `scripts/runpod_transcription_worker.py` - Worker Cloud Run
4. `Dockerfile.runpod-worker` - Image Docker worker
5. `requirements-runpod.txt` - Dépendances worker
6. `cloudbuild-runpod.yaml` - Build configuration
7. `test_runpod_client.py` - Script de test
8. `RUNPOD_DEPLOYMENT_GUIDE.md` - Guide déploiement
9. `RUNPOD_IMPLEMENTATION_SUMMARY.md` - Résumé implémentation

### Fichiers modifiés (3)
1. `config/highlight_config.json` - Configuration backend
2. `scripts/subtitles_vm_worker.py` - Utilisation backend abstrait
3. `scripts/highlight_orchestrator_cloud.py` - Respect des flags VM

### Fichiers de documentation (2)
1. `CONFIG_REFERENCE.md` - Référence configuration
2. `IMPLEMENTATION_CHECKLIST.md` - Cette checklist

## 🎯 Objectifs de la migration

- [x] Abstraire le backend de transcription
- [x] Supporter RunPod GPU comme backend
- [x] Garder le CPU local comme fallback
- [x] Feature flags pour contrôle fin
- [x] Documentation complète
- [ ] Tests en production
- [ ] Validation de la qualité
- [ ] Validation des coûts

## 📞 Support

En cas de problème:
1. Consulter `RUNPOD_DEPLOYMENT_GUIDE.md` - section Troubleshooting
2. Vérifier `CONFIG_REFERENCE.md` - validation configuration
3. Consulter les logs Cloud Run
4. Vérifier le dashboard RunPod
5. Si bloqué: rollback vers CPU avec la procédure ci-dessus

---

**Date de début**: ____________

**Date de fin**: ____________

**Status**: ⬜ En cours / ⬜ Complété / ⬜ Rollback effectué

**Notes**:
_________________________________________________________________________
_________________________________________________________________________
_________________________________________________________________________
