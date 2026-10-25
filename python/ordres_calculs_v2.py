"""Calculs purs des ordres V2 aux formules non ambiguës.

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


def facteur_discours_de_la_mort(moral):
    """Moral * 1,10, cumul multiplicatif possible avec de futurs facteurs.

    Renvoie une Fraction exacte, SANS arrondir ni plafonner ici : le moment
    de l'arrondi (et l'ordre des plafonds entre bonus) n'a pas été tranché.
    30 PM -> 33 PM. Le moteur final appliquera les règles d'arrondi communes.
    """
    from fractions import Fraction
    _naturel(moral, "Moral")
    if moral > 100:
        raise ValueError("Le moral initial est borné à 100.")
    return Fraction(moral * 11, 10)


def reserve_peut_intercepter(victoire_adverse, unites_reserve, deja_elimine=False):
    """Condition minimale de Réserve stratégique, pas son effet.

    Interceptions répétées permises : aucun compteur de déclenchements, aucune
    pénalité de fatigue ajoutée par cet ordre. Il faut une victoire adverse
    et au moins une unité disponible dans le général de réserve.
    """
    if type(victoire_adverse) is not bool or type(deja_elimine) is not bool:
        raise ValueError("États booléens requis.")
    _naturel(unites_reserve, "Unités de réserve")
    return victoire_adverse and unites_reserve > 0 and not deja_elimine


def derniere_charge_possible(general_precedent_vaincu, flanc):
    """L'activation impose la défaite du précédent et un flanc unique G/D.

    Ne réanime aucune unité ; les règles d'éligibilité physique des soldats
    restent une étape distincte à définir.
    """
    if type(general_precedent_vaincu) is not bool or flanc not in ("G", "D"):
        raise ValueError("Défaite booléenne et flanc G/D requis.")
    return general_precedent_vaincu

def tentatives_rafale(nombre_archers_arriere):
    """Une tentative de perte directe pour quatre archers à l'Arrière.

    Le tirage des cibles, la protection des unités lourdement blindées et
    la résolution des pertes sont laissés au moteur lors du choc initial.
    """
    return _naturel(nombre_archers_arriere, "Archers à l'arrière") // 4


def conversions_spore(base, bonus_spora_adicte=False, confinement=False):
    """Confinement neutralise Spore, même si Spora-adicte l'améliore."""
    _naturel(base, "Conversions de Spore")
    if type(bonus_spora_adicte) is not bool or type(confinement) is not bool:
        raise ValueError("États Spore booléens requis.")
    if confinement:
        return 0
    return base + int(bonus_spora_adicte)


def conversions_propagation(base, propagafion=False):
    """Propagafion ajoute deux transformations au calcul normal.

    Ne détermine pas les cibles ni la faisabilité des transformations :
    les interdictions Zombie contre Zombie restent au niveau moteur.
    """
    _naturel(base, "Conversions de propagation")
    if type(propagafion) is not bool:
        raise ValueError("État Propagafion booléen requis.")
    return base + (2 if propagafion else 0)
