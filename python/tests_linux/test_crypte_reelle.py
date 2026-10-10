"""Socket, scanner installé et permissions réelles ; comptes temporaires isolés."""
import grp
import json
import os
from pathlib import Path
import pwd
import socket
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '.dev/tests'))
import test_permissions_reelles as reel
from test_crypte_scanner import BashSession
import crypte
import crypte_installer


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'Linux root et systemd requis')
class CrypteReelle(unittest.TestCase):
    setUpClass = classmethod(reel.PermissionsReelles.setUpClass.__func__)
    nettoyer_comptes = classmethod(reel.PermissionsReelles.nettoyer_comptes.__func__)
    en_joueur = reel.PermissionsReelles.en_joueur

    def setUp(self):
        reel.PermissionsReelles.setUp(self)
        self.application = self.root / 'application'
        crypte_installer.installer(self.c, self.application, self.root / 'profil.sh')
        cycle = reel.etat.charger_cycle_survie(self.c)
        cycle['echeance'] = time.time() + 120
        reel.etat.sauvegarder_cycle_survie(cycle, self.c)
        self.collecteur = crypte.Collecteur(self.c)

    def shell(self, j='j1'):
        repertoire = self.root / ('session-' + j)
        repertoire.mkdir()
        compte = pwd.getpwnam(j)
        shell = BashSession(repertoire, source=self.application / 'crypte.bash',
                            atelier=crypte.zone(self.c, j) / 'atelier', uid=compte.pw_uid,
                            gid=compte.pw_gid, groups=(grp.getgrnam('mythodea_allies').gr_gid,))
        groupe = Path(f'/sys/fs/cgroup/user.slice/user-{compte.pw_uid}.slice/mythodea-crypte-test')
        groupe.mkdir()
        (groupe / 'cgroup.procs').write_text(str(shell.pid))
        self.addCleanup(groupe.rmdir)
        self.addCleanup(shell.close)
        if not hasattr(self.collecteur, 'socket'):
            self.enterContext(self.collecteur)
        return shell

    def reussir(self, shell, recette=crypte.RECETTE):
        self.assertIn('tentative ouverte', shell.command('crypte_commence'))
        for ligne in recette:
            sortie = shell.command(ligne)
            self.assertNotIn('Crypte indisponible', sortie)
        self.assertIn('Réussite enregistrée', shell.command('crypte_fin'))

    def test_archers_scanner_socket_publication(self):
        shell = self.shell()
        self.reussir(shell, crypte.RECETTE2)
        self.assertEqual(crypte.charger(self.c)['j1']['a_creer']['recette'], 'recette2')
        reel.survie.resoudre_tour_survie(self.c, gestion=self.g)
        p = crypte.zone(self.c, 'j1') / 'recompense/general2'
        self.assertEqual(p.stat().st_uid, pwd.getpwnam('j1').pw_uid)
        self.assertEqual([len(list((p / b).iterdir())) for b in reel.config.ordre_blocs], [0, 0, 0, 20])
        self.assertEqual(len(list(p.glob('arriere/infanterie*/arc'))), 20)
        self.assertEqual(reel.etat.initialiser_quota_normal('j1'), 1)

    def test_pic_nic_scanner_socket_permissions_publication(self):
        shell = self.shell()
        self.assertIn('tentative ouverte', shell.command('crypte_commence'))
        atelier = crypte.zone(self.c, 'j1') / 'atelier'
        for i, ligne in enumerate(crypte.RECETTE3):
            sortie = shell.command(ligne)
            self.assertNotIn('invalidée', sortie)
            if i in (2, 4):
                self.assertEqual((atelier / 'rempart').stat().st_mode & 0o7777,
                                 0o660 if i == 2 else 0o600)
            if i in (3, 5):
                self.assertIn('-rw-rw----' if i == 3 else '-rw-------', sortie)
        self.assertIn('Réussite enregistrée', shell.command('crypte_fin'))
        self.assertEqual(crypte.charger(self.c)['j1']['a_creer']['recette'], 'recette3')
        reel.survie.resoudre_tour_survie(self.c, gestion=self.g)
        p = crypte.zone(self.c, 'j1') / 'recompense/general2'
        self.assertEqual(p.stat().st_uid, pwd.getpwnam('j1').pw_uid)
        self.assertEqual([len(list((p / b).iterdir())) for b in reel.config.ordre_blocs], [6, 7, 7, 0])
        self.assertEqual(len(list(p.glob('*/infanterie*/pique'))), 20)
        self.assertEqual(reel.generaux.lire_fiche_general(p)['nom_affichage'], 'pic-nic')
        self.assertEqual(reel.etat.initialiser_quota_normal('j1'), 1)

    def test_scanner_socket_uid_et_succes_prive(self):
        self.reussir(self.shell())
        gid = grp.getgrnam('mythodea_allies').gr_gid
        for p, mode in ((self.c['game_path'] / '.systeme', 0o710),
                        (self.collecteur.chemin.parent, 0o710), (self.collecteur.chemin, 0o660)):
            self.assertEqual((p.stat().st_uid, p.stat().st_gid, p.stat().st_mode & 0o777), (0, gid, mode))
        for j in ('j1', 'j2'):
            for p in (self.c['game_path'] / '.systeme', self.collecteur.chemin.parent):
                self.assertNotEqual(self.en_joueur(j, 'import os,sys; os.listdir(sys.argv[1])', p).returncode, 0)
                self.assertNotEqual(self.en_joueur(j, "import pathlib,sys; (pathlib.Path(sys.argv[1]) / 'intrus').touch()", p).returncode, 0)
        donnees = crypte.charger(self.c)
        self.assertIsNotNone(donnees['j1']['a_creer'])
        self.assertIsNone(donnees['j2']['a_creer'])
        self.assertFalse(list((crypte.zone(self.c, 'j1') / 'recompense').iterdir()))
        self.assertFalse(list((crypte.zone(self.c, 'j1') / 'atelier').iterdir()))
        for nom in ('crypte.json', 'crypte_config.json', 'compteur_creation_normale_j1.txt'):
            p = self.c['game_path'] / '.systeme' / nom
            self.assertEqual((p.stat().st_uid, p.stat().st_gid, p.stat().st_mode & 0o777), (0, 0, 0o600))
            code = "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('faux')"
            self.assertNotEqual(self.en_joueur('j1', code, p).returncode, 0)
            self.assertNotEqual(self.en_joueur('j2', code, p).returncode, 0)
            for j in ('j1', 'j2'):
                self.assertNotEqual(self.en_joueur(j, 'import sys; open(sys.argv[1]).read()', p).returncode, 0)

    def test_refus_reel_mauvais_atelier_et_commande_extra(self):
        shell = self.shell()
        shell.command('cd ..')
        self.assertIn('atelier', shell.command('crypte_commence'))
        shell.command(f'cd {crypte.zone(self.c, "j1") / "atelier"}')
        shell.command('crypte_commence')
        shell.command('mkdir appel')
        self.assertIn('invalidée', shell.command('ls'))
        self.assertFalse(list((crypte.zone(self.c, 'j1') / 'atelier').iterdir()))
        self.assertNotIn('Réussite enregistrée', shell.command('crypte_fin'))
        self.assertIn('invalidée', shell.command('crypte_commence; ls'))
        self.assertNotIn('Réussite enregistrée', shell.command('crypte_fin'))
        self.assertIsNone(crypte.charger(self.c)['j1']['dernier_tour'])

    def test_deconnexion_detectee_hors_hook(self):
        shell = self.shell()
        shell.command('crypte_commence')
        shell.command('mkdir appel')
        # Aucun événement de fermeture envoyé : le collecteur observe /proc.
        shell.close()
        limite = time.monotonic() + 3
        while self.collecteur.tentatives and time.monotonic() < limite:
            time.sleep(.02)
        self.assertFalse(self.collecteur.tentatives)
        self.assertFalse(list((crypte.zone(self.c, 'j1') / 'atelier').iterdir()))
        self.assertIsNone(crypte.charger(self.c)['j1']['dernier_tour'])

    def test_publication_et_mv_reels(self):
        self.reussir(self.shell())
        reel.survie.resoudre_tour_survie(self.c, gestion=self.g)
        p = crypte.zone(self.c, 'j1') / 'recompense/general2'
        self.assertTrue(p.exists())  # general1 normal était déjà dans le home.
        self.assertEqual(p.stat().st_uid, pwd.getpwnam('j1').pw_uid)
        self.assertEqual(len(list(p.glob('*/cavalerie*/cheval'))), 20)
        self.g.permissions_actions()
        cible = self.c['game_path'] / 'village/j1/garnison/1/general2'
        code = 'from pathlib import Path; import sys; Path(sys.argv[1]).rename(Path(sys.argv[2]))'
        self.assertEqual(self.en_joueur('j1', code, p, cible).returncode, 0)
        self.assertTrue(cible.exists())
        reel.survie.securite.verifier_tous_les_deplacements(self.c)
        self.assertEqual(reel.etat.charger_positions_generaux()['j1:general2'], 'village')

    def test_republication_ne_recree_pas_recompense(self):
        self.reussir(self.shell())
        original = reel.cycle_linux.ecrire_json
        def panne(chemin, valeur):
            if chemin.name == 'publication.json' and any(o['etat'] == 'ancien_retire' for o in valeur['operations']):
                raise RuntimeError('panne publication Crypte')
            return original(chemin, valeur)
        with patch.object(reel.cycle_linux, 'ecrire_json', side_effect=panne):
            with self.assertRaisesRegex(RuntimeError, 'panne publication Crypte'):
                reel.survie.resoudre_tour_survie(self.c, gestion=self.g)
        with patch.object(crypte, 'materialiser', side_effect=AssertionError('double attribution')):
            reel.survie_admin.republier(self.c, self.g.generation.name)
        d = crypte.charger(self.c)['j1']
        self.assertEqual(len(d['attributions']), 1)
        self.assertIsNone(d['a_creer'])
        self.assertEqual(reel.etat.lire_compteur_general('j1'), 2)

    def test_pdf_et_script_lisibles_non_modifiables(self):
        pdfs = [crypte.zone(self.c, 'j1') / f'grimoire/recette{i}.pdf' for i in (1, 2, 3)]
        code = 'from pathlib import Path; import sys; print(Path(sys.argv[1]).read_bytes()[:8])'
        for pdf in pdfs:
            self.assertEqual(self.en_joueur('j1', code, pdf).returncode, 0)
            self.assertEqual(pdf.stat().st_mode & 0o777, 0o640)
            self.assertNotEqual(self.en_joueur('j2', code, pdf).returncode, 0)
        code = "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('modifie')"
        for p in (*pdfs, self.application / 'crypte.bash', self.application / 'crypte_client.py'):
            self.assertNotEqual(self.en_joueur('j1', code, p).returncode, 0)

    def test_message_malforme_ne_tue_pas_collecteur(self):
        shell = self.shell()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(self.collecteur.chemin))
            s.sendall(b'{"event":"before","line":null}\n')
            with s.makefile('rb') as f:
                reponse = json.loads(f.readline())
        self.assertFalse(reponse['ok'])
        self.assertIn('Format', reponse['erreur'])
        self.reussir(shell)

    def test_marqueurs_administrateur_reellement_utilises(self):
        reel.etat.ecrire_prive(self.c['game_path'] / '.systeme/crypte_config.json',
                              json.dumps({'debut': 'crypte_ouvre', 'fin': 'crypte_ferme'}))
        crypte.preparer(self.c)
        crypte_installer.installer(self.c, self.application, self.root / 'profil.sh')
        self.collecteur = crypte.Collecteur(self.c)
        shell = self.shell()
        self.assertIn('tentative ouverte', shell.command('crypte_ouvre'))
        for ligne in crypte.RECETTE:
            shell.command(ligne)
        self.assertIn('Réussite enregistrée', shell.command('crypte_ferme'))
        self.assertIsNotNone(crypte.charger(self.c)['j1']['a_creer'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
