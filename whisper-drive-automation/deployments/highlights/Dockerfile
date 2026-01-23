FROM python:3.11-slim

# Installation de ffmpeg (nécessaire pour découpage vidéo)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de requirements (version légère sans torch/whisperx)
COPY deployments/highlights/requirements-orchestrator.txt ./requirements.txt

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY src/ /app/src/
COPY scripts/highlight_orchestrator_cloud.py /app/
COPY config/ /app/config/

# Variables d'environnement
ENV PYTHONPATH=/app/src
ENV PORT=8080

# Exposer le port pour Cloud Run
EXPOSE 8080

# Point d'entrée - Highlights Processor avec gunicorn
CMD ["gunicorn", "--bind", ":8080", "--workers", "1", "--threads", "4", "--timeout", "3600", "highlight_orchestrator_cloud:app"]
