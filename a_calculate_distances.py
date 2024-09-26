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

def osrm_table_batch(src_coords, dst_coords, profile='car'):
    """
    Appelle l'API OSRM en mode "table" pour obtenir la distance et la durée entre plusieurs paires de points en une seule requête.
    
    Args:
        src_coords (list): Liste des coordonnées sources sous forme [(lon, lat), (lon, lat), ...].
        dst_coords (list): Liste des coordonnées destinations sous forme [(lon, lat), (lon, lat), ...].
        profile (str): Le profil de véhicule à utiliser pour les calculs (par défaut : 'car').
    
    Returns:
        list: Liste des tuples (distance, durée) pour chaque paire source-destination.
    """
    src_str = ";".join([f"{coord[0]},{coord[1]}" for coord in src_coords])
    dst_str = ";".join([f"{coord[0]},{coord[1]}" for coord in dst_coords])

    # Ajout du paramètre 'annotations=distance,duration' pour obtenir les distances ET durées
    url = f'http://localhost:5000/table/v1/{profile}/{src_str};{dst_str}?annotations=distance,duration'
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Vérification que 'distances' et 'durations' existent bien dans la réponse
            if 'distances' in data and 'durations' in data:
                distances = data['distances']
                durations = data['durations']
                # Extraction des résultats pour chaque paire source-destination correspondante
                results = [(distances[i][i + len(src_coords)], durations[i][i + len(src_coords)]) for i in range(len(src_coords))]
                return results
        else:
            print(f"Erreur de réponse : {response.text}")
        return None
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OSRM : {e}")
        return None

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

    result = {
        'index': index,
        'distance_km': dist / 1000 if dist else None,  # Convertir en km
        'duration_min': dur / 60 if dur else None      # Convertir en minutes
    }
    return result

def process_batch(src_coords, dst_coords):
    """
    Traite plusieurs paires source-destination en une seule requête OSRM via l'API "table".

    Args:
        src_coords (list): Liste des coordonnées source (lon, lat).
        dst_coords (list): Liste des coordonnées destination (lon, lat).

    Returns:
        list: Liste des dictionnaires contenant l'index, la distance et la durée pour chaque paire source-destination.
    """
    batch_results = osrm_table_batch(src_coords, dst_coords)
    if batch_results:
        results = []
        for index, (dist, dur) in enumerate(batch_results):
            results.append({
                'index': index,
                'distance_km': dist / 1000 if dist else None,
                'duration_min': dur / 60 if dur else None
            })
        return results
    else:
        return []

def process_in_parallel(route, max_workers=30):
    """
    Traite les requêtes en parallèle en utilisant ThreadPoolExecutor pour les appels individuels à osrm_route.

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

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing futures"):
            results.append(future.result())

    return results

def compare_batch_vs_parallel(route):
    """
    Compare le temps et les résultats entre le traitement batch et les appels individuels en parallèle pour 4 paires.

    Args:
        route (pandas dataframe): DataFrame des routes avec coordonnées source et destination.

    Returns:
        dict: Un dictionnaire contenant les résultats des deux méthodes (batch vs appels individuels).
    """
    # Extraire les premières 4 paires
    route_extract = route[:10]
    src_coords = [(row['X1'], row['Y1']) for _, row in route_extract.iterrows()]
    dst_coords = [(row['X2'], row['Y2']) for _, row in route_extract.iterrows()]

    # Appels batch (osrm_table)
    print("Traitement batch...")
    batch_results = process_batch(src_coords, dst_coords)

    # Appels individuels en parallèle (osrm_route)
    print("Traitement parallèle...")
    parallel_results = process_in_parallel(route_extract)
    parallel_results = sorted(parallel_results, key=lambda x: x['index'])
    return {
        "batch_results": batch_results,
        "parallel_results": parallel_results
    }

def main():
    """
    Main function
    """
    # Lecture du fichier CSV
    route = pd.read_csv('routes_totales.csv')

    # Ajouter des colonnes pour stocker les résultats OSRM
    route['distance_km'] = None
    route['duration_min'] = None

    # Traiter les requêtes par lots en parallèle
    compare_batch_vs_parallel(route)
    results = process_in_parallel(route, max_workers=30)

    # Mise à jour du DataFrame avec les résultats
    for result in results:
        route.at[result['index'], 'distance_km'] = result['distance_km']
        route.at[result['index'], 'duration_min'] = result['duration_min']

    # Vérifier le nombre d'échecs
    num_failures = route['distance_km'].isna().sum()
    print(f"Nombre d'échecs : {num_failures}")

    # Sauvegarder les résultats si nécessaire
    route.to_csv('routes_avec_osrm.csv', index=False)
    print("Finished")

if __name__ == '__main__':
    main()
