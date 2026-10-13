"""Mini-défis Survie : documents, Courrier et décisions privées par joueur."""
from contextlib import contextmanager
import grp
import hashlib
import json
import os
import secrets
import stat
import time

import config
import crypte
import etat

DEFI = 'cabane_est_2_defi_1'
NOM_RECOMPENSE = 'cavalier_noir'
INTERVALLE_SCAN = 10
LIMITE_MESSAGE = 65536
FICHE = '''CAVALERIE LOURDE

Statut :
Débloquée comme récompense spéciale

Catégorie :
Cavalier

Force :
- Archer
- Cavalier

Faiblesse :
- Piquier

Effet spécial :
Si au moins 15 cavaliers lourds frappent ensemble depuis le bloc avant,
chaque unité vaut 2 au lieu de 1 pour cette résolution.
L'avantage de type multiplie ensuite cette valeur par 2.

Construction :
Verrouillée
'''
README = '''Quelqu'un a laissé une récompense dans cette cabane.
Le sceau n'est pas visible au premier regard.
Trouvez-le, lisez-le, puis cherchez sa référence dans les archives.
Envoyez le flag trouvé à l'Hôtel de Ville, par le Courrier.
'''
# Sources : Plutarque, Vie de Crassus, 24-27 ; Encyclopaedia Iranica, « Carrhae ».
NOTES = (
    "Les cataphractaires parthes sont une forme célèbre de cavalerie lourde antique.\n"
    "Le cavalier portait une armure couvrant largement son corps.\n"
    "Son cheval était lui aussi protégé par une armure.\n"
    "Une longue lance lui permettait de frapper au contact.\n"
    "Ces cavaliers combattaient aux côtés d'archers montés plus mobiles.\n"
    "Ils jouèrent un rôle important à Carrhes, en 53 av. J.-C.\n",
    "À Carrhes, les Parthes combinèrent archers montés et cavaliers lourds.\n"
    "Les archers harcelaient les Romains à distance et évitaient le corps à corps.\n"
    "Des réserves de flèches transportées par des chameaux entretenaient leurs tirs.\n"
    "Les cataphractaires chargeaient les formations exposées ou affaiblies.\n"
    "Leurs longues lances complétaient ainsi l'action des archers.\n"
    "Cette combinaison contribua à la défaite majeure de l'armée romaine de Crassus.\n",
)


def charger(c):
    p = c['game_path'] / '.systeme/defis.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def sauver(c, donnees):
    etat.ecrire_prive(c['game_path'] / '.systeme/defis.json',
                      json.dumps(donnees, ensure_ascii=False) + '\n')


def preparer(c):
    """Prépare les documents, sans valider de flag ni créer de général."""
    if c['mode'] != 'survie':
        return
    from cycle_linux import sans_liens
    d = charger(c)
    if d is None:
        # Le flag complet n'est jamais livré dans les sources publiques du moteur.
        d = {'flags': {DEFI: 'mythodea{charge_du_cavalier_noir_' + secrets.token_hex(8) + '}'},
             'joueurs': {j: {DEFI: {'termine': False, 'recompense_recue': False,
                                    'general': None},
                             'courrier': {'empreinte': None, 'modification': None, 'a_repondre': None}}
                         for j in c['joueurs']}}
        sauver(c, d)
    cabane = c['game_path'] / 'est_2/cabane_mysterieuse'
    nouvelle = not cabane.exists()
    for nom in ('', 'coffre', 'archives', 'notes'):
        p = cabane / nom
        sans_liens(p)
        if not p.exists():
            p.mkdir(parents=True)
            os.chown(p, 0, 0)
            os.chmod(p, 0o700)
    documents = {'readme.txt': README, 'coffre/.sceau': 'SCEAU=NOIR-17\n',
                 'notes/note1.txt': NOTES[0], 'notes/note2.txt': NOTES[1]}
    couleurs = ('ROUGE', 'BLEU', 'VERT', 'GRIS', 'OCRE')
    mentions = ('ancienne livraison', 'équipement manquant', 'transfert annulé',
                'archive secondaire', 'convoi arrivé', 'inventaire vérifié', 'fourrage réservé')
    for numero in range(1, 4):
        lignes = [f'{couleurs[i % len(couleurs)]}-{numero * 40 + i:03} '
                  f'{mentions[(i + numero) % len(mentions)]}' for i in range(40)]
        if numero == 2:
            lignes[23] = 'NOIR-17 ' + d['flags'][DEFI]
        documents[f'archives/registre{numero}.txt'] = '\n'.join(lignes) + '\n'
    for nom, contenu in documents.items():
        p = cabane / nom
        sans_liens(p)
        if not p.exists() or p.read_text(encoding='utf-8') != contenu:
            etat.ecrire_prive(p, contenu)
            os.chown(p, 0, 0)
            os.chmod(p, 0o600)
    if nouvelle:
        publier_acces(c)
    for j in c['joueurs']:
        bestiaire = c['game_path'] / 'village' / j / 'hotel_de_ville/bestiaire'
        sans_liens(bestiaire)
        bestiaire.mkdir(parents=True, exist_ok=True)
        os.chown(bestiaire, 0, grp.getgrnam(c['acteurs'][j]['groupe_linux']).gr_gid)
        os.chmod(bestiaire, 0o750)
        if d['joueurs'][j][DEFI]['termine']:
            publier_fiche(c, j)


def publier_acces(c):
    """Accès du camp propriétaire, fixé à l'installation de l'état publié."""
    from cycle_linux import sans_liens
    cabane = c['game_path'] / 'est_2/cabane_mysterieuse'
    if not cabane.exists():
        return
    camp = etat.charger_controle_territoires(c).get('est_2', 'neutre')
    # Neutre/contesté ne sont jamais des propriétaires, même mal configurés.
    groupe = None if camp in ('neutre', 'conteste') else c['groupes_camps'].get(camp)
    gid = grp.getgrnam(groupe).gr_gid if groupe else 0
    for p in [cabane, *cabane.rglob('*')]:
        sans_liens(p)
        os.chown(p, 0, gid)
        os.chmod(p, (0o750 if p.is_dir() else 0o640) if groupe
                 else (0o700 if p.is_dir() else 0o600))


@contextmanager
def document(c, joueur, dossier, nom, flags, creation=False):
    """Accès ancré par fd sous Linux, même si le joueur renomme son village.

    Les répertoires administrateur et les sorties restent possédés par le moteur.
    Les liens et objets spéciaux sont refusés ; aucun texte joueur n'est exécuté.
    """
    from cycle_linux import sans_liens
    chemin = c['game_path'] / 'village' / joueur / 'hotel_de_ville' / dossier / nom
    fd_dossier = None
    fd = None
    try:
        if os.name == 'posix':
            fd_dossier = os.open(c['game_path'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            for partie in ('village', joueur, 'hotel_de_ville', dossier):
                suivant = os.open(partie, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                  dir_fd=fd_dossier)
                os.close(fd_dossier)
                fd_dossier = suivant
                if partie in ('hotel_de_ville', dossier) and os.fstat(suivant).st_uid != os.geteuid():
                    raise RuntimeError('Dossier administrateur remplacé dans le Courrier.')
            fd = os.open(nom, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd_dossier)
        else:
            # Tests Windows uniquement : pas de sessions joueurs Unix concurrentes.
            sans_liens(chemin)
            fd = os.open(chemin, flags | getattr(os, 'O_BINARY', 0), 0o600)
        infos = os.fstat(fd)
        if not stat.S_ISREG(infos.st_mode) or infos.st_nlink != 1:
            raise RuntimeError('Document de Courrier non régulier ou lié.')
        if creation and os.name == 'posix':
            if infos.st_uid != os.geteuid():
                raise RuntimeError('Document administrateur remplacé.')
            os.fchown(fd, 0, grp.getgrnam(c['acteurs'][joueur]['groupe_linux']).gr_gid)
            os.fchmod(fd, 0o640)
        elif creation:
            os.chown(chemin, 0, grp.getgrnam(c['acteurs'][joueur]['groupe_linux']).gr_gid)
            os.chmod(chemin, 0o640)
        with os.fdopen(fd, 'r+b' if creation else 'rb') as fichier:
            fd = None
            yield fichier
    finally:
        if fd is not None:
            os.close(fd)
        if fd_dossier is not None:
            os.close(fd_dossier)


def publier_fiche(c, joueur):
    with document(c, joueur, 'bestiaire', 'cavalerie_lourde.txt',
                  os.O_RDWR | os.O_CREAT, creation=True) as f:
        contenu = FICHE.encode('utf-8')
        if f.read() != contenu:
            f.seek(0)
            f.write(contenu)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())


def repondre(c, joueur, texte):
    with document(c, joueur, 'courrier', 'reception_message.txt',
                  os.O_RDWR | os.O_CREAT, creation=True) as f:
        reponse = (texte + '\n').encode('utf-8')
        f.seek(0, os.SEEK_END)
        taille = f.tell()
        f.seek(max(0, taille - len(reponse)))
        if f.read() == reponse:
            return  # reprise après écriture de la réponse, avant acquittement privé
        f.seek(0, os.SEEK_END)
        if taille:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b'\n':
                f.write(b'\n')
        f.write(reponse)
        f.flush()
        os.fsync(f.fileno())


def scanner(c, horloge=None, cloture=False):
    """Un seul pilote sous verrou de cycle ; décision durable avant réponse."""
    if c['mode'] != 'survie':
        return
    horloge = time.time if horloge is None else horloge
    with crypte.VERROU:
        cycle = etat.charger_cycle_survie(c)
        if not cycle or (cycle['phase'] != 'capture' if cloture else (
                cycle['phase'] != 'actions' or horloge() >= cycle['echeance'])):
            return
        d = charger(c)
        if d is None:
            return
        for j in c['joueurs']:
            courrier = d['joueurs'][j]['courrier']
            # Une réponse en attente est terminée avant de lire un autre message.
            if courrier['a_repondre'] is not None:
                if d['joueurs'][j][DEFI]['termine']:
                    publier_fiche(c, j)
                repondre(c, j, courrier['a_repondre'])
                courrier['a_repondre'] = None
                sauver(c, d)
            try:
                with document(c, j, 'courrier', 'envoie_message.txt', os.O_RDONLY) as f:
                    avant = os.fstat(f.fileno())
                    contenu = f.read(LIMITE_MESSAGE + 1)
                    apres = os.fstat(f.fileno())
            except FileNotFoundError:
                continue
            if (avant.st_mtime_ns, avant.st_size) != (apres.st_mtime_ns, apres.st_size):
                continue  # le joueur écrit encore ; relire au prochain passage
            if len(contenu) > LIMITE_MESSAGE:
                continue
            empreinte = hashlib.sha256(contenu).hexdigest()
            if empreinte == courrier['empreinte'] and apres.st_mtime_ns == courrier['modification']:
                continue
            lignes = [ligne.split() for ligne in contenu.decode('utf-8', errors='replace').splitlines()]
            demandes = [mots for mots in lignes if mots and mots[0] == 'FLAG']
            if not demandes:
                # Ne pas modifier l'état pour une demande d'un autre service.
                continue
            reponses = []
            for mots in demandes:
                identifiant = next((i for i, flag in d['flags'].items()
                                    if len(mots) == 2 and mots[1] == flag), None)
                if identifiant is None:
                    reponses.append('Flag invalide.')
                elif d['joueurs'][j][identifiant]['termine']:
                    reponses.append('Ce défi a déjà été validé.')
                else:
                    d['joueurs'][j][identifiant]['termine'] = True
                    reponses.append('Flag valide. Votre récompense divine sera publiée dans la Crypte '
                                    'en fin de tour, dès que sa zone de récompense sera libre.')
            courrier.update(empreinte=empreinte, modification=apres.st_mtime_ns,
                            a_repondre='\n'.join(reponses))
            sauver(c, d)
            if d['joueurs'][j][DEFI]['termine']:
                publier_fiche(c, j)
            repondre(c, j, courrier['a_repondre'])
            courrier['a_repondre'] = None
            sauver(c, d)


def synchroniser_courrier_publie(c):
    """La copie moteur d'un brouillon ne constitue pas un nouvel envoi joueur."""
    d = charger(c)
    if d is None:
        return
    change = False
    for j in c['joueurs']:
        try:
            with document(c, j, 'courrier', 'envoie_message.txt', os.O_RDONLY) as f:
                contenu = f.read(LIMITE_MESSAGE + 1)
                modification = os.fstat(f.fileno()).st_mtime_ns
        except FileNotFoundError:
            continue
        courrier = d['joueurs'][j]['courrier']
        if hashlib.sha256(contenu).hexdigest() == courrier['empreinte']:
            if courrier['modification'] != modification:
                courrier['modification'] = modification
                change = True
    if change:
        sauver(c, d)


def materialiser(c, tour):
    """Après la recette Crypte, dans travail/ ; attendre si sa place est occupée."""
    import generaux
    import rapports
    d = charger(c)
    if d is None:
        return
    recompenses = crypte.charger(c)
    for j in c['joueurs']:
        defi = d['joueurs'][j][DEFI]
        if not defi['termine'] or defi['recompense_recue']:
            continue
        fiche = recompenses[j]
        if fiche['en_attente'] or fiche['a_creer'] or any((crypte.zone(c, j) / 'recompense').iterdir()):
            continue
        composition = {'nom': NOM_RECOMPENSE, 'blocs': (20, 0, 0, 0),
                       'unite': config.unites_equipements['cavalerie_lourde'][0],
                       'equipements': config.unites_equipements['cavalerie_lourde'][1]}
        attribution = {'id': f'defi:{j}:{DEFI}', 'source': 'defi', 'defi': DEFI,
                       'tour': tour, 'nom_affichage': NOM_RECOMPENSE}
        # Une interruption privée est bloquante ; ne jamais créer une seconde attribution.
        if any(a['id'] == attribution['id'] for a in fiche['attributions']):
            raise RuntimeError('Attribution de défi déjà enregistrée : récupération requise.')
        nom = crypte.attribuer_recompense(c, j, fiche, attribution, composition)
        crypte.sauver(c, recompenses)
        defi.update(recompense_recue=True, general=nom)
        sauver(c, d)
        repondre(c, j, 'Une récompense divine vous attend dans la Crypte.')
        rapports.ecrire_rapport_court(f'{j} : {NOM_RECOMPENSE} ({nom}) attend dans village/{j}/crypte/recompense/.')
    generaux.scanner_ordres_surnombre(c)
