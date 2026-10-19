"""Calculs et sélection des donneurs d'ordres, sans inventer leurs effets."""
import catalogues
import progression


def effectif(points, types_unites):
    # Les appelants transmettent les types génériques, jamais leurs étiquettes.
    types = set(types_unites)
    if not types <= catalogues.UNITE_PAR_NOM.keys():
        raise ValueError('Type générique inconnu.')
    if type(points) is not int or points < 0:
        raise ValueError('Commandement entier positif ou nul requis.')
    return points // max(1, len(types))


def global_armee(generaux, qg):
    """Les caractéristiques reçues doivent provenir de l'état privé du moteur."""
    strateges = [g for g in generaux if progression.orientation_principale(g) == 'stratege']
    autres = sum(progression.orientation_principale(g) != 'stratege' for g in generaux)
    points_qg = qg['points_commandement'] if qg is not None else 0
    points_autres = sum(g['points_commandement'] for g in strateges if g is not qg)
    return (2 * points_qg + points_autres) // (2 * max(1, autres))


def selectionner_qg(candidats, points):
    """Aucun départage implicite. Le calcul pertinent est fourni par l'appelant."""
    eligibles = [g for g in candidats if g['nature'] in ('stratege', 'stratege_hybride', 'instinctif_hybride')
                 and g.get('qg') and g.get('effectif_bloc_qg', 0) > 0]
    if not eligibles:
        return None
    meilleur = max(points(g) for g in eligibles)
    premiers = [g for g in eligibles if points(g) == meilleur]
    return premiers[0] if len(premiers) == 1 else None


class QuartierGeneral:
    """Sélection unique pour une bataille ; aucune relève après destruction."""
    def __init__(self, candidats, points):
        self.general = selectionner_qg(candidats, points)
        self.detruit = False

    def actif(self, effectif_bloc):
        if self.general is not None and effectif_bloc(self.general) <= 0:
            self.detruit = True
        return None if self.detruit else self.general


def donneur_duel(general, qg, ordres):
    return general if ordres(general) else qg if qg is not None and ordres(qg) else None


def comparer(points_1, points_2):
    return (points_1 > points_2) - (points_1 < points_2)


def ordres_applicables(identifiants, nature, categorie, comparaison=None, catalogue=None, acquis=()):
    """Sélection seulement : les effets réservés ne deviennent jamais exécutables.

    Une égalité n'est pas une défaite. Les contre-ordres individuels nécessitent
    eux aussi une situation explicite ; aucune comparaison n'est créée pour eux.
    """
    catalogue = catalogues.ORDRES if catalogue is None else catalogue
    if categorie not in ('globale', 'duel', 'individuelle'):
        raise ValueError('Catégorie inconnue.')
    if categorie == 'globale' and nature not in ('stratege', 'stratege_hybride', 'instinctif_hybride'):
        return []
    resultat = []
    for identifiant in dict.fromkeys(identifiants):
        if categorie == 'globale' and nature == 'instinctif_hybride' and identifiant not in acquis:
            continue
        ordre = catalogue.get(identifiant)
        if not ordre or not ordre['disponible'] or ordre['categorie'] != categorie:
            continue
        if ordre['contre']:
            if comparaison != -1:
                continue
        elif categorie != 'individuelle' and comparaison != 1:
            # Une égalité concurrente reste sans gagnant tant qu'aucune règle
            # de départage des effets n'est définie.
            continue
        resultat.append(identifiant)
    return resultat


def confronter_globaux(armee_1, qg_1, ordres_1, armee_2, qg_2, ordres_2, catalogue=None):
    points_1 = global_armee(armee_1, qg_1)
    points_2 = global_armee(armee_2, qg_2)
    comparaison = comparer(points_1, points_2)
    return (ordres_applicables(ordres_1, qg_1['nature'], 'globale', comparaison, catalogue,
                              qg_1.get('evolutions_acquises', ())) if qg_1 else [],
            ordres_applicables(ordres_2, qg_2['nature'], 'globale', -comparaison, catalogue,
                              qg_2.get('evolutions_acquises', ())) if qg_2 else [])
