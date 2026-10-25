"""Frontière entre ordre.txt (jetons) et le catalogue de commandement V2.

Sans effet sur les combats. Ne fusionne JAMAIS les ordres de généraux
différents et ignore les ordres désactivés. Le vieux 1-2 reste exécuté
par le moteur historique jusqu'à sa migration explicite.
"""
import catalogues
import commandement
import progression

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


def confronter_intentions(donneur_1, donneur_2, categorie, points_1, points_2,
                         catalogue=None):
    """Compare deux donneurs explicitement identifiés, sans effet de combat.

    donneur_N : dict avec un champ « general » (dictionnaire moteur)
    ou None si ce camp n'a aucun donneur pour CETTE confrontation.
    Les PC sont calculés et transmis par l'appelant : aucune règle de
    calcul globale/duel n'est supposée ici.
    Cette API n'est PAS un mécanisme de sélection automatique du QG.
    """
    if categorie not in _CATEGORIES:
        raise ValueError("Catégorie inconnue.")
    if any(type(p) is not int or p < 0 for p in (points_1, points_2)):
        raise ValueError("Les points de commandement doivent être des entiers positifs ou nuls.")
    catalogue = catalogues.ORDRES if catalogue is None else catalogue

    def intentions(donneur):
        if donneur is None:
            return (), "", ()
        general = donneur["general"]
        fiche = general.get("caracteristiques")
        if not isinstance(fiche, dict) or not isinstance(fiche.get("nature"), str):
            raise ValueError("Caractéristiques officielles du général requises.")
        return (ordres_du_general(general, categorie, catalogue),
                fiche["nature"], fiche.get("evolutions_acquises", ()))

    ids_1, nature_1, acquis_1 = intentions(donneur_1)
    ids_2, nature_2, acquis_2 = intentions(donneur_2)
    comparaison = commandement.comparer(points_1, points_2)
    retenus_1, retenus_2 = commandement.confronter_donneurs(
        ids_1, nature_1, acquis_1, ids_2, nature_2, acquis_2,
        categorie, comparaison, catalogue)
    return {"comparaison": comparaison, "camp_1": retenus_1, "camp_2": retenus_2}


def donneurs_officiels(forces, categorie=None, catalogue=None):
    """Prépare les donneurs depuis la progression PRIVÉE, sans effets.

    Renvoie une entrée par général et par catégorie demandée. Aucun champ
    fiche.txt du joueur ne sert d'autorité ; l'absence de fiche privée est
    une erreur, jamais une permission implicite. Sans ordre disponible,
    le général n'est pas retenu comme donneur.
    """
    groupes = ordres_par_donneur(forces, categorie, catalogue)
    donneurs = []
    for groupe in groupes:
        general = groupe["general"]
        fiche = progression.caracteristiques_general(general)
        if not isinstance(fiche, dict) or not isinstance(fiche.get("nature"), str):
            raise ValueError("Progression privée absente pour un donneur d'ordres.")
        donneurs.append({
            "camp": groupe["camp"],
            "position": groupe["position"],
            "general": {**general, "caracteristiques": fiche},
            "identifiants": list(groupe["identifiants"]),
        })
    return donneurs
