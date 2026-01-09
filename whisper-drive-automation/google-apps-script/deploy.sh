#!/bin/bash

# Script de déploiement automatique pour le Marqueur Segments Vidéo
# Usage: ./deploy.sh [version] [description]

set -e

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Vérifier que clasp est installé
if ! command -v clasp &> /dev/null; then
    echo -e "${RED}❌ clasp n'est pas installé${NC}"
    echo "Installation: npm install -g @google/clasp"
    exit 1
fi

# Vérifier que nous sommes dans le bon dossier
if [ ! -f "MarqueurSegments.gs" ]; then
    echo -e "${RED}❌ Erreur: Exécutez ce script depuis le dossier google-apps-script${NC}"
    exit 1
fi

# Vérifier que l'utilisateur est connecté
if ! clasp login --status &> /dev/null; then
    echo -e "${YELLOW}⚠️  Vous n'êtes pas connecté à clasp${NC}"
    echo "Connexion en cours..."
    clasp login
fi

echo -e "${GREEN}🚀 Déploiement du Marqueur Segments Vidéo${NC}\n"

# Vérifier si le projet existe
if [ ! -s ".clasp.json" ] || [ "$(cat .clasp.json | grep -o '"scriptId": ""')" ]; then
    echo -e "${YELLOW}📝 Création d'un nouveau projet...${NC}"

    # Créer le projet
    clasp create --type standalone --title "Marqueur Segments Vidéo"

    echo -e "${GREEN}✅ Projet créé avec succès${NC}\n"
else
    echo -e "${GREEN}✅ Projet existant détecté${NC}\n"
fi

# Pousser le code
echo -e "${YELLOW}📤 Upload du code...${NC}"
clasp push

echo -e "${GREEN}✅ Code uploadé${NC}\n"

# Récupérer les arguments
VERSION=${1:-"1.0.0"}
DESCRIPTION=${2:-"Déploiement automatique"}

# Créer une version
echo -e "${YELLOW}📦 Création de la version ${VERSION}...${NC}"
clasp version "${DESCRIPTION}"

# Déployer
echo -e "${YELLOW}🚀 Déploiement en production...${NC}"
DEPLOY_OUTPUT=$(clasp deploy --description "v${VERSION} - ${DESCRIPTION}")

echo -e "${GREEN}✅ Déploiement réussi${NC}\n"

# Afficher les infos du déploiement
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📋 INFORMATIONS DE DÉPLOIEMENT${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}\n"

# Extraire et afficher le Script ID
SCRIPT_ID=$(cat .clasp.json | grep scriptId | cut -d'"' -f4)
echo -e "${YELLOW}Script ID:${NC} ${SCRIPT_ID}"
echo -e "${YELLOW}Version:${NC} ${VERSION}"
echo -e "${YELLOW}Description:${NC} ${DESCRIPTION}\n"

# Afficher le lien
echo -e "${GREEN}🔗 Lien d'édition:${NC}"
echo "https://script.google.com/d/${SCRIPT_ID}/edit"
echo ""

# Instructions pour les utilisateurs
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}📖 INSTRUCTIONS POUR LES UTILISATEURS${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}\n"

cat << EOF
Donnez ces instructions aux utilisateurs :

1. Ouvrez votre Google Doc
2. Extensions → Apps Script
3. Bibliothèques (icône +)
4. Collez le Script ID: ${SCRIPT_ID}
5. Cliquez sur "Rechercher" → "Ajouter"
6. Copiez le code de WrapperTemplate.gs
7. Sauvegardez et rafraîchissez votre document

Le menu 🎬 Extraits Vidéo apparaîtra !
EOF

echo -e "\n${GREEN}═══════════════════════════════════════════════════${NC}\n"

# Demander si l'utilisateur veut ouvrir le projet
read -p "Voulez-vous ouvrir le projet dans l'éditeur web ? (o/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Oo]$ ]]; then
    clasp open
fi

echo -e "\n${GREEN}✅ Déploiement terminé avec succès !${NC}\n"
