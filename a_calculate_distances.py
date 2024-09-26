"""
Script pour calculer les distances routières entre plusieurs points en utilisant OSRM.
Le script traite les données en parallèle en utilisant ThreadPoolExecutor.
"""
from concurrent.futures import ProcessPoolExecutor, as_completed
import requests
from tqdm import tqdm
import pandas as pd

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
            if 'distances' in data and 'durations' in data:
                distances = data['distances']
                durations = data['durations']
                results = [(distances[i][i + len(src_coords)], durations[i][i + len(src_coords)]) for i in range(len(src_coords))]
                return results
        else:
            print(f"Erreur de réponse : {response.text}")
        return None
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OSRM : {e}")
        return None

def process_batch(src_coords, dst_coords, start_index):
    """
    Traite plusieurs paires source-destination en une seule requête OSRM via l'API "table" et retourne les résultats avec leur index d'origine.

    Args:
        src_coords (list): Liste des coordonnées source (lon, lat).
        dst_coords (list): Liste des coordonnées destination (lon, lat).
        start_index (int): Index de départ pour les paires dans le DataFrame.

    Returns:
        list: Liste des dictionnaires contenant l'index, la distance et la durée pour chaque paire source-destination.
    """
    batch_results = osrm_table_batch(src_coords, dst_coords)
    if batch_results:
        results = []
        for index, (dist, dur) in enumerate(batch_results):
            results.append({
                'index': start_index + index,
                'distance_km': dist / 1000 if dist else None,
                'duration_min': dur / 60 if dur else None
            })
        return results
    else:
        assert 0

def process_in_batches(route, batch_size=50, max_workers=30):
    """
    Traite les requêtes par batch en utilisant ThreadPoolExecutor.

    Args:
        route (pandas dataframe): DataFrame des routes avec coordonnées source et destination.
        batch_size (int): Nombre de paires à traiter par batch.
        max_workers (int): Nombre maximum de threads pour le traitement parallèle.

    Returns:
        list: Une liste contenant tous les résultats des requêtes.
    """
    import math
    num_batches = math.ceil(len(route) / batch_size)
    futures = []
    results = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for batch_idx in tqdm(range(num_batches), desc="Processing batches"):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(route))
            batch_data = route.iloc[start_idx:end_idx]

            src_coords = [(row['X1'], row['Y1']) for _, row in batch_data.iterrows()]
            dst_coords = [(row['X2'], row['Y2']) for _, row in batch_data.iterrows()]

            futures.append(executor.submit(process_batch, src_coords, dst_coords, start_idx))

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing futures"):
            batch_result = future.result()
            if batch_result:
                results.extend(batch_result)

    return results

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
    results = process_in_batches(route, batch_size=50, max_workers=30)

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