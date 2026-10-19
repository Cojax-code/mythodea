"""Réserve et bâtiments : relevés vivants, validation privée et publication."""
import json
import stat

import catalogues
import progression
import soldats


EMPLACEMENTS = ('001', '002', '003')


def preparer_emplacements(configuration, migrer=True):
    """Six places d'École et une Forge communes, avec accès privés par joueur.

    Migration des anciens dossiers d'École par renommage, sans écrasement.
    Une destination déjà existante réclame une récupération explicite, sans perte.
    """
    import os
    import pwd
    import grp
    import generaux
    from cycle_linux import sans_liens
    migrations = []
    anciens = []
    for territoire in configuration['territoires']:
        if territoire.name not in configuration['villages']:
            continue
        for joueur in configuration['joueurs']:
            acteur = configuration['acteurs'][joueur]
            uid = pwd.getpwnam(acteur['proprietaire_linux']).pw_uid
            gid = grp.getgrnam(acteur['groupe_linux']).gr_gid
            groupe = grp.getgrnam(configuration['groupes_camps'][acteur['camp']]).gr_gid
            for zone in generaux.zones_generaux_territoire(territoire, joueur, configuration):
                if not zone.get('commun'):
                    continue
                dossier = zone['chemin']
                for commun in (dossier.parent.parent, dossier.parent):
                    sans_liens(commun)
                    commun.mkdir(parents=True, exist_ok=True)
                    os.chown(commun, 0, groupe)
                    os.chmod(commun, 0o750)
                sans_liens(dossier)
                dossier.mkdir(exist_ok=True)
                os.chown(dossier, uid, gid)
                os.chmod(dossier, 0o700)
                if zone['batiment'] != 'ecole_officiers' or not migrer:
                    continue
                ancien = territoire / joueur / 'ecole_officiers' / dossier.parent.name
                sans_liens(ancien)
                if ancien.is_dir():
                    anciens.append(ancien)
                    for source in ancien.iterdir():
                        sans_liens(source)
                        destination = dossier / source.name
                        if destination.exists():
                            raise RuntimeError(f'Migration École ambiguë : {destination}')
                        migrations.append((source, destination))
    # Contrôler tous les chemins avant le premier transfert.
    for source, destination in migrations:
        source.rename(destination)
    for ancien in anciens:
        ancien.rmdir()
        if not any(ancien.parent.iterdir()):
            ancien.parent.rmdir()


def charger():
    import config
    chemin = config.racine_metier() / '.systeme/formation.json'
    return json.loads(chemin.read_text(encoding='utf-8')) if chemin.exists() else {
        'manuels': {}, 'sejours': {}, 'valides': []}


def sauvegarder(donnees):
    import config
    import etat
    etat.ecrire_prive(config.racine_metier() / '.systeme/formation.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def demande_ecriture(texte):
    champs = texte.split()
    if champs and champs[0].lower() == 'e':
        champs = champs[1:]
    if (len(champs) != 2 or champs[0] not in EMPLACEMENTS or
            not champs[1].isascii() or not champs[1].isdecimal()):
        raise ValueError('Écriture attendue : emplacement 001..003 et ID universel.')
    identifiant = int(champs[1])
    if identifiant not in catalogues.EVOLUTIONS:
        raise ValueError('Évolution inconnue.')
    return champs[0], identifiant


def demande_lecture(texte):
    champs = texte.split()
    if champs and champs[0].lower() == 'a':
        if len(champs) != 3:
            raise ValueError('Apprentissage attendu : a 001 ID.')
        demande_ecriture(' '.join(champs[1:]))
        champs = champs[1:2]
    if len(champs) != 1 or champs[0] not in EMPLACEMENTS:
        raise ValueError('Lecture attendue : un emplacement 001..003.')
    return champs[0]


def commencer_sejour(tour, general, lieu, camp, preuve_presence,
                     ecrire='', lire='', unites=None, eligibles_forge=()):
    """Appelé une fois au début du tour ; aucune modification tardive de demande.

    preuve_presence est relevée par le moteur sur le disque vivant (inode et
    changement du dossier), puis contrôlée avant la capture privée. Les seuls
    chemins copiés ne peuvent pas démontrer un tour complet de présence.
    """
    identite = f"{general['joueur']}:{general['nom']}"
    cle = f'{tour}:{identite}'
    donnees = charger()
    if cle in donnees['sejours'] or cle in donnees['valides']:
        return False
    if lieu not in ('ecole_officiers', 'hopital', 'forge', 'reserve'):
        raise ValueError('Lieu de formation inconnu.')
    if not preuve_presence:
        raise ValueError('Preuve de présence moteur requise.')
    action, emplacement, evolution = 'soins', None, None
    if lieu == 'forge':
        action = 'forge'
    if lieu == 'reserve':
        action = 'formation'
    if lieu == 'ecole_officiers':
        if bool(ecrire.strip()) == bool(lire.strip()):
            raise ValueError('Une seule demande de lecture ou écriture est nécessaire.')
        caracteristiques = progression.caracteristiques_general(general)
        if caracteristiques is None:
            raise ValueError('Caractéristiques officielles du général absentes.')
        if ecrire.strip():
            emplacement, evolution = demande_ecriture(ecrire)
            if evolution not in caracteristiques['evolutions_acquises']:
                raise ValueError('Le général ne possède pas cette évolution.')
            action = 'ecriture'
        else:
            emplacement = demande_lecture(lire)
            if lire.split()[0].lower() == 'a':
                evolution = int(lire.split()[2])
            action = 'lecture'
    donnees['sejours'][cle] = dict(tour=tour, identite=identite, lieu=lieu, camp=camp,
        preuve=list(preuve_presence), action=action, emplacement=emplacement,
        evolution=evolution, unites={i: list(preuve) for i, preuve in (unites or {}).items()},
        eligibles_forge=sorted(eligibles_forge))
    sauvegarder(donnees)
    return True


def valider_sejour(tour, general, lieu, camp, preuve_presence, tour_termine=False, unites=None):
    """Le pilote garantit la fin du tour et fournit l'observation sous gel.

    Un appel sans fin de tour attestée ne valide rien. En cas de départ ou de
    changement de preuve, la demande expire sans soin ni apprentissage.
    """
    identite = f"{general['joueur']}:{general['nom']}"
    cle = f'{tour}:{identite}'
    donnees = charger()
    sejour = donnees['sejours'].get(cle)
    if not tour_termine or sejour is None or cle in donnees['valides']:
        return False
    if (sejour['lieu'], sejour['camp'], sejour['preuve']) != (lieu, camp, list(preuve_presence)):
        del donnees['sejours'][cle]
        sauvegarder(donnees)
        return False
    manuel = donnees['manuels'].setdefault(camp, dict.fromkeys(EMPLACEMENTS))
    if sejour['action'] == 'ecriture':
        # Ne pas départager deux inscriptions concurrentes par l'ordre du scan.
        concurrents = [s for k, s in donnees['sejours'].items() if k != cle and
                      s['tour'] == tour and s['camp'] == camp and s['action'] == 'ecriture'
                      and s['emplacement'] == sejour['emplacement']]
        if concurrents:
            raise ValueError('Écritures concurrentes : règle de départage à définir.')
        officiel = progression.caracteristiques_general(general)
        if sejour['evolution'] not in officiel['evolutions_acquises']:
            raise ValueError('Autorisation d’écriture perdue.')
        manuel[sejour['emplacement']] = sejour['evolution']
    elif sejour['action'] == 'lecture':
        identifiant = manuel[sejour['emplacement']]
        if sejour['evolution'] is not None and identifiant != sejour['evolution']:
            raise ValueError('L’ID demandé ne correspond pas au contenu du manuel.')
        officielles = progression.charger()
        fiche = officielles[identite]
        if cle not in fiche.get('apprentissages_valides', []):
            if fiche.get('evolution_apprise') is not None:
                raise ValueError('Un apprentissage est déjà en attente ; remplacement non défini.')
            if identifiant not in progression.evolutions_eligibles(fiche):
                raise ValueError('Mémoire vide, incompatible ou indisponible.')
            fiche['evolution_apprise'] = identifiant
            fiche.setdefault('apprentissages_valides', []).append(cle)
            progression.sauvegarder(officielles)
        progression.publier_fiche(general['chemin'], fiche)
    elif sejour['action'] == 'forge':
        if unites is None:
            return False
        forger(general, cle, sejour['unites'], unites, sejour.get('eligibles_forge', ()))
    elif sejour['action'] == 'formation':
        progression.valider_evenement(general, 'formation', cle)
    else:
        # La présence du général ne prouve pas celle des unités : le pilote doit
        # relever séparément leur présence continue, avant toute copie privée.
        if unites is None:
            return False
        registre = soldats.charger()
        for identifiant, preuve in sejour['unites'].items():
            if not preuve or list(unites.get(identifiant, ())) != preuve:
                continue
            valeur = registre.get(identifiant)
            if valeur and not valeur.get('detruit') and valeur.get('dernier_soin') != cle:
                valeur['blessures'] = 0
                valeur['dernier_soin'] = cle
        soldats.sauvegarder(registre)
    donnees['valides'].append(cle)
    del donnees['sejours'][cle]
    sauvegarder(donnees)
    return True


def publier_manuel(repertoire, camp, gid):
    """Document commun administré par le moteur ; aucune création de zone tactique."""
    import os
    from cycle_linux import sans_liens
    import etat
    sans_liens(repertoire)
    repertoire.mkdir(parents=True, exist_ok=True)
    os.chown(repertoire, 0, gid)
    os.chmod(repertoire, 0o750)
    manuel = charger()['manuels'].get(camp, dict.fromkeys(EMPLACEMENTS))
    chemin = repertoire / 'memoire_des_generaux.txt'
    etat.ecrire_prive(chemin, ''.join(f"{place} {manuel[place] or 'vide'}\n" for place in EMPLACEMENTS))
    os.chown(chemin, 0, gid)
    os.chmod(chemin, 0o640)


def preparer_demandes(general):
    for nom in ('ecrire_ses_memoires.txt', 'lire_les_memoires.txt', 'formation_resultat.txt'):
        chemin = general['chemin'] / nom
        if not chemin.exists():
            soldats.ecrire_copie(chemin, '')


def occupants(configuration):
    """Présences dans les bâtiments ; une place partagée en collision est exclue."""
    import generaux
    from cycle_linux import sans_liens
    places = {}
    for joueur in configuration['joueurs']:
        camp = configuration['acteurs'][joueur]['camp']
        for zone in generaux.zones_generaux(joueur, configuration):
            lieu = zone.get('batiment')
            if (zone['position'] in configuration['villages']
                    and zone['chemin'].name == 'reserve'):
                lieu = 'reserve'
            if not lieu:
                continue
            parent = zone['chemin']
            sans_liens(parent)
            if not parent.is_dir():
                continue
            for chemin in parent.iterdir():
                sans_liens(chemin)
                if chemin.is_dir() and generaux.numero_general_depuis_nom(chemin.name) is not None:
                    place = (joueur, chemin.name) if lieu == 'reserve' else zone['emplacement']
                    places.setdefault((zone['position'], camp, place), []).append(
                        dict(joueur=joueur, nom=chemin.name, chemin=chemin,
                             lieu=lieu, camp=camp))
    return [gs[0] for gs in places.values() if len(gs) == 1]


def preuve(chemin):
    infos = chemin.stat()
    return [infos.st_dev, infos.st_ino, infos.st_ctime_ns]


def preuve_general(general):
    if general.get('lieu') == 'reserve':
        # L'arrivée d'un autre général ne rompt pas ce séjour. Le ctime du
        # général détecte sa propre sortie/retour ; l'inode du parent le situe.
        return [*preuve(general['chemin']), *preuve(general['chemin'].parent)[:2]]
    return [*preuve(general['chemin']), *preuve(general['chemin'].parent)]


def relever_unites(general, initialiser=False):
    import config
    import generaux
    from cycle_linux import sans_liens
    registre = soldats.charger()
    resultat = {}
    for bloc in config.ordre_blocs:
        parent = general['chemin'] / bloc
        sans_liens(parent)
        if not parent.is_dir():
            continue
        for unite in parent.iterdir():
            sans_liens(unite)
            type_unite = generaux.identifier_unite(unite)
            if type_unite == 'inconnu':
                continue
            identifiant = soldats.retrouver(unite, registre, config.dans_generation_privee())
            if identifiant is None and initialiser:
                identifiant = soldats.enregistrer(unite, registre, type_unite)
                soldats.publier(unite, identifiant, registre[identifiant])
            if identifiant is not None:
                resultat[identifiant] = preuve(unite)
                if general.get('lieu') == 'forge':
                    for nom in catalogues.UNITES[4]['recette']:
                        fichier = unite / nom
                        sans_liens(fichier)
                        resultat[identifiant].extend(preuve(fichier) if fichier.is_file() else [None])
    if initialiser:
        soldats.sauvegarder(registre)
    return resultat


def unites_forge_validees(configuration, general):
    """Rapproche les inodes vivants de la référence officiellement publiée.

    Ni l'inscription du séjour, ni un UUID copié par le joueur ne prouvent une
    validation antérieure. Le relevé se fait sous gel AVANT la capture privée.
    """
    import etat
    import securite
    reference = etat.charger_unites_actions(configuration) or {'generaux': {}}
    nouveaux = set(reference.get('premiers_deploiements', ()))
    anciennes = {tuple(u) for g in reference['generaux'].values()
                 if g['identifiant'] not in nouveaux
                 for u in g['unites'].values() if u[-1] == 'cavalier'}
    registre = soldats.charger()
    resultat = set()
    identite = f"{general['joueur']}:{general['nom']}"
    for g in securite.inventorier_unites_actions(configuration).values():
        if g['identifiant'] != identite:
            continue
        for relatif, signature in g['unites'].items():
            if tuple(signature) in anciennes:
                identifiant = soldats.retrouver(general['chemin'] / relatif, registre)
                if identifiant is not None:
                    resultat.add(identifiant)
    return resultat


def forger(general, sejour, initiales, finales, eligibles=()):
    """Renomme les soldats validés ; une recette refusée ne détruit rien."""
    import config
    import generaux
    import rapports
    from cycle_linux import sans_liens
    fiche = progression.caracteristiques_general(general)
    if (not fiche or progression.orientation_principale(fiche) != 'instinctif'
            or 104 not in fiche['evolutions_acquises']):
        raise ValueError('Forge refusée : orientation instinctive et technologie 104 requises.')
    registre = soldats.charger()
    transformees = 0
    def refuser(unite, raison):
        rapports.ecrire_rapport_long(
            f"Forge refusée : {general['joueur']}:{general['nom']}, "
            f"{unite.parent.name}/{unite.name} : {raison} ; unité conservée.")

    for bloc in config.ordre_blocs:
        dossier = general['chemin'] / bloc
        if not dossier.is_dir():
            continue
        for unite in sorted(dossier.iterdir()):
            sans_liens(unite)
            if generaux.identifier_unite(unite) != 'cavalier':
                continue
            identifiant = soldats.retrouver(unite, registre, config.dans_generation_privee())
            if identifiant not in eligibles:
                refuser(unite, 'absence de validation officielle au tour précédent')
                continue
            if (identifiant not in initiales or not initiales[identifiant] or
                    initiales[identifiant] != list(finales.get(identifiant, ()))):
                refuser(unite, 'séjour ou recette non constants pendant le tour complet')
                continue
            valide = True
            for nom in catalogues.UNITES[4]['recette']:
                fichier = unite / nom
                sans_liens(fichier)
                if (not fichier.is_file() or not stat.S_ISREG(fichier.stat().st_mode)
                        or fichier.stat().st_nlink != 1):
                    valide = False
            if not valide:
                refuser(unite, 'recette incomplète ou équipement non ordinaire')
                continue
            suffixe = unite.name.removeprefix('cavalerie')
            numero = int(suffixe) if suffixe.isascii() and suffixe.isdecimal() else 1
            destination = dossier / f'cavalerie_L{numero}'
            while destination.exists() or destination.is_symlink():
                numero += 1
                destination = dossier / f'cavalerie_L{numero}'
            unite.rename(destination)
            valeur = registre[identifiant]
            valeur.update(type='cavalerie_lourde', chemin=soldats.cle(destination),
                          device=destination.stat().st_dev, inode=destination.stat().st_ino,
                          forge=sejour)
            soldats.publier(destination, identifiant, valeur)
            transformees += 1
            rapports.ecrire_rapport_court(
                f"Forge : {general['joueur']}:{general['nom']}, {bloc}/{unite.name} "
                f"transformée en {destination.name} ; identité et états conservés.")
    soldats.sauvegarder(registre)
    if not transformees:
        raise ValueError('Forge : aucune cavalerie légère validée au tour précédent avec '
                         'recette et séjour complets ; unités conservées. Voir le rapport long.')


def migrer_ancienne_ecole(configuration):
    """Appelé sous gel uniquement ; ne touche pas les preuves des parties à jour."""
    if any((territoire / joueur / 'ecole_officiers' / place).is_dir() or
           (territoire / joueur / 'ecole_officiers' / place).is_symlink()
           for territoire in configuration['territoires'] if territoire.name in configuration['villages']
           for joueur in configuration['joueurs'] for place in configuration['emplacements_ecole']):
        preparer_emplacements(configuration)


def preparer(configuration):
    """Documents seulement ; les emplacements proviennent des zones communes."""
    import grp
    import generaux
    if configuration['mode'] != 'survie':
        return
    camp = configuration['acteurs'][configuration['joueurs'][0]]['camp']
    gid = grp.getgrnam(configuration['groupes_camps'][camp]).gr_gid
    publier_manuel(configuration['game_path'] / 'village/ecole_officiers', camp, gid)
    for joueur in configuration['joueurs']:
        for zone in generaux.zones_generaux(joueur, configuration):
            if not zone['chemin'].is_dir():
                continue
            for chemin in zone['chemin'].iterdir():
                if chemin.is_dir() and generaux.numero_general_depuis_nom(chemin.name) is not None:
                    preparer_demandes(dict(chemin=chemin))


def ouvrir_tour(configuration, tour):
    """Sous gel, avant ACTIONS : demandes figées et présence initiale officielle."""
    import etat
    from cycle_linux import sans_liens
    donnees = charger()
    if tour in donnees.get('tours_ouverts', []):
        return
    positions = etat.charger_positions_generaux()
    for general in occupants(configuration):
        identite = f"{general['joueur']}:{general['nom']}"
        if positions.get(identite) != 'village':
            continue
        preparer_demandes(general)
        try:
            textes = []
            for nom in ('ecrire_ses_memoires.txt', 'lire_les_memoires.txt'):
                chemin = general['chemin'] / nom
                sans_liens(chemin)
                infos = chemin.stat()
                if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
                    raise ValueError('Une demande doit être un fichier ordinaire sans lien physique.')
                textes.append(chemin.read_text(encoding='utf-8'))
            unites = relever_unites(general, initialiser=True) if general['lieu'] in ('hopital', 'forge') else {}
            eligibles = unites_forge_validees(configuration, general) if general['lieu'] == 'forge' else ()
            commencer_sejour(tour, general, general['lieu'], general['camp'], preuve_general(general),
                             ecrire=textes[0], lire=textes[1], unites=unites, eligibles_forge=eligibles)
        except ValueError as erreur:
            soldats.ecrire_copie(general['chemin'] / 'formation_resultat.txt', str(erreur) + '\n')
    donnees = charger()
    donnees.setdefault('tours_ouverts', []).append(tour)
    sauvegarder(donnees)


def clore_tour(configuration, tour):
    """Sous gel de clôture : relève sans accorder encore soins ni apprentissages."""
    donnees = charger()
    observations = {}
    for general in occupants(configuration):
        identite = f"{general['joueur']}:{general['nom']}"
        observations[identite] = dict(lieu=general['lieu'], camp=general['camp'],
            preuve=preuve_general(general), unites=relever_unites(general))
    donnees.setdefault('clotures', {})[str(tour)] = observations
    sauvegarder(donnees)


def resoudre_tour(configuration, tour):
    """Après l'audit privé : toutes les lectures précèdent toutes les écritures."""
    donnees = charger()
    cloture = donnees.get('clotures', {}).get(str(tour), {})
    presents = {f"{g['joueur']}:{g['nom']}": g for g in occupants(configuration)}
    sejours = [(cle, s) for cle, s in donnees['sejours'].items() if s['tour'] == tour]
    complets = []
    for cle, sejour in sejours:
        general = presents.get(sejour['identite'])
        observation = cloture.get(sejour['identite'])
        if (general and observation and
                (sejour['lieu'], sejour['camp'], sejour['preuve']) ==
                (observation['lieu'], observation['camp'], observation['preuve']) and
                (general['lieu'], general['camp']) == (sejour['lieu'], sejour['camp'])):
            complets.append((cle, sejour))
        else:
            # Une inscription annulée ne concurrence pas une écriture valide.
            donnees['sejours'].pop(cle, None)
            if general:
                soldats.ecrire_copie(general['chemin'] / 'formation_resultat.txt',
                                     'Séjour incomplet : aucune validation.\n')
    if len(complets) != len(sejours):
        sauvegarder(donnees)
    sejours = complets
    places_ecrites = {}
    for cle, sejour in sejours:
        if sejour['action'] == 'ecriture':
            places_ecrites.setdefault((sejour['camp'], sejour['emplacement']), []).append(cle)
    conflits = {cle for cles in places_ecrites.values() if len(cles) > 1 for cle in cles}
    sejours.sort(key=lambda item: (
        {'lecture': 0, 'ecriture': 1, 'soins': 2, 'forge': 3, 'formation': 4}[item[1]['action']], item[0]))
    for cle, sejour in sejours:
        general = presents.get(sejour['identite'])
        observation = cloture.get(sejour['identite'])
        resultat = 'Séjour incomplet : aucune validation.'
        try:
            if cle in conflits:
                raise ValueError('Écritures concurrentes : aucun remplacement ; priorité à définir.')
            if general and observation:
                # Une unité retirée par l'audit ne peut pas être soignée.
                unites_presentes = relever_unites(general)
                unites = {i: p for i, p in observation['unites'].items()
                          if i in unites_presentes}
                if valider_sejour(tour, general, general['lieu'], general['camp'],
                                  observation['preuve'], True, unites):
                    resultat = 'Tour complet validé : ' + sejour['action'] + '.'
        except ValueError as erreur:
            resultat = str(erreur)
        if general:
            soldats.ecrire_copie(general['chemin'] / 'formation_resultat.txt', resultat + '\n')
        restant = charger()
        restant['sejours'].pop(cle, None)
        sauvegarder(restant)
    # Les copies des compteurs seront rafraîchies lors de la publication.
