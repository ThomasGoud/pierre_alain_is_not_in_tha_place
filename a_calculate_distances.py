"""
Script pour calculer les distances routières entre plusieurs points en utilisant OSRM.
Le script traite les données en parallèle en utilisant ThreadPoolExecutor.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from tqdm import tqdm
import pandas as pd

def osrm_route(src_coord, dst_coord, profile='car'):
    """
    Appelle l'API OSRM en mode "route" pour obtenir la distance et la durée entre une paire de points.

    Args:
        src_coord (tuple): Coordonnées source sous forme (lon, lat).
        dst_coord (tuple): Coordonnées destination sous forme (lon, lat).
        profile (str): Le profil de véhicule à utiliser pour les calculs (par défaut : 'car').

    Returns:
        tuple: Retourne la distance (en mètres) et la durée (en secondes) entre src_coord et dst_coord.
    """
    url = f'http://localhost:5000/route/v1/{profile}/{src_coord[0]},{src_coord[1]};{dst_coord[0]},{dst_coord[1]}?overview=false&steps=false'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'routes' in data:
                route = data['routes'][0]
                return route['distance'], route['duration']
        else:
            print(f"Erreur de réponse : {response.text}")
        return None, None
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OSRM : {e}")
        return None, None

def process_pair(src_coord, dst_coord, index):
    """
    Traite une paire source-destination en appelant l'API OSRM pour obtenir la distance et la durée.

    Args:
        src_coord (tuple): Coordonnées source (lon, lat).
        dst_coord (tuple): Coordonnées destination (lon, lat).
        index (int): Index de la paire dans le DataFrame.

    Returns:
        dict: Un dictionnaire contenant l'index, la distance et la durée calculées pour la paire source-destination.
    """
    dist, dur = osrm_route(src_coord, dst_coord)

    # Si une réponse a été obtenue, stocker les résultats
    result = {
        'index': index,
        'osrm_distance_km': dist / 1000 if dist else None,  # Convertir en km
        'osrm_duration_min': dur / 60 if dur else None      # Convertir en minutes
    }
    return result

def process_in_parallel(route, max_workers=30):
    """
    Traite les requêtes en parallèle en utilisant ThreadPoolExecutor.

    Args:
        route (pandas dataframe): DataFrame des routes avec coordonnées source et destination.
        max_workers (int): Nombre maximum de threads pour le traitement parallèle.

    Returns:
        list: Une liste contenant tous les résultats des requêtes.
    """
    futures = []
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for index, row in tqdm(route.iterrows(), total=route.shape[0], desc="Processing pairs in parallel"):
            src_coord = (row['X1'], row['Y1'])
            dst_coord = (row['X2'], row['Y2'])
            futures.append(executor.submit(process_pair, src_coord, dst_coord, index))

        # Récupérer les résultats au fur et à mesure de la complétion des futures
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing futures"):
            results.append(future.result())

    return results

def main():
    """
    Main function
    """
    # Lecture du fichier CSV
    route = pd.read_csv('routes_totales.csv')

    # Filtrer les routes avec une distance inférieure à 10 km
    route = route[route['distance_km'] < 10]

    # Trier les routes par distance croissante
    route = route.sort_values('distance_km').reset_index(drop=True)

    # Ajouter des colonnes pour stocker les résultats OSRM
    route['osrm_distance_km'] = None
    route['osrm_duration_min'] = None

    # Traiter les requêtes par lots en parallèle
    results = process_in_parallel(route, max_workers=30)

    # Mise à jour du DataFrame avec les résultats
    for result in results:
        route.at[result['index'], 'osrm_distance_km'] = result['osrm_distance_km']
        route.at[result['index'], 'osrm_duration_min'] = result['osrm_duration_min']

    # Vérifier le nombre d'échecs
    num_failures = route['osrm_distance_km'].isna().sum()
    print(f"Nombre d'échecs : {num_failures}")

    # Sauvegarder les résultats si nécessaire
    route.to_csv('routes_avec_osrm.csv', index=False)
    print("Finished")

if __name__ == '__main__':
    main()
