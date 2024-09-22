# Projet OSRM Distance Calculator

Ce projet est composé de deux scripts Python et d'un serveur OSRM local pour calculer les distances routières entre plusieurs points géographiques. Il utilise OSRM (Open Source Routing Machine) pour obtenir les distances optimales et analyser les besoins en fonction des trajets calculés.

## Structure des fichiers

- **a_calculate_distances.py** : Ce script calcule les distances routières entre les points source et destination à l'aide de l'API OSRM "table".
- **b_process_results.py** : Ce script traite les résultats des distances obtenues et calcule l'offre et la demande pour chaque paire source-destination.
- **osm_server.sh** : Ce script permet de démarrer un serveur OSRM local en utilisant Docker.

## Prérequis

- Python 3.9 ou supérieur
- Docker installé sur votre machine
- Les bibliothèques Python listées dans `requirements.txt`

## Installation

### Étape 1 : Installer les bibliothèques Python
```bash
pip install -r requirements.txt
```

### Étape 2 : Démarrer le serveur OSRM

1. Exécutez le script **osm_server.sh** avec le fichier `.pbf` comme argument :
   ```bash
   bash osm_server.sh provence-alpes-cote-d-azur-latest.osm.pbf
   ```

### Étape 3 : Exécution des scripts

1. Exécutez le script **a_calculate_distances.py** pour calculer les distances entre les points :
   ```bash
   python a_calculate_dibtances.py
   ```
2. Exécutez ensuite le script **b_process_results.py** pour traiter les résultats des trajets et analyser l'offre et la demande :
   ```bash
   python b_process_results.py
   ```

## Fichiers de données

Les fichiers de données utilisés dans ce projet sont :

- **oc.shp** : Fichier shapefile contenant les points sources (producteurs).
- **fi.shp** : Fichier shapefile contenant les points destinations (consommateurs).
- **routes_avec_osrm.csv** : Résultats des distances calculées par l'OSRM, généré par le script **a_calculate_distances.py**.

## Résultatb

Les fichiers suivants sont générés à la fin du processus :

- **from_restants_mis_a_jour.csv** : Mise à jour des stocks restants pour les points sources après distribution.
- **to_restants_mis_a_jour.csv** : Mise à jour des besoins satisfaits pour les points de destination.
- **routes_avec_km_parcourus.csv** : Trajets avec les distances parcourues mises à jour.
- **routes_avec_osrm.shp** : Shapefile contenant les lignes représentant les trajets calculés.

## Contact

Pour toute question ou problème, veuillez me contacter à **votre.email@example.com**.
