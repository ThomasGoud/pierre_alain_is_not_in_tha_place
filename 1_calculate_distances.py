import pandas as pd
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Lire le fichier CSV
route = pd.read_csv('routes_totales.csv')

# Filtrer les routes avec une distance inférieure à 10 km
route = route[route['distance_km'] < 10]

# Trier les routes par distance croissante
route = route.sort_values('distance_km').reset_index(drop=True)

# Ajouter des colonnes pour stocker les résultats OSRM
route['osrm_distance_km'] = None
route['osrm_duration_min'] = None

# Fonction pour appeler l'API OSRM en mode "table" pour plusieurs paires
def osrm_table(src_coords, dst_coords, profile='car'):
    src_str = ";".join([f"{lon},{lat}" for lon, lat in src_coords])
    dst_str = ";".join([f"{lon},{lat}" for lon, lat in dst_coords])

    url = f'http://localhost:5000/table/v1/{profile}/{src_str};{dst_str}?annotations=distance,duration'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if 'durations' in data and 'distances' in data:
                return data['distances'], data['durations']
        else:
            print(f"Erreur de réponse : {response.text}")
        return None, None
    except Exception as e:
        print(f"Erreur lors de l'appel à l'API OSRM : {e}")
        return None, None

# Fonction pour traiter chaque batch de données en une seule requête
def process_batch(batch):
    src_coords = list(zip(batch['X1'], batch['Y1']))
    dst_coords = list(zip(batch['X2'], batch['Y2']))

    # Appeler l'API OSRM en mode "table"
    distances, durations = osrm_table(src_coords, dst_coords)

    # Si une réponse a été obtenue, mettre à jour les résultats dans le DataFrame
    results = []
    if distances and durations:
        # Assurez-vous que chaque src[i] correspond à dst[i]
        for j in range(len(batch)):
            try:
                # Ici on traite chaque paire source-destination correspondante
                dist = distances[j][0]  # Seule la distance src[i] -> dst[i] nous intéresse
                dur = durations[j][0]   # Pareil pour la durée src[i] -> dst[i]

                results.append({
                    'index': batch.index[j],
                    'osrm_distance_km': dist / 1000,  # Convertir en km
                    'osrm_duration_min': dur / 60     # Convertir en minutes
                })
            except Exception as e:
                print(f"Erreur lors du traitement du résultat pour l'index {batch.index[j]}: {e}")
    else:
        print(f"Pas de réponse valide pour le batch avec l'index {batch.index.tolist()}")

    return results


# Fonction principale pour gérer le traitement en parallèle ou en série
def process_in_parallel(batch_size=100, max_workers=30):
    futures = []
    results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in tqdm(range(0, len(route), batch_size), desc="Processing batches in parallel"):
            batch = route.iloc[i:i + batch_size]
            futures.append(executor.submit(process_batch, batch))

        # Récupérer les résultats au fur et à mesure de la complétion des futures
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing futures"):
            results.extend(future.result())

    return results

# Traiter les requêtes par lots en parallèle
results = process_in_parallel(batch_size=50, max_workers=10)

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
