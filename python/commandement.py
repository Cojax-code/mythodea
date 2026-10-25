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


def effectif_general(fiche, composition):
    """Applique une fois l'effet racial à l'armée avant la diversité des types."""
    import unites
    ajustee = unites.caracteristiques_armee(fiche, composition)
    return effectif(ajustee['points_commandement'],
                    [t for bloc in composition.values() for t, nombre in bloc.items() if nombre])


def global_armee(generaux, qg):
    """Les caractéristiques reçues doivent provenir de l'état privé du moteur."""
    strateges = [g for g in generaux if progression.orientation_principale(g) == 'stratege']
    autres = sum(progression.orientation_principale(g) != 'stratege' for g in generaux)
    points_qg = qg['points_commandement'] if qg is not None else 0
    points_autres = sum(g['points_commandement'] for g in strateges if g is not qg)
    return (2 * points_qg + points_autres) // (2 * max(1, autres))


def selectionner_qg(candidats, points=None):
    """Une seule déclaration valide, quelle que soit la nature du général.

    ``points`` reste accepté pour les anciens appelants, mais n'est jamais
    consulté : plusieurs déclarations annulent tous les QG de ce camp.
    """
    eligibles = [g for g in candidats if g.get('qg') in
                 ('avant', 'droite', 'gauche', 'arriere')
                 and g.get('effectif_bloc_qg', 0) > 0]
    return eligibles[0] if len(eligibles) == 1 else None


class QuartierGeneral:
    """Sélection unique pour une bataille ; aucune relève après destruction."""
    def __init__(self, candidats, points=None):
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


def _ordres_eligibles(identifiants, nature, categorie, catalogue, acquis):
    """Préserve l'ordre d'un seul donneur : ne fusionne jamais deux généraux."""
    if categorie not in ('globale', 'duel', 'individuelle'):
        raise ValueError('Catégorie inconnue.')
    if categorie == 'globale' and nature not in (
            'stratege', 'stratege_hybride', 'instinctif_hybride'):
        return []
    resultat = []
    for identifiant in dict.fromkeys(identifiants):
        if categorie == 'globale' and nature == 'instinctif_hybride' and identifiant not in acquis:
            continue
        ordre = catalogue.get(identifiant)
        if ordre and ordre.get('acquisition_requise') and identifiant not in acquis:
            continue
        if ordre and ordre['disponible'] and ordre['categorie'] == categorie:
            resultat.append(identifiant)
    return resultat


def ordres_applicables(identifiants, nature, categorie, comparaison=None,
                       catalogue=None, acquis=(), ordres_adverses=None):
    """Sélection des ordres d'UN général, sans exécuter leurs effets.

    ordres_adverses doit être la liste éligible du donneur adverse de la même
    catégorie. None conserve une comparaison ancienne, sans inventer d'absence
    d'ordres. Sans ordre adverse : les ordres ordinaires et les contre-ordres
    sont candidats. En duel ordre/contre-ordre, les deux sont candidats.
    Les ordres normaux et les contre-ordres d'un même donneur ne se cumulent pas :
    le groupe incompatible est écarté, sans priorité arbitraire.
    """
    catalogue = catalogues.ORDRES if catalogue is None else catalogue
    propres = _ordres_eligibles(identifiants, nature, categorie, catalogue, acquis)
    if not propres:
        return []
    if ordres_adverses is None:
        # Compatibilité avec les appels historiques : l'absence d'ordre adverse
        # n'est jamais déduite d'une comparaison de PC.
        adverses = None
    else:
        adverses = [catalogue[i] for i in ordres_adverses
                    if i in catalogue and catalogue[i]['disponible']
                    and catalogue[i]['categorie'] == categorie]
    if any(catalogue[i]['contre'] for i in propres) and any(
            not catalogue[i]['contre'] for i in propres):
        return []
    resultat = []
    for identifiant in propres:
        contre = catalogue[identifiant]['contre']
        if adverses is not None and not adverses:
            actif = True
        elif adverses is not None and any(
                autre['contre'] != contre for autre in adverses):
            actif = True
        elif contre:
            actif = comparaison == -1
        elif categorie == 'individuelle' and comparaison is None:
            actif = True
        else:
            actif = comparaison == 1
        if actif:
            resultat.append(identifiant)
    return resultat


def confronter_donneurs(ordres_1, nature_1, acquis_1,
                        ordres_2, nature_2, acquis_2, categorie,
                        comparaison, catalogue=None):
    """Confronte deux donneurs sans agréger d'ordres entre généraux.

    Ordre contre ordre à PC égaux : annulation. Ordre contre contre-ordre :
    les deux peuvent fonctionner. Les incompatibilités d'effets entre plusieurs
    ordres normaux restent à contrôler lorsque leurs effets seront définis.
    """
    catalogue = catalogues.ORDRES if catalogue is None else catalogue
    candidats_1 = _ordres_eligibles(ordres_1, nature_1, categorie, catalogue, acquis_1)
    candidats_2 = _ordres_eligibles(ordres_2, nature_2, categorie, catalogue, acquis_2)
    # Un groupe illégal ne doit pas annuler les ordres du camp adverse.
    def compatibles(candidats):
        return candidats if len({catalogue[i]['contre'] for i in candidats}) <= 1 else []
    candidats_1, candidats_2 = compatibles(candidats_1), compatibles(candidats_2)
    return (
        ordres_applicables(candidats_1, nature_1, categorie, comparaison,
                          catalogue, acquis_1, candidats_2),
        ordres_applicables(candidats_2, nature_2, categorie, -comparaison,
                          catalogue, acquis_2, candidats_1),
    )


def confronter_globaux(armee_1, qg_1, ordres_1, armee_2, qg_2, ordres_2, catalogue=None):
    points_1 = global_armee(armee_1, qg_1)
    points_2 = global_armee(armee_2, qg_2)
    comparaison = comparer(points_1, points_2)
    if not qg_1 and not qg_2:
        return [], []
    # Un seul QG donne les ordres globaux de chaque camp. Aucun amalgame
    # avec les ordres des autres généraux de l'armée.
    return confronter_donneurs(
        ordres_1 if qg_1 else (), qg_1['nature'] if qg_1 else '',
        qg_1.get('evolutions_acquises', ()) if qg_1 else (),
        ordres_2 if qg_2 else (), qg_2['nature'] if qg_2 else '',
        qg_2.get('evolutions_acquises', ()) if qg_2 else (),
        'globale', comparaison, catalogue)
