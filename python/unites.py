"""Capacités communes des unités, indépendantes du mode et des ordres futurs."""
import catalogues
from contextlib import contextmanager
from contextvars import ContextVar
import json
import uuid

_duel = ContextVar('capacites_duel', default=None)


def definition(type_unite):
    return catalogues.UNITES[catalogues.UNITE_PAR_NOM[type_unite]]


def etiquette(type_unite, nom, general=None):
    if nom == 'orc' and type_unite == 'sauvageon' and general is not None:
        import ordres_pipeline
        if ordres_pipeline.effet(general, 1008):
            return True
    return nom in definition(type_unite)['etiquettes'] if type_unite != 'vide' else False


def avantage(attaquant, defenseur, general_attaquant=None, general_defenseur=None):
    """Une force et la faiblesse correspondante désignent un seul avantage.

    Le moteur historique applique le multiplicateur à la valeur effective,
    utilisée pour les dégâts et la résistance, sans seconde division adverse.
    """
    if 'vide' in (attaquant, defenseur):
        return 1
    a, d = definition(attaquant), definition(defenseur)
    valeur = a.get('multiplicateur', 2) if defenseur in a['forces'] else 1
    if (attaquant == 'orc_chaman' and defenseur == 'sauvageon'
            and etiquette(defenseur, 'orc', general_defenseur)):
        valeur = max(valeur, 3)
    # Pour l'honneur ôte seulement les faiblesses du défenseur au choc
    # initial. Les forces naturelles de l'attaquant restent intactes.
    import ordres_pipeline
    faiblesses = (() if ordres_pipeline.honneur_protege(general_defenseur)
                  else d['faiblesses'])
    faible = (attaquant in faiblesses or 'tout' in faiblesses or
              ('distance' in faiblesses and etiquette(attaquant, 'distance')) or
              ('non_orc' in faiblesses and not etiquette(attaquant, 'orc', general_attaquant)))
    return max(valeur, 2 if faible else 1)


def occupation(composition):
    """Places d'une armée complète ; un Gros zombie en utilise dix."""
    return sum(nombre * definition(type_unite)['places']
               for bloc in composition.values() for type_unite, nombre in bloc.items())


def caracteristiques_armee(fiche, composition, general=None):
    """Bonus dérivés, jamais ajoutés à la progression persistante du général."""
    resultat = dict(fiche)
    orcs = sum(n for bloc in composition.values() for t, n in bloc.items() if etiquette(t, 'orc', general))
    chevaliers = sum(bloc.get('chevalier_clinquant', 0) for bloc in composition.values())
    # Les Orcs modifient uniquement le moral, jamais les points de commandement.
    # Sans Orc, aucun malus ; avec 1..9 Orcs, malus de (10 - orcs).
    # Au-delà de 10 Orcs, bonus de (orcs - 10).
    resultat['moral'] = max(0, min(100, fiche['moral'] +
                                  (orcs - 10 if orcs else 0) + chevaliers))
    return resultat


def blessures_max(type_unite, batailles):
    base = definition(type_unite)['blessures']
    if base == 0:
        return 0
    return base + (2 if batailles >= 10 else 1 if batailles >= 5 else 0)


def ordres_classiques(type_unite):
    return not etiquette(type_unite, 'sans_cerveau')


def ordres_messagers(nombre, generaux_sous_ordres, qg_vivant):
    """Point d'extension : aucun nouvel ordre n'est exécuté par ce calcul."""
    return min(nombre, generaux_sous_ordres) if qg_vivant else 0


def permissions_messager(chemin):
    """Chaque fichier réserve ses droits à la seule classe demandée."""
    import stat
    for nom, masque in (('monocle', 0o700), ('sceau du roi', 0o070), ('enveloppe', 0o007)):
        p = chemin / nom
        infos = p.lstat()
        droits = stat.S_IMODE(infos.st_mode)
        if (not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1 or
                not droits & masque or droits & ~masque):
            return False
    return True


def creer_officielle(chemin, type_unite, origine, contenu=None):
    """Création moteur dans une génération privée ; aucune entrée joueur."""
    import soldats
    soldats.creer_dossier_unite(chemin)
    for nom in definition(type_unite)['recette']:
        soldats.ecrire_copie(chemin / nom, (contenu or {}).get(nom, ''))
    registre = soldats.charger()
    identifiant = soldats.enregistrer(chemin, registre, type_unite)
    registre[identifiant]['origine_officielle'] = origine
    soldats.sauvegarder(registre)
    soldats.publier(chemin, identifiant, registre[identifiant])
    return identifiant


def scanner_messagers(configuration):
    """La recette de permissions est validée uniquement dans l'entraînement légal."""
    import config
    import etat
    import generaux
    import progression
    import securite
    import soldats
    reference = etat.charger_unites_actions(configuration)
    if reference is None:
        return
    observations = reference.get('capture') or securite.inventorier_unites_actions(configuration)
    origines = {g['identifiant']: g for g in reference['generaux'].values()}
    registre = soldats.charger()
    for cle, actuel in observations.items():
        joueur, nom = actuel['identifiant'].split(':')
        chemin = securite.chemin_general_actions(cle, configuration)
        general = dict(joueur=joueur, nom=nom, chemin=chemin)
        fiche = progression.caracteristiques_general(general)
        origine = origines.get(actuel['identifiant'], {})
        if (not fiche or 110 not in fiche['evolutions_acquises'] or
                not progression.compatible(fiche, ('stratege',)) or
                not (actuel['entrainement'] or origine.get('position') == 'home' and
                     actuel['position'] == configuration['bases_joueurs'][joueur])):
            continue
        for relatif, preuve in actuel['unites'].items():
            if preuve[-1] != 'messager_du_QG':
                continue
            unite = chemin / relatif
            if not unite.is_dir() or not permissions_messager(unite):
                continue
            identifiant = soldats.retrouver(unite, registre, config.dans_generation_privee())
            if identifiant is not None:
                if registre[identifiant].get('origine_officielle'):
                    continue
                # Un ancien soldat ne devient pas messager par simple renommage.
                if registre[identifiant]['type'] != 'messager_du_QG':
                    continue
            else:
                identifiant = soldats.enregistrer(unite, registre, 'messager_du_QG')
            registre[identifiant]['origine_officielle'] = {'recrutement': actuel['identifiant'],
                                                         'tour': reference['tour']}
            soldats.publier(unite, identifiant, registre[identifiant])
    soldats.sauvegarder(registre)


def transformer_chevaliers(general, evenement, initiales, finales):
    """Seuls les Sauvageons officiels restés un tour à l'École sont convertis."""
    import config
    import progression
    import soldats
    fiche = progression.caracteristiques_general(general)
    if (not fiche or 106 not in fiche['evolutions_acquises'] or
            not progression.compatible(fiche, ('instinctif',))):
        raise ValueError('Connaissance 106 et compatibilité instinctive requises.')
    registre = soldats.charger()
    nombre = 0
    for bloc in config.ordre_blocs:
        for unite in sorted((general['chemin'] / bloc).iterdir()):
            if not unite.is_dir() or unite.is_symlink():
                continue
            identifiant = soldats.retrouver(unite, registre, config.dans_generation_privee())
            valeur = registre.get(identifiant, {})
            if (valeur.get('type') != 'sauvageon' or not valeur.get('origine_officielle') or
                    identifiant not in initiales or not initiales[identifiant] or
                    list(finales.get(identifiant, ())) != list(initiales[identifiant]) or
                    (unite / 'sauvageon.txt').exists() or (unite / 'sauvageon.txt').is_symlink()):
                continue
            destination = unite.parent / ('chevalier_clinquant_' + identifiant)
            if destination.exists():
                raise RuntimeError('Destination chevalier déjà occupée.')
            unite.rename(destination)
            valeur.update(type='chevalier_clinquant', chemin=soldats.cle(destination),
                          device=destination.stat().st_dev, inode=destination.stat().st_ino)
            valeur['origine_officielle'] = {'transformation': evenement, 'type_precedent': 'sauvageon'}
            soldats.sauvegarder(registre)
            soldats.publier(destination, identifiant, valeur)
            nombre += 1
    return nombre


def charger_capacites():
    import config
    p = config.racine_metier() / '.systeme/capacites_unites.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'propagations': {}}


def sauver_capacites(donnees):
    import config
    import etat
    etat.ecrire_prive(config.racine_metier() / '.systeme/capacites_unites.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def bloc_destination_zombies(general, rng=None):
    """Placement commun Spore/Propagation chez le général source de la création."""
    import config
    import generaux
    composition = generaux.lire_composition_general(general['chemin'])
    effectifs = {b: sum(n for t, n in composition[b].items() if etiquette(t, 'mort_vivant'))
                for b in config.ordre_blocs}
    maximum = max(effectifs.values())
    if maximum == 0:
        return 'arriere'
    from bouclier_vivant import bloc_destination_spore
    return bloc_destination_spore(effectifs, config.ordre_blocs, rng)


def propager(general, bloc, pertes_adverses, survivants, evenement, duel, rng=None):
    """Le résolveur fournit le bloc source et une identité de confrontation.

    Aucune limite ici : elle s'applique exclusivement après la bataille territoriale.
    Une décision réservée n'est jamais tirée ni appliquée une seconde fois.
    """
    import config
    import soldats
    if bloc not in config.ordre_blocs or type(pertes_adverses) is not int or pertes_adverses < 0:
        raise ValueError('Bloc et nombre de pertes adverses valides requis.')
    if survivants <= 0 or pertes_adverses == 0:
        return 0
    d = charger_capacites()
    if evenement in d['propagations']:
        if not d['propagations'][evenement]['terminee']:
            raise RuntimeError('Propagation interrompue : récupération administrative requise, sans rejeu.')
        return 0
    nombre = (pertes_adverses + 1) // 2
    import ordres_pipeline
    import ordres_calculs_v2
    nombre = ordres_calculs_v2.conversions_propagation(
        nombre, ordres_pipeline.effet(general, 1012))
    bloc = bloc_destination_zombies(general, rng)
    identifiants = [uuid.uuid4().hex for _ in range(nombre)]
    contexte_bataille = soldats._bataille.get()
    territoire = contexte_bataille[0] if contexte_bataille else None
    d['propagations'][evenement] = dict(duel=duel, joueur=general['joueur'],
        general=general['nom'], bloc=bloc, soldats=identifiants, terminee=False)
    sauver_capacites(d)
    registre = soldats.charger()
    for identifiant in identifiants:
        chemin = general['chemin'] / bloc / ('zombi_' + identifiant)
        soldats.creer_dossier_unite(chemin)
        infos = chemin.stat()
        registre[identifiant] = dict(type='zombie', chemin=soldats.cle(chemin),
            device=infos.st_dev, inode=infos.st_ino, blessures=0, batailles=0,
            derniere_bataille=None, batailles_comptees=[],
            origine_officielle={'propagation': evenement, 'duel': duel, 'territoire': territoire})
        soldats.publier(chemin, identifiant, registre[identifiant])
    soldats.sauvegarder(registre)
    d['propagations'][evenement]['terminee'] = True
    sauver_capacites(d)
    return nombre


def terminer_duel(general, duel):
    import config
    import generaux
    import shutil
    import soldats
    if not general['chemin'].is_dir():
        return 0
    composition = generaux.lire_composition_general(general['chemin'])
    import progression
    surplus = occupation(composition) - progression.capacite_maximale_general(general)
    if surplus <= 0:
        return 0
    registre = soldats.charger()
    candidats = []
    for bloc in config.ordre_blocs:
        for chemin in (general['chemin'] / bloc).iterdir():
            if generaux.identifier_unite(chemin) != 'zombie':
                continue
            identifiant = soldats.retrouver(chemin, registre, config.dans_generation_privee())
            if identifiant and registre[identifiant].get('origine_officielle', {}).get('duel') == duel:
                candidats.append((identifiant, chemin))
    retires = 0
    for identifiant, chemin in sorted(candidats, reverse=True):
        if surplus <= 0:
            break
        shutil.rmtree(chemin)
        registre[identifiant]['detruit'] = True
        surplus -= 1
        retires += 1
    soldats.sauvegarder(registre)
    return retires


def terminer_territoire(territoire, evenement, configuration):
    """Limite les unités apparues pendant cette bataille complète, après la cascade.

    Ne touche jamais aux soldats historiques, et n'efface pas les unités d'un
    autre territoire ou d'une autre bataille.
    """
    import config
    import generaux
    import progression
    import shutil
    import soldats
    registre = soldats.charger()
    retires = 0
    for joueur in configuration['joueurs']:
        for zone in generaux.zones_generaux_territoire(territoire, joueur, configuration):
            if not zone['chemin'].is_dir():
                continue
            for chemin_general in zone['chemin'].iterdir():
                if not chemin_general.is_dir() or generaux.numero_general_depuis_nom(chemin_general.name) is None:
                    continue
                general = {'joueur': joueur, 'nom': chemin_general.name, 'chemin': chemin_general}
                surplus = occupation(generaux.lire_composition_general(chemin_general)) - progression.capacite_maximale_general(general)
                if surplus <= 0:
                    continue
                candidats = []
                for bloc in config.ordre_blocs:
                    dossier = chemin_general / bloc
                    if not dossier.is_dir():
                        continue
                    for soldat in dossier.iterdir():
                        if generaux.identifier_unite(soldat) != 'zombie':
                            continue
                        identifiant = soldats.retrouver(soldat, registre, config.dans_generation_privee())
                        preuve = registre.get(identifiant, {}).get('origine_officielle', {})
                        if preuve.get('territoire') == evenement and ('propagation' in preuve or 'spore' in preuve):
                            candidats.append((identifiant, soldat))
                for identifiant, soldat in sorted(candidats, reverse=True):
                    if surplus <= 0:
                        break
                    shutil.rmtree(soldat)
                    registre[identifiant]['detruit'] = True
                    surplus -= 1
                    retires += 1
                if surplus > 0:
                    raise RuntimeError(
                        f'Surplus non régulable sans supprimer de soldats historiques : {joueur} {chemin_general.name}')
    soldats.sauvegarder(registre)
    # Le territoire est fini : la prochaine bataille redémarre à 250.
    capacites = charger_capacites()
    resistances = capacites.get('resistances_boucliers', {})
    for cle in tuple(resistances):
        if cle.startswith(evenement + ':'):
            resistances.pop(cle)
    sauver_capacites(capacites)
    return retires


@contextmanager
def duel(general_1, general_2):
    identifiant = uuid.uuid4().hex
    memoriser_sauvageons((general_1, general_2), identifiant)
    courant = {'id': identifiant, 'confrontation': 0, 'propagation': False}
    jeton = _duel.set(courant)
    try:
        yield
        # Les nouvelles unités ne sont plus régulées ici : un duel n'est pas
        # nécessairement le dernier du territoire.
    finally:
        _duel.reset(jeton)


def apres_confrontation(general_1, general_2, bloc_1, bloc_2, infos_1, infos_2, pertes_1, pertes_2):
    import soldats
    contexte = _duel.get()
    if contexte is None:
        return
    contexte['confrontation'] += 1
    for general, bloc, infos, pertes in (
            (general_1, bloc_1, infos_1, pertes_2), (general_2, bloc_2, infos_2, pertes_1)):
        adversaire = infos_2 if general is general_1 else infos_1
        # Aucun Zombie, même un Gros zombie, ne se propage contre un autre Zombie.
        if (etiquette(adversaire['type'], 'mort_vivant') or
                not etiquette(infos['type'], 'propagation') or
                infos['nombre'] <= 0 or not pertes):
            continue
        evenement = f"{contexte['id']}:{contexte['confrontation']}:{general['joueur']}:{general['nom']}"
        nombre = propager(general, bloc, len(pertes), infos['nombre'], evenement, contexte['id'])
        if nombre:
            import generaux
            infos.update(generaux.lire_blocs_general(general['chemin'])[bloc])
        contexte['propagation'] = True


def moral_bloc(fiche, composition, bloc, general=None):
    """Conserve les fractions jusqu'au calcul collectif des sauvetages."""
    from fractions import Fraction
    valeur = caracteristiques_armee(fiche, composition, general)['moral']
    if any(etiquette(t, 'cruelle') for t in composition.get(bloc, {})):
        chamans = sum(effectifs.get('orc_chaman', 0) for b, effectifs in composition.items() if b != bloc)
        valeur = min(100, Fraction(valeur * (100 + 2 * chamans), 100))
    return valeur


def soigner_victoire_territoriale(configuration, territoire, evenement):
    import generaux
    import soldats
    forces = generaux.lire_forces_territoire(territoire, configuration)
    camps = {camp for camp, places in forces.items() if any(
        general and generaux.general_a_des_unites(general) for general in places.values())}
    if len(camps) != 1:
        return 0
    camp = next(iter(camps))
    presents = []
    chaman = False
    for joueur, acteur in configuration['acteurs'].items():
        if acteur['camp'] != camp:
            continue
        for zone in generaux.zones_generaux_territoire(territoire, joueur, configuration):
            if not zone['chemin'].is_dir():
                continue
            for chemin in zone['chemin'].iterdir():
                if not chemin.is_dir() or generaux.numero_general_depuis_nom(chemin.name) is None:
                    continue
                for bloc in config_blocs(chemin):
                    for unite in bloc.iterdir():
                        type_unite = generaux.identifier_unite(unite)
                        if type_unite == 'inconnu':
                            continue
                        chaman |= type_unite == 'orc_chaman'
                        presents.append((unite, type_unite))
    if not chaman:
        return 0
    registre = soldats.charger()
    nombre = 0
    import config
    for chemin, type_unite in presents:
        if definition(type_unite)['soins'] is None:
            continue
        identifiant = soldats.retrouver(chemin, registre, config.dans_generation_privee())
        valeur = registre.get(identifiant)
        if valeur and not valeur.get('detruit') and evenement not in valeur.get('soins_chaman', []):
            valeur['blessures'] = 0
            valeur.setdefault('soins_chaman', []).append(evenement)
            soldats.publier(chemin, identifiant, valeur)
            nombre += 1
    soldats.sauvegarder(registre)
    return nombre


def config_blocs(chemin):
    import config
    return [chemin / bloc for bloc in config.ordre_blocs if (chemin / bloc).is_dir()]


def memoriser_sauvageons(generaux, duel):
    import config
    import soldats
    import etat
    d = charger_capacites()
    registre = soldats.charger()
    contexte = soldats._bataille.get()
    cycle = etat.charger_cycle_survie(contexte[1]) if contexte and contexte[1] else None
    modifie = False
    for general in generaux:
        blocs = {}
        for bloc in config_blocs(general['chemin']):
            unites = []
            for chemin in sorted(bloc.iterdir()):
                identifiant = soldats.retrouver(chemin, registre, config.dans_generation_privee()) if chemin.is_dir() else None
                valeur = registre.get(identifiant, {})
                if valeur.get('type') == 'sauvageon' and not valeur.get('detruit'):
                    unites.append(dict(id=identifiant, nom=chemin.name))
            if unites:
                blocs[bloc.name] = unites
        if blocs:
            d.setdefault('sauvageons', {})[f"{general['joueur']}:{general['nom']}"] = dict(
                duel=duel, tour=cycle['tour'] if cycle else None, blocs=blocs, utilise=False)
            modifie = True
    if modifie:
        sauver_capacites(d)


def regenerer_fuite(general, configuration):
    """Restaure les soldats du début du dernier duel de ce tour, une seule fois."""
    import config
    import etat
    import generaux
    import soldats
    d = charger_capacites()
    souvenir = d.get('sauvageons', {}).get(f"{general['joueur']}:{general['nom']}")
    cycle = etat.charger_cycle_survie(configuration)
    if (not souvenir or souvenir['utilise'] or
            souvenir['tour'] is not None and (not cycle or souvenir['tour'] != cycle['tour'])):
        return 0
    registre = soldats.charger()
    nombre = 0
    for bloc, initiaux in souvenir['blocs'].items():
        for initial in initiaux:
            identifiant = initial['id']
            valeur = registre[identifiant]
            if not valeur.get('detruit'):
                continue
            chemin = general['chemin'] / bloc / initial['nom']
            if chemin.exists():
                raise RuntimeError('Régénération interrompue ou destination occupée ; récupération requise.')
            soldats.creer_dossier_unite(chemin)
            soldats.ecrire_copie(chemin / 'sauvageon.txt', 'boueux\net\ncrasseux\n')
            infos = chemin.stat()
            valeur.update(detruit=False, chemin=soldats.cle(chemin), device=infos.st_dev, inode=infos.st_ino)
            valeur.setdefault('regenerations', []).append(souvenir['duel'])
            soldats.sauvegarder(registre)
            soldats.publier(chemin, identifiant, valeur)
            nombre += 1
    souvenir['utilise'] = True
    sauver_capacites(d)
    return nombre
