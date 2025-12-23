# Architecture Highlights - VM On-Demand

## Vue d'ensemble

Le système de highlights utilise une architecture **event-driven** avec VM on-demand pour minimiser les coûts.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────┘

  ⏰ Cloud Scheduler (toutes les 5 min)
              ↓
  ☁️  Cloud Run Orchestrator
       • Vérifie nouveaux fichiers sur Drive
       • Décide si lancement VM nécessaire
       • Lance la VM si besoin
              ↓
  🖥️  VM Highlights (démarre uniquement si travail)
       ├─ Étape 1: highlight_worker.py
       │   • Extrait commentaires Google Docs
       │   • Match avec timestamps
       │   • Génère Excel
       │
       ├─ Étape 2: process_video_segments.py
       │   • Lit Excel
       │   • Télécharge vidéo source
       │   • Découpe segments avec ffmpeg
       │   • Fusionne segments identiques
       │   • Upload sur Drive
       │
       └─ Auto-shutdown après traitement
              ↓
  📁 Google Drive (résultats)
       • Highlights Excel/
       • Segments Videos/{nom_video}/
```

---

## Composants

### 1. Cloud Run Orchestrator

**Fichier** : `scripts/highlight_orchestrator_cloud.py`

**Rôle** :
- Endpoint HTTP qui vérifie Drive périodiquement
- Détecte nouveaux fichiers avec commentaires
- Détecte Excel non traités
- Lance la VM si nécessaire via Compute Engine API

**Endpoints** :
- `GET /` : Health check
- `POST /trigger` : Vérifie et lance la VM (appelé par Scheduler)
- `GET /status` : Statut de la VM et fichiers en attente

**Coût** : ~0€/mois (scale-to-zero, <1s par invocation)

### 2. VM Highlights Worker

**Configuration** :
- Type : `e2-standard-2` (2 vCPU, 8GB RAM)
- Disque : 30GB
- Auto-shutdown : Oui (après traitement)

**Script de startup** : `scripts/vm_startup_highlights.sh`

Workflow :
1. Démarre automatiquement
2. Exécute `highlight_worker.py` (one-shot)
3. Exécute `process_video_segments.py` (one-shot)
4. Nettoie les fichiers temporaires
5. Upload logs sur Drive
6. S'éteint automatiquement

**Coût** : 0.03€/h × temps réel d'utilisation (~1-5€/mois)

### 3. Cloud Scheduler

**Job** : `trigger-highlights`
- Schedule : `*/5 * * * *` (toutes les 5 minutes)
- Action : Appelle `POST /trigger` sur Cloud Run
- Timeout : 60s

**Coût** : ~0€/mois (3 jobs gratuits)

---

## Différences avec l'architecture précédente

| Aspect | Avant (Polling) | Maintenant (Event-driven) |
|--------|----------------|---------------------------|
| **VM** | Allumée 24/7 | On-demand uniquement |
| **Coût VM** | ~15-20€/mois | ~1-5€/mois |
| **Workers** | Boucle `while True` | Exécution one-shot |
| **Trigger** | Polling interne | Cloud Scheduler → Cloud Run |
| **Latence** | Détection immédiate | Max 5 min |
| **Complexité** | Simple | Moyenne |

---

## Déploiement

### Prérequis

1. **GCP Project configuré**
2. **APIs activées** :
   - Cloud Run API
   - Compute Engine API
   - Cloud Scheduler API
   - Cloud Build API
3. **Service Account** avec permissions :
   - Compute Instance Admin
   - Cloud Run Admin
   - Service Account User

### Déploiement automatique

```bash
cd whisper-drive-automation
chmod +x scripts/deploy_highlights.sh
./scripts/deploy_highlights.sh
```

Ce script :
1. ✅ Active les APIs GCP
2. ✅ Déploie Cloud Run orchestrator
3. ✅ Crée la VM (arrêtée par défaut)
4. ✅ Configure Cloud Scheduler
5. ✅ Configure les metadata de startup

### Déploiement manuel

#### 1. Cloud Run

```bash
cd whisper-drive-automation
gcloud run deploy highlights-orchestrator \
  --source . \
  --region=europe-west1 \
  --allow-unauthenticated \
  --memory=1Gi \
  --timeout=60s \
  --max-instances=1
```

#### 2. VM

```bash
gcloud compute instances create highlights-worker \
  --zone=europe-west1-b \
  --machine-type=e2-standard-2 \
  --image-family=debian-11 \
  --image-project=debian-cloud \
  --boot-disk-size=30GB \
  --scopes=cloud-platform \
  --metadata-from-file=startup-script=scripts/vm_startup_highlights.sh \
  --tags=highlights-worker

# Arrêter immédiatement (sera lancée par Cloud Run)
gcloud compute instances stop highlights-worker --zone=europe-west1-b
```

#### 3. Copier les fichiers sur la VM

```bash
gcloud compute instances start highlights-worker --zone=europe-west1-b

# Attendre que la VM démarre...
sleep 30

gcloud compute scp --recurse \
  config src scripts requirements.txt \
  amel@highlights-worker:~/whisper-drive-automation/ \
  --zone=europe-west1-b

# Installer les dépendances
gcloud compute ssh highlights-worker --zone=europe-west1-b --command="
  cd whisper-drive-automation
  sudo apt-get update
  sudo apt-get install -y python3-pip ffmpeg
  pip3 install -r requirements.txt
"

# Arrêter la VM
gcloud compute instances stop highlights-worker --zone=europe-west1-b
```

#### 4. Cloud Scheduler

```bash
chmod +x scripts/setup_scheduler.sh
./scripts/setup_scheduler.sh
```

---

## Tests

### 1. Test Cloud Run (local)

```bash
# Démarrer localement
cd whisper-drive-automation
export PORT=8080
python3 scripts/highlight_orchestrator_cloud.py
```

Dans un autre terminal :
```bash
# Health check
curl http://localhost:8080/

# Trigger
curl -X POST http://localhost:8080/trigger

# Status
curl http://localhost:8080/status
```

### 2. Test Cloud Run (production)

```bash
CLOUD_RUN_URL=$(gcloud run services describe highlights-orchestrator \
  --region=europe-west1 --format='value(status.url)')

# Trigger manuel
curl -X POST $CLOUD_RUN_URL/trigger

# Vérifier le statut
curl $CLOUD_RUN_URL/status
```

### 3. Test complet avec fichier

1. Ajouter un fichier Google Doc avec commentaires dans `Highlighted Files`
2. Attendre 5 min (ou trigger manuel)
3. Vérifier les logs Cloud Run
4. Vérifier que la VM démarre
5. Vérifier les logs VM
6. Vérifier que l'Excel est créé
7. Vérifier que les segments vidéo sont uploadés
8. Vérifier que la VM s'éteint

---

## Monitoring

### Logs Cloud Run

```bash
gcloud run services logs read highlights-orchestrator \
  --region=europe-west1 \
  --limit=50
```

### Logs VM

```bash
# En temps réel (si VM running)
gcloud compute ssh highlights-worker --zone=europe-west1-b \
  --command="tail -f ~/whisper-drive-automation/logs/highlights_*.log"

# Logs de startup
gcloud compute instances get-serial-port-output highlights-worker \
  --zone=europe-west1-b
```

### Status VM

```bash
gcloud compute instances describe highlights-worker \
  --zone=europe-west1-b \
  --format='value(status)'
```

### Cloud Scheduler

```bash
# Lister les jobs
gcloud scheduler jobs list --location=europe-west1

# Voir les exécutions
gcloud scheduler jobs describe trigger-highlights \
  --location=europe-west1
```

---

## Coûts Estimés

| Service | Usage | Coût mensuel |
|---------|-------|--------------|
| **Cloud Run** | ~8640 invocations/mois (5 min) | 0€ (tier gratuit) |
| **Cloud Scheduler** | 1 job | 0€ (3 jobs gratuits) |
| **VM e2-standard-2** | ~10-50h/mois | 1-5€ |
| **Storage** | Logs, fichiers temp | <1€ |
| **Network** | Uploads/downloads | <1€ |
| **TOTAL** | | **~2-7€/mois** |

### Comparaison avec polling 24/7

| Architecture | Coût mensuel | Économie |
|--------------|--------------|----------|
| **Polling (VM 24/7)** | ~20€ | - |
| **Event-driven (VM on-demand)** | ~4€ | **80%** 💰 |

---

## Troubleshooting

### Cloud Run ne démarre pas la VM

**Symptômes** :
- Status 500 sur `/trigger`
- Logs : "Erreur démarrage VM"

**Solutions** :
1. Vérifier les permissions du Service Account :
   ```bash
   gcloud projects add-iam-policy-binding artificial-intelligence-cmk \
     --member="serviceAccount:YOUR_SA@artificial-intelligence-cmk.iam.gserviceaccount.com" \
     --role="roles/compute.instanceAdmin.v1"
   ```

2. Vérifier que la VM existe et est TERMINATED :
   ```bash
   gcloud compute instances describe highlights-worker --zone=europe-west1-b
   ```

### VM ne s'éteint pas après traitement

**Causes possibles** :
- Erreur dans le script de startup
- Process bloqué

**Debug** :
```bash
gcloud compute ssh highlights-worker --zone=europe-west1-b

# Voir les processes Python
ps aux | grep python

# Voir les logs
cat ~/whisper-drive-automation/logs/highlights_*.log

# Arrêt manuel
sudo shutdown -h now
```

### Excel créé mais pas de segments vidéo

**Vérifications** :
1. ffmpeg installé ? `which ffmpeg`
2. Vidéo source existe dans `Files` ?
3. Excel correctement formaté ?
4. Logs : `cat ~/whisper-drive-automation/logs/highlights_*.log`

### Cloud Scheduler ne trigger pas

```bash
# Tester manuellement
gcloud scheduler jobs run trigger-highlights --location=europe-west1

# Voir les logs d'exécution
gcloud scheduler jobs describe trigger-highlights --location=europe-west1
```

---

## Optimisations Futures

### 1. Webhook Drive (Latence 0)

Au lieu de polling 5 min, utiliser les notifications Drive API :
- Webhook sur modification dossier
- Push notification → Cloud Function → Start VM
- Latence : <30s

### 2. Spot/Preemptible VM (Coût -70%)

VM Spot = 0.01€/h au lieu de 0.03€/h
- Acceptable car travail non critique
- Relance automatique si préempté

### 3. Batch Processing

Grouper plusieurs fichiers avant de lancer VM :
- Réduire le nombre de démarrages
- Amortir le coût du boot (2-3 min)

---

## Migration depuis l'ancienne architecture

Si vous aviez déjà déployé avec polling 24/7 :

1. **Arrêter l'ancien worker systemd** :
   ```bash
   gcloud compute ssh whisper-cpu-worker --zone=europe-west1-b --command="
     sudo systemctl stop highlight-worker
     sudo systemctl disable highlight-worker
     sudo systemctl stop video-segment-processor
     sudo systemctl disable video-segment-processor
   "
   ```

2. **Déployer la nouvelle architecture** :
   ```bash
   ./scripts/deploy_highlights.sh
   ```

3. **Tester** avec un fichier

4. **Supprimer les anciens services systemd** (optionnel) :
   ```bash
   gcloud compute ssh whisper-cpu-worker --zone=europe-west1-b --command="
     sudo rm /etc/systemd/system/highlight-worker.service
     sudo rm /etc/systemd/system/video-segment-processor.service
     sudo systemctl daemon-reload
   "
   ```

---

## FAQ

**Q: Pourquoi ne pas utiliser Cloud Functions directement ?**
R: Cloud Functions ont un timeout de 9 min max. Le découpage vidéo peut prendre plus longtemps.

**Q: Pourquoi Cloud Run + VM et pas juste Cloud Run ?**
R: Cloud Run timeout = 60 min. Découpage vidéo peut dépasser pour longues vidéos.

**Q: Peut-on réduire l'intervalle à 1 min ?**
R: Oui, changer `*/5 * * * *` en `* * * * *` dans setup_scheduler.sh. Mais coût augmente légèrement.

**Q: Que se passe-t-il si 2 triggers en même temps ?**
R: Le Cloud Run vérifie le statut VM avant de démarrer. Si RUNNING, il skip.

**Q: Peut-on notifier l'utilisateur quand c'est terminé ?**
R: Oui, ajouter un envoi d'email à la fin du script de startup VM.
