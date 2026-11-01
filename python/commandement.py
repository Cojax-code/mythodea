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
    identifiant_qg = qg.get('identifiant')
    autres_uniques = {}
    for general in generaux_territoire:
        identifiant = general.get('identifiant')
        if general is qg or (identifiant_qg is not None and identifiant == identifiant_qg):
            continue
        # Un général ne contribue qu'une fois au bonus du Messager.
        if identifiant is None:
            raise ValueError('Identifiant officiel requis pour les généraux alliés.')
        autres_uniques[identifiant] = max(0, general.get('points_commandement', 0))
    return sum(autres_uniques.values()) // 10


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


def instantane_qg_territorial(qg, generaux_presents):
    """Fige les PC et effets globaux du QG avant les duels du territoire.

    L'appelant fournit le QG officiel et uniquement les généraux présents
    sur le même territoire. Aucune désignation implicite et aucune écriture
    dans les caractéristiques permanentes ne sont effectuées.
    """
    if qg is None:
        return None
    identite_qg = (qg['joueur'], qg['nom'])
    allies = [g for g in generaux_presents if g is not None
              and g.get('camp') == qg['camp']]
    if not any((g['joueur'], g['nom']) == identite_qg for g in allies):
        return None
    fiche_qg = progression.caracteristiques_general(qg)
    if fiche_qg is None:
        return None
    pc_initial = fiche_qg['points_commandement']
    pc_global = pc_qg_sur_territoire(qg, allies)
    fiche_globale = dict(fiche_qg, points_commandement=pc_global)
    effets = effets_etiquettes_general(
        fiche_globale, set(catalogues.ETIQUETTES_COMBAT),
        portee='global')
    return {
        'qg': identite_qg,
        'camp': qg['camp'],
        'pc_initial': pc_initial,
        'bonus_messager': pc_global - pc_initial,
        'pc_global': pc_global,
        'effets_globaux': dict(effets),
    }


def repartir_malus_qg(instantane, generaux_adverses):
    """Répartit un malus territorial une seule fois entre cibles éligibles.

    Retourne des effets par identité de général, sans modifier les fiches.
    Les fractions exactes évitent pertes par arrondi et double comptage.
    Le responsable de la bataille conserve ce résultat jusqu'à sa fin.
    """
    from fractions import Fraction
    import generaux
    if not instantane:
        return {}
    cibles = {}
    for general in generaux_adverses:
        if general is None or general.get('camp') == instantane['camp']:
            continue
        identite = (general['joueur'], general['nom'])
        if identite in cibles:
            continue
        composition = generaux.lire_composition_general(general['chemin'])
        types = {type_unite for bloc in composition.values()
                 for type_unite, effectif in bloc.items() if effectif > 0}
        cibles[identite] = types
    repartition = {identite: {} for identite in cibles}
    for (effet, cible), valeur in instantane.get('effets_globaux', {}).items():
        if not effet.startswith('malus_'):
            continue
        concernes = [identite for identite, types in cibles.items()
                     if cible is None or any(
                         cible in catalogues.UNITES[catalogues.UNITE_PAR_NOM[t]]['etiquettes']
                         for t in types if t in catalogues.UNITE_PAR_NOM)]
        if not concernes:
            continue
        part = Fraction(valeur, len(concernes))
        for identite in concernes:
            repartition[identite][(effet, cible)] = part
    return repartition


def bonus_etiquettes(pc, coefficients):
    """Somme des bonus en points de pourcentage ; pas de produit en cascade.

    Exemple : PC 15 et coefficients (1, -0.5) => +7.5 % net.
    Le moteur de combat appliquera ensuite ce pourcentage à la valeur visée.
    """
    from fractions import Fraction
    if pc < 0:
        raise ValueError('PC négatifs interdits.')
    return sum((Fraction(pc) * Fraction(c) for c in coefficients), Fraction(0))

def coefficient_niveau_general(niveau):
    """0..4 => 1/2 ; 5..9 => 1 ; 10..14 => 3/2, etc."""
    from fractions import Fraction
    if type(niveau) is not int or niveau < 0:
        raise ValueError('Niveau invalide.')
    return Fraction(niveau // 5 + 1, 2)


def effets_etiquettes_general(fiche, etiquettes_cibles, *, portee='duel'):
    """Bonus/malus bruts par type, calculables sans modifier les unités.

    Les effets globaux sont calculés séparément une fois par bataille
    territoriale. Les effets de duel sont recalculés à chaque confrontation.
    La portée propre à chaque apprentissage pourra être documentée dans
    son registre ; sans portée explicite, on utilise 'duel'.
    """
    from fractions import Fraction
    if portee not in ('duel', 'global'):
        raise ValueError('Portée inconnue.')
    pc = fiche.get('points_commandement', 0)
    # Coefficient fixe : le niveau du général borne l'apprentissage,
    # mais ne multiplie plus une deuxième fois les bonus.
    from fractions import Fraction
    coeff = Fraction(1, 2)
    total = {}
    for nom, niveau in fiche.get('etiquettes', {}).items():
        regle = catalogues.ETIQUETTES_COMBAT.get(nom)
        if not regle or type(niveau) is not int or niveau <= 0:
            continue
        # Les niveaux d'apprentissage multiplient le coefficient de tranche.
        # Une portée future peut être déclarée par le registre de l'effet.
        if regle.get('portee', 'duel') != portee:
            continue
        cible = regle['cible']
        if cible is not None and cible not in etiquettes_cibles:
            continue
        cle = (regle['effet'], cible)
        total[cle] = total.get(cle, Fraction(0)) + Fraction(pc) * coeff * niveau
    return total
