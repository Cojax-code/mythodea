"""Frontière entre ordre.txt (jetons) et le catalogue de commandement V2.

Sans effet sur les combats. Ne fusionne JAMAIS les ordres de généraux
différents et ignore les ordres désactivés. Le vieux 1-2 reste exécuté
par le moteur historique jusqu'à sa migration explicite.
"""
import catalogues

_CATEGORIES = {"globale", "duel", "individuelle"}


def index_jetons(catalogue=None):
    catalogue = catalogues.ORDRES if catalogue is None else catalogue
    index = {}
    for identifiant, fiche in catalogue.items():
        jeton = fiche["jeton"]
        if jeton in index:
            raise ValueError("Jeton d'ordre ambigu dans le catalogue.")
        index[jeton] = identifiant
    return index


def ordres_du_general(general, categorie=None, catalogue=None):
    """Retourne les IDs disponibles, ordonnés, pour CE général uniquement.

    La variante avec ciblage doit être traitée par un validateur distinct
    avant d'activer l'effet. La conversion d'un jeton à un ID ne signifie
    pas que son effet est exécuté dans un combat.
    """
    catalogue = catalogues.ORDRES if catalogue is None else catalogue
    if categorie is not None and categorie not in _CATEGORIES:
        raise ValueError("Catégorie inconnue.")
    index = index_jetons(catalogue)
    resultat = []
    for demande in general.get("ordres", ()):
        if not isinstance(demande, dict):
            continue
        jeton = demande.get("identifiant")
        identifiant = index.get(jeton)
        if identifiant is None:
            continue
        fiche = catalogue[identifiant]
        if not fiche["disponible"] or (
                categorie is not None and fiche["categorie"] != categorie):
            continue
        # Pas d'invention d'une cible par défaut : une spécification future
        # devra être validée selon la définition de l'ordre concerné.
        if demande.get("specification") is not None:
            continue
        if identifiant not in resultat:
            resultat.append(identifiant)
    return resultat


def ordres_par_donneur(forces, categorie=None, catalogue=None):
    """Retourne une liste par général actif, sans agrégation des donneurs.

    L'entrée est celle de lire_forces_territoire : camp -> position -> général.
    Les positions et propriétaires ne sont jamais fusionnés ici.
    """
    groupes = []
    for camp, positions in forces.items():
        for position, general in positions.items():
            if not general or not general.get("total_unites", 0):
                continue
            demandes = ordres_du_general(general, categorie, catalogue)
            if demandes:
                groupes.append(dict(camp=camp, position=position,
                                    general=general, identifiants=demandes))
    return groupes
