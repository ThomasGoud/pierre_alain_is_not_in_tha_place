#!/bin/bash

# Vérifier si un fichier .pbf a été fourni en entrée
if [ -z "$1" ]; then
    echo "Usage: $0 /chemin/vers/le/fichier.osm.pbf"
    exit 1
fi

# Chemin absolu vers le fichier .pbf
PBF_FILE=$(realpath "$1")

# Extraire le nom de fichier sans le chemin ni l'extension
BASENAME=$(basename "$PBF_FILE" .osm.pbf)

# Nom des fichiers OSRM extraits
OSRM_FILE="data/$BASENAME.osrm"

# Créer le répertoire 'data' s'il n'existe pas
mkdir -p data/

# Partie 1: Extraction et préparation des fichiers OSM
echo "Checking if $OSRM_FILE exists"
if [ ! -f "$OSRM_FILE" ]; then
    echo "Extraction des fichiers OSM pour $BASENAME"

    # Télécharger l'image Docker OSRM
    docker pull osrm/osrm-backend

    # Extraction des données depuis le fichier PBF
    echo "Extrait le fichier OSM vers /data/$BASENAME..."
    docker run -t -v $(pwd)/data:/data -v "$PBF_FILE":/data/$BASENAME.osm.pbf osrm/osrm-backend osrm-extract -p /opt/car.lua /data/$BASENAME.osm.pbf

    # Création des données de contraction hierarchy (CH)
    echo "Création de la contraction hierarchy (CH)..."
    docker run -t -v $(pwd)/data:/data osrm/osrm-backend osrm-partition "/data/$BASENAME.osrm"
    docker run -t -v $(pwd)/data:/data osrm/osrm-backend osrm-customize "/data/$BASENAME.osrm"
else
    echo "Les fichiers OSRM pour $BASENAME existent déjà, pas besoin d'extraction."
fi

# Partie 2: Démarrer le serveur OSRM
echo "Démarrage du serveur OSRM pour $BASENAME..."
docker run -t -i -p 5000:5000 -v $(pwd)/data:/data osrm/osrm-backend osrm-routed --algorithm mld "/data/$BASENAME.osrm"
