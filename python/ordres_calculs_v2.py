"""Calculs purs des ordres V2 aux formules non ambiguës.

Ces fonctions ne sélectionnent ni donneur ni cible : aucun accès disque ni mutation
d'effectifs, ni modification de l'état officiel des généraux.
Le pipeline appelle les calculs intégrés après validation de
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


def tirages_charges_suicidaires(pertes_1, pertes_2, active_1, active_2, aleatoire):
    """Deux tirages indépendants, sans tuer ni déplacer un seul soldat.

    Retourne (attaque_1_reussie, attaque_2_reussie). Les pertes doivent être
    celles du duel qui vient de finir ; aucun cumul ni état persistant ici.
    """
    chances = (probabilite_charge_suicidaire(pertes_1),
               probabilite_charge_suicidaire(pertes_2))
    if type(active_1) is not bool or type(active_2) is not bool:
        raise ValueError('Activations booléennes requises.')
    return tuple(active and aleatoire.randrange(100) < chance
                 for active, chance in zip((active_1, active_2), chances))


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


def participants_muraille(identites, qg_nommade=None, reserve_strategique=None):
    """Exclut les deux rôles validés d'une liste de participants déjà admissibles.

    Identités (joueur, generalN), jamais noms seuls ni places compactées. Aucun
    choix de donneur, prêt de soldat ou règle de pertes n'est déduit de ce filtre.
    L'appelant fournit le QG uniquement si QG_nommade a été retenu.
    """
    identites = tuple(identites)
    if len(set(identites)) != len(identites):
        raise ValueError('Un général ne contribue pas deux fois à la muraille.')
    return tuple(i for i in identites if i not in (qg_nommade, reserve_strategique))


def choisir_avant_muraille(bilans, positions_origine, aleatoire):
    """Meilleur bilan fourni, puis position numérique, puis hasard reproductible.

    Les bilans viennent des simulations : ce sélecteur ne décide ni ce qu'est
    un dégât, ni les pertes, ni l'admissibilité des blocs. La position d'origine
    suit l'ordre numérique croissant commun, pas la séquence On_melange.
    Un tirage intervient seulement pour départager les derniers ex aequo.
    """
    from fractions import Fraction
    if any(type(b) is not int and not isinstance(b, Fraction) for b in bilans.values()):
        raise ValueError('Bilans numériques exacts requis.')
    positions = {}
    for identite in bilans:
        position = positions_origine.get(identite)
        if (not isinstance(position, str) or not position.isascii()
                or not position.isdecimal() or int(position) <= 0):
            raise ValueError('Position d’origine numérique positive requise.')
        positions[identite] = int(position)
    if not bilans:
        return None
    meilleur = max(bilans.values())
    candidats = [i for i in bilans if bilans[i] == meilleur]
    premiere = min(positions[i] for i in candidats)
    candidats = sorted(i for i in candidats if positions[i] == premiere)
    return candidats[0] if len(candidats) == 1 else aleatoire.choice(candidats)


def facteur_discours_de_la_mort(moral):
    """Moral * 1,10, cumul multiplicatif possible avec de futurs facteurs.

    Renvoie une Fraction exacte, SANS arrondir ni plafonner ici. Le pipeline
    conserve les fractions jusqu'au calcul collectif des sauvetages du moteur.
    """
    from fractions import Fraction
    if (type(moral) is not int and not isinstance(moral, Fraction)) or not 0 <= moral <= 100:
        raise ValueError("Le moral initial est un entier ou une fraction entre 0 et 100.")
    return moral * Fraction(11, 10)


def facteur_cruelle(nombre_unites_cruelles):
    """Réduction multiplicative exacte ; le plafond commun relève du moteur."""
    from fractions import Fraction
    return Fraction(100 - _naturel(nombre_unites_cruelles, 'Unités cruelles'), 100)


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



def interception_reserve(vainqueur_adverse, reserve, *, qg_nommade=None):
    """Décision pure : intercepter un vainqueur sans consommer la rotation.

    Les généraux sont des identités (joueur, nom) distinctes. Aucune sélection
    de la réserve, perte, fatigue ni mutation de formation n'est effectuée ici.
    """
    if reserve is None or vainqueur_adverse is None:
        return None
    if reserve == qg_nommade or reserve == vainqueur_adverse:
        return None
    return reserve




def vainqueur_pour_reserve(resultat, camp_de_reserve):
    """Identifie un adversaire survivant après la défaite du général allié.

    Retourne l'identité stable du vainqueur, ou None. Les deux survivants
    interdisent une interception : le duel n'a pas éliminé l'allié.
    """
    camps = (resultat.get('camp_1'), resultat.get('camp_2'))
    finals = (resultat.get('final_1'), resultat.get('final_2'))
    identites = ((resultat.get('joueur_1'), resultat.get('general_1')),
                 (resultat.get('joueur_2'), resultat.get('general_2')))
    if camps.count(camp_de_reserve) != 1:
        return None
    n = camps.index(camp_de_reserve)
    adverse = 1 - n
    if (type(finals[n]) is not int or type(finals[adverse]) is not int
            or finals[n] != 0 or finals[adverse] <= 0):
        return None
    return identites[adverse]


def designer_interception_reserve(resultat, camp, reserve, *, qg_nommade=None,
                                 unites_reserve=0):
    """Décide sans mutation si la réserve désignée doit intercepter."""
    vainqueur = vainqueur_pour_reserve(resultat, camp)
    if not reserve_peut_intercepter(vainqueur is not None, unites_reserve):
        return None
    return interception_reserve(vainqueur, reserve, qg_nommade=qg_nommade)



def derniere_charge_possible(general_precedent_vaincu, flanc, *, effectif_eligible=None):
    """L'activation impose la défaite du précédent et un flanc unique G/D.

    Ne réanime aucune unité ; les règles d'éligibilité physique des soldats
    restent une étape distincte à définir. Si l'appelant connaît l'effectif
    éligible, zéro interdit l'effet ; son absence ne sélectionne aucun mort.
    G/g et D/d sont équivalents, sans changer ici la grammaire d'ordre.txt.
    """
    if type(general_precedent_vaincu) is not bool or flanc not in ("G", "D", "g", "d"):
        raise ValueError("Défaite booléenne et flanc G/D requis.")
    if effectif_eligible is not None:
        _naturel(effectif_eligible, 'Soldats éligibles à la dernière charge')
        return general_precedent_vaincu and effectif_eligible > 0
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
