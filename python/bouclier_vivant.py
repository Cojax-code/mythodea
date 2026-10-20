"""Calculs purs pour le Bouclier vivant V2.

Aucun changement de disque ici : le résolveur territorial effectuera ensuite
les conversions, les combats et les écritures officielles.
"""
from fractions import Fraction
import random

RESISTANCE_INITIALE = Fraction(250)
TYPE_BOUCLIER = "Trop_gros_zombie"


def resistance_apres_choc(resistance, puissance_adverse):
    """Compare avant usure. L'égalité détruit le bouclier.

    Renvoie (survit, résistance restante), sans arrondi.
    """
    r, p = Fraction(resistance), Fraction(puissance_adverse)
    if r <= 0 or p < 0:
        raise ValueError("Résistance positive et puissance adverse non négative requises.")
    if p >= r:
        return False, Fraction(0)
    return True, r - p / 4


def choisir_spore(soldats_adverses, rng=None):
    """Un soldat ayant le moins de batailles ; tirage en cas d'égalité.

    Les victimes possibles sont les soldats réellement présents dans le bloc.
    La mutation et la persistance relèvent du résolveur officiel.
    """
    if not soldats_adverses:
        return None
    minimum = min(s["batailles"] for s in soldats_adverses)
    candidats = [s for s in soldats_adverses if s["batailles"] == minimum]
    return (rng or random).choice(candidats)


def bloc_destination_spore(effectifs_par_bloc, blocs_eligibles, rng=None):
    """Destination parmi les blocs compatibles, le plus rempli d'abord."""
    possibles = [b for b in blocs_eligibles if b in effectifs_par_bloc]
    if not possibles:
        return None
    maxi = max(effectifs_par_bloc[b] for b in possibles)
    return (rng or random).choice([b for b in possibles if effectifs_par_bloc[b] == maxi])


def choisir_bloc_favorable(blocs_adverses, potentiel, rng=None):
    """Sélectionne uniquement une cible gagnable ; None sinon.

    potentiel(bloc) retourne True si la confrontation ordinaire serait gagnante.
    Le moteur principal reste responsable du calcul des rapports de force.
    """
    candidats = [b for b in blocs_adverses if potentiel(b)]
    return (rng or random).choice(candidats) if candidats else None


def seulement_bouclier(composition):
    """Un général sans autre unité combattante perd automatiquement."""
    boucliers = sum(bloc.get(TYPE_BOUCLIER, 0) for bloc in composition.values())
    ordinaires = sum(n for bloc in composition.values()
                    for type_unite, n in bloc.items()
                    if type_unite != TYPE_BOUCLIER and type_unite != "messager_du_QG")
    return boucliers > 0 and ordinaires == 0


def verifier_un_seul_bouclier(composition):
    nombre = sum(bloc.get(TYPE_BOUCLIER, 0) for bloc in composition.values())
    if nombre > 1:
        raise ValueError("Un seul Trop gros zombie autorisé par général.")
    return nombre
