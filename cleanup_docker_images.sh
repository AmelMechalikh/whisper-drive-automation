#!/bin/bash
#
# Script de nettoyage manuel des anciennes images Docker
# Garde les 3 dernières versions de chaque image
#
set -e

PROJECT_ID="artificial-intelligence-cmk"
REGION="europe-west1"
REPO="cloud-run-source-deploy"
KEEP_VERSIONS=3

echo "🧹 Nettoyage des images Docker anciennes"
echo "=========================================="
echo "Projet: $PROJECT_ID"
echo "Garder: $KEEP_VERSIONS dernières versions par image"
echo ""

# Fonction de nettoyage pour Artifact Registry
cleanup_package() {
    local package=$1
    local package_name=$(basename $package)

    echo "📦 Analyse: $package_name"

    versions=$(gcloud artifacts docker images list "$package" \
        --format='value(version)' \
        --sort-by=~CREATE_TIME \
        --limit=1000 2>/dev/null || echo "")

    if [ -z "$versions" ]; then
        echo "   ⚠️  Aucune version trouvée"
        return
    fi

    total=$(echo "$versions" | wc -l | tr -d ' ')
    to_delete=$((total - KEEP_VERSIONS))

    if [ $to_delete -le 0 ]; then
        echo "   ✓ Seulement $total versions, rien à supprimer"
        return
    fi

    echo "   Total: $total versions"
    echo "   À garder: $KEEP_VERSIONS"
    echo "   À supprimer: $to_delete versions"

    deleted=0
    echo "$versions" | tail -n +$((KEEP_VERSIONS + 1)) | while read version; do
        if [ -n "$version" ]; then
            echo "   🗑️  Suppression: ${version:0:20}..."
            gcloud artifacts docker images delete "${package}@${version}" \
                --quiet --delete-tags 2>/dev/null || true
            deleted=$((deleted + 1))
        fi
    done

    echo "   ✅ $to_delete versions supprimées"
    echo ""
}

# Fonction de nettoyage pour Container Registry
cleanup_gcr_image() {
    local image=$1
    local image_name=$(basename $image)

    echo "📦 Analyse: $image_name"

    digests=$(gcloud container images list-tags "$image" \
        --format='get(digest)' \
        --sort-by=~timestamp \
        --limit=1000 2>/dev/null || echo "")

    if [ -z "$digests" ]; then
        echo "   ⚠️  Aucune version trouvée"
        return
    fi

    total=$(echo "$digests" | wc -l | tr -d ' ')
    to_delete=$((total - KEEP_VERSIONS))

    if [ $to_delete -le 0 ]; then
        echo "   ✓ Seulement $total versions, rien à supprimer"
        return
    fi

    echo "   Total: $total versions"
    echo "   À garder: $KEEP_VERSIONS"
    echo "   À supprimer: $to_delete versions"

    deleted=0
    echo "$digests" | tail -n +$((KEEP_VERSIONS + 1)) | while read digest; do
        if [ -n "$digest" ]; then
            echo "   🗑️  Suppression: ${digest:0:12}..."
            gcloud container images delete "${image}@${digest}" \
                --quiet --force-delete-tags 2>/dev/null || true
            deleted=$((deleted + 1))
        fi
    done

    echo "   ✅ Supprimé $to_delete versions"
    echo ""
}

# Nettoyer Artifact Registry
echo "🔍 Nettoyage Artifact Registry..."
echo ""
packages=$(gcloud artifacts docker images list \
    "${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}" \
    --format='value(package)' \
    --include-tags 2>/dev/null | sort -u)

if [ -n "$packages" ]; then
    for package in $packages; do
        cleanup_package "$package"
    done
else
    echo "Aucun package trouvé"
fi

echo "=========================================="
echo "✅ Nettoyage Artifact Registry terminé"
echo "=========================================="
echo ""

# Nettoyer Container Registry
echo "🔍 Nettoyage Container Registry (gcr.io)..."
echo ""

for image_name in \
    "highlights-orchestrator" \
    "highlights-processor" \
    "whisper-automation" \
    "whisper-transcription"
do
    image="gcr.io/$PROJECT_ID/$image_name"
    if gcloud container images describe "$image:latest" &>/dev/null 2>&1; then
        cleanup_gcr_image "$image"
    else
        echo "📦 $image_name - n'existe pas ou vide"
    fi
done

echo "=========================================="
echo "✅ Nettoyage Container Registry terminé"
echo "=========================================="
echo ""
echo "💰 Économies estimées: ~$35-40/mois si beaucoup d'images supprimées"
echo ""
