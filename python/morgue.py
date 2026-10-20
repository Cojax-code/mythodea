"""Morts officielles, généraux zombies et ressources de la Morgue.

Les décisions et leurs identités sont persistées avant leur matérialisation.
Les probabilités et conditions d'ouverture non décidées restent désactivées.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import stat
import uuid

import config
import etat
import progression
import soldats
import unites
aleatoire_resurrection = random.Random()


def charger(c):
    p = c['game_path'] / '.systeme/morgue.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {
        'morts': {}, 'cadavres': {}, 'rituels': {}}


def sauver(c, donnees):
    etat.ecrire_prive(c['game_path'] / '.systeme/morgue.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def zone(c, joueur):
    return c['game_path'] / 'village' / joueur / 'hopital/morgue'


def est_zombie(general):
    return bool((progression.caracteristiques_general(general) or {}).get('etat_zombie'))


def enregistrer_mort(c, general, bataille, aleatoire=None):
    """Une seule décision par identité de général, même si l'appel est rejoué."""
    if c['mode'] != 'survie' or general['joueur'] not in c['joueurs']:
        return False
    cle = f"{general['joueur']}:{general['nom']}"
    d = charger(c)
    if cle in d['morts']:
        return d['morts'][cle]['zombifie']
    probabilite = c.get('probabilite_general_zombie')
    if probabilite is not None and (type(probabilite) not in (float, int) or
                                    not 0 <= probabilite <= 1):
        raise ValueError('Probabilité de général zombie : nombre entre 0 et 1, ou None.')
    fiche = progression.caracteristiques_general(general)
    if fiche is None:
        return False
    tirage = None
    if probabilite is not None:
        tirage = (aleatoire_resurrection if aleatoire is None else aleatoire).random()
    reanime = tirage is not None and tirage < probabilite
    mort = dict(joueur=general['joueur'], general=general['nom'], bataille=bataille,
                historique=deepcopy(fiche), probabilite=probabilite, tirage=tirage,
                zombifie=reanime, nouveau_general=None, materialise=False)
    if reanime:
        mort['cadavre'] = uuid.uuid4().hex
        d['cadavres'][mort['cadavre']] = dict(joueur=general['joueur'], origine=cle,
                                           consomme_par=None)
    d['morts'][cle] = mort
    sauver(c, d)
    return reanime


def preparer(c):
    """Ouvre la Morgue uniquement selon une règle administrativement définie."""
    import grp
    import pwd
    from cycle_linux import sans_liens
    if c['mode'] != 'survie' or c.get('acces_morgue') != 'premiere_apparition':
        return
    d = charger(c)
    for joueur in c['joueurs']:
        if not any(m['joueur'] == joueur and m['zombifie'] for m in d['morts'].values()):
            continue
        uid = pwd.getpwnam(c['acteurs'][joueur]['proprietaire_linux']).pw_uid
        gid = grp.getgrnam(c['acteurs'][joueur]['groupe_linux']).gr_gid
        for nom in ('', 'generaux', 'cadavres', 'rituels'):
            dossier = zone(c, joueur) / nom
            sans_liens(dossier)
            dossier.mkdir(parents=True, exist_ok=True)
            os.chown(dossier, uid, gid)
            os.chmod(dossier, 0o700)


def materialiser(c):
    """Exclusivement dans la résolution privée ; les identités sont réservées."""
    import generaux
    if c['mode'] != 'survie':
        return
    d = charger(c)
    for cle, mort in d['morts'].items():
        if not mort['zombifie'] or mort['materialise']:
            continue
        if c.get('acces_morgue') != 'premiere_apparition':
            continue
        joueur = mort['joueur']
        if mort['nouveau_general'] is None:
            numero = etat.lire_compteur_general(joueur) + 1
            mort['nouveau_general'] = f'general{numero}'
            # Une interruption peut laisser un numéro réservé, jamais le recycler.
            sauver(c, d)
        nom = mort['nouveau_general']
        numero = generaux.numero_general_depuis_nom(nom)
        etat.sauvegarder_compteur_general(joueur, max(numero, etat.lire_compteur_general(joueur)))
        preparer(c)
        chemin = zone(c, joueur) / 'generaux' / nom
        generaux.creer_general(chemin, nom)
        fiches = progression.charger()
        fiches[cle]['mort'] = True
        historique = deepcopy(mort['historique'])
        historique.update(etat_zombie=True, origine_zombie=cle, mort=False)
        fiches[f'{joueur}:{nom}'] = historique
        progression.sauvegarder(fiches)
        progression.publier_fiche(chemin, historique)
        generaux.donner_permissions_general(chemin, c['acteurs'][joueur]['proprietaire_linux'])
        cadavre = zone(c, joueur) / 'cadavres' / ('cadavre_' + mort['cadavre'])
        from cycle_linux import sans_liens
        sans_liens(cadavre)
        texte = mort['cadavre'] + '\n'
        if not cadavre.exists():
            cadavre.write_text(texte, encoding='utf-8')
        elif not cadavre.is_file() or cadavre.read_text(encoding='utf-8') != texte:
            raise RuntimeError('Cadavre réservé altéré ; récupération administrative requise.')
        proprietaire = chemin.stat()
        os.chown(cadavre, proprietaire.st_uid, proprietaire.st_gid)
        os.chmod(cadavre, 0o400)
        infos = cadavre.stat()
        d['cadavres'][mort['cadavre']].update(device=infos.st_dev, inode=infos.st_ino)
        positions = etat.charger_positions_generaux()
        positions.pop(cle, None)
        positions[f'{joueur}:{nom}'] = 'village'
        etat.sauvegarder_positions_generaux(positions)
        mort['materialise'] = True
        sauver(c, d)


def authentifier_rituel(c, joueur, general, bloc, identifiant, dossier):
    """Contrôle vivant sous gel, avant la copie qui détruit les preuves d'inode."""
    from cycle_linux import sans_liens
    d = charger(c)
    ressource = d['cadavres'].get(identifiant)
    if (not ressource or ressource['joueur'] != joueur or ressource['consomme_par'] or
            general['joueur'] != joueur or not est_zombie(general) or bloc not in config.ordre_blocs):
        raise ValueError('Cadavre ou général zombie non autorisé.')
    attendu = zone(c, joueur) / 'rituels' / general['nom'] / bloc / identifiant
    if dossier != attendu:
        raise ValueError('Rattachement du rituel incorrect.')
    source = zone(c, joueur) / 'cadavres' / ('cadavre_' + identifiant)
    lien = dossier / 'reliques/coeur_necrotique'
    ame = dossier / 'rituel/ame'
    for p in (source, lien, ame.parent):
        sans_liens(p)
    original, physique = source.lstat(), lien.lstat()
    if (not stat.S_ISREG(original.st_mode) or not stat.S_ISREG(physique.st_mode) or
            (original.st_dev, original.st_ino) != (ressource.get('device'), ressource.get('inode')) or
            (original.st_dev, original.st_ino) != (physique.st_dev, physique.st_ino) or
            original.st_nlink != 2 or source.read_text(encoding='utf-8') != identifiant + '\n'):
        raise ValueError('Le lien physique ne correspond pas au cadavre officiel unique.')
    if not ame.is_symlink() or os.readlink(ame) != '../reliques/coeur_necrotique':
        raise ValueError('Lien symbolique relatif vers la relique requis.')
    if (set(p.name for p in dossier.iterdir()) != {'reliques', 'rituel'} or
            set(p.name for p in lien.parent.iterdir()) != {'coeur_necrotique'} or
            set(p.name for p in ame.parent.iterdir()) != {'ame'}):
        raise ValueError('Références supplémentaires dans le rituel.')
    return dict(joueur=joueur, general=general['nom'], bloc=bloc, cadavre=identifiant,
                device=original.st_dev, inode=original.st_ino)


def actualiser_cadavres(c):
    """Après publication contrôlée uniquement : la copie a de nouveaux inodes."""
    d = charger(c)
    for identifiant, valeur in d['cadavres'].items():
        p = zone(c, valeur['joueur']) / 'cadavres' / ('cadavre_' + identifiant)
        if not valeur['consomme_par'] and p.is_file():
            from cycle_linux import sans_liens
            sans_liens(p)
            if p.read_text(encoding='utf-8') != identifiant + '\n':
                raise RuntimeError('Cadavre publié altéré.')
            infos = p.stat()
            valeur.update(device=infos.st_dev, inode=infos.st_ino)
    if d['cadavres']:
        sauver(c, d)


def consommer_rituel(c, preuve, general):
    """La preuve vient du gel, jamais d'un fichier détenu par le joueur."""
    d = charger(c)
    identifiant = preuve['cadavre']
    ressource = d['cadavres'].get(identifiant)
    if (not ressource or not est_zombie(general) or
            (preuve['joueur'], preuve['general']) != (general['joueur'], general['nom']) or
            (preuve['device'], preuve['inode']) != (ressource['device'], ressource['inode'])):
        raise ValueError('Preuve de rituel invalide.')
    if ressource['consomme_par']:
        destination = general['chemin'] / preuve['bloc'] / ('Trop_gros_zombie_' + identifiant)
        if not destination.is_dir():
            raise RuntimeError('Rituel déjà consommé sans unité présente : vérifier la génération, sans rejeu.')
        return False
    import generaux
    if unites.occupation(generaux.lire_composition_general(general['chemin'])) + 10 > config.max_unites_par_general:
        raise ValueError('Dix places libres sont nécessaires au Trop gros zombie.')
    destination = general['chemin'] / preuve['bloc'] / ('Trop_gros_zombie_' + identifiant)
    # Réserver d'abord la ressource : jamais de seconde unité après interruption.
    ressource['consomme_par'] = soldats.cle(destination)
    sauver(c, d)
    unites.creer_officielle(destination, 'Trop_gros_zombie', {'cadavre': identifiant})
    source = zone(c, general['joueur']) / 'cadavres' / ('cadavre_' + identifiant)
    source.unlink(missing_ok=True)
    return True


def relever_rituels(c, tour):
    """Capture des preuves Linux ; les exercices restent hors copie de partie."""
    import generaux
    from cycle_linux import sans_liens
    d = charger(c)
    preuves = []
    for joueur in c['joueurs']:
        racine = zone(c, joueur) / 'rituels'
        sans_liens(racine)
        if not racine.is_dir():
            continue
        for dossier_general in sorted(racine.iterdir()):
            sans_liens(dossier_general)
            if not dossier_general.is_dir() or generaux.numero_general_depuis_nom(dossier_general.name) is None:
                continue
            position, chemin = generaux.trouver_position_general(joueur, dossier_general.name, c)
            if chemin is None or position != 'village':
                continue
            general = dict(joueur=joueur, nom=dossier_general.name, chemin=chemin)
            for bloc in config.ordre_blocs:
                parent = dossier_general / bloc
                sans_liens(parent)
                if not parent.is_dir():
                    continue
                for rituel in sorted(parent.iterdir()):
                    sans_liens(rituel)
                    if not rituel.is_dir():
                        continue
                    try:
                        preuve = authentifier_rituel(c, joueur, general, bloc, rituel.name, rituel)
                    except (OSError, ValueError, RuntimeError) as erreur:
                        import rapports
                        rapports.ecrire_rapport_long(f'Morgue : rituel refusé pour {joueur}:{general["nom"]} : {erreur}')
                    else:
                        preuves.append(preuve)
    if preuves or d['morts']:
        d['rituels'] = dict(tour=tour, preuves=preuves)
        sauver(c, d)


def convertir_deplacements(c):
    """Un déplacement d'inode depuis une unité publiée conserve son identité.

    Les transferts restent internes au territoire, entre deux généraux du même
    joueur. Les copies et changements de territoire ne prouvent pas un mv.
    """
    import generaux
    import securite
    reference = etat.charger_unites_actions(c)
    if reference is None or 'capture' not in reference:
        return 0
    origines = {}
    for ancien in reference['generaux'].values():
        for relatif, preuve in ancien['unites'].items():
            if preuve[-1] in ('archer', 'piquier', 'cavalier'):
                origines[tuple(preuve)] = (ancien, relatif, preuve[-1])
    registre = soldats.charger()
    converties = 0
    for cle, actuel in reference['capture'].items():
        joueur, nom = actuel['identifiant'].split(':')
        general = dict(joueur=joueur, nom=nom, chemin=securite.chemin_general_actions(cle, c))
        if not general['chemin'].is_dir() or not est_zombie(general):
            continue
        for relatif, preuve in actuel['unites'].items():
            origine = origines.get(tuple(preuve))
            if origine is None:
                continue
            ancien, ancien_relatif, type_origine = origine
            if (ancien['identifiant'] == actuel['identifiant'] or
                    ancien['identifiant'].split(':')[0] != joueur or
                    ancien['position'] != actuel['position']):
                continue
            unite = general['chemin'] / relatif
            if not unite.is_dir():
                continue
            identifiant = soldats.retrouver(unite, registre, config.dans_generation_privee())
            valeur = registre.get(identifiant)
            if not valeur or valeur.get('detruit') or valeur['type'] != type_origine:
                continue
            # Une seconde copie revendiquant la même identité empêche la conversion.
            copies = [p for zone_general in generaux.zones_generaux(joueur, c)
                      if zone_general['chemin'].is_dir()
                      for p in zone_general['chemin'].glob('general*/*/*/identifiant_soldat.txt')
                      if p.is_file() and not p.is_symlink() and p.read_text(encoding='utf-8').strip() == identifiant]
            if len(copies) != 1:
                continue
            destination = unite.parent / ('zombi_' + identifiant)
            if destination.exists():
                raise RuntimeError('Destination zombie déjà occupée.')
            unite.rename(destination)
            valeur.update(type='zombie', chemin=soldats.cle(destination),
                          device=destination.stat().st_dev, inode=destination.stat().st_ino,
                          origine_officielle={'conversion': ancien['identifiant'], 'tour': reference['tour']})
            # Ni batailles, ni blessures, ni statuts ne sont réinitialisés.
            soldats.sauvegarder(registre)
            soldats.publier(destination, identifiant, valeur)
            converties += 1
    return converties


def resoudre_rituels(c, tour):
    import generaux
    d = charger(c)
    demandes = d.get('rituels', {})
    if demandes.get('tour') != tour:
        return
    for preuve in demandes.get('preuves', []):
        position, chemin = generaux.trouver_position_general(preuve['joueur'], preuve['general'], c)
        if chemin is None or position != 'village':
            continue
        general = dict(joueur=preuve['joueur'], nom=preuve['general'], chemin=chemin)
        try:
            consommer_rituel(c, preuve, general)
        except ValueError as erreur:
            import rapports
            rapports.ecrire_rapport_long(f'Morgue : {erreur}')
