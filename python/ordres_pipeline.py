"""Frontière entre ordre.txt (jetons) et le catalogue de commandement V2.

Ne fusionne JAMAIS les ordres de généraux
différents et ignore les ordres désactivés. Le vieux 1-2 reste exécuté
par le moteur historique jusqu'à sa migration explicite.
"""
import catalogues
import commandement
import progression
import ordres_calculs_v2
from contextlib import contextmanager
from contextvars import ContextVar
from fractions import Fraction

_duel = ContextVar('ordres_duel', default=None)

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
        if fiche.get('acquisition_requise') and identifiant not in general.get(
                'caracteristiques', {}).get('evolutions_acquises', ()):
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
    # Authentifier avant le filtrage des connaissances, sans croire les champs
    # 'caracteristiques' éventuellement présents dans l'objet appelant.
    officiels = {}
    for camp, positions in forces.items():
        officiels[camp] = {}
        for position, general in positions.items():
            if not general or not general.get('total_unites', 0):
                continue
            fiche = progression.caracteristiques_general(general)
            if fiche is None:
                if general.get('ordres'):
                    raise ValueError("Progression privée absente pour un donneur d'ordres.")
                continue
            officiels[camp][position] = {**general, 'caracteristiques': fiche}
    groupes = ordres_par_donneur(officiels, categorie, catalogue)
    donneurs = []
    for groupe in groupes:
        general = groupe["general"]
        fiche = general['caracteristiques']
        if not isinstance(fiche, dict) or not isinstance(fiche.get("nature"), str):
            raise ValueError("Progression privée absente pour un donneur d'ordres.")
        donneurs.append({
            "camp": groupe["camp"],
            "position": groupe["position"],
            "general": {**general, "caracteristiques": fiche},
            "identifiants": list(groupe["identifiants"]),
        })
    return donneurs


def points_duel_officiels(general):
    """Calcule les PC d'un général depuis les données moteur authentiques.

    Ne sélectionne ni QG ni ordre ; applique simplement le calcul V2 existant
    de commandement.effectif_general aux unités réellement présentes.
    """
    fiche = progression.caracteristiques_general(general)
    if not isinstance(fiche, dict) or type(fiche.get("points_commandement")) is not int:
        raise ValueError("PC officiels introuvables pour le duel.")
    if fiche["points_commandement"] < 0:
        raise ValueError("PC officiels négatifs.")
    import generaux
    composition = generaux.lire_composition_general(general["chemin"])
    return commandement.effectif_general(fiche, composition)


def confronter_duel_officiel(general_1, general_2, donneur_1, donneur_2,
                            catalogue=None):
    """Confrontation duel sans effet entre deux généraux *déjà choisis*.

    Un ordre de duel est confronté avec les PC de son DONNEUR : si le QG
    transmet l'ordre à la place du général engagé, ce sont les PC du général
    possédant le QG qui comptent, en appliquant effectif_general.
    Le calcul global d'armée (global_armee) est distinct, réservé aux ordres
    globaux. Les deux engagés restent des arguments explicites pour contrôler
    plus tard la provenance, les cibles et la validité des donneurs.
    Aucun choix automatique de QG ni effet de combat.
    """
    if donneur_1 is None and donneur_2 is None:
        points_1 = points_2 = 0
    else:
        points_1 = points_duel_officiels(
            donneur_1["general"]) if donneur_1 is not None else 0
        points_2 = points_duel_officiels(
            donneur_2["general"]) if donneur_2 is not None else 0
    return confronter_intentions(donneur_1, donneur_2, "duel",
                                points_1, points_2, catalogue)


def identite(general):
    return general['joueur'], general['nom']


def intention_personnelle(general, categorie):
    """Relit les demandes et l'autorité privée au début du véritable duel.

    Un ancien général sans profil ne gagne aucun droit nouveau. Les généraux
    zombies ne peuvent donner les ordres classiques. 1-2 reste hors de ce circuit.
    """
    import generaux
    fiche = progression.caracteristiques_general(general)
    if not fiche or fiche.get('etat_zombie') or not general['chemin'].is_dir():
        return None
    officiel = {**general, 'caracteristiques': fiche,
                'ordres': generaux.lire_ordres_general(general['chemin'])}
    demandes = ordres_du_general(officiel, categorie)
    demandes = [i for i in demandes if i != 1002 and i in fiche['evolutions_acquises']]
    if not demandes:
        return None
    jetons = {catalogues.ORDRES[i]['jeton'] for i in demandes}
    officiel['ordres'] = [o for o in officiel['ordres'] if o['identifiant'] in jetons]
    return {'general': officiel, 'identifiants': demandes}


@contextmanager
def duel(general_1, general_2):
    """Décisions temporaires, réinitialisées même si le calcul est interrompu.

    Aucun droit ni bonus n'est écrit dans les fiches des soldats ou généraux.
    Les ordres globaux attendent la matérialisation officielle du QG.
    """
    generaux = (general_1, general_2)
    contexte = {identite(g): dict(effets=set(), facteur_cruelle=Fraction(1)) for g in generaux}
    decisions = []
    for categorie in ('duel', 'individuelle'):
        donneurs = [intention_personnelle(g, categorie) for g in generaux]
        if not any(donneurs):
            continue
        points = [points_duel_officiels(d['general']) if d else 0 for d in donneurs]
        resultat = confronter_intentions(*donneurs, categorie, *points)
        for numero, (general, donneur) in enumerate(zip(generaux, donneurs), 1):
            if not donneur:
                continue
            retenus = resultat[f'camp_{numero}']
            contexte[identite(general)]['effets'].update(catalogues.ORDRES[i]['nom'] for i in retenus)
            decisions.append(dict(joueur=general['joueur'], general=general['nom'],
                categorie=categorie, pc=points[numero - 1], demandes=donneur['identifiants'],
                retenus=retenus))
    # Cruelle dépend de l'armée du donneur au début du duel, pas de ses pertes
    # futures. Les deux malus sont préparés avant toute mutation de soldats.
    import generaux as moteur_generaux
    import unites
    for donneur, cible in ((general_1, general_2), (general_2, general_1)):
        if 'cruelle' in contexte[identite(donneur)]['effets']:
            composition = moteur_generaux.lire_composition_general(donneur['chemin'])
            nombre = sum(n for bloc in composition.values() for t, n in bloc.items()
                         if unites.etiquette(t, 'cruelle'))
            contexte[identite(cible)]['facteur_cruelle'] = ordres_calculs_v2.facteur_cruelle(nombre)
    jeton = _duel.set(contexte)
    try:
        yield decisions
    finally:
        _duel.reset(jeton)


def effet(general, nom):
    contexte = _duel.get()
    return bool(general is not None and contexte and
                nom in contexte.get(identite(general), {}).get('effets', ()))


def moral(general, valeur):
    """Les fractions vont jusqu'au plancher collectif des sauvetages existants."""
    if effet(general, 'discours_de_la_mort'):
        valeur = ordres_calculs_v2.facteur_discours_de_la_mort(valeur)
    contexte = _duel.get()
    if contexte and general is not None:
        valeur *= contexte.get(identite(general), {}).get('facteur_cruelle', 1)
    return max(0, min(100, valeur))


def rafales(general_1, general_2, aleatoire, resoudre_pertes):
    """Tirs préalables au choc, même en présence d'un Bouclier vivant.

    Les deux plans sont arrêtés avant les pertes ; aucun avantage de parcours
    j1/j2. Sauvetages collectifs par bloc, avec les blessures et UUID habituels.
    """
    import config
    import generaux
    import soldats
    import unites
    plans = []
    for tireur, cible in ((general_1, general_2), (general_2, general_1)):
        if not effet(tireur, 'rafale'):
            continue
        arriere = generaux.lire_blocs_general(tireur['chemin'])['arriere']
        tirs = ordres_calculs_v2.tentatives_rafale(
            arriere['nombre'] if arriere['type'] == 'archer' else 0)
        if not tirs:
            continue
        blocs = generaux.lire_blocs_general(cible['chemin'])
        candidats = [u for b in config.ordre_blocs
                     for u in (*blocs[b]['unites'], *blocs[b].get('boucliers', ()),
                               *blocs[b].get('soutiens', ()))
                     if not unites.etiquette(generaux.identifier_unite(u), 'lourde')]
        victimes = aleatoire.sample(candidats, min(tirs, len(candidats)))
        plans.append((tireur, cible, tirs, blocs, victimes))
    details = []
    for tireur, cible, tirs, blocs, victimes in plans:
        pertes = 0
        if victimes:
            soldats.affrontement(tireur, cible)
        for bloc in config.ordre_blocs:
            visees = [u for u in victimes if u.parent.name == bloc]
            types = dict.fromkeys(generaux.identifier_unite(u) for u in visees)
            for type_unite in types:
                groupe = [u for u in visees if generaux.identifier_unite(u) == type_unite]
                infos = dict(type=type_unite, nombre=len(groupe), unites=groupe)
                pertes += len(resoudre_pertes(infos, 0, cible))
        details.append(dict(joueur=tireur['joueur'], general=tireur['nom'],
                            tirs=tirs, touches=len(victimes), pertes=pertes))
    for general in (general_1, general_2):
        if plans:
            generaux.supprimer_general_si_vide(general)
    return details
