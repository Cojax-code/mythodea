"""Commandement et points temporaires des généraux et du QG."""
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


def global_armee(generaux, qg, messager_present=False):
    """PC du QG pour ses effets globaux, sans l'ancienne division des ordres."""
    return pc_qg_globaux(qg, generaux, messager_present)



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


def bonus_pc_messager(qg, generaux_territoire, messager_present):
    """10 % des PC des autres généraux alliés du même territoire.

    Un ou plusieurs Messagers donnent un seul bonus, arrondi à l'entier
    inférieur. Le calcul ne modifie jamais la fiche permanente du QG.
    Les fiches passées dans generaux_territoire doivent appartenir au même camp
    et au même territoire que le QG, sans doublons.
    """
    if qg is None or not messager_present:
        return 0
    autres = (g for g in generaux_territoire if g is not qg
              and (qg.get('identifiant') is None or
                   g.get('identifiant') != qg['identifiant']))
    return sum(max(0, g.get('points_commandement', 0)) for g in autres) // 10


def pc_qg_globaux(qg, generaux_territoire, messager_present=False):
    """PC globaux du QG, bonus du Messager compris, sans persistance."""
    if qg is None:
        return 0
    return qg['points_commandement'] + bonus_pc_messager(
        qg, generaux_territoire, messager_present)


def pc_qg_sur_territoire(qg, generaux_presents):
    """Calcule les PC globaux à partir des généraux réellement présents.

    Chaque général est un dictionnaire contenant joueur, nom, chemin et camp.
    Les PC proviennent des fiches privées, jamais des valeurs déclarées par le joueur.
    Le messager doit se trouver dans un bloc d'un général du même territoire
    et du même camp que le QG. Son effet n'est pas cumulable.
    """
    if qg is None:
        return 0
    import generaux
    identite = (qg['joueur'], qg['nom'])
    camp = qg['camp']
    fiches = []
    qg_fiche = None
    messager = False
    for general in generaux_presents:
        if general is None or general.get('camp') != camp:
            continue
        fiche = progression.caracteristiques_general(general)
        if fiche is None:
            continue
        entree = dict(fiche, identifiant=(general['joueur'], general['nom']))
        fiches.append(entree)
        if entree['identifiant'] == identite:
            qg_fiche = entree
        composition = generaux.lire_composition_general(general['chemin'])
        messager |= any(bloc.get('messager_du_QG', 0) > 0
                        for bloc in composition.values())
    return pc_qg_globaux(qg_fiche, fiches, messager)


def bonus_etiquettes(pc, coefficients):
    """Somme des bonus en points de pourcentage ; pas de produit en cascade.

    Exemple : PC 15 et coefficients (1, -0.5) => +7.5 % net.
    Le moteur de combat appliquera ensuite ce pourcentage à la valeur visée.
    """
    from fractions import Fraction
    if pc < 0:
        raise ValueError('PC négatifs interdits.')
    return sum((Fraction(pc) * Fraction(c) for c in coefficients), Fraction(0))
