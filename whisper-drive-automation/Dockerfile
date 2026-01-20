FROM python:3.11-slim

# Installation des dépendances système + Google Cloud SDK
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    gnupg \
    lsb-release \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg \
    && apt-get update -y \
    && apt-get install google-cloud-cli -y \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de requirements
COPY requirements.txt .

# Installation des dépendances Python avec optimisations
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY src/ src/
COPY scripts/ scripts/
COPY config/ config/

# Variables d'environnement pour GCP et optimisations
ENV PYTHONPATH=/app
# GOOGLE_APPLICATION_CREDENTIALS non défini - Cloud Run utilisera ADC (Application Default Credentials)
ENV PORT=8080
ENV WHISPER_CACHE_DIR=/tmp/whisper

# Créer le cache Whisper
RUN mkdir -p /tmp/whisper

# Exposer le port pour Cloud Run
EXPOSE 8080

# Point d'entrée avec serveur HTTP pour Cloud Run - version modulaire avec anti-doublons
CMD ["python3", "scripts/cloud_run_server.py"]
