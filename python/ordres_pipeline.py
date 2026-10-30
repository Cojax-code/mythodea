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
_defenseur_off_def = ContextVar('defenseur_off_def', default=None)
_choc_initial = ContextVar('ordres_choc_initial', default=False)

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
        if not progression.ordre_autorise(general.get('caracteristiques', {}), identifiant):
            continue
        if not fiche["disponible"] or (
                categorie is not None and fiche["categorie"] != categorie):
            continue
        if fiche.get('acquisition_requise') and identifiant not in general.get(
                'caracteristiques', {}).get('evolutions_acquises', ()):
            continue
        # Pas d'invention d'une cible par défaut : une spécification future
        # devra être validée selon la définition de l'ordre concerné.
        specification = demande.get('specification')
        if identifiant == 1017:
            if (not isinstance(specification, tuple) or len(specification) != 2
                    or any(type(p) is not int or p <= 0 for p in specification)):
                continue
        elif identifiant == 1025:
            if (categorie != 'globale' or type(specification) is not int
                    or not 1 <= specification <= 20):
                continue
        elif specification is not None:
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
                   annules={}, retraits_tactiques={}, ralliement=None, ralliement_attente=[], ralliement_active=False, ralliement_effectue=False)
    jeton = _bataille.set(courant)
    try:
        preparer_compatibilites(forces, courant)
        confronter_frontal_melange(forces, courant)
        if _defenseur_off_def.get() is not None:
            preparer_ralliement(_defenseur_off_def.get())
        yield courant
    finally:
        _bataille.reset(jeton)



def preparer_ralliement(defenseur):
    """Sélectionne le seul QG défenseur admissible au début d'OFF/DEF."""
    courant = _bataille.get()
    if courant is None:
        return
    courant['ralliement'] = None
    quartier = courant['quartiers'].get(defenseur)
    if quartier is None or quartier.general is None or quartier.detruit:
        return
    qg = quartier.general
    donneur = intention_personnelle(qg, 'globale')
    donneur = retirer_ordres_annules(
        donneur, courant['annules'].get(defenseur, ()))
    if donneur is None or 1023 not in donneur['identifiants']:
        return
    if not catalogues.ORDRES[1023]['disponible']:
        return
    # Ne pas esquiver la confrontation de PC : les décisions officielles du
    # duel contrôlent ensuite l'activation effective de cet ordre.
    courant['ralliement'] = dict(qg=qg, camp=defenseur)



def activer_ralliement_duel(generaux):
    courant = _bataille.get()
    if courant is None:
        return
    choix = courant.get('ralliement')
    courant['ralliement_active'] = bool(
        choix and any(
            courant['configuration']['acteurs'][g['joueur']]['camp'] == choix['camp']
            and effet(g, 1023) for g in generaux))



def tenter_ralliement(unite, donnees, aleatoire):
    """Réserve un mort, après l'échec de son sauvetage, sans le supprimer."""
    courant = _bataille.get()
    if courant is None or not courant.get('ralliement'):
        return False
    cible = courant['ralliement']['qg']
    if not cible['chemin'].is_dir():
        return False
    if not courant.get('ralliement_active'):
        return False
    import generaux
    import soldats
    import config
    type_unite = generaux.identifier_unite(unite)
    blocs = generaux.lire_composition_general(cible['chemin'])
    bloc = next((b for b, types in blocs.items()
                 if types.get(type_unite, 0) > 0), None)
    if bloc is None or aleatoire.randrange(100) >= 20:
        return False
    identifiant = soldats.retrouver(
        unite, donnees, config.dans_generation_privee())
    if identifiant is None:
        return False
    # Écarter physiquement le mort du combat courant ; sans cela une nouvelle
    # lecture des blocs le ferait combattre une seconde fois.
    import shutil
    transit = config.racine_metier() / '.systeme' / 'ralliement_transit'
    transit.mkdir(parents=True, exist_ok=True)
    destination = transit / identifiant
    if destination.exists():
        raise RuntimeError('Ralliement : doublon de soldat en transit.')
    shutil.move(str(unite), str(destination))
    courant['ralliement_attente'].append((destination, identifiant, bloc, cible, unite.name))
    return True


def finaliser_ralliement():
    """Transfère les réservations après le duel : jamais de retour dans le même duel."""
    courant = _bataille.get()
    if courant is None:
        return
    import generaux
    import soldats
    import shutil
    attente = courant['ralliement_attente']
    courant['ralliement_attente'] = []
    if not attente:
        return
    courant['ralliement_effectue'] = True
    donnees = soldats.charger()
    for source, identifiant, bloc, qg, nom_original in attente:
        if not source.is_dir():
            continue
        quartier = courant['quartiers'].get(courant['ralliement']['camp'])
        if (not qg['chemin'].is_dir() or quartier is None or quartier.detruit):
            # Le QG est détruit : le mort doit rester mort.
            donnees[identifiant]['detruit'] = True
            shutil.rmtree(source)
            continue
        destination = qg['chemin'] / bloc / (nom_original + '_rallie_' + identifiant)
        if destination.exists():
            raise RuntimeError('Ralliement : identité déjà présente au QG.')
        shutil.move(str(source), str(destination))
        infos = destination.stat()
        valeur = donnees[identifiant]
        valeur.update(chemin=soldats.cle(destination),
                      device=infos.st_dev, inode=infos.st_ino)
        soldats.publier(destination, identifiant, valeur)
    soldats.sauvegarder(donnees)


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
        personnelle = filtrer_gros_poisson(general, personnelle)
        if personnelle or categorie == 'individuelle':
            return personnelle
    qg = qg_du_general(general)
    donneur = intention_personnelle(qg, categorie) if qg is not None else None
    donneur = filtrer_gros_poisson(general, donneur)
    if donneur and categorie == 'globale':
        courant = _bataille.get()
        camp = courant['configuration']['acteurs'][general['joueur']]['camp']
        annules = courant['annules'].get(camp, ())
        donneur = retirer_ordres_annules(donneur, annules)
    return donneur


def cibles_gros_poisson(beneficiaire, donneur):
    """Résout les positions actives du camp, sous l'autorité du QG courant."""
    courant = _bataille.get()
    qg = qg_du_general(beneficiaire)
    if courant is None or qg is None or identite(qg) != identite(donneur['general']):
        return []
    import generaux
    configuration = courant['configuration']
    camp = configuration['acteurs'][beneficiaire['joueur']]['camp']
    forces = generaux.lire_forces_territoire(courant['territoire'], configuration)[camp]
    couples = []
    for demande in donneur['general']['ordres']:
        if demande['identifiant'] != '2-6':
            continue
        specification = demande.get('specification')
        if not isinstance(specification, tuple) or len(specification) != 2:
            continue
        a, b = (forces.get(str(p)) for p in specification)
        if not a or not b or identite(a) != identite(beneficiaire):
            continue
        if identite(a) == identite(b):
            continue  # Sans effet, y compris dans la confrontation d'ordres.
        profils = [progression.caracteristiques_general(g) for g in (a, b)]
        if any(not fiche or not progression.reception_ordre_autorisee(fiche, 1017)
               for fiche in profils):
            continue
        if not any(identite(b) == identite(preteur) for _, preteur in couples):
            couples.append((a, b))
    return couples


def filtrer_gros_poisson(beneficiaire, donneur):
    if donneur and 1017 in donneur['identifiants']:
        if not cibles_gros_poisson(beneficiaire, donneur):
            return retirer_ordres_annules(donneur, {1017})
    return donneur


def retirer_ordres_annules(donneur, annules):
    """Filtre les annulations internes directement par identifiants."""
    if donneur is None:
        return None
    ids = [i for i in donneur['identifiants'] if i not in annules]
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
        identifiants = set()
        if generaux.joueur_possede_ordre_armee(forces, camp, catalogues.ORDRES[1002]['jeton']):
            identifiants.add(1002)
        if quartier.general is not None:
            donneur = intention_personnelle(quartier.general, 'globale')
            if donneur:
                fiche = donneur['general']['caracteristiques']
                ids = commandement.ordres_applicables(donneur['identifiants'],
                    fiche['nature'], 'globale', acquis=fiche['evolutions_acquises'],
                    ordres_adverses=[], profil=fiche)
                identifiants.update(ids)
        diagnostic = commandement.compatibilite_formations(identifiants)
        # Aucun effet de paire non définie ne peut être activé silencieusement.
        if diagnostic['non_definies']:
            raise ValueError('Compatibilité de formations non définie.')
        contexte['annules'][camp] = diagnostic['annules']
        for a, b in diagnostic['incompatibles']:
            rapports.ecrire_rapport_territoire(contexte['territoire'],
                f"Formations {camp} : {catalogues.ORDRES[a]['nom']} et {catalogues.ORDRES[b]['nom']} annulés mutuellement " 
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
        demandes_ids = set(ids)
        # Le déclencheur historique ne peut contourner l'autorité QG/PC
        # dans le cas désormais migré ; le comparateur recevra le vrai donneur.
        if (frontal_autorise(camp)
                and generaux.joueur_possede_ordre_armee(
                    forces, camp, catalogues.ORDRES[1002]['jeton'])):
            demandes_ids.add(1002)
        demandes.append(demandes_ids)
    opposees = any(1002 in demandes[a] and 1015 in demandes[b]
                   for a, b in ((0, 1), (1, 0)))
    if not opposees:
        return
    points = [points_globaux_officiels(d) if d else 0 for d in donneurs]
    resultat = confronter_intentions(*donneurs, 'globale', *points)
    for n, camp in enumerate(camps, 1):
        demandes_formation = demandes[n - 1] & {1002, 1015}
        retenus = set(resultat[f'camp_{n}'])
        annules = demandes_formation - retenus
        contexte['annules'][camp] |= annules
        for identifiant in sorted(
                demandes_formation, key=lambda i: catalogues.ORDRES[i]['nom']):
            nom = catalogues.ORDRES[identifiant]['nom']
            statut = 'retenu' if identifiant in retenus else 'annulé'
            rapports.ecrire_rapport_territoire(contexte['territoire'],
                f'Formation {camp} : {nom} {statut} '
                '(confrontation globale Attaque frontale / On_melange).')
    rapports.afficher_et_ecrire(
        f'Confrontation formations : camps={camps}, PC globaux={points}, résultat={resultat}')


def frontal_autorise(camp):
    contexte = _bataille.get()
    return contexte is None or 1002 not in contexte['annules'].get(camp, ())


def formations_retenues(forces):
    """Confronte les globaux avec les PC actuels avant de choisir le duel.

    On_melange et QG_nommade modifient la séquence. Muraille humaine,
    lorsqu'elle sera déclarée exécutable au catalogue, doit également
    être transmise au pilote territorial ; elle ne déplace pas les généraux.
    """
    if _bataille.get() is None:
        return {}
    camps = list(forces)
    donneurs = []
    for camp in camps:
        general = next((g for g in forces[camp].values()
                        if g and g.get('total_unites', 0)), None)
        donneurs.append(intention(general, 'globale') if general else None)
    # 1019 est archivé : ne jamais le considérer comme formation active.
    formations_territoriales = frozenset((1015, 1016))
    if not any(
            d and any(i in formations_territoriales
                      and catalogues.ORDRES[i]['disponible']
                      for i in d['identifiants'])
            for d in donneurs):
        return {}
    points = [points_globaux_officiels(d) if d else 0 for d in donneurs]
    resultat = confronter_intentions(*donneurs, 'globale', *points)
    return {camp: dict(ordres=set(resultat[f'camp_{n}']),
                       qg=identite(d['general']))
            for n, (camp, d) in enumerate(zip(camps, donneurs), 1) if d}




def transmission_muraille_active(camp):
    """Une Muraille ne reçoit plus de désignations si son QG a disparu.

    Réutilise l'état territorial du QG, qui mémorise sa destruction même si
    des capacités spéciales repeuplent ensuite un bloc.
    """
    courant = _bataille.get()
    if courant is None:
        return False
    verifier_qg()
    quartier = courant['quartiers'].get(camp)
    return bool(quartier is not None and quartier.general is not None
                and not quartier.detruit)


def participants_muraille_territoire(forces, formations, camp, *,
                                   reserve_strategique=None):
    """Prépare la formation Muraille depuis les décisions territoriales retenues.

    Ne lit ni ne déplace de soldats ; refuse une formation absente ou annulée.
    Les exclusions QG_nommade, Réserve stratégique et Zombies précèdent
    toute simulation. Les positions originales ne sont pas compactées.
    """
    import generaux
    formation = formations.get(camp)
    if not formation or 1019 not in formation['ordres']:
        return ()
    candidats = tuple(g for g in forces.get(camp, {}).values()
                      if g and generaux.general_a_des_unites(g)
                      and progression.general_recoit_ordre(g, 1019))
    qg_exclu = (formation['qg']
                 if 1016 in formation['ordres'] else None)
    admissibles = ordres_calculs_v2.participants_muraille(
        (identite(g) for g in candidats), qg_exclu, reserve_strategique)
    return tuple(g for g in candidats if identite(g) in admissibles)


def qg_hors_formation(general, formation):
    return bool(general and formation and 1016 in formation['ordres']
                and progression.general_recoit_ordre(general, 1016)
                and identite(general) == formation['qg'])



def marquer_retrait_tactique(camp, general, formation):
    """Après son premier duel, place le général engagé en fin de rotation.

    Le déplacement est purement logique et ne touche jamais aux dossiers,
    unités, positions territoriales ni sanctions de repli.
    """
    courant = _bataille.get()
    if (courant is None or not formation or 1021 not in formation['ordres']
            or camp in courant['retraits_tactiques']):
        return False
    courant['retraits_tactiques'][camp] = identite(general)
    return True


def generaux_en_formation(actifs, formation):
    if not formation:
        return actifs
    # Les Zombies occupent leurs rangs de la séquence normale. Seuls les autres
    # généraux sont réordonnés entre les places restantes, sans les compacter.
    normaux = sorted(actifs, key=lambda g: int(g['emplacement']))
    eligibles = [g for g in normaux if all(progression.general_recoit_ordre(g, identifiant)
                                         for identifiant in formation['ordres'])]
    positions = {g['emplacement']: g for g in eligibles}
    qg = next((p for p, g in positions.items() if identite(g) == formation['qg']), None)
    courant = _bataille.get()
    camp = next((courant['configuration']['acteurs'][g['joueur']]['camp']
                 for g in eligibles), None) if courant is not None else None
    retrait = (courant.get('retraits_tactiques', {}).get(camp)
               if courant is not None and 1021 in formation['ordres'] else None)
    position_retrait = next(
        (p for p, g in positions.items() if identite(g) == retrait), None)
    sequence = commandement.sequence_formation(
        positions, formation['ordres'], qg, position_retrait)
    reorganises = iter(positions[p] for p in sequence)
    return [next(reorganises) if g['emplacement'] in positions else g for g in normaux]


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
    import generaux as moteur_generaux
    # Les prêts reviennent avant le déplacement : un bénéficiaire sans soldats
    # propres ne peut réserver une retraite qui déplacerait un général supprimé.
    candidats = [g for g in generaux if effet(g, 1011) and g['chemin'].is_dir()
                 and moteur_generaux.total_general_depuis_chemin(g['chemin']) > 0]
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
    # Le général du QG utilise qg.txt pour tous ses ordres ;
    # les autres généraux utilisent ordre.txt pour duel / individuel.
    qg = qg_du_general(general)
    est_qg = qg is not None and identite(qg) == identite(general)
    if categorie == 'globale' and not est_qg:
        return None
    source = (generaux.lire_ordres_qg(general['chemin']) if est_qg
              else generaux.lire_ordres_general(general['chemin']))
    officiel = {**general, 'caracteristiques': fiche, 'ordres': source}
    demandes = ordres_du_general(officiel, categorie)
    demandes = [i for i in demandes if (i != 1002 or inclure_frontal)
                and i in fiche['evolutions_acquises']]
    if _retraite.get() is None:
        demandes = [i for i in demandes if i != 1011]
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
                interdits = {i for i in donneurs[n]['identifiants']
                             if not progression.reception_ordre_autorisee(fiche, i)}
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
            contexte[identite(general)]['effets'].update(retenus)
            if 1010 in retenus:
                sources_cruelles[identite(general)] = donneur['general']
            if 1017 in retenus:
                contexte[identite(general)]['gros_poisson'] = cibles_gros_poisson(general, donneur)
            decisions.append(dict(joueur=general['joueur'], general=general['nom'],
                categorie=categorie, pc=points[numero - 1], demandes=donneur['identifiants'],
                donneur_joueur=donneur['general']['joueur'], donneur_general=donneur['general']['nom'],
                retenus=retenus))
    # Cruelle dépend de l'armée du donneur au début du duel, pas de ses pertes
    # futures. Les deux malus sont préparés avant toute mutation de soldats.
    import generaux as moteur_generaux
    import unites
    for donneur, cible in ((general_1, general_2), (general_2, general_1)):
        if 1010 in contexte[identite(donneur)]['effets']:
            source = sources_cruelles[identite(donneur)]
            contexte[identite(cible)]['source_cruelle'] = source
            composition = moteur_generaux.lire_composition_general(source['chemin'])
            nombre = sum(n for bloc in composition.values() for t, n in bloc.items()
                         if unites.etiquette(t, 'cruelle'))
            contexte[identite(cible)]['facteur_cruelle'] = ordres_calculs_v2.facteur_cruelle(nombre)
    jeton = _duel.set(contexte)
    try:
        yield decisions
    finally:
        _duel.reset(jeton)



@contextmanager
def effets_muraille(dominant, adversaire, contributeurs):
    """Contexte du choc collectif : commandement dominant et effets propres.

    Les catégories globale/duel passent une seule fois par le duel officiel.
    Les contributions supplémentaires ne transmettent pas leurs ordres de duel :
    seules leurs demandes individuelles éligibles leur appartiennent.
    """
    contributeurs = tuple(contributeurs)
    if len({identite(g) for g in contributeurs}) != len(contributeurs):
        raise ValueError('Contributeur Muraille répété.')
    with duel(dominant, adversaire) as decisions:
        contexte = _duel.get()
        for general in contributeurs:
            cle = identite(general)
            if cle in contexte:
                continue
            donneur = intention_personnelle(general, 'individuelle')
            effets = set()
            if donneur:
                fiche = progression.caracteristiques_general(general)
                demandes = retirer_ordres_annules(
                    donneur, {i for i in donneur['identifiants']
                             if not progression.reception_ordre_autorisee(fiche, i)})
                if demandes:
                    pc = points_duel_officiels(demandes['general'])
                    resultat = confronter_intentions(
                        demandes, None, 'individuelle', pc, 0)
                    effets.update(resultat['camp_1'])
                    decisions.append(dict(
                        joueur=general['joueur'], general=general['nom'],
                        categorie='individuelle', pc=pc,
                        demandes=demandes['identifiants'],
                        donneur_joueur=demandes['general']['joueur'],
                        donneur_general=demandes['general']['nom'],
                        retenus=resultat['camp_1']))
            contexte[cle] = dict(effets=effets, facteur_cruelle=Fraction(1))
        yield decisions


@contextmanager
def participations_duel(general_1, general_2, participants, decisions):
    """Ouvre les prêts retenus pour ce duel, puis libère toutes les réservations."""
    import generaux
    import soldats
    courant = _duel.get() or {}
    couples = [couple for g in (general_1, general_2)
               for couple in courant.get(identite(g), {}).get('gros_poisson', ())]
    if not couples:
        yield participants
        return
    configuration = _bataille.get()['configuration']
    contributions, origines, prets = [], {}, []
    beneficiaires_par_preteur = {}
    for beneficiaire, preteur in couples:
        if identite(beneficiaire) == identite(preteur):
            for decision in decisions:
                if (decision['joueur'], decision['general']) == identite(beneficiaire) and 1017 in decision['retenus']:
                    decision['motif'] = (decision.get('motif', '') +
                        ' Ligne Gros_poisson sans effet : auto-désignation.').strip()
            continue
        benef = identite(beneficiaire)
        origine = identite(preteur)
        if origine in beneficiaires_par_preteur and beneficiaires_par_preteur[origine] != benef:
            raise ValueError('Gros_poisson conflictuel : un prêteur désigne plusieurs bénéficiaires du duel.')
        beneficiaires_par_preteur[origine] = benef
        prets.append((beneficiaire, preteur))
        for g in (beneficiaire, preteur):
            origines[identite(g)] = g
    if not prets:
        yield participants
        return
    if participants.groupe:
        raise RuntimeError('Le duel possède déjà une participation temporaire.')
    for g in origines.values():
        contributions.extend((g, b, generaux.chemins_bloc(infos))
                             for b, infos in generaux.lire_blocs_general(g['chemin'], lecture_seule=True).items())
    with soldats.participation_temporaire(contributions) as groupe:
        par_commandant_bloc = {}
        for beneficiaire, preteur in prets:
            # Le groupe commun peut contenir les prêts des deux camps ; chaque
            # sélection reste strictement limitée au couple autorisé.
            choix = groupe.selections_gros_poisson(beneficiaire, preteur, configuration,
                                                   autres_couples=True)
            par_bloc = {}
            for (bloc, _), ids in choix['selections'].items():
                par_bloc.setdefault(bloc, []).extend(ids)
            for bloc, ids in par_bloc.items():
                cle = identite(beneficiaire), bloc
                selection = par_commandant_bloc.setdefault(cle, (beneficiaire, {}))[1]
                selection.update(dict.fromkeys(ids))
            if choix['motif']:
                for decision in decisions:
                    if (decision['joueur'], decision['general']) == identite(beneficiaire) and 1017 in decision['retenus']:
                        decision['motif'] = (decision.get('motif', '') +
                            f" Prêteur {preteur['joueur']} {preteur['nom']} : {choix['motif']}").strip()
        affectations = [(g, bloc, tuple(ids)) for (_, bloc), (g, ids) in par_commandant_bloc.items()]
        vue = soldats.VueParticipants(groupe, affectations, conserver_non_affectes=True)
        vue.verifier_duel(general_1, general_2)
        import unites
        for donnees in courant.values():
            source = donnees.get('source_cruelle')
            if source:
                nombre = sum(n for bloc in vue.composition(source).values() for t, n in bloc.items()
                             if unites.etiquette(t, 'cruelle'))
                donnees['facteur_cruelle'] = ordres_calculs_v2.facteur_cruelle(nombre)
        yield vue
    for g in origines.values():
        generaux.supprimer_general_si_vide(g)


@contextmanager
def defense_off_def(camp):
    jeton = _defenseur_off_def.set(camp)
    try:
        yield
    finally:
        _defenseur_off_def.reset(jeton)


@contextmanager
def choc_initial():
    jeton = _choc_initial.set(True)
    try:
        yield
    finally:
        _choc_initial.reset(jeton)


def honneur_protege(general):
    """Protection des faiblesses uniquement en choc initial OFF/DEF."""
    if general is None or not _choc_initial.get():
        return False
    courant = _bataille.get()
    camp = (courant['configuration']['acteurs'][general['joueur']]['camp']
            if courant is not None else general.get('camp', general['joueur']))
    return camp == _defenseur_off_def.get() and effet(general, 1022)


def effet(general, identifiant):
    contexte = _duel.get()
    return bool(general is not None and contexte and
                identifiant in contexte.get(identite(general), {}).get('effets', ())
                and progression.general_recoit_ordre(general, identifiant))


def moral(general, valeur, *, type_unite=None):
    """Les fractions vont jusqu'au plancher collectif des sauvetages existants."""
    import unites
    if effet(general, 1007) and (type_unite is None or unites.ordres_classiques(type_unite)):
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
        if not effet(tireur, 1009):
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
