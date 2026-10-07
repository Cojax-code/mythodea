"""Tests destructifs UNIQUEMENT pour leurs comptes temporaires j1/j2.

Exiger une VM Linux dédiée où j1, j2 et mythodea_allies n'existent pas.
Ne touche jamais /home/game ni /home/j1 ou /home/j2. Aucun droit Unix simulé.
"""
import grp
import json
import os
from pathlib import Path
import pwd
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import cycle_linux
import etat
import generaux
import plateau
import rapports
import survie
import survie_admin


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'Linux réel, root et systemd requis')
class PermissionsReelles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for nom in ('j1', 'j2'):
            try:
                pwd.getpwnam(nom)
            except KeyError:
                pass
            else:
                raise RuntimeError('Environnement non isolé : compte existant ' + nom)
        try:
            grp.getgrnam('mythodea_allies')
        except KeyError:
            pass
        else:
            raise RuntimeError('Le groupe mythodea_allies existe déjà : utiliser une VM dédiée.')
        cls.crees = []
        cls.addClassCleanup(cls.nettoyer_comptes)
        subprocess.run(['groupadd', 'mythodea_allies'], check=True)
        cls.groupe_cree = True
        for nom in ('j1', 'j2'):
            subprocess.run(['useradd', '--no-create-home', '--user-group', '--home-dir', '/nonexistent',
                            '--shell', '/usr/sbin/nologin', '--groups', 'mythodea_allies', nom], check=True)
            cls.crees.append(nom)

    @classmethod
    def nettoyer_comptes(cls):
        for nom in reversed(cls.crees):
            uid = pwd.getpwnam(nom).pw_uid
            subprocess.run(['systemctl', 'stop', f'user@{uid}.service'], check=False)
            subprocess.run(['systemctl', 'stop', f'user-{uid}.slice'], check=False)
            subprocess.run(['userdel', nom], check=True)
        if getattr(cls, 'groupe_cree', False):
            subprocess.run(['groupdel', 'mythodea_allies'], check=True)

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='mythodea-linux-')
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.root.chmod(0o755)
        config.game_path = self.root / 'game'
        config.game_path.mkdir(mode=0o755)
        for nom, relatif in {'positions_generaux_path': 'systeme/positions_generaux.txt',
            'fatigue_generaux_path': 'systeme/fatigue_generaux.txt',
            'controle_territoires_path': 'systeme/controle_territoires.txt', 'repli_path': 'repli',
            'meteo_path': 'systeme/meteo.txt', 'rapport_dir': 'rapport',
            'rapport_long_path': 'rapport/rapport_long.txt', 'rapport_court_path': 'rapport/rapport_court.txt',
            'rapports_territoires_dir': 'rapport/territoires'}.items():
            setattr(config, nom, config.game_path / relatif)
        self.c = config.configuration_mode('survie')
        self.c.update(duree_gel_secondes=0, duree_phase_action_secondes=0,
                      duree_consultation_secondes=0, publication_homes_path=self.root / 'staging')
        self.c['homes'] = {j: self.root / 'homes' / j for j in ('j1', 'j2')}
        for j, home in self.c['homes'].items():
            home.mkdir(parents=True)
            compte = pwd.getpwnam(j)
            os.chown(home, compte.pw_uid, compte.pw_gid)
            home.chmod(0o700)
        self.g = cycle_linux.Generations(self.c)
        self.g.preparer()
        survie.ouvrir_tour_survie(self.c)
        self.general = self.c['homes']['j1'] / 'general1'
        (self.general / 'avant/infanterie1').mkdir()
        (self.general / 'avant/infanterie1/arc').touch()
        generaux.donner_permissions_general(self.general, 'j1')

    def en_joueur(self, joueur, code, *args):
        return subprocess.run(['runuser', '-u', joueur, '--', sys.executable, '-c', code, *map(str, args)],
                              text=True, capture_output=True)

    def test_actions_ecriture_uid_gid_et_separation_joueurs_bot(self):
        for j in ('j1', 'j2'):
            home = self.c['homes'][j]
            self.assertEqual(home.stat().st_uid, pwd.getpwnam(j).pw_uid)
            self.assertEqual(self.en_joueur(j, "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('1-2')",
                                           home / 'general1/ordre.txt').returncode, 0)
        interdit = self.en_joueur('j1', "from pathlib import Path; import sys; Path(sys.argv[1]).read_text()",
                                 self.c['homes']['j2'] / 'general1/ordre.txt')
        self.assertNotEqual(interdit.returncode, 0)
        for territoire in self.c['territoires']:
            p = territoire / 'bot'
            self.assertEqual(p.stat().st_mode & 0o777, 0o700)
            self.assertNotEqual(self.en_joueur('j1', 'import os,sys; os.listdir(sys.argv[1])', p).returncode, 0)
        for p in (self.c['game_path'] / 'village/j1/garnison',
                  self.c['game_path'] / 'village/j1/reserve',
                  self.c['game_path'] / 'village/j1/renforts/5', self.c['repli_path'] / 'j1'):
            self.assertEqual(p.stat().st_mode & 0o777, 0o700)

    def test_etats_moteur_prives_y_compris_compteurs(self):
        for p in (self.c['game_path'] / 'systeme').iterdir():
            if p.is_file():
                self.assertEqual((p.stat().st_uid, p.stat().st_gid, p.stat().st_mode & 0o777), (0, 0, 0o600))
                for j in ('j1', 'j2'):
                    self.assertNotEqual(self.en_joueur(j, "import sys; open(sys.argv[1],'a').write('x')", p).returncode, 0)

    def test_capture_reelle_uid_preserve_root_peut_modifier_joueur_non(self):
        prive, _ = self.g.capturer(0)
        p = prive['game_path'].parent / 'homes/j1/general1/ordre.txt'
        self.assertEqual(p.stat().st_uid, pwd.getpwnam('j1').pw_uid)
        self.assertNotEqual(self.en_joueur('j1', "import sys; open(sys.argv[1],'w').write('x')", p).returncode, 0)
        p.write_text('root travaille')
        self.assertEqual(p.read_text(), 'root travaille')

    def test_fd_ouvert_avant_capture_independant_apres_publication(self):
        ordre = self.general / 'ordre.txt'
        with ordre.open('r+b') as fd:
            original = survie._resoudre_tour_capture
            def tardif(c, aleatoire):
                fd.write(b'3-1\n')
                fd.flush()
                return original(c, aleatoire)
            with patch.object(survie, '_resoudre_tour_capture', side_effect=tardif):
                survie.resoudre_tour_survie(self.c, gestion=self.g)
            fd.seek(0)
            fd.write(b'2-2\n')
            fd.flush()
            self.assertEqual(ordre.read_text(), '1-2\n')
        self.assertEqual(self.c['homes']['j1'].stat().st_uid, pwd.getpwnam('j1').pw_uid)

    def test_consultation_lecture_et_retour_droits_actions(self):
        survie.resoudre_tour_survie(self.c, gestion=self.g)
        p = self.general / 'ordre.txt'
        self.assertNotEqual(self.en_joueur('j1', "import sys; open(sys.argv[1],'w').write('x')", p).returncode, 0)
        self.assertEqual(self.en_joueur('j1', 'import sys; print(open(sys.argv[1]).read())', p).returncode, 0)
        self.g.permissions_actions()
        self.assertEqual(self.en_joueur('j1', "import sys; open(sys.argv[1],'w').write('1-2')", p).returncode, 0)

    def test_rapports_allies_et_journal_technique(self):
        with rapports.droits_allies(self.g.gid):
            rapports.preparer_rapports(self.c)
        for p in (config.rapport_court_path, config.rapport_long_path):
            self.assertEqual(p.stat().st_uid, 0)
        self.assertEqual(config.rapport_court_path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(config.rapport_long_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.en_joueur('j1', 'import sys; open(sys.argv[1]).read()', config.rapport_court_path).returncode, 0)
        self.assertNotEqual(self.en_joueur('j1', 'import sys; open(sys.argv[1]).read()', config.rapport_long_path).returncode, 0)

    def test_interruption_et_verrou(self):
        with etat.verrou_cycle_survie(self.c):
            with self.assertRaises(RuntimeError):
                survie.resoudre_tour_survie(self.c, gestion=self.g)
            self.assertEqual((self.c['game_path'] / 'systeme/verrou_cycle_survie').stat().st_mode & 0o777, 0o600)
        with patch.object(survie, 'creer_vague_est', side_effect=RuntimeError('panne injectée')):
            with self.assertRaises(RuntimeError):
                survie.resoudre_tour_survie(self.c, gestion=self.g)
        self.assertEqual(etat.charger_cycle_survie(self.c)['phase'], 'recuperation')
        self.assertFalse(self.g.backend.geles)

    def test_gel_noyau_reel_processus_joueur_reprend_sans_etre_tue(self):
        compte = pwd.getpwnam('j1')
        groupe = self.g.backend.groupes[0] / 'mythodea-test'
        groupe.mkdir(exist_ok=True)
        commandes_r, commandes_w = os.pipe()
        reponses_r, reponses_w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(commandes_w)
            os.close(reponses_r)
            os.read(commandes_r, 1)  # root attend son placement dans le cgroup
            os.setgroups([])
            os.setgid(compte.pw_gid)
            os.setuid(compte.pw_uid)
            with (self.general / 'ordre.txt').open('a') as f:
                os.write(reponses_w, b'R')
                while os.read(commandes_r, 1) == b'W':
                    f.write('x')
                    f.flush()
                    os.write(reponses_w, b'O')
            os._exit(0)
        os.close(commandes_r)
        os.close(reponses_w)
        try:
            (groupe / 'cgroup.procs').write_text(str(pid))
            os.write(commandes_w, b'S')
            self.assertEqual(os.read(reponses_r, 1), b'R')
            self.g.backend.geler()
            os.write(commandes_w, b'W')
            self.assertFalse(select.select([reponses_r], [], [], 0.05)[0])
            self.g.backend.verifier_gel()
            self.g.backend.degeler()
            self.assertTrue(select.select([reponses_r], [], [], 2)[0])
            self.assertEqual(os.read(reponses_r, 1), b'O')
        finally:
            self.g.backend.degeler()
            os.write(commandes_w, b'Q')
            os.close(commandes_w)
            os.close(reponses_r)
            os.waitpid(pid, 0)
            groupe.rmdir()

    def test_arret_brutal_degel_administratif_sans_rejeu_ni_suppression_verrou(self):
        import survie_admin
        pid = os.fork()
        if pid == 0:
            self.g.marquer(0, 'capture')
            self.g.backend.geler()
            os._exit(0)  # simule l'absence totale de finally après un arrêt brutal
        _, statut = os.waitpid(pid, 0)
        self.assertEqual(statut, 0)
        verrou = self.c['game_path'] / 'systeme/verrou_cycle_survie'
        etat.ecrire_prive(verrou, str(pid))
        try:
            self.assertTrue(all('frozen 1' in (p / 'cgroup.events').read_text() for p in self.g.backend.groupes))
            with self.assertRaises(RuntimeError):
                self.g.preparer()
            survie_admin.degeler(self.c)
            self.assertTrue(verrou.exists())
            self.assertEqual(etat.charger_cycle_survie(self.c)['phase'], 'recuperation')
            self.assertTrue(all((p / 'cgroup.freeze').read_text().strip() == '0' for p in self.g.backend.groupes))
            survie_admin.retirer_verrou(self.c)
            self.assertFalse(verrou.exists())
        finally:
            for groupe in self.g.backend.groupes:
                (groupe / 'cgroup.freeze').write_text('0')

    def test_liens_refuses_et_hardlink_source_copie_independamment(self):
        source = self.general / 'ordre.txt'
        lien = self.general / 'lien'
        lien.symlink_to(source)
        try:
            with self.assertRaisesRegex(RuntimeError, 'Lien interdit'):
                self.g.capturer(0)
        finally:
            lien.unlink()
        os.link(source, lien)
        prive, _ = self.g.capturer(0)
        copie = prive['game_path'].parent / 'homes/j1/general1/lien'
        self.assertNotEqual(copie.stat().st_ino, source.stat().st_ino)
        self.assertEqual(copie.stat().st_nlink, 1)

    def test_processus_joueur_hors_slice_refuse_avant_capture(self):
        compte = pwd.getpwnam('j1')
        pret_r, pret_w = os.pipe()
        fin_r, fin_w = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(pret_r)
            os.close(fin_w)
            os.setgroups([])
            os.setgid(compte.pw_gid)
            os.setuid(compte.pw_uid)
            os.write(pret_w, b'R')
            os.read(fin_r, 1)
            os._exit(0)
        os.close(pret_w)
        os.close(fin_r)
        try:
            self.assertEqual(os.read(pret_r, 1), b'R')
            with self.assertRaisesRegex(RuntimeError, 'hors confinement'):
                self.g.backend.geler()
            self.assertFalse(self.g.backend.geles)
        finally:
            os.write(fin_w, b'Q')
            os.close(fin_w)
            os.close(pret_r)
            os.waitpid(pid, 0)

    def test_republication_explicite_apres_interruption_sans_rejouer_metier(self):
        import survie_admin
        original = cycle_linux.ecrire_json
        def panne(chemin, valeur):
            if chemin.name == 'publication.json' and any(o['etat'] == 'ancien_retire' for o in valeur['operations']):
                raise RuntimeError('panne publication')
            return original(chemin, valeur)
        with patch.object(cycle_linux, 'ecrire_json', side_effect=panne):
            with self.assertRaisesRegex(RuntimeError, 'panne publication'):
                survie.resoudre_tour_survie(self.c, gestion=self.g)
        self.assertEqual(etat.charger_cycle_survie(self.c)['phase'], 'recuperation')
        with patch.object(survie, '_resoudre_tour_capture', side_effect=AssertionError('rejeu interdit')):
            survie_admin.republier(self.c, self.g.generation.name)
        self.assertEqual(etat.charger_cycle_survie(self.c)['phase'], 'consultation')
        self.assertTrue(list(self.g.generation.glob('publication.json.interrompu-*')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
