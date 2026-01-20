# Configuration Cloud Run - À NE PAS OUBLIER

## Service Account à utiliser

**TOUJOURS** spécifier ce service account lors du déploiement :
```
id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com
```

### Pourquoi ?

1. **Les dossiers sont sur un Shared Drive Google**
2. Ce service account a accès au Shared Drive
3. Le service account par défaut (`996015165236-compute@...`) n'a PAS accès

### Comment déployer

Le script `deployments/whisper/deploy.sh` contient déjà :
```bash
--service-account=id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com
```

**Ne JAMAIS retirer cette ligne !**

### Vérification après déploiement

```bash
gcloud run services describe whisper-automation \
  --region=europe-west1 \
  --format="value(spec.template.spec.serviceAccountName)"
```

Doit retourner : `id-whisper-automation@artificial-intelligence-cmk.iam.gserviceaccount.com`

### Application Default Credentials (ADC)

Le code utilise maintenant ADC au lieu de `credentials.json` :
- ✅ Plus besoin de `credentials.json` dans l'image Docker
- ✅ Plus sécurisé
- ✅ ADC utilise automatiquement le service account de Cloud Run

**Mais il faut spécifier le BON service account au déploiement !**

## IDs des dossiers (Shared Drive)

```
Input:          1A29pkQvrBodU_HxNS8deYt6T27AlmbSe
Transcriptions: 1yHcy9um2_We459w9I0cITwHBGXKTlOJa
Queue:          1yvN9VP0bAmZJGfyUlBFG4mzR22c5addV
```

Toutes les requêtes Drive doivent utiliser :
```python
supportsAllDrives=True
includeItemsFromAllDrives=True
```
