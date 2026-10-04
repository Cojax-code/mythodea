"""Compositions des vagues Est, sans lecture ni écriture du plateau."""
import random

import config


TERRITOIRES_EST = ("est_1", "est_2", "est_3")
TYPES_UNITES = ("archer", "piquier", "cavalier")


def composition_general(effectif, aleatoire, type_unique=None, tout_avant=False):
    """Répartit l'effectif puis choisit un seul type par bloc non vide."""
    nombres = dict.fromkeys(config.ordre_blocs, 0)
    for _ in range(effectif):
        bloc = "avant" if tout_avant else aleatoire.choice(config.ordre_blocs)
        nombres[bloc] += 1
    return {
        bloc: {"nombre": nombre,
               "type": (type_unique or aleatoire.choice(TYPES_UNITES)) if nombre else None}
        for bloc, nombre in nombres.items()
    }


def composer_vague_est(numero, aleatoire=None):
    """Retourne une liste de généraux : territoire, vague, affichage et blocs.

    Les tirages de chaque général sont indépendants, même pour un Boss répété.
    Le numéro dans la vague est unique sur l'ensemble des territoires.
    """
    if type(numero) is not int or numero < 1:
        raise ValueError("Le numéro de vague doit être un entier positif.")
    if aleatoire is None:
        aleatoire = random

    territoires = ("est_3",)
    if numero == 1:
        territoires = TERRITOIRES_EST
        pattern = [(5, None, False)]
    elif numero in (2, 3):
        pattern = [(numero * 5, None, False)]
    elif numero == 4:
        pattern = [(10, None, False)] * 2
    elif numero == 5:
        territoires = TERRITOIRES_EST
        pattern = [(20, None, False), (20, "cavalier", True)]
    elif numero >= 26:
        territoires = TERRITOIRES_EST
        pattern = [(20, None, False)] * 4
    else:
        base = (numero - 1) // 5
        pattern = [(20, None, False)] * base
        reste = numero % 5
        if reste == 0:
            territoires = TERRITOIRES_EST
            pattern.append((20, None, False))
        else:
            type_special = {1: "archer", 2: "piquier"}.get(reste, "mono")
            pattern.append((20, type_special, False))
            if reste == 4:
                territoires = ("est_2", "est_3")

    vague = []
    for territoire in territoires:
        for effectif, type_unique, tout_avant in pattern:
            if type_unique == "mono":
                type_unique = aleatoire.choice(TYPES_UNITES)
            vague.append({
                "territoire": territoire,
                "vague": numero,
                "nom_affichage": f"general{numero}_{len(vague) + 1}",
                "blocs": composition_general(effectif, aleatoire, type_unique, tout_avant),
            })
    return vague
