# Téléchargez l'image Docker d'OSRM
docker pull osrm/osrm-backend

# Extrayez et préparez les fichiers OSM pour la Côte d'Azur (remplacez le chemin vers votre fichier .pbf)
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/provence-alpes-cote-d-azur-latest.osm.pbf

# Créez les données de contraction hierarchy (CH)
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/provence-alpes-cote-d-azur-latest.osrm
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/provence-alpes-cote-d-azur-latest.osrm

# Démarrer le backend
docker run -t -i -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/provence-alpes-cote-d-azur-latest.osrm
