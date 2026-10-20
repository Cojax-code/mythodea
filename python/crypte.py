"""Crypte V0.1 : décisions privées, recettes et récompenses différées.

Le scanner est un instrument pédagogique non fiable. Seul ce module attribue
une réussite et seul le résolveur privé matérialise son général.
"""
from contextlib import contextmanager
import grp
import json
import os
from pathlib import Path
import pwd
import re
import random
import shlex
import shutil
import socket
import stat
import struct
import threading
import time
import uuid

import config
import etat

RECETTE = ('mkdir appel', 'touch appel/cavalerie', 'cp appel/cavalerie appel/offrande',
           'mv appel/offrande appel/poulin')
NOM = 'ame_et_lie_poulin'
RECETTE2 = ('lsblk > a.txt', 'cat a.txt', 'cat a.txt | grep "NAME"', 'grep "NAME" a.txt')
RECETTE3 = ('touch rempart', 'ls -l rempart', 'chmod 660 rempart',
            'ls -l rempart', 'chmod 600 rempart', 'ls -l rempart')
RECETTES = {
    'recette1': {'lignes': RECETTE, 'nom': NOM, 'blocs': (10, 5, 5, 0),
                 'unite': 'cavalerie', 'equipement': 'cheval'},
    'recette2': {'lignes': RECETTE2, 'nom': 'har-chez-moi', 'blocs': (0, 0, 0, 20),
                 'unite': 'infanterie', 'equipement': 'arc'},
    'recette3': {'lignes': RECETTE3, 'nom': 'pic-nic', 'blocs': (6, 7, 7, 0),
                 'unite': 'infanterie', 'equipement': 'pique'},
}

# Textes originaux installés par le moteur. Ne pas les générer à chaque tour :
# les numéros donnés par nl font partie des recettes reproductibles.
LIVRES = {
    'orc_assaillant': '\n'.join((
        'Le registre des portes de terre',
        'Sous les plaines, les anciens tenaient le compte des saisons.',
        'Un orc_assaillant grava son nom dans le registre du village.',
        'Il portait sept pierres quand il ouvrait la marche.',
        'Sur les flancs il en gardait six, pour laisser une main libre.',
        'Ses compagnons comptaient ensemble leurs forces et leurs absents.',
        'La nuit venue, le chaman relisait le registre près du feu.',
        'Aucune page ne promettait une victoire sans retour.')) + '\n',
    'orc_archer': '\n'.join((
        'Le carnet des roseaux',
        'Un orc_archer suivait le vent depuis les collines.',
        'Le premier orc_archer tailla une flèche dans un roseau.',
        'La rivière conservait le reflet des sentinelles.',
        'Chaque orc_archer inscrivait une ligne avant de partir.',
        'Un jeune orc_archer confondit le nord avec son ombre.',
        'La vieille cartographe lui prêta sa boussole.',
        'Cet orc_archer apprit à compter les tours de garde.',
        'Le soir, un orc_archer retrouva le carnet perdu.',
        'Son voisin orc_archer y ajouta le nom des absents.',
        'Tous les roseaux ne deviennent pas des flèches.',
        'Le dernier orc_archer referma le livre sans arracher de page.')) + '\n',
    'orc_chaman': '\n'.join((
        'Les cinq braises',
        'Une braise pour la terre qui porte le camp.',
        'Une braise pour les noms que personne ne prononce.',
        'Une braise pour la main qui soigne après la bataille.',
        'Une braise pour le silence avant le chant.',
        'Une braise pour les vivants qui rentreront demain.',
        'Le chaman savait lire les premières lignes sans brûler les suivantes.',
        'Il conservait les chants dans un tome à couverture de bois.',
        'Les archers écoutaient, mais son chant ne tirait aucune flèche.',
        'Au matin, les cinq braises avaient laissé cinq cercles de cendre.',
        'Le registre restait ouvert pour ceux qui reviendraient.')) + '\n',
}


def lignes_orc_archer():
    # Aucun blanc dans ce livre : nl par défaut et la numérotation physique
    # coïncident. Toutes les occurrences sont acceptées, pas seulement la première.
    return {n for n, ligne in enumerate(LIVRES['orc_archer'].splitlines(), 1)
            if 'orc_archer' in ligne}


def preparer_bibliotheque(c):
    from cycle_linux import sans_liens
    for joueur in c['joueurs']:
        dossier = c['game_path'] / 'village' / joueur / 'hotel_de_ville/bibliotheque'
        sans_liens(dossier)
        dossier.mkdir(parents=True, exist_ok=True)
        gid = grp.getgrnam(c['acteurs'][joueur]['groupe_linux']).gr_gid
        os.chown(dossier, 0, gid)
        os.chmod(dossier, 0o750)
        for nom, texte in LIVRES.items():
            livre = dossier / f'tome_du_{nom}'
            sans_liens(livre)
            if livre.exists() and (not livre.is_file() or livre.stat().st_nlink != 1):
                raise RuntimeError('Livre de bibliothèque non ordinaire.')
            if not livre.exists() or livre.read_text(encoding='utf-8') != texte:
                etat.ecrire_prive(livre, texte)
            os.chown(livre, 0, gid)
            os.chmod(livre, 0o640)


def commandes_etape(ligne):
    # Seul ce pipeline précis est une étape autorisée, sans interpréteur Python.
    return ('cat a.txt', 'grep "NAME"') if ligne == RECETTE2[2] else (ligne,)


def site(c):
    return c.get('crypte_site', 'crypte')


def contexte_plaines(c):
    return dict(c, crypte_site='crypte_des_plaines')


def chemin_etat(c):
    return c['game_path'] / '.systeme' / (site(c) + '.json')


def catalogue(c, joueur='j1'):
    if site(c) == 'crypte':
        return RECETTES
    racine = c.get('game_public_path', config.game_public_path)
    bibliotheque = racine / 'village' / joueur / 'hotel_de_ville/bibliotheque'
    resultat = {
        'sauvageon': dict(nom='sauvageon', evolution=105,
            lignes=('mkdir sauvageon', 'vi sauvageon/sauvageon.txt', '{bloc}')),
    }
    for nom, evolution in (('orc_assaillant', 107), ('orc_archer', 108), ('orc_chaman', 109)):
        tome = f'tome_du_{nom}'
        lecture = (f'du -h {tome}',) if nom == 'orc_assaillant' else (
            (f'nl {tome}', 'pwd', '{ligne}') if nom == 'orc_archer' else
            (f'head {tome}', 'pwd', f'head -n 5 {tome}'))
        resultat[nom] = dict(nom=nom, evolution=evolution,
            lignes=('pwd', f'cp {shlex.quote(str(bibliotheque / tome))} {tome}',
                    'pwd', *lecture, 'pwd', '{bloc}'))
    return resultat


def correspond_etape(attendu, ligne):
    if attendu == '{bloc}':
        return any(ligne == f'echo {bloc} > bloc.txt' for bloc in config.ordre_blocs)
    if attendu == '{ligne}':
        return any(ligne == f'echo {numero} > ligne.txt' for numero in lignes_orc_archer())
    return attendu == ligne


def verifier_plaines(c, joueur, recette, lignes):
    """Complète la preuve des commandes ; ne la remplace jamais."""
    def lire(fd, nom):
        fichier = os.open(nom, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(fichier, 'r', encoding='utf-8') as entree:
            infos = os.fstat(entree.fileno())
            if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1 or infos.st_size > 65536:
                raise ValueError('Objet de recette non ordinaire ou trop grand.')
            return entree.read()
    with dossier_atelier(c, joueur) as fd:
        bloc = lire(fd, 'bloc.txt').strip()
        if bloc not in config.ordre_blocs or lignes[-1] != f'echo {bloc} > bloc.txt':
            raise ValueError('Bloc différent de la commande observée.')
        if recette == 'sauvageon':
            if set(os.listdir(fd)) != {'sauvageon', 'bloc.txt'}:
                raise ValueError('Atelier différent de la recette.')
            sous = os.open('sauvageon', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                if set(os.listdir(sous)) != {'sauvageon.txt'}:
                    raise ValueError('Dossier Sauvageon différent de la recette.')
                if lire(sous, 'sauvageon.txt').splitlines() != ['boueux', 'et', 'crasseux']:
                    raise ValueError('Texte du Sauvageon incorrect.')
            finally:
                os.close(sous)
        else:
            tome = f'tome_du_{recette}'
            attendus = {tome, 'bloc.txt'} | ({'ligne.txt'} if recette == 'orc_archer' else set())
            if set(os.listdir(fd)) != attendus or lire(fd, tome) != LIVRES[recette]:
                raise ValueError('Livre différent de la bibliothèque officielle.')
            if recette == 'orc_archer':
                numero = lire(fd, 'ligne.txt').strip()
                if (not numero.isascii() or not numero.isdecimal() or
                        int(numero) not in lignes_orc_archer() or
                        f'echo {numero} > ligne.txt' not in lignes):
                    raise ValueError('Ligne orc_archer incorrecte ou non observée.')
    return bloc


def verifier_connaissance_plaines(c, joueur, evolution):
    """L'autorité est la progression privée, jamais la fiche copiée du joueur."""
    import progression
    general = destinataire_plaines(c, joueur)
    fiche = progression.caracteristiques_general(general)
    if not fiche or fiche.get('etat_zombie') or evolution not in fiche['evolutions_acquises']:
        raise ValueError('Le général présent ne possède pas personnellement cette connaissance.')
    return general


def destinataire_plaines(c, joueur):
    import generaux
    from cycle_linux import sans_liens
    presents = []
    for j in c['joueurs']:
        parent = c['game_path'] / 'est_1/crypte_des_plaines/1' / j
        sans_liens(parent)
        if parent.is_dir():
            for p in parent.iterdir():
                sans_liens(p)
                if p.is_dir() and generaux.numero_general_depuis_nom(p.name) is not None:
                    presents.append(dict(joueur=j, nom=p.name, chemin=p))
    if len(presents) != 1 or presents[0]['joueur'] != joueur:
        raise ValueError('Un seul général du joueur doit occuper la place commune de la Crypte des plaines.')
    g = presents[0]
    if f"{joueur}:{g['nom']}" not in etat.charger_positions_generaux():
        raise ValueError('Général destinataire non officiel.')
    return g


VERROU = threading.RLock()
SERVICES = {}
random_livraison = random.Random()


def charger(c):
    p = chemin_etat(c)
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return {j: {'dernier_tour': None, 'a_creer': None, 'en_attente': None,
                'attributions': []} for j in c['joueurs']}


def sauver(c, donnees):
    etat.ecrire_prive(chemin_etat(c),
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def zone(c, joueur):
    territoire = 'village' if site(c) == 'crypte' else 'est_1'
    return c['game_path'] / territoire / joueur / site(c)


def configuration(c):
    p = c['game_path'] / '.systeme/crypte_config.json'
    if not p.exists():
        etat.ecrire_prive(p, json.dumps({'debut': 'crypte_commence', 'fin': 'crypte_fin'}))
    resultat = json.loads(p.read_text(encoding='utf-8'))
    for valeur in resultat.values():
        if not isinstance(valeur, str) or not re.fullmatch(r'crypte_[a-zA-Z0-9_]+', valeur):
            raise ValueError('Marqueur Crypte invalide (préfixe crypte_ requis).')
    if set(resultat) != {'debut', 'fin'} or resultat['debut'] == resultat['fin']:
        raise ValueError('Deux marqueurs Crypte distincts sont requis.')
    return resultat


def preparer(c):
    """Structure uniquement : ne crée jamais une récompense sur le plateau vivant."""
    if c['mode'] != 'survie':
        return
    from cycle_linux import sans_liens
    preparer_bibliotheque(c)
    if site(c) == 'crypte_des_plaines':
        import formation
        formation.preparer_emplacements(c, migrer=False)
    for j in c['joueurs']:
        acteur = c['acteurs'][j]
        uid = pwd.getpwnam(acteur['proprietaire_linux']).pw_uid
        gid = grp.getgrnam(acteur['groupe_linux']).gr_gid
        for nom in ('', 'atelier', 'recompense', 'grimoire'):
            p = zone(c, j) / nom
            sans_liens(p)
            p.mkdir(parents=True, exist_ok=True)
            os.chown(p, 0 if nom == 'grimoire' else uid, gid)
            os.chmod(p, 0o750 if nom == 'grimoire' else 0o700)
        for identifiant in catalogue(c, j):
            pdf = zone(c, j) / f'grimoire/{identifiant}.pdf'
            sans_liens(pdf)
            contenu = recette_pdf(configuration(c), identifiant,
                                  c.get('game_public_path', config.game_public_path), c, j)
            if not pdf.exists() or pdf.read_bytes() != contenu:
                # Source installée avec le moteur ; aucun contenu fourni par le joueur.
                temporaire = pdf.with_suffix('.nouveau')
                sans_liens(temporaire)
                fd = os.open(temporaire, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
                try:
                    with os.fdopen(fd, 'wb') as fichier:
                        fichier.write(contenu)
                        fichier.flush()
                        os.fsync(fichier.fileno())
                    temporaire.replace(pdf)
                finally:
                    temporaire.unlink(missing_ok=True)
            os.chown(pdf, 0, gid)
            os.chmod(pdf, 0o640)
        etat.initialiser_quota_normal(j)
    configuration(c)
    if not chemin_etat(c).exists():
        sauver(c, charger(c))
    if site(c) == 'crypte':
        preparer(contexte_plaines(c))


@contextmanager
def dossier_atelier(c, j):
    """Ancre chaque composant : un renommage concurrent ne redirige pas le fd."""
    fd = os.open(c['game_path'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for nom in (*zone(c, j).relative_to(c['game_path']).parts, 'atelier'):
            suivant = os.open(nom, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = suivant
        yield fd
    finally:
        os.close(fd)


def nettoyer(c, j):
    atelier = zone(c, j) / 'atelier'
    if not atelier.exists() and not atelier.is_symlink():
        return
    if os.name != 'posix':
        # Les tests Windows n'ont pas de joueurs Unix concurrents.
        if atelier.is_symlink():
            raise RuntimeError('Atelier lié interdit.')
        for p in atelier.iterdir():
            if p.is_symlink() or not p.is_dir():
                p.unlink()
            else:
                shutil.rmtree(p)
        return
    with dossier_atelier(c, j) as fd:
        for nom in os.listdir(fd):
            infos = os.stat(nom, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(infos.st_mode):
                shutil.rmtree(nom, dir_fd=fd)
            else:
                os.unlink(nom, dir_fd=fd)


def recette_pdf(marqueurs, identifiant="recette1", racine=None, contexte=None, joueur='j1'):
    """PDF une page sans dépendance : texte sélectionnable pour SCP/SFTP."""
    racine = (config.game_public_path if racine is None else racine).as_posix()
    recette = catalogue(contexte, joueur)[identifiant] if contexte else RECETTES[identifiant]
    explications = [
        'mkdir cree le dossier appel.',
        'touch cree le fichier vide appel/cavalerie.',
        'cp copie cavalerie vers offrande : le fichier cavalerie reste present.',
        'mv renomme offrande en poulin dans le dossier appel.',
        'A la fin : appel/cavalerie et appel/poulin sont deux fichiers vides.',
    ] if identifiant == 'recette1' else [
        'lsblk liste les peripheriques de stockage de la machine.',
        '> cree a.txt (ou remplace son contenu) avec la sortie de lsblk.',
        'cat a.txt affiche tout le contenu du fichier dans le terminal.',
        '| transmet la sortie de cat a grep, qui ne garde que les lignes contenant NAME.',
        'grep "NAME" a.txt lit directement le meme fichier, sans passer par cat.',
        'NAME est sensible aux majuscules ; les guillemets font partie de la recette.',
        'Le pipeline est une seule etape ; cat et grep doivent tous deux reussir.',
        'Le tableau depend des disques de la machine ; aucun disque n est modifie.',
    ]
    composition = '20 cavaliers (10/5/5/0)' if identifiant == 'recette1' else '20 archers (0/0/0/20)'
    if identifiant == 'recette3':
        explications = [
            'touch cree le fichier vide rempart.',
            'Comparez les trois sorties de ls -l, surtout la premiere colonne.',
            'Au debut, les permissions dependent du masque de creation (umask).',
            'chmod 660 : -rw-rw---- ; lecture/ecriture pour proprietaire et groupe.',
            'chmod 600 : -rw------- ; lecture/ecriture pour le proprietaire seul.',
            'Les trois chiffres designent proprietaire, groupe, puis autres.',
            '6 = lecture (4) + ecriture (2) ; 0 = aucun droit.',
            'Apres le dernier chmod, le groupe perd ses droits ; les autres restent sans droit.',
        ]
        composition = '20 piquiers (6/7/7/0)'
    lignes = [
        'MYTHODEA - Crypte V0.1', f'{identifiant} : {recette["nom"]}', '',
        'Telechargez ce PDF avec votre client SFTP, puis lisez-le sur votre PC.',
        'Exemple SCP depuis votre PC (remplacez ADRESSE_DU_PI) :',
        f'scp j1@ADRESSE_DU_PI:{racine}/village/j1/crypte/grimoire/{identifiant}.pdf .',
        'Pour j2, remplacez j1 par j2 dans les chemins et la connexion.', '',
        'Pendant ACTIONS, dans votre Bash habituel :',
        f'cd {racine}/village/j1/crypte/atelier', marqueurs['debut'], *recette['lignes'], marqueurs['fin'], '',
        'Saisissez une commande par ligne, dans cet ordre exact.',
        'Aucune commande supplementaire : ls, clear, cd... invalident la tentative.',
        'Une commande echouee, Ctrl+C ou une tentative inachevee ne rapporte rien.',
        'L atelier est jetable : ne placez aucun fichier personnel dedans.', '',
        *explications, '',
        'Une reussite tous les 5 tours par joueur, delai partage entre toutes les recettes.',
        'Les erreurs ne consomment pas ce delai.',
        'La recompense apparait apres la publication du tour, dans recompense/.',
        'Un seul general en attente. Son identite reste generalN.',
        f'Nom affiche : {recette["nom"]} ; {composition}.',
        'Cette recompense ne consomme pas les 5 creations normales.', '',
        'Apres publication : cd ~ puis revenez sur la carte.',
        'Lors des ACTIONS suivantes, choisissez une destination legale et libre :',
        f'mv {racine}/village/j1/crypte/recompense/generalN {racine}/village/j1/garnison/1/',
        'Ne ramenez pas un general dans recompense/ apres sa recuperation.',
    ]
    if contexte and site(contexte) == 'crypte_des_plaines':
        atelier = f'{racine}/est_1/{joueur}/crypte_des_plaines/atelier'
        lignes = [
            'MYTHODEA - Crypte des plaines', identifiant, '',
            f'Connaissance personnelle requise : evolution {recette["evolution"]}.',
            f'Placer le general dans {racine}/est_1/crypte_des_plaines/1/{joueur}/.',
            f'cd {atelier}', marqueurs['debut'], *recette['lignes'], marqueurs['fin'], '',
            'Une commande par ligne, dans cet ordre, sans commande supplementaire.',
            'Remplacez {bloc} par echo avant > bloc.txt (ou droite, gauche, arriere).',
            'Remplacez {ligne} par echo N > ligne.txt ; N contient orc_archer dans nl.',
            'Chaque numero correspondant du livre est accepte.',
            'Sauvageon : saisir dans vi trois lignes : boueux, et, crasseux.',
            'Une interruption ou une commande echouee invalide toute la tentative.',
            'Livraison : jusqu a 4 unites, selon les places libres du general.',
            'Bloc incompatible : autre bloc compatible choisi au hasard, avec message.',
            'Aucune place : aucune unite. Delai : une reussite tous les 5 tours.',
        ]
    commandes = ['BT /F1 10 Tf 42 795 Td 17 TL']
    for ligne in lignes:
        texte = ligne.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        commandes.append(f'({texte}) Tj T*')
    contenu = ('\n'.join(commandes) + '\nET').encode('ascii')
    objets = [b'<< /Type /Catalog /Pages 2 0 R >>',
              b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
              b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 900] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
              b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
              b'<< /Length ' + str(len(contenu)).encode() + b' >>\nstream\n' + contenu + b'\nendstream']
    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for i, objet in enumerate(objets, 1):
        offsets.append(len(pdf))
        pdf.extend(f'{i} 0 obj\n'.encode() + objet + b'\nendobj\n')
    xref = len(pdf)
    pdf.extend(b'xref\n0 6\n0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(pdf)


def verifier_offrande(c, j):
    with dossier_atelier(c, j) as fd:
        if set(os.listdir(fd)) != {'appel'}:
            raise ValueError('Atelier différent de la recette.')
        appel = os.open('appel', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        try:
            if set(os.listdir(appel)) != {'cavalerie', 'poulin'}:
                raise ValueError('Offrande absente ou objets supplémentaires.')
            for nom in ('cavalerie', 'poulin'):
                infos = os.stat(nom, dir_fd=appel, follow_symlinks=False)
                if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1 or infos.st_size != 0:
                    raise ValueError('Offrande incorrecte (deux fichiers vides, sans lien).')
        finally:
            os.close(appel)


def verifier_lecture(c, j):
    with dossier_atelier(c, j) as fd:
        if set(os.listdir(fd)) != {'a.txt'}:
            raise ValueError('Atelier différent de la recette.')
        fichier = os.open('a.txt', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(fichier, 'rb') as contenu:
            infos = os.fstat(contenu.fileno())
            if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
                raise ValueError('a.txt doit être un fichier ordinaire sans lien.')
            if not any(b'NAME' in ligne for ligne in contenu):
                raise ValueError('a.txt ne contient pas le motif NAME.')


def verifier_rempart(c, j):
    with dossier_atelier(c, j) as fd:
        if set(os.listdir(fd)) != {'rempart'}:
            raise ValueError('Atelier différent de la recette.')
        infos = os.stat('rempart', dir_fd=fd, follow_symlinks=False)
        if (not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1
                or infos.st_size != 0 or stat.S_IMODE(infos.st_mode) != 0o600):
            raise ValueError('Rempart incorrect (fichier vide, sans lien, permissions 600).')


def clore(c):
    """Appelé sous gel avant capture ; aucun succès accepté après fermeture."""
    with VERROU:
        service = SERVICES.get(str(c['game_path']))
        if service:
            service.tentatives.clear()
        for j in c['joueurs']:
            nettoyer(c, j)
            if site(c) == 'crypte':
                nettoyer(contexte_plaines(c), j)


def verifier_collecteur(c):
    service = SERVICES.get(str(c['game_path']))
    if service and service.erreur is not None:
        raise RuntimeError(f'Collecteur Crypte interrompu : {service.erreur}')


def auditer_recuperations(c):
    """La zone d'attente est inactive et à sens unique, audit commun ensuite."""
    if c['mode'] != 'survie':
        return set()
    import mouvements
    import rapports
    donnees = charger(c)
    punis = set()
    for j, fiche in donnees.items():
        attente = zone(c, j) / 'recompense'
        if not attente.exists():
            continue
        for p in list(attente.iterdir()):
            if p.is_dir() and p.name != fiche['en_attente']:
                rapports.afficher_et_ecrire(f'Retour interdit dans la Crypte : {j}:{p.name}.')
                mouvements.envoyer_general_au_repli(j, p.name, p, c)
                punis.add(f'{j}:{p.name}')
        if fiche['en_attente'] and not (attente / fiche['en_attente']).exists():
            fiche['en_attente'] = None
    if chemin_etat(c).exists():
        sauver(c, donnees)
    return punis


def attribuer_recompense(c, joueur, fiche, attribution, composition):
    """Création commune dans une génération privée, hors quota normal."""
    import generaux
    attente = zone(c, joueur) / 'recompense'
    if any(attente.iterdir()):
        raise RuntimeError('Récompense Crypte occupée : attribution impossible.')
    numero = etat.lire_compteur_general(joueur) + 1
    etat.sauvegarder_compteur_general(joueur, numero)
    nom = f'general{numero}'
    general = attente / nom
    generaux.creer_general(general, nom)
    with (general / 'fiche.txt').open('a', encoding='utf-8') as f:
        f.write(f'\nnom_affichage={composition["nom"]}\n')
    equipements = composition.get('equipements')
    if equipements is None:
        equipements = (composition['equipement'],)
    for bloc, taille in zip(config.ordre_blocs, composition['blocs']):
        for i in range(1, taille + 1):
            unite = general / bloc / f'{composition["unite"]}{i}'
            if composition.get('type_officiel'):
                import unites
                unites.creer_officielle(unite, composition['type_officiel'],
                    {'source': site(c), 'attribution': attribution['id']}, composition.get('contenu'))
                continue
            unite.mkdir()
            for equipement in equipements:
                (unite / equipement).touch()
    generaux.donner_permissions_general(general, c['acteurs'][joueur]['proprietaire_linux'])
    positions = etat.charger_positions_generaux()
    positions[f'{joueur}:{nom}'] = 'village' if site(c) == 'crypte' else 'est_1'
    etat.sauvegarder_positions_generaux(positions)
    fiche['en_attente'] = nom
    fiche['attributions'].append({**attribution, 'general': nom})
    return nom


def materialiser(c, tour):
    _materialiser_site(c, tour)
    if site(c) == 'crypte':
        _materialiser_site(contexte_plaines(c), tour)


def _materialiser_site(c, tour):
    """Uniquement dans travail/ : aucune lecture/écriture de la partie vivante."""
    import generaux
    import rapports
    donnees = charger(c)
    for j, fiche in donnees.items():
        demande = fiche['a_creer']
        if demande is None:
            continue
        if demande['tour'] != tour:
            raise RuntimeError('Réussite Crypte d’un autre tour : récupération administrative requise.')
        if demande['id'] in {a['id'] for a in fiche['attributions']}:
            raise RuntimeError('Attribution Crypte déjà consommée.')
        if site(c) == 'crypte_des_plaines':
            livrer_plaines(c, j, donnees, demande)
            continue
        # Les réussites historiques sans identifiant sont celles de recette1.
        recette = catalogue(c, j)[demande.get('recette', 'recette1')]
        attente = zone(c, j) / 'recompense'
        if any(attente.iterdir()):
            raise RuntimeError('Récompense Crypte occupée après acceptation : vérifier la partie.')
        nom = attribuer_recompense(c, j, fiche, demande, recette)
        fiche['a_creer'] = None
        sauver(c, donnees)
        relatif = zone(c, j).relative_to(c['game_path']) / 'recompense'
        rapports.ecrire_rapport_court(f'{j} : {recette["nom"]} ({nom}) attend dans {relatif}/.')
    generaux.scanner_ordres_surnombre(c)


def identite_processus(pid):
    p = Path('/proc') / str(pid)
    champs = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    if champs[0] == 'Z':
        raise ValueError('Session terminée.')
    return (p.stat().st_uid, int(champs[1]), champs[19])


def livrer_plaines(c, joueur, donnees, demande):
    import generaux
    import rapports
    import unites
    fiche = donnees[joueur]
    general = None
    raison = ''
    try:
        general = verifier_connaissance_plaines(c, joueur, catalogue(c, joueur)[demande['recette']]['evolution'])
        if general['nom'] != demande['general']:
            raise ValueError('Le général bénéficiaire a quitté la Crypte.')
    except ValueError as erreur:
        raison = str(erreur)
    nombre = 0
    bloc = demande['bloc']
    if general and not raison:
        composition = generaux.lire_composition_general(general['chemin'])
        places = max(0, config.max_unites_par_general - unites.occupation(composition))
        compatibles = [b for b, types in composition.items() if all(
            t == demande['recette'] or unites.etiquette(t, 'non_combattant') for t in types)]
        if not places:
            raison = 'Aucune place disponible dans le général.'
        elif not compatibles:
            raison = 'Aucun bloc compatible disponible.'
        else:
            if bloc not in compatibles:
                bloc = random_livraison.choice(compatibles)
                rapports.ecrire_rapport_court(
                    f"Crypte des plaines : {joueur}:{general['nom']}, bloc {demande['bloc']} incompatible ; livraison dans {bloc}.")
            nombre = min(4, places)
    attribution = dict(demande, bloc_livre=bloc, nombre=nombre, terminee=False)
    fiche['attributions'].append(attribution)
    sauver(c, donnees)
    for numero in range(nombre):
        definition = unites.definition(demande['recette'])
        destination = general['chemin'] / bloc / f"{definition['prefixe']}_{demande['id']}_{numero}"
        contenu = ({'sauvageon.txt': 'boueux\net\ncrasseux\n'} if demande['recette'] == 'sauvageon'
                   else {f"tome_du_{demande['recette']}": LIVRES[demande['recette']]})
        unites.creer_officielle(destination, demande['recette'],
                               {'crypte_des_plaines': demande['id']}, contenu)
    if general:
        generaux.donner_permissions_general(general['chemin'], c['acteurs'][joueur]['proprietaire_linux'])
    attribution['terminee'] = True
    fiche['a_creer'] = None
    sauver(c, donnees)
    rapports.ecrire_rapport_court(
        f"Crypte des plaines : {joueur}:{demande['general']}, {nombre} {demande['recette']} livré(s). {raison}")


class Collecteur:
    """Socket locale root, une séquence numérotée par tentative et session Bash."""
    def __init__(self, c, horloge=time.time):
        self.c, self.horloge = c, horloge
        self.tentatives = {}
        self.arret = threading.Event()
        self.erreur = None
        self.marqueurs = configuration(c)
        self.uids = {pwd.getpwnam(c['acteurs'][j]['proprietaire_linux']).pw_uid: j for j in c['joueurs']}

    def evenement(self, uid, session, message):
        with VERROU:
            if uid not in self.uids:
                raise ValueError('UID non joueur.')
            j = self.uids[uid]
            cycle = etat.charger_cycle_survie(self.c)
            if not cycle or cycle['phase'] != 'actions' or self.horloge() >= cycle['echeance']:
                raise ValueError('La fenêtre ACTIONS est fermée.')
            op = message['event']
            if op == 'start':
                c = next((c for c in (self.c, contexte_plaines(self.c))
                          if Path(message['cwd']) == zone(c, j) / 'atelier'), None)
                if c is None:
                    raise ValueError('Entrer dans votre atelier avant de commencer.')
                ancienne = self.tentatives.pop(j, None)
                if ancienne:
                    nettoyer(dict(self.c, crypte_site=ancienne['site']), j)
                nettoyer(c, j)
                d = charger(c)[j]
                if d['a_creer'] or any((zone(c, j) / 'recompense').iterdir()):
                    raise ValueError('Une récompense est déjà en attente.')
                if d['dernier_tour'] is not None and cycle['tour'] < d['dernier_tour'] + 5:
                    raise ValueError(f"Prochaine utilisation au tour {d['dernier_tour'] + 5}.")
                token = uuid.uuid4().hex
                beneficiaire = destinataire_plaines(c, j) if site(c) == 'crypte_des_plaines' else None
                self.tentatives[j] = {'token': token, 'session': session, 'tour': cycle['tour'],
                                      'seq': 0, 'etape': 0, 'pending': False, 'erreur': None,
                                      'recette': None, 'composants': 0, 'history': None,
                                      'site': site(c), 'candidats': list(catalogue(c, j)),
                                      'lignes': [], 'pending_line': '',
                                      'general': beneficiaire['nom'] if beneficiaire else None,
                                      'presence': ([beneficiaire['chemin'].stat().st_dev,
                                                    beneficiaire['chemin'].stat().st_ino,
                                                    beneficiaire['chemin'].stat().st_ctime_ns] if beneficiaire else None)}
                return token
            t = self.tentatives.get(j)
            if (t is None or message.get('token') != t['token'] or session != t['session']
                    or t['tour'] != cycle['tour'] or type(message.get('seq')) is not int
                    or message.get('seq') != t['seq'] + 1):
                raise ValueError('Tentative inconnue, ancienne ou événement rejoué.')
            t['seq'] += 1
            c = dict(self.c, crypte_site=t['site'])
            recettes = catalogue(c, j)
            if Path(message['cwd']) != zone(c, j) / 'atelier':
                t['erreur'] = 'Hors de votre atelier.'
            if op == 'before':
                ligne = message['line']
                if ligne == self.marqueurs['fin'] and message['command'] == ligne:
                    return ''
                t['candidats'] = [r for r in t['candidats']
                    if t['etape'] < len(recettes[r]['lignes']) and
                    correspond_etape(recettes[r]['lignes'][t['etape']], ligne)]
                t['recette'] = t['candidats'][0] if len(t['candidats']) == 1 else None
                kind = 'builtin' if site(c) != 'crypte' and (
                    ligne == 'pwd' or ligne.startswith('echo ')) else 'file'
                if (t['pending'] or not t['candidats']
                        or message['command'] != commandes_etape(ligne)[0] or message['kind'] != kind
                        or not message['history'].endswith('/1')):
                    t['erreur'] = 'Commande inattendue : tentative invalidée.'
                t['pending'] = True
                t['composants'] = 1
                t['history'] = message['history']
                t['pending_line'] = ligne
            elif op == 'component':
                attendus = commandes_etape(t['pending_line'])
                if (not t['pending'] or t['composants'] >= len(attendus)
                        or message['line'] != t['pending_line']
                        or message['command'] != attendus[t['composants']]
                        or message['kind'] != 'file' or message['history'] != t['history']):
                    t['erreur'] = 'Commande inattendue : tentative invalidée.'
                t['composants'] += 1
            elif op == 'after':
                attendus = commandes_etape(t['pending_line'])
                if (not t['pending'] or message['status'] != '0'
                        or t['composants'] != len(attendus)
                        or (len(attendus) == 2 and message.get('command') != '0 0')):
                    t['erreur'] = 'Commande échouée : tentative invalidée.'
                if not t['erreur']:
                    t['etape'] += 1
                    t['lignes'].append(t['pending_line'])
                t['pending'] = False
                if t['erreur']:
                    nettoyer(c, j)
            elif op in ('interrupt', 'unobserved', 'close'):
                t['erreur'] = 'Tentative interrompue ou ligne non exécutée.'
                nettoyer(c, j)
            elif op == 'end':
                del self.tentatives[j]  # Consommation même si la vérification finale échoue.
                try:
                    lignes = recettes[t['recette']]['lignes'] if t['recette'] else ()
                    if t['erreur'] or t['pending'] or not lignes or t['etape'] != len(lignes):
                        raise ValueError(t['erreur'] or 'Recette incomplète.')
                    bloc = None
                    if site(c) == 'crypte_des_plaines':
                        bloc = verifier_plaines(c, j, t['recette'], t['lignes'])
                        general = verifier_connaissance_plaines(c, j, recettes[t['recette']]['evolution'])
                        presence = general['chemin'].stat()
                        if general['nom'] != t['general'] or [presence.st_dev, presence.st_ino, presence.st_ctime_ns] != t['presence']:
                            raise ValueError('Le général présent a changé pendant la recette.')
                    elif t['recette'] == 'recette1':
                        verifier_offrande(c, j)
                    elif t['recette'] == 'recette2':
                        verifier_lecture(c, j)
                    else:
                        verifier_rempart(c, j)
                    if self.horloge() >= cycle['echeance']:
                        raise ValueError('La fenêtre ACTIONS est fermée.')
                    d = charger(c)
                    f = d[j]
                    if f['a_creer'] or any((zone(c, j) / 'recompense').iterdir()):
                        raise ValueError('Récompense déjà en attente.')
                    if f['dernier_tour'] is not None and cycle['tour'] < f['dernier_tour'] + 5:
                        raise ValueError('Cooldown actif.')
                    f['dernier_tour'] = cycle['tour']
                    f['a_creer'] = {'id': t['token'], 'tour': cycle['tour'], 'recette': t['recette']}
                    if bloc is not None:
                        f['a_creer']['bloc'] = bloc
                        f['a_creer']['general'] = t['general']
                    sauver(c, d)
                finally:
                    nettoyer(c, j)
                return 'Réussite enregistrée. Récompense après la publication du tour.'
            else:
                t['erreur'] = 'Événement inconnu.'
            return t['erreur'] or ''

    def verifier_session(self, peer_pid, uid, shell_pid):
        identite = identite_processus(shell_pid)
        if identite[0] != uid:
            raise ValueError('Session d’un autre UID.')
        pid = peer_pid
        for _ in range(32):
            if pid == shell_pid:
                return (shell_pid, identite[2])
            ident = identite_processus(pid)
            if ident[0] != uid or ident[1] <= 1:
                break
            pid = ident[1]
        raise ValueError('Client hors de la session déclarée.')

    def surveiller_sessions(self):
        with VERROU:
            for j, t in list(self.tentatives.items()):
                try:
                    ident = identite_processus(t['session'][0])
                    vivant = ident[2] == t['session'][1]
                except (OSError, ValueError):
                    vivant = False
                if not vivant:
                    del self.tentatives[j]
                    nettoyer(dict(self.c, crypte_site=t['site']), j)

    def servir(self):
        while not self.arret.is_set():
            try:
                self.surveiller_sessions()
                try:
                    connexion, _ = self.socket.accept()
                except socket.timeout:
                    continue
                with connexion:
                    connexion.settimeout(.5)
                    try:
                        pid, uid, _ = struct.unpack('3i', connexion.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                        fichier = connexion.makefile('rb')
                        with fichier:
                            ligne = fichier.readline(16385)
                        if len(ligne) > 16384 or not ligne.endswith(b'\n'):
                            raise ValueError('Message incomplet ou trop long.')
                        m = json.loads(ligne)
                        if (not isinstance(m, dict)
                                or any(not isinstance(m.get(k), str) for k in
                                       ('event', 'line', 'command', 'status', 'cwd', 'history', 'kind', 'token'))
                                or type(m.get('seq')) is not int or type(m.get('session')) is not int):
                            raise ValueError('Format de message Crypte invalide.')
                        session = self.verifier_session(pid, uid, int(m['session']))
                        # Le cwd provient du processus réel, pas de sa déclaration.
                        m['cwd'] = str(Path(f'/proc/{session[0]}/cwd').resolve(strict=True))
                        resultat = self.evenement(uid, session, m)
                        reponse = {'ok': True, 'resultat': resultat}
                    except (OSError, ValueError, KeyError, TypeError) as erreur:
                        reponse = {'ok': False, 'erreur': str(erreur)}
                    try:
                        connexion.sendall((json.dumps(reponse) + '\n').encode())
                    except OSError:
                        pass
            except Exception as erreur:
                # La prochaine clôture refuse la résolution et exige une vérification.
                self.erreur = str(erreur)
                self.arret.set()

    def __enter__(self):
        from cycle_linux import sans_liens
        config.verifier_structure_actuelle(self.c)
        etat.preparer_systeme_survie(self.c)
        racine = self.c['game_path'] / '.systeme/communication'
        sans_liens(racine)
        racine.mkdir(mode=0o710, exist_ok=True)
        gid = grp.getgrnam(self.c['groupe_allie']).gr_gid
        os.chown(racine, 0, gid)
        os.chmod(racine, 0o710)
        self.chemin = racine / 'crypte.sock'
        if self.chemin.exists() or self.chemin.is_symlink():
            raise RuntimeError('Socket Crypte résiduelle : vérifier l’ancien moteur avant retrait administratif.')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.bind(str(self.chemin))
        os.chown(self.chemin, 0, gid)
        os.chmod(self.chemin, 0o660)
        self.socket.listen(8)
        self.socket.settimeout(.1)
        SERVICES[str(self.c['game_path'])] = self
        self.thread = threading.Thread(target=self.servir, name='crypte', daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.arret.set()
        self.thread.join(timeout=2)
        self.socket.close()
        self.chemin.unlink(missing_ok=True)
        SERVICES.pop(str(self.c['game_path']), None)


@contextmanager
def service(c):
    if not c.get('collecteur_crypte', True):
        yield
    else:
        with Collecteur(c):
            yield
