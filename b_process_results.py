"""
Script pour traiter les résultats OSRM et calculer les besoins et l'offre
des produits entre producteurs et consommateurs, en manipulant des données
géospatiales avec GeoPandas.
"""

import pandas as pd
import geopandas as gpd
from shapely.geometry import LineString


def load_data():
    """
    Charge les fichiers shapefile et CSV nécessaires pour les calculs.

    Returns:
        tuple: DataFrames contenant les données des points de départ ('from_file'),
        de destination ('to_file'), et les routes ('routes').
    """
    from_file = gpd.read_file('oc.shp')
    to_file = gpd.read_file('fi.shp')
    routes = pd.read_csv('routes_avec_osrm.csv')

    # Convertir les fichiers shapefile en projections correctes (WGS84)
    from_file = from_file.to_crs(epsg=4326)
    to_file = to_file.to_crs(epsg=4326)

    return from_file, to_file, routes


def add_coordinates(from_file, to_file, routes):
    """
    Ajoute les coordonnées des points source et destination au DataFrame des routes.

    Args:
        from_file (GeoDataFrame): GeoDataFrame contenant les points de départ.
        to_file (GeoDataFrame): GeoDataFrame contenant les points d'arrivée.
        routes (DataFrame): DataFrame des routes.

    Returns:
        GeoDataFrame: GeoDataFrame des routes avec les géométries créées.
    """
    # Supprimer la géométrie pour travailler uniquement avec les colonnes
    from_data = from_file.drop(columns='geometry')
    to_data = to_file.drop(columns='geometry')

    # Ajouter les coordonnées des points "from" et "to"
    from_data['X1'] = from_file.geometry.x
    from_data['Y1'] = from_file.geometry.y
    to_data['X2'] = to_file.geometry.x
    to_data['Y2'] = to_file.geometry.y

    # Fusionner les données "from" et "to" avec les routes
    routes = routes.merge(from_data[['id', 'X1', 'Y1']], left_on='id_from', right_on='id', how='left')
    routes = routes.merge(to_data[['id', 'X2', 'Y2']], left_on='id_to', right_on='id', how='left')

    # Créer la géométrie des routes sous forme de lignes
    geometry = [LineString([(x1, y1), (x2, y2)]) for x1, y1, x2, y2 in zip(routes['X1'], routes['Y1'], routes['X2'], routes['Y2'])]
    gdf_routes = gpd.GeoDataFrame(routes, geometry=geometry, crs="EPSG:4326")

    # Reprojeter en Lambert 93 (EPSG:2154) pour des calculs précis sur les distances
    gdf_routes = gdf_routes.to_crs(epsg=2154)

    return gdf_routes, from_data, to_data


def calculer_besoins_et_offre(from_data, to_data, routes):
    """
    Calcule les besoins en fonction de l'offre et la demande pour chaque produit.
    Met à jour l'offre des producteurs et la demande des consommateurs.

    Args:
        from_data (DataFrame): DataFrame contenant les données des producteurs.
        to_data (DataFrame): DataFrame contenant les données des consommateurs.
        routes (GeoDataFrame): GeoDataFrame contenant les données des trajets.

    Returns:
        tuple: DataFrames mis à jour pour 'from_data', 'to_data' et 'routes'.
    """
    for i in range(len(routes)):
        # Récupérer les indices des producteurs et consommateurs pour chaque ligne
        id_from = routes.loc[i, 'id_from']
        id_to = routes.loc[i, 'id_to']

        # Extraire l'offre et la demande
        offre_leg = from_data.loc[from_data['id'] == id_from, 'PL_Tan'].values[0]
        demande_leg = to_data.loc[to_data['id'] == id_to, 'CL_Tan'].values[0]

        offre_fru = from_data.loc[from_data['id'] == id_from, 'PF_Tan'].values[0]
        demande_fru = to_data.loc[to_data['id'] == id_to, 'CF_Tan'].values[0]

        # Calculer les différences entre offre et demande pour chaque produit
        diff_leg = offre_leg - demande_leg
        diff_fru = offre_fru - demande_fru

        # Mettre à jour l'offre et la demande après distribution
        if diff_leg > 0:
            from_data.loc[from_data['id'] == id_from, 'PL_Tan'] = diff_leg
            to_data.loc[to_data['id'] == id_to, 'CL_Tan'] = 0
        else:
            from_data.loc[from_data['id'] == id_from, 'PL_Tan'] = 0
            to_data.loc[to_data['id'] == id_to, 'CL_Tan'] = abs(diff_leg)

        if diff_fru > 0:
            from_data.loc[from_data['id'] == id_from, 'PF_Tan'] = diff_fru
            to_data.loc[to_data['id'] == id_to, 'CF_Tan'] = 0
        else:
            from_data.loc[from_data['id'] == id_from, 'PF_Tan'] = 0
            to_data.loc[to_data['id'] == id_to, 'CF_Tan'] = abs(diff_fru)

        # Complétion du besoin pour le consommateur
        to_data.loc[to_data['id'] == id_to, 'cptL'] = (1 - (to_data.loc[to_data['id'] == id_to, 'CL_Tan'].values[0] / demande_leg)) * 100
        to_data.loc[to_data['id'] == id_to, 'cptF'] = (1 - (to_data.loc[to_data['id'] == id_to, 'CF_Tan'].values[0] / demande_fru)) * 100

        # Mise à jour des kilomètres parcourus
        routes.loc[i, 'km_parcourus'] = routes.loc[i, 'osrm_distance_km']

    return from_data, to_data, routes


def main():
    """
    Fonction principale pour exécuter le script. Charge les données, calcule les besoins et
    enregistre les résultats.
    """
    # Charger les fichiers et initialiser les données
    from_file, to_file, routes = load_data()

    # Ajouter les coordonnées et créer la géométrie des routes
    gdf_routes, from_data, to_data = add_coordinates(from_file, to_file, routes)

    # Calculer les besoins et mettre à jour les routes
    from_data, to_data, gdf_routes = calculer_besoins_et_offre(from_data, to_data, gdf_routes)

    # Sauvegarder les résultats dans des fichiers CSV et Shapefile
    from_data.to_csv('from_restants_mis_a_jour.csv', index=False)
    to_data.to_csv('to_restants_mis_a_jour.csv', index=False)
    gdf_routes.to_file('routes_avec_osrm.shp')

    # Sauvegarder un fichier CSV des routes mises à jour
    gdf_routes.drop(columns='geometry').to_csv('routes_avec_km_parcourus.csv', index=False)

    # Afficher un résumé des kilomètres parcourus
    print(f"Total des kilomètres parcourus : {gdf_routes['km_parcourus'].sum()} km")


if __name__ == "__main__":
    main()
