"""Clôture Linux : gel, copies indépendantes, publication et diagnostic durable.

Ce module ne connaît aucune règle de combat. Les effets Unix sont regroupés dans
Linux pour permettre aux tests d'injecter une horloge et un contrôleur de gel.
"""
import grp
import hashlib
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import time
import uuid

import config
import etat
import generaux
import rapports


def synchroniser_dossier(chemin):
    if os.name == "posix":
        fd = os.open(chemin, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def sans_liens(chemin):
    """Vérifie également les parents ; aucune traversée d'un lien utilisateur."""
    for parent in reversed((chemin, *chemin.parents)):
        if parent.is_symlink():
            raise RuntimeError(f"Lien interdit dans un chemin moteur : {parent}")


def dossier_prive(chemin):
    sans_liens(chemin)
    chemin.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chown(chemin, 0, 0)
    os.chmod(chemin, 0o700)


def ecrire_json(chemin, valeur):
    etat.ecrire_prive(chemin, json.dumps(valeur, ensure_ascii=False, indent=2) + "\n")


def copier(source, destination, verifier=lambda: None):
    """Copie physique vérifiée ; garde UID/GID/modes, jamais les liens source."""
    verifier()
    sans_liens(source)
    sans_liens(destination)
    infos = source.lstat()
    if stat.S_ISDIR(infos.st_mode):
        destination.mkdir(mode=0o700)
        for enfant in sorted(source.iterdir()):
            copier(enfant, destination / enfant.name, verifier)
        synchroniser_dossier(destination)
    elif stat.S_ISREG(infos.st_mode):
        empreinte = hashlib.sha256()
        # O_NOFOLLOW complète l'inventaire ; les producteurs sont gelés à la capture.
        fd = os.open(source, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as entree, destination.open("xb") as sortie:
            while bloc := entree.read(65536):
                verifier()
                empreinte.update(bloc)
                sortie.write(bloc)
            sortie.flush()
            os.fsync(sortie.fileno())
        controle = hashlib.sha256()
        with destination.open("rb") as copie:
            while bloc := copie.read(65536):
                verifier()
                controle.update(bloc)
        if empreinte.digest() != controle.digest():
            raise RuntimeError(f"Copie non conforme : {source}")
    else:
        raise RuntimeError(f"Objet non copiable sans risque : {source}")
    os.chown(destination, infos.st_uid, infos.st_gid)
    os.chmod(destination, stat.S_IMODE(infos.st_mode))
    if os.name == 'posix':
        fd = os.open(destination, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    verifier()


def entrees_home(home):
    # Inclure les noms non canoniques qui influencent home_contient_general().
    return sorted(p for p in home.iterdir() if p.name.startswith("general"))


class Linux:
    """Backend réel : jamais de repli silencieux vers un faux gel."""
    def __init__(self, configuration):
        if os.name != "posix" or os.geteuid() != 0:
            raise RuntimeError("Le cycle sécurisé exige Linux et root.")
        self.configuration = configuration
        self.uids = [pwd.getpwnam(configuration["acteurs"][j]["proprietaire_linux"]).pw_uid
                     for j in configuration["joueurs"]]
        if 0 in self.uids or len(set(self.uids)) != len(self.uids):
            raise RuntimeError("Les joueurs exigent deux comptes non-root distincts.")
        self.groupes = [Path(f"/sys/fs/cgroup/user.slice/user-{uid}.slice") for uid in self.uids]
        self.geles = []
        self.journal = configuration["game_path"] / "systeme/gel_survie.json"

    def verifier_processus(self):
        attendus = dict(zip(self.uids, [str(p.relative_to('/sys/fs/cgroup')) for p in self.groupes]))
        for proc in Path('/proc').iterdir():
            if not proc.name.isdecimal():
                continue
            try:
                texte = (proc / 'status').read_text()
                ligne = next(l for l in texte.splitlines() if l.startswith('Uid:'))
                uids = {int(n) for n in ligne.split()[1:]}
                groupe = (proc / 'cgroup').read_text().strip().removeprefix('0::').lstrip('/')
            except (FileNotFoundError, ProcessLookupError):
                continue
            for uid in uids & attendus.keys():
                if not (groupe == attendus[uid] or groupe.startswith(attendus[uid] + '/')):
                    raise RuntimeError(f"Processus joueur hors confinement : PID {proc.name}, UID {uid}")
        courant = Path('/proc/self/cgroup').read_text()
        if any(f'/user-{uid}.slice' in courant for uid in self.uids):
            raise RuntimeError("Lancer le moteur depuis un compte administrateur distinct des joueurs.")

    def preparer(self):
        if not Path('/sys/fs/cgroup/cgroup.controllers').exists():
            raise RuntimeError("cgroup v2 requis.")
        game = self.configuration['game_path']
        for parent in (game, *game.parents):
            infos = parent.stat()
            if infos.st_uid != 0 or (infos.st_mode & 0o022 and not infos.st_mode & stat.S_ISVTX):
                raise RuntimeError(f'Parent modifiable par un tiers : {parent}')
        grp.getgrnam(self.configuration['groupe_allie'])
        if self.journal.exists():
            raise RuntimeError("Journal de gel présent : diagnostic administratif requis.")
        for uid in self.uids:
            # Une slice vide StopWhenUnneeded disparaît immédiatement. Le
            # gestionnaire utilisateur maintient la slice, même sans SSH ouvert.
            subprocess.run(['systemctl', 'start', f'user@{uid}.service'], check=True, timeout=15)
        self.verifier_processus()
        for groupe in self.groupes:
            if (groupe / 'cgroup.freeze').read_text().strip() != '0':
                raise RuntimeError(f"Groupe déjà gelé : {groupe}")

    def annoncer(self, message):
        subprocess.run(['wall', '-n', '-t', '2', '-g', self.configuration['groupe_allie']],
                       input=message + '\n', text=True, check=True, timeout=5)

    def geler(self):
        self.verifier_processus()
        try:
            for groupe in self.groupes:
                if (groupe / 'cgroup.freeze').read_text().strip() != '0':
                    raise RuntimeError(f"Gel extérieur détecté : {groupe}")
                self.geles.append(groupe)
                ecrire_json(self.journal, {'pid': os.getpid(), 'groupes': [str(p) for p in self.geles]})
                (groupe / 'cgroup.freeze').write_text('1')
            limite = time.monotonic() + 15
            while not all('frozen 1' in (p / 'cgroup.events').read_text() for p in self.geles):
                if time.monotonic() > limite:
                    raise TimeoutError("Impossible de confirmer le gel.")
                time.sleep(0.01)
            self.verifier_gel()
        except BaseException:
            self.degeler()
            raise

    def verifier_gel(self):
        self.verifier_processus()
        if len(self.geles) != len(self.groupes) or not all(
                'frozen 1' in (p / 'cgroup.events').read_text() for p in self.geles):
            raise RuntimeError("Le gel a été interrompu : capture/publication abandonnée.")

    def degeler(self):
        erreurs = []
        for groupe in self.geles:
            try:
                (groupe / 'cgroup.freeze').write_text('0')
            except FileNotFoundError:
                pass  # une slice disparue ne peut plus contenir de joueur gelé
            except OSError as erreur:
                erreurs.append(erreur)
        if erreurs:
            raise RuntimeError('Dégel incomplet : utiliser le journal pour la récupération.') from erreurs[0]
        self.geles.clear()
        if self.journal.exists():
            self.journal.unlink()
            synchroniser_dossier(self.journal.parent)


class Generations:
    def __init__(self, configuration, backend=None, horloge=None, dormir=None, monotone=None):
        self.c = configuration
        self.backend = backend if backend is not None else Linux(configuration)
        self.horloge = horloge or time.time
        self.dormir = dormir or time.sleep
        self.monotone = monotone or time.monotonic
        self.game = configuration['game_path']
        self.homes = {j: next(z['chemin'] for z in generaux.zones_generaux(j, configuration)
                              if z['position'] == 'home') for j in configuration['joueurs']}
        self.gid = grp.getgrnam(configuration['groupe_allie']).gr_gid
        self.home_stage = configuration.get('publication_homes_path', Path('/home/.mythodea-publication'))
        self.generation = None

    def preparer(self):
        import minuterie
        for nom in ('duree_gel_secondes', 'duree_consultation_secondes', 'seuil_capture_secondes'):
            minuterie.valider_duree(self.c[nom])
        if self.c['seuil_capture_secondes'] <= self.c['duree_gel_secondes']:
            raise ValueError('Le seuil de capture doit dépasser le gel minimum.')
        for chemin in (self.game, *self.homes.values()):
            sans_liens(chemin)
        dossier_prive(self.game / 'systeme')
        dossier_prive(self.game / 'systeme/generations')
        dossier_prive(self.home_stage)
        # Une partition dédiée /home/game n'oblige pas à déplacer les homes.
        for home in self.homes.values():
            if home.stat().st_dev != self.home_stage.stat().st_dev:
                raise RuntimeError("Le staging des homes doit être sur leur système de fichiers.")
        for nom in config.ETATS_METIER:
            p = self.game / 'systeme' / nom
            if p.exists():
                sans_liens(p)
                os.chown(p, 0, 0)
                os.chmod(p, 0o600)
        for d in (self.game / 'rapport', self.game / 'rapport/territoires', self.game / 'clocher'):
            sans_liens(d)
            d.mkdir(parents=True, exist_ok=True)
            os.chown(d, 0, self.gid)
            os.chmod(d, 0o750)
        with rapports.droits_allies(self.gid):
            for fichier in (self.game / 'rapport').rglob('*'):
                sans_liens(fichier)
                if fichier.is_file():
                    if fichier.stat().st_nlink != 1:
                        raise RuntimeError(f'Rapport lié à un autre fichier : {fichier}')
                    rapports.proteger_rapport(fichier)
        self.backend.preparer()

    def afficher(self, tour, phase, restant=None, detail=''):
        texte = f"TOUR : {tour}\nPHASE : {phase.upper()}\n"
        if restant is not None:
            secondes = max(0, int(restant + 0.999))
            texte += f"TEMPS RESTANT : {secondes // 60:02}:{secondes % 60:02}\n"
        if detail:
            texte += detail + '\n'
        repertoire = self.game / 'clocher'
        repertoire.mkdir(parents=True, exist_ok=True)
        courant = repertoire / 'etat_tour.txt'
        etat.ecrire_prive(courant, texte)
        os.chown(courant, 0, self.gid)
        os.chmod(courant, 0o640)
        suivi = repertoire / 'suivi_tour.log'
        sans_liens(suivi)
        fd = os.open(suivi, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'a', encoding='utf-8') as f:
            os.chown(suivi, 0, self.gid)
            os.chmod(suivi, 0o640)
            f.write(texte + '\n')

    def attendre(self, cycle):
        import minuterie
        minuterie.attendre_jusqua(cycle['echeance'], self.horloge, self.dormir,
            observer=lambda restant: self.afficher(cycle['tour'], cycle['phase'], restant))

    def marquer(self, tour, phase, **autres):
        cycle = {'tour': tour, 'phase': phase, **autres}
        if self.generation:
            cycle['generation'] = self.generation.name
        precedent = etat.charger_cycle_survie(self.c) or {}
        if 'generation_active' in precedent:
            cycle.setdefault('generation_active', precedent['generation_active'])
        etat.sauvegarder_cycle_survie(cycle, self.c)
        return cycle

    def capturer(self, tour):
        import crypte
        self.generation = self.game / 'systeme/generations' / f'g{tour:06}-{uuid.uuid4().hex[:12]}'
        dossier_prive(self.generation)
        with crypte.VERROU:
            self.marquer(tour, 'capture')
        self.backend.annoncer(f'FIN DU TOUR {tour}\nRÉSOLUTION EN COURS\nPAUSE : 10 secondes minimum')
        self.afficher(tour, 'capture', detail='FIN DU TOUR\nRESOLUTION EN COURS\nGEL DEMANDE')
        self.backend.geler()
        debut = self.monotone()
        derniere = [-1]
        def verifier():
            ecoule = self.monotone() - debut
            if ecoule >= self.c['seuil_capture_secondes']:
                raise TimeoutError('Seuil de sécurité de capture dépassé ; récupération requise.')
            if int(ecoule) != derniere[0]:
                self.backend.verifier_gel()
                self.afficher(tour, 'capture', detail='FIN DU TOUR\nRESOLUTION EN COURS\nJOUEURS GELES\n'
                              + ('PROLONGATION TECHNIQUE' if ecoule >= self.c['duree_gel_secondes']
                                 else 'PAUSE : 10 secondes'))
                derniere[0] = int(ecoule)
        try:
            crypte.clore(self.c)
            capture = self.generation / 'capture'
            dossier_prive(capture)
            dossier_prive(capture / 'game')
            dossier_prive(capture / 'homes')
            for source in (*self.c['territoires'], self.c['repli_path']):
                if source.exists():
                    copier(source, capture / 'game' / source.name, verifier)
            dossier_prive(capture / 'game/systeme')
            for nom in config.ETATS_METIER:
                source = self.game / 'systeme' / nom
                if source.exists():
                    copier(source, capture / 'game/systeme' / nom, verifier)
            for j, home in self.homes.items():
                dossier_prive(capture / 'homes' / j)
                for source in entrees_home(home):
                    copier(source, capture / 'homes' / j / source.name, verifier)
            verifier()
            ecrire_json(self.generation / 'manifeste.json', {'tour': tour, 'capture_validee': True,
                        'etats_metier': list(config.ETATS_METIER), 'generation': self.generation.name})
            while self.monotone() - debut < self.c['duree_gel_secondes']:
                verifier()
                self.dormir(min(0.25, self.c['duree_gel_secondes'] - (self.monotone() - debut)))
            self.backend.verifier_gel()
        finally:
            self.backend.degeler()
        copier(capture, self.generation / 'travail')
        travail = self.generation / 'travail'
        profil = dict(self.c, game_path=travail / 'game',
                      territoires=[travail / 'game' / p.name for p in self.c['territoires']],
                      repli_path=travail / 'game/repli')
        return profil, {j: travail / 'homes' / j for j in self.homes}

    def preparer_publication(self):
        travail = self.generation / 'travail'
        public = self.generation / 'publication'
        dossier_prive(public)
        copier(travail / 'game', public / 'game')
        dossier_prive(public / 'anciens')
        stage = self.home_stage / self.generation.name
        dossier_prive(stage)
        copier(travail / 'homes', stage / 'nouveaux')
        dossier_prive(stage / 'anciens')
        return public, stage

    def publier(self, tour, public, stage, defaite):
        self.marquer(tour, 'publication')
        journal = {'generation': self.generation.name, 'termine': False, 'operations': []}
        fichier = self.generation / 'publication.json'
        ecrire_json(fichier, journal)
        self.backend.annoncer('PUBLICATION DU TOUR\nBRÈVE PAUSE TECHNIQUE')
        self.backend.geler()
        try:
            def remplacer(source, destination, ancien):
                self.backend.verifier_gel()
                for p in (source, destination, ancien):
                    sans_liens(p)
                if destination.parent.stat().st_dev != source.parent.stat().st_dev:
                    raise RuntimeError('Publication inter-systèmes de fichiers refusée.')
                op = {'source': str(source), 'destination': str(destination), 'ancien': str(ancien),
                      'etat': 'preparee'}
                journal['operations'].append(op)
                ecrire_json(fichier, journal)
                if destination.exists():
                    destination.rename(ancien)
                    synchroniser_dossier(destination.parent)
                    synchroniser_dossier(ancien.parent)
                op['etat'] = 'ancien_retire'
                ecrire_json(fichier, journal)
                if source.exists():
                    source.rename(destination)
                    synchroniser_dossier(destination.parent)
                    synchroniser_dossier(source.parent)
                op['etat'] = 'installee'
                ecrire_json(fichier, journal)
            for nom in [p.name for p in self.c['territoires']] + ['repli']:
                remplacer(public / 'game' / nom, self.game / nom, public / 'anciens' / nom)
            for j, home in self.homes.items():
                dossier_prive(stage / 'anciens' / j)
                noms = {p.name for p in entrees_home(home)} | {p.name for p in (stage / 'nouveaux' / j).iterdir()}
                for nom in sorted(noms):
                    remplacer(stage / 'nouveaux' / j / nom, home / nom, stage / 'anciens' / j / nom)
            dossier_prive(public / 'anciens/systeme')
            for nom in config.ETATS_METIER:
                remplacer(public / 'game/systeme' / nom, self.game / 'systeme' / nom,
                          public / 'anciens/systeme' / nom)
            self.permissions_consultation()
            journal['termine'] = True
            ecrire_json(fichier, journal)
            self.marquer(tour, 'defaite' if defaite else 'consultation',
                         generation_active=self.generation.name,
                         **({} if defaite else {'echeance': self.horloge() + self.c['duree_consultation_secondes']}))
        finally:
            self.backend.degeler()

    def permissions_consultation(self):
        # Mesure de confort, pas une frontière de sécurité : les propriétaires
        # peuvent rétablir leurs modes. Les homes eux-mêmes restent intacts.
        racines = [p / j for p in (*self.c['territoires'], self.c['repli_path']) for j in self.homes]
        racines += [p for home in self.homes.values() for p in entrees_home(home)]
        for racine in racines:
            if racine.exists():
                for p in [racine, *racine.rglob('*')]:
                    sans_liens(p)
                    os.chmod(p, stat.S_IMODE(p.stat().st_mode) & ~0o222)

    def permissions_actions(self):
        # Restaure seulement les permissions des entrées du jeu, jamais leur UID.
        racines = [p / j for p in (*self.c['territoires'], self.c['repli_path']) for j in self.homes]
        racines += [p for home in self.homes.values() for p in entrees_home(home)]
        for racine in racines:
            if racine.exists():
                for p in [racine, *racine.rglob('*')]:
                    sans_liens(p)
                    os.chmod(p, 0o700 if p.is_dir() else 0o600)
        # Les documents administrateur doivent rester lisibles par leur joueur.
        import crypte
        crypte.preparer(self.c)

    def erreur(self, tour, erreur):
        self.marquer(tour, 'recuperation', erreur=str(erreur))
        self.afficher(tour, 'recuperation', detail='INTERVENTION ADMINISTRATEUR REQUISE\n' + str(erreur))
