"""Registre de CONCEPTION des 21 ordres V2.

Ce module n'est pas le catalogue exécutable (catalogues.ORDRES).
Ne donne aucun droit d'apprentissage ou d'exécution et n'est pas lu par le combat.
Les détails sont dans docs/ordres-v2-preparation.md ; ne pas leur inventer
d'effet tant que les décisions ouvertes ne sont pas tranchées.
"""

from types import MappingProxyType

# Nom canonique -> (catégorie, est_contre_ordre).
# AUCUN identifiant numérique ni jeton ordre.txt attribué : Codex/moteur
# le feront lorsque les effets seront prêts.
_DEFINITIONS = {
    "charge_suicidaire": ("individuelle", False),
    "gros_poisson": ("duel", False),
    "choca_fuite": ("duel", False),
    "retrait_tactique": ("globale", True),
    "herisson": ("individuelle", False),
    "discours_de_la_mort": ("individuelle", False),
    "spora_adicte": ("globale", False),
    "propagafion": ("globale", False),
    "confinement": ("globale", True),
    "pour_l_honneur": ("globale", False),
    "ralliement": ("globale", False),
    "rafale": ("individuelle", False),
    "cruelle": ("duel", False),
    "orc_un_jour_orc_toujour": ("duel", False),
    "etincellant": ("globale", False),
    "on_melange": ("globale", False),
    "qg_nommade": ("globale", False),
    "chat_man": ("duel", True),
    "muraille_humaine": ("globale", False),
    "reserve_strategique": ("globale", False),
    "derniere_charge": ("duel", True),
}

ORDRES_EN_CONCEPTION = MappingProxyType({
    nom: MappingProxyType({"categorie": categorie, "contre": contre,
                           "disponible": False})
    for nom, (categorie, contre) in _DEFINITIONS.items()
})


def verifier_registre():
    if len(ORDRES_EN_CONCEPTION) != 21:
        raise ValueError("Le registre doit contenir les 21 ordres prévus.")
    categories = {"globale", "duel", "individuelle"}
    for nom, fiche in ORDRES_EN_CONCEPTION.items():
        if not nom or fiche["categorie"] not in categories:
            raise ValueError("Ordre ou catégorie invalide.")
        if type(fiche["contre"]) is not bool or fiche["disponible"] is not False:
            raise ValueError("Les ordres en conception doivent rester désactivés.")


verifier_registre()
