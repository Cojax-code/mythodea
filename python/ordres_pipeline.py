"""Frontière entre ordre.txt (jetons) et le catalogue de commandement V2.

Ne fusionne JAMAIS les ordres de généraux
différents et ignore les ordres désactivés. Le frontal 1-2 garde son parcours
historique, avec annulations internes et confrontation ciblée face à On_melange.
"""
import catalogues
import commandement
import progression
import ordres_calculs_v2
from contextlib import contextmanager
from contextvars import ContextVar
from fractions import Fraction

_duel = ContextVar('ordres_duel', default=None)
_bataille = ContextVar('ordres_bataille', default=None)
_retraite = ContextVar('retraite_apres_choc', default=None)

_CATEGORIES = {"globale", "duel", "individuelle"}


def index_jetons(catalogue=None):
    catalogue = catalogues.ORDRES if catalogue is None else catalogue
    index = {}
    for identifiant, fiche in catalogue.items():
        jeton = fiche["jeton"]
        if jeton in index:
            raise ValueError("Jeton d'ordre ambigu dans le catalogue.")
        index[jeton] = identifiant
    return index


def ordres_du_general(general, categorie=None, catalogue=None):
    """Retourne les IDs disponibles, ordonnés, pour CE général uniquement.

    La variante avec ciblage doit être traitée par un validateur distinct
    avant d'activer l'effet. La conversion d'un jeton à un ID ne signifie
    pas que son effet est exécuté dans un combat.
    """
    catalogue = catalogues.ORDRES if catalogue is None else catalogue
    if categorie is not None and categorie not in _CATEGORIES:
        raise ValueError("Catégorie inconnue.")
    index = index_jetons(catalogue)
    resultat = []
    for demande in general.get("ordres", ()):
        if not isinstance(demande, dict):
            continue
        jeton = demande.get("identifiant")
        identifiant = index.get(jeton)
        if identifiant is None:
            continue
        fiche = catalogue[identifiant]
        if not progression.ordre_autorise(general.get('caracteristiques', {}), fiche.get('nom')):
            continue
        if not fiche["disponible"] or (
                categorie is not None and fiche["categorie"] != categorie):
            continue
        if fiche.get('acquisition_requise') and identifiant not in general.get(
                'caracteristiques', {}).get('evolutions_acquises', ()):
            continue
        # Pas d'invention d'une cible par défaut : une spécification future
        # devra être validée selon la définition de l'ordre concerné.
        if demande.get("specification") is not None:
            continue
        if identifiant not in resultat:
            resultat.append(identifiant)
    return resultat


def ordres_par_donneur(forces, categorie=None, catalogue=None):
    """Retourne une liste par général actif, sans agrégation des donneurs.

    L'entrée est celle de lire_forces_territoire : camp -> position -> général.
    Les positions et propriétaires ne sont jamais fusionnés ici.
    """
    groupes = []
    for camp, positions in forces.items():
        for position, general in positions.items():
            if not general or not general.get("total_unites", 0):
                continue
            demandes = ordres_du_general(general, categorie, catalogue)
            if demandes:
                groupes.append(dict(camp=camp, position=position,
                                    general=general, identifiants=demandes))
    return groupes


def confronter_intentions(donneur_1, donneur_2, categorie, points_1, points_2,
                         catalogue=None):
    """Compare deux donneurs explicitement identifiés, sans effet de combat.

    donneur_N : dict avec un champ « general » (dictionnaire moteur)
    ou None si ce camp n'a aucun donneur pour CETTE confrontation.
    Les PC sont calculés et transmis par l'appelant : aucune règle de
    calcul globale/duel n'est supposée ici.
    Cette API n'est PAS un mécanisme de sélection automatique du QG.
    """
    if categorie not in _CATEGORIES:
        raise ValueError("Catégorie inconnue.")
    if any(type(p) is not int or p < 0 for p in (points_1, points_2)):
        raise ValueError("Les points de commandement doivent être des entiers positifs ou nuls.")
    catalogue = catalogues.ORDRES if catalogue is None else catalogue

    def intentions(donneur):
        if donneur is None:
            return (), "", ()
        general = donneur["general"]
        fiche = general.get("caracteristiques")
        if not isinstance(fiche, dict) or not isinstance(fiche.get("nature"), str):
            raise ValueError("Caractéristiques officielles du général requises.")
        return (ordres_du_general(general, categorie, catalogue),
                fiche["nature"], fiche.get("evolutions_acquises", ()))

    ids_1, nature_1, acquis_1 = intentions(donneur_1)
    ids_2, nature_2, acquis_2 = intentions(donneur_2)
    comparaison = commandement.comparer(points_1, points_2)
    retenus_1, retenus_2 = commandement.confronter_donneurs(
        ids_1, nature_1, acquis_1, ids_2, nature_2, acquis_2,
        categorie, comparaison, catalogue,
        profil_1=donneur_1['general']['caracteristiques'] if donneur_1 else None,
        profil_2=donneur_2['general']['caracteristiques'] if donneur_2 else None)
    return {"comparaison": comparaison, "camp_1": retenus_1, "camp_2": retenus_2}


def donneurs_officiels(forces, categorie=None, catalogue=None):
    """Prépare les donneurs depuis la progression PRIVÉE, sans effets.

    Renvoie une entrée par général et par catégorie demandée. Aucun champ
    fiche.txt du joueur ne sert d'autorité ; l'absence de fiche privée est
    une erreur, jamais une permission implicite. Sans ordre disponible,
    le général n'est pas retenu comme donneur.
    """
    # Authentifier avant le filtrage des connaissances, sans croire les champs
    # 'caracteristiques' éventuellement présents dans l'objet appelant.
    officiels = {}
    for camp, positions in forces.items():
        officiels[camp] = {}
        for position, general in positions.items():
            if not general or not general.get('total_unites', 0):
                continue
            fiche = progression.caracteristiques_general(general)
            if fiche is None:
                if general.get('ordres'):
                    raise ValueError("Progression privée absente pour un donneur d'ordres.")
                continue
            officiels[camp][position] = {**general, 'caracteristiques': fiche}
    groupes = ordres_par_donneur(officiels, categorie, catalogue)
    donneurs = []
    for groupe in groupes:
        general = groupe["general"]
        fiche = general['caracteristiques']
        if not isinstance(fiche, dict) or not isinstance(fiche.get("nature"), str):
            raise ValueError("Progression privée absente pour un donneur d'ordres.")
        donneurs.append({
            "camp": groupe["camp"],
            "position": groupe["position"],
            "general": {**general, "caracteristiques": fiche},
            "identifiants": list(groupe["identifiants"]),
        })
    return donneurs


def points_duel_officiels(general):
    """Calcule les PC d'un général depuis les données moteur authentiques.

    Ne sélectionne ni QG ni ordre ; applique simplement le calcul V2 existant
    de commandement.effectif_general aux unités réellement présentes.
    """
    fiche = progression.caracteristiques_general(general)
    if not isinstance(fiche, dict) or type(fiche.get("points_commandement")) is not int:
        raise ValueError("PC officiels introuvables pour le duel.")
    if fiche["points_commandement"] < 0:
        raise ValueError("PC officiels négatifs.")
    import generaux
    composition = generaux.lire_composition_general(general["chemin"])
    return commandement.effectif_general(fiche, composition)


def confronter_duel_officiel(general_1, general_2, donneur_1, donneur_2,
                            catalogue=None):
    """Confrontation duel sans effet entre deux généraux *déjà choisis*.

    Un ordre de duel est confronté avec les PC de son DONNEUR : si le QG
    transmet l'ordre à la place du général engagé, ce sont les PC du général
    possédant le QG qui comptent, en appliquant effectif_general.
    Le calcul global d'armée (global_armee) est distinct, réservé aux ordres
    globaux. Les deux engagés restent des arguments explicites pour contrôler
    plus tard la provenance, les cibles et la validité des donneurs.
    Aucun choix automatique de QG ni effet de combat.
    """
    if donneur_1 is None and donneur_2 is None:
        points_1 = points_2 = 0
    else:
        points_1 = points_duel_officiels(
            donneur_1["general"]) if donneur_1 is not None else 0
        points_2 = points_duel_officiels(
            donneur_2["general"]) if donneur_2 is not None else 0
    return confronter_intentions(donneur_1, donneur_2, "duel",
                                points_1, points_2, catalogue)


def identite(general):
    return general['joueur'], general['nom']


@contextmanager
def bataille(territoire, configuration):
    """Fige les déclarations pour toute la bataille, y compris ses renforts."""
    courant = _bataille.get()
    if courant is not None:
        if courant['territoire'] != territoire:
            raise ValueError('Deux territoires ne partagent pas une sélection de QG.')
        yield courant
        return
    import generaux
    import rapports
    forces = generaux.lire_forces_territoire(territoire, configuration)
    quartiers = {}
    for camp, positions in forces.items():
        candidats = []
        for general in positions.values():
            if not general:
                continue
            bloc = generaux.lire_declaration_qg(general['chemin'])
            if bloc:
                candidats.append(dict(general, qg=bloc, effectif_bloc_qg=1))
        quartiers[camp] = commandement.QuartierGeneral(candidats)
        if len(candidats) > 1:
            rapports.ecrire_rapport_territoire(territoire,
                f'QG {camp} : déclarations multiples, tous annulés.')
        elif candidats:
            qg = candidats[0]
            rapports.ecrire_rapport_territoire(territoire,
                f"QG {camp} : {qg['joueur']} {qg['nom']}, bloc {qg['qg']}.")
    courant = dict(territoire=territoire, configuration=configuration, quartiers=quartiers,
                   annules={})
    jeton = _bataille.set(courant)
    try:
        preparer_compatibilites(forces, courant)
        confronter_frontal_melange(forces, courant)
        yield courant
    finally:
        _bataille.reset(jeton)


def verifier_qg():
    """Mémorise la destruction avant qu'une capacité ne repeuple un bloc."""
    courant = _bataille.get()
    if courant is None:
        return
    import generaux
    import rapports
    def effectif(general):
        return sum(generaux.lire_composition_general(general['chemin'])[general['qg']].values())
    for camp, quartier in courant['quartiers'].items():
        detruit = quartier.detruit
        quartier.actif(effectif)
        if quartier.detruit and not detruit:
            rapports.ecrire_rapport_territoire(courant['territoire'],
                f'QG {camp} détruit : aucun remplacement pendant cette bataille.')


def qg_du_general(general):
    courant = _bataille.get()
    if courant is None:
        return None
    verifier_qg()
    configuration = courant['configuration']
    camp = configuration['acteurs'][general['joueur']]['camp']
    quartier = courant['quartiers'].get(camp)
    if quartier is None or quartier.detruit or quartier.general is None:
        return None
    qg = quartier.general
    if ':'.join(identite(qg)) in configuration.get('generaux_hors_combat', ()):
        return None
    return qg


def intention(general, categorie):
    if categorie != 'globale':
        personnelle = intention_personnelle(general, categorie)
        if personnelle or categorie == 'individuelle':
            return personnelle
    qg = qg_du_general(general)
    donneur = intention_personnelle(qg, categorie) if qg is not None else None
    if donneur and categorie == 'globale':
        courant = _bataille.get()
        camp = courant['configuration']['acteurs'][general['joueur']]['camp']
        annules = courant['annules'].get(camp, ())
        donneur = retirer_ordres_annules(donneur, annules)
    return donneur


def retirer_ordres_annules(donneur, annules):
    if donneur is None:
        return None
    ids = [i for i in donneur['identifiants'] if catalogues.ORDRES[i]['nom'] not in annules]
    if not ids:
        return None
    jetons = {catalogues.ORDRES[i]['jeton'] for i in ids}
    return dict(donneur, identifiants=ids, general=dict(donneur['general'],
        ordres=[o for o in donneur['general']['ordres'] if o['identifiant'] in jetons]))


def preparer_compatibilites(forces, contexte):
    """Annule les paires interdites du camp avant les comparaisons adverses.

    Le frontal conserve sa voie historique, même demandé par un autre allié.
    Les nouveaux globaux exigent le QG, l'apprentissage et la nature autorisée.
    Les annulations sont figées pour la bataille, cascades comprises : la mort
    d'un donneur ne réactive pas un ordre déjà annulé.
    """
    import generaux
    import rapports
    for camp, quartier in contexte['quartiers'].items():
        noms = set()
        if generaux.joueur_possede_ordre_armee(forces, camp, '1-2'):
            noms.add('attaque_frontale')
        if quartier.general is not None:
            donneur = intention_personnelle(quartier.general, 'globale')
            if donneur:
                fiche = donneur['general']['caracteristiques']
                ids = commandement.ordres_applicables(donneur['identifiants'],
                    fiche['nature'], 'globale', acquis=fiche['evolutions_acquises'],
                    ordres_adverses=[], profil=fiche)
                noms.update(catalogues.ORDRES[i]['nom'] for i in ids)
        diagnostic = commandement.compatibilite_formations(noms)
        # Aucun effet de paire non définie ne peut être activé silencieusement.
        if diagnostic['non_definies']:
            raise ValueError('Compatibilité de formations non définie.')
        contexte['annules'][camp] = diagnostic['annules']
        for a, b in diagnostic['incompatibles']:
            rapports.ecrire_rapport_territoire(contexte['territoire'],
                f'Formations {camp} : {a} et {b} annulés mutuellement '
                '(combinaison incompatible).')


def confronter_frontal_melange(forces, contexte):
    """Migration ciblée du frontal opposé à On_melange, avant le premier duel.

    Les annulations internes ont déjà été appliquées. Le schéma perdant ne
    revient pas après les premières pertes ; les transmissions du gagnant
    restent soumises à la survie du QG. Hors de cette opposition précise,
    le déclenchement historique du frontal est conservé.
    """
    import generaux
    import rapports
    camps = list(forces)
    donneurs, demandes = [], []
    for camp in camps:
        qg = contexte['quartiers'][camp].general
        donneur = intention_personnelle(qg, 'globale', inclure_frontal=True) if qg else None
        donneur = retirer_ordres_annules(donneur, contexte['annules'][camp])
        donneurs.append(donneur)
        fiche = donneur['general']['caracteristiques'] if donneur else {}
        ids = commandement.ordres_applicables(donneur['identifiants'],
            fiche['nature'], 'globale', acquis=fiche['evolutions_acquises'],
            ordres_adverses=[], profil=fiche) if donneur else []
        noms = {catalogues.ORDRES[i]['nom'] for i in ids}
        # Le déclencheur historique ne peut contourner l'autorité QG/PC
        # dans le cas désormais migré ; le comparateur recevra le vrai donneur.
        if (frontal_autorise(camp)
                and generaux.joueur_possede_ordre_armee(forces, camp, '1-2')):
            noms.add('attaque_frontale')
        demandes.append(noms)
    opposees = any('attaque_frontale' in demandes[a] and 'on_melange' in demandes[b]
                   for a, b in ((0, 1), (1, 0)))
    if not opposees:
        return
    points = [points_globaux_officiels(d) if d else 0 for d in donneurs]
    resultat = confronter_intentions(*donneurs, 'globale', *points)
    for n, camp in enumerate(camps, 1):
        demandes_formation = demandes[n - 1] & {'attaque_frontale', 'on_melange'}
        retenus = {catalogues.ORDRES[i]['nom'] for i in resultat[f'camp_{n}']}
        annules = demandes_formation - retenus
        contexte['annules'][camp] |= annules
        for nom in sorted(demandes_formation):
            statut = 'retenu' if nom in retenus else 'annulé'
            rapports.ecrire_rapport_territoire(contexte['territoire'],
                f'Formation {camp} : {nom} {statut} '
                '(confrontation globale Attaque frontale / On_melange).')
    rapports.afficher_et_ecrire(
        f'Confrontation formations : camps={camps}, PC globaux={points}, résultat={resultat}')


def frontal_autorise(camp):
    contexte = _bataille.get()
    return contexte is None or 'attaque_frontale' not in contexte['annules'].get(camp, ())


def formations_retenues(forces):
    """Confronte les globaux avec les PC actuels avant de choisir le duel.

    Seuls On_melange et QG_nommade déplacent actuellement la séquence. Les
    autres globaux participent à la confrontation ordinaire, sans déplacement.
    """
    if _bataille.get() is None:
        return {}
    camps = list(forces)
    donneurs = []
    for camp in camps:
        general = next((g for g in forces[camp].values()
                        if g and g.get('total_unites', 0)), None)
        donneurs.append(intention(general, 'globale') if general else None)
    if not any(d and {1015, 1016}.intersection(d['identifiants']) for d in donneurs):
        return {}
    points = [points_globaux_officiels(d) if d else 0 for d in donneurs]
    resultat = confronter_intentions(*donneurs, 'globale', *points)
    return {camp: dict(ordres={catalogues.ORDRES[i]['nom']
                              for i in resultat[f'camp_{n}']},
                       qg=identite(d['general']))
            for n, (camp, d) in enumerate(zip(camps, donneurs), 1) if d}


def qg_hors_formation(general, formation):
    return bool(general and formation and 'qg_nommade' in formation['ordres']
                and identite(general) == formation['qg'])


def generaux_en_formation(actifs, formation):
    if not formation:
        return actifs
    positions = {g['emplacement']: g for g in actifs}
    qg = next((p for p, g in positions.items() if identite(g) == formation['qg']), None)
    sequence = commandement.sequence_formation(positions, formation['ordres'], qg)
    return [positions[p] for p in sequence]


def points_globaux_officiels(donneur):
    """Garde le même objet fiche pour le QG et l'armée, sans double comptage."""
    import generaux
    courant = _bataille.get()
    configuration = courant['configuration']
    qg = donneur['general']
    camp = configuration['acteurs'][qg['joueur']]['camp']
    forces = generaux.lire_forces_territoire(courant['territoire'], configuration)
    armee = []
    fiche_qg = None
    for general in forces[camp].values():
        if not general:
            continue
        fiche = progression.caracteristiques_general(general)
        if fiche is None:
            continue
        armee.append(fiche)
        if identite(general) == identite(qg):
            fiche_qg = fiche
    if fiche_qg is None:
        raise ValueError('Le QG donneur ne fait plus partie des forces actives.')
    return commandement.global_armee(armee, fiche_qg)


@contextmanager
def retraites_apres_choc(callback):
    jeton = _retraite.set(callback)
    try:
        yield
    finally:
        _retraite.reset(jeton)


def fuir_apres_choc(generaux):
    """La Survie fournit sa procédure existante ; aucun placement ici."""
    callback = _retraite.get()
    if callback is None:
        return []
    candidats = [g for g in generaux if effet(g, 'choca_fuite') and g['chemin'].is_dir()]
    return callback(candidats) if candidats else []


def intention_personnelle(general, categorie, inclure_frontal=False):
    """Relit les demandes et l'autorité privée au début du véritable duel.

    Un ancien général sans profil ne gagne aucun droit nouveau. Les généraux
    zombies ne peuvent donner les ordres classiques. 1-2 entre uniquement
    dans la confrontation de formations explicitement migrée.
    """
    import generaux
    fiche = progression.caracteristiques_general(general)
    if not fiche or not general['chemin'].is_dir():
        return None
    officiel = {**general, 'caracteristiques': fiche,
                'ordres': generaux.lire_ordres_general(general['chemin'])}
    demandes = ordres_du_general(officiel, categorie)
    demandes = [i for i in demandes if (i != 1002 or inclure_frontal)
                and i in fiche['evolutions_acquises']]
    if _retraite.get() is None:
        demandes = [i for i in demandes if catalogues.ORDRES[i]['nom'] != 'choca_fuite']
    if not demandes:
        return None
    jetons = {catalogues.ORDRES[i]['jeton'] for i in demandes}
    officiel['ordres'] = [o for o in officiel['ordres'] if o['identifiant'] in jetons]
    return {'general': officiel, 'identifiants': demandes}


@contextmanager
def duel(general_1, general_2):
    """Décisions temporaires, réinitialisées même si le calcul est interrompu.

    Aucun droit ni bonus n'est écrit dans les fiches des soldats ou généraux.
    Les ordres déjà transmis persistent jusqu'à la fin du duel, même si le
    QG disparaît. Le duel suivant ne reçoit plus aucune transmission de lui.
    """
    generaux = (general_1, general_2)
    contexte = {identite(g): dict(effets=set(), facteur_cruelle=Fraction(1)) for g in generaux}
    decisions = []
    sources_cruelles = {}
    for categorie in ('globale', 'duel', 'individuelle'):
        donneurs = [intention(g, categorie) for g in generaux]
        # Le droit du QG émetteur ne suffit pas à autoriser le destinataire.
        # Filtrer avant la confrontation évite qu'un ordre interdit annule
        # celui de l'adversaire. Ne pas confondre ce profil avec ses troupes.
        for n, general in enumerate(generaux):
            fiche = progression.caracteristiques_general(general)
            if fiche and donneurs[n]:
                interdits = {catalogues.ORDRES[i]['nom'] for i in donneurs[n]['identifiants']
                             if not progression.reception_ordre_autorisee(fiche, catalogues.ORDRES[i]['nom'])}
                donneurs[n] = retirer_ordres_annules(donneurs[n], interdits)
        if not any(donneurs):
            continue
        points = [(points_globaux_officiels(d) if categorie == 'globale'
                   else points_duel_officiels(d['general'])) if d else 0 for d in donneurs]
        resultat = confronter_intentions(*donneurs, categorie, *points)
        for numero, (general, donneur) in enumerate(zip(generaux, donneurs), 1):
            if not donneur:
                continue
            retenus = resultat[f'camp_{numero}']
            contexte[identite(general)]['effets'].update(catalogues.ORDRES[i]['nom'] for i in retenus)
            if any(catalogues.ORDRES[i]['nom'] == 'cruelle' for i in retenus):
                sources_cruelles[identite(general)] = donneur['general']
            decisions.append(dict(joueur=general['joueur'], general=general['nom'],
                categorie=categorie, pc=points[numero - 1], demandes=donneur['identifiants'],
                donneur_joueur=donneur['general']['joueur'], donneur_general=donneur['general']['nom'],
                retenus=retenus))
    # Cruelle dépend de l'armée du donneur au début du duel, pas de ses pertes
    # futures. Les deux malus sont préparés avant toute mutation de soldats.
    import generaux as moteur_generaux
    import unites
    for donneur, cible in ((general_1, general_2), (general_2, general_1)):
        if 'cruelle' in contexte[identite(donneur)]['effets']:
            source = sources_cruelles[identite(donneur)]
            composition = moteur_generaux.lire_composition_general(source['chemin'])
            nombre = sum(n for bloc in composition.values() for t, n in bloc.items()
                         if unites.etiquette(t, 'cruelle'))
            contexte[identite(cible)]['facteur_cruelle'] = ordres_calculs_v2.facteur_cruelle(nombre)
    jeton = _duel.set(contexte)
    try:
        yield decisions
    finally:
        _duel.reset(jeton)


def effet(general, nom):
    contexte = _duel.get()
    return bool(general is not None and contexte and
                nom in contexte.get(identite(general), {}).get('effets', ()))


def moral(general, valeur):
    """Les fractions vont jusqu'au plancher collectif des sauvetages existants."""
    if effet(general, 'discours_de_la_mort'):
        valeur = ordres_calculs_v2.facteur_discours_de_la_mort(valeur)
    contexte = _duel.get()
    if contexte and general is not None:
        valeur *= contexte.get(identite(general), {}).get('facteur_cruelle', 1)
    return max(0, min(100, valeur))


def rafales(general_1, general_2, aleatoire, resoudre_pertes, *, participants=None):
    """Tirs préalables au choc, même en présence d'un Bouclier vivant.

    Les deux plans sont arrêtés avant les pertes ; aucun avantage de parcours
    j1/j2. Sauvetages collectifs par bloc, avec les blessures et UUID habituels.
    """
    import config
    import generaux
    import soldats
    import unites
    participants = participants if participants is not None else soldats.VueParticipants()
    plans = []
    for tireur, cible in ((general_1, general_2), (general_2, general_1)):
        if not effet(tireur, 'rafale'):
            continue
        arriere = participants.blocs(tireur)['arriere']
        tirs = ordres_calculs_v2.tentatives_rafale(
            arriere['nombre'] if arriere['type'] == 'archer' else 0)
        if not tirs:
            continue
        blocs = participants.blocs(cible)
        candidats = [u for b in config.ordre_blocs
                     for u in (*blocs[b]['unites'], *blocs[b].get('boucliers', ()),
                               *blocs[b].get('soutiens', ()))
                     if not unites.etiquette(generaux.identifier_unite(u), 'lourde')]
        victimes = aleatoire.sample(candidats, min(tirs, len(candidats)))
        plans.append((tireur, cible, tirs, blocs, victimes))
    details = []
    for tireur, cible, tirs, blocs, victimes in plans:
        pertes = 0
        if victimes:
            soldats.affrontement(tireur, cible)
        for bloc in config.ordre_blocs:
            visees = [u for u in victimes if u.parent.name == bloc]
            types = dict.fromkeys(generaux.identifier_unite(u) for u in visees)
            for type_unite in types:
                groupe = [u for u in visees if generaux.identifier_unite(u) == type_unite]
                infos = dict(type=type_unite, nombre=len(groupe), unites=groupe)
                pertes += len(resoudre_pertes(infos, 0, cible))
        details.append(dict(joueur=tireur['joueur'], general=tireur['nom'],
                            tirs=tirs, touches=len(victimes), pertes=pertes))
    for general in (general_1, general_2):
        if plans:
            participants.supprimer_general_si_vide(general)
    return details
