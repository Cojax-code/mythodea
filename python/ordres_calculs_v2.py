"""Calculs purs pour des ordres V2 dont la formule a été explicitement validée.

AUCUNE activation en combat : ni décision de cible, ni aléatoire, ni mutation
d'effectifs, ni modification de l'état officiel des généraux.
Seul un futur module d'effets peut appeler ces fonctions après validation de
toutes les préconditions (ordre acquis, donneur, phase, camp, conflit).
"""


def _naturel(nombre, nom):
    if type(nombre) is not int or nombre < 0:
        raise ValueError(f"{nom} doit être un entier positif ou nul.")
    return nombre


def probabilite_charge_suicidaire(pertes_du_duel):
    """Pourcentage ENTIER de mort adverse : 1 % par quatre unités perdues.

    Uniquement les pertes du duel entre ces deux généraux. Ne lance aucun dé
    et ne décide pas qui est mort. Aucune limite de chance supplémentaire
    n'a été validée dans la spécification.
    """
    return _naturel(pertes_du_duel, "Pertes du duel") // 4


def renforts_ralliement(pertes_par_type, types_du_beneficiaire):
    """20 % des pertes éligibles, ARRONDI À L'ENTIER INFÉRIEUR par type.

    Un type absent des blocs du bénéficiaire ne reçoit aucun renfort.
    Renvoie seulement des quantités, sans créer de soldats ni attribuer
    d'identité, de fatigue ou de propriétaire.
    """
    if not isinstance(pertes_par_type, dict):
        raise ValueError("Les pertes doivent être données par type.")
    eligibles = set(types_du_beneficiaire)
    resultat = {}
    for type_unite, pertes in pertes_par_type.items():
        _naturel(pertes, f"Pertes ({type_unite})")
        if type_unite in eligibles:
            resultat[type_unite] = pertes // 5
    return resultat


def malus_cruelle(nombre_unites_cruelles):
    """Nombre de points de moral retirés avant le duel (1 par unité cruelle)."""
    return _naturel(nombre_unites_cruelles, "Unités cruelles")


def bonus_discours_mort(moral):
    """Ajoute dix points de moral, sans dépasser le plafond officiel de 100."""
    _naturel(moral, "Moral")
    if moral > 100:
        raise ValueError("Le moral initial ne peut pas dépasser 100.")
    return min(100, moral + 10)
