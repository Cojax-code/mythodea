"""État privé des soldats et copies lisibles dans leurs dossiers individuels."""
import json
import os
from pathlib import Path
import random
import stat
import uuid
from contextlib import contextmanager
from contextvars import ContextVar


_participants = ContextVar('soldats_bataille_complete', default=None)


@contextmanager
def bataille_complete(identifiant=None):
    """Une résolution territoriale ; les duels n'incrémentent aucun compteur."""
    participants = set()
    jeton = _participants.set(participants)
    try:
        yield
        if participants:
            terminer_bataille(participants, identifiant or 'classique:' + uuid.uuid4().hex)
    finally:
        _participants.reset(jeton)


def participer(general):
    import generaux
    participants = _participants.get()
    if participants is not None:
        for bloc in generaux.lire_blocs_general(general['chemin']).values():
            participants.update(bloc['unites'])


def limite_blessures(batailles):
    return 3 if batailles >= 10 else 2 if batailles >= 5 else 1


def charger():
    import config
    chemin = config.racine_metier() / '.systeme/soldats.json'
    return json.loads(chemin.read_text(encoding='utf-8')) if chemin.exists() else {}


def sauvegarder(donnees):
    import config
    import etat
    etat.ecrire_prive(config.racine_metier() / '.systeme/soldats.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def ecrire_copie(chemin, texte):
    """Copie de consultation, jamais l'autorité des blessures ou des soins."""
    for p in (chemin, *chemin.parents):
        if p.is_symlink():
            raise RuntimeError(f'Métadonnée de soldat liée : {chemin}')
    if chemin.exists() and (not stat.S_ISREG(chemin.stat().st_mode) or chemin.stat().st_nlink != 1):
        raise RuntimeError(f'Métadonnée de soldat non ordinaire : {chemin}')
    parent = chemin.parent.stat()
    fd = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as fichier:
        fichier.write(texte)
    os.chown(chemin, parent.st_uid, parent.st_gid)
    os.chmod(chemin, 0o600)


def publier(unite, identifiant, donnees):
    ecrire_copie(unite / 'identifiant_soldat.txt', identifiant + '\n')
    ecrire_copie(unite / 'batailles_survecues.txt', str(donnees['batailles']) + '\n')
    ecrire_copie(unite / 'blessures.txt', str(donnees['blessures']) + '\n')
    for nom, seuil in (('veteran', 5), ('heroique', 10)):
        marqueur = unite / nom
        if donnees['batailles'] >= seuil:
            ecrire_copie(marqueur, '')
        elif marqueur.exists() or marqueur.is_symlink():
            if marqueur.is_dir() and not marqueur.is_symlink():
                raise RuntimeError(f'Marqueur de statut non ordinaire : {marqueur}')
            marqueur.unlink()


def marqueur(unite):
    chemin = unite / 'identifiant_soldat.txt'
    if chemin.is_symlink():
        raise RuntimeError('Identifiant de soldat lié interdit.')
    return chemin.read_text(encoding='utf-8').strip() if chemin.is_file() else None


def cle(unite):
    import config
    root = config.racine_metier()
    if unite.is_relative_to(root):
        return 'game/' + unite.relative_to(root).as_posix()
    for joueur in config.joueurs:
        home = config.home_generation(joueur) or Path('/home') / joueur
        if unite.is_relative_to(home):
            return f'home/{joueur}/' + unite.relative_to(home).as_posix()
    # API isolées : leur chemin absolu demeure privé dans le registre de test.
    return unite.as_posix()


def enregistrer(unite, donnees, type_unite):
    infos = unite.stat()
    identifiant = uuid.uuid4().hex
    donnees[identifiant] = dict(batailles=0, blessures=0, derniere_bataille=None, batailles_comptees=[],
                               type=type_unite, chemin=cle(unite), device=infos.st_dev, inode=infos.st_ino)
    return identifiant


def retrouver(unite, donnees, generation_privee=False):
    infos = unite.stat()
    for identifiant, valeur in donnees.items():
        if not valeur.get('detruit') and (valeur['device'], valeur['inode']) == (infos.st_dev, infos.st_ino):
            return identifiant
    # Pendant les calculs, la capture a déjà vérifié les identités originales.
    if generation_privee:
        identifiant = marqueur(unite)
        if identifiant in donnees and not donnees[identifiant].get('detruit'):
            return identifiant
    return None


def synchroniser(configuration, publication=False):
    """Sous gel : authentifie les métadonnées avant copie, ou lie les nouveaux inodes.

    Le bit publication n'est destiné qu'à la copie terminée et contrôlée par le
    moteur. Les fichiers utilisateur ne peuvent jamais déclarer ce contexte.
    """
    import config
    import generaux
    from cycle_linux import sans_liens
    donnees = charger()
    if not donnees:
        return
    presents = set()
    observations = []
    for joueur in configuration['acteurs']:
        for zone in generaux.zones_generaux(joueur, configuration):
            parent = zone['chemin']
            if not parent.is_dir():
                continue
            for general in parent.iterdir():
                if not general.is_dir() or generaux.numero_general_depuis_nom(general.name) is None:
                    continue
                for bloc in config.ordre_blocs:
                    if not (general / bloc).is_dir():
                        continue
                    for unite in (general / bloc).iterdir():
                        sans_liens(unite)
                        type_unite = generaux.identifier_unite(unite)
                        if type_unite == 'inconnu':
                            continue
                        observations.append((unite, type_unite,
                                             retrouver(unite, donnees, publication)))
    # Les identités reconnues par inode passent avant les copies revendiquant le
    # même marqueur : une copie ne peut jamais guérir l'original ou lui voler son état.
    observations.sort(key=lambda observation: observation[2] is None)
    for unite, type_unite, identifiant in observations:
        candidat = marqueur(unite)
        infos = unite.stat()
        if identifiant is None:
            ancien = donnees.get(candidat)
            if (ancien and not ancien.get('detruit') and candidat not in presents
                    and ancien['device'] != infos.st_dev and ancien['type'] == type_unite):
                identifiant = candidat
            elif ancien:
                # Une copie ne reçoit aucun statut de l'original. Les effectifs,
                # identités de généraux et sanctions restent soumis à l'audit commun.
                identifiant = enregistrer(unite, donnees, type_unite)
        if identifiant in presents:
            identifiant = enregistrer(unite, donnees, type_unite)
        if identifiant is None:
            # Les mêmes generalN existent chez plusieurs joueurs : le nom seul
            # ne permet jamais de conclure à un déplacement entre systèmes de fichiers.
            identite_general = unite.parent.parent.name
            joueur = next((p.name for p in unite.parents if p.name in configuration['acteurs']), None)
            if any(i not in presents and not v.get('detruit') and v['type'] == type_unite and
                   v['device'] != infos.st_dev and identite_general in Path(v['chemin']).parts
                   and joueur in Path(v['chemin']).parts
                   for i, v in donnees.items()):
                raise RuntimeError('Transfert sans identité de soldat : récupération explicite requise.')
            continue
        presents.add(identifiant)
        valeur = donnees[identifiant]
        infos = unite.stat()
        valeur.update(chemin=cle(unite), device=infos.st_dev, inode=infos.st_ino)
        publier(unite, identifiant, valeur)
    # Garder les soldats absents pour ne jamais accepter un ancien état comme neuf.
    sauvegarder(donnees)


def pertes(infos, survivants, moral=0, aleatoire=None):
    """Sélection collective puis sauvetages distincts, sans réattribuer un échec."""
    import config
    import generaux
    import shutil
    aleatoire = random if aleatoire is None else aleatoire
    if type(moral) is not int or not 0 <= moral <= 100:
        raise ValueError('Moral entier de 0 à 100 requis.')
    nombre_pertes = infos['nombre'] - survivants
    if nombre_pertes <= 0:
        return []
    perdus = aleatoire.sample(infos['unites'], nombre_pertes)
    tentatives = aleatoire.sample(perdus, nombre_pertes * moral // 100) if moral else []
    donnees = charger()
    supprimes = []
    for unite in perdus:
        identifiant = retrouver(unite, donnees, config.dans_generation_privee())
        if identifiant is None and unite in tentatives:
            identifiant = enregistrer(unite, donnees, generaux.identifier_unite(unite))
        valeur = donnees.get(identifiant)
        if unite in tentatives and valeur['blessures'] < limite_blessures(valeur['batailles']):
            valeur['blessures'] += 1
            publier(unite, identifiant, valeur)
        else:
            supprimes.append(f"{unite.name} ({infos['type']})")
            shutil.rmtree(unite)
            if valeur is not None:
                valeur['detruit'] = True
    if donnees:
        sauvegarder(donnees)
    infos['unites'] = [u for u in infos['unites'] if u.exists()]
    infos['nombre'] = len(infos['unites'])
    return supprimes


def terminer_bataille(unites, identifiant_bataille):
    """Le pilote fournit une identité de bataille complète, stable à la reprise."""
    import config
    import generaux
    if not identifiant_bataille:
        raise ValueError('Identifiant de bataille complète requis.')
    donnees = charger()
    for unite in set(unites):
        if not unite.is_dir():
            continue
        identifiant = retrouver(unite, donnees, config.dans_generation_privee())
        if identifiant is None:
            identifiant = enregistrer(unite, donnees, generaux.identifier_unite(unite))
        valeur = donnees[identifiant]
        if identifiant_bataille not in valeur.setdefault('batailles_comptees', []):
            valeur['batailles'] += 1
            valeur['derniere_bataille'] = identifiant_bataille
            valeur['batailles_comptees'].append(identifiant_bataille)
        publier(unite, identifiant, valeur)
    sauvegarder(donnees)
