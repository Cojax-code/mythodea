"""Pic-nic : six étapes, permissions Unix réelles et récompense commune."""
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_crypte
from test_crypte_scanner import BashSession


class PicNic(unittest.TestCase):
    setUp = test_crypte.Crypte.setUp
    activer = test_crypte.Crypte.activer
    message = test_crypte.Crypte.message
    creer = test_crypte.Crypte.creer
    commande = test_crypte.Crypte.commande
    reussir = test_crypte.Crypte.reussir
    etapes_archers = test_crypte.Crypte.etapes_archers
    reussir_archers = test_crypte.Crypte.reussir_archers

    def etapes(self, echec=None):
        self.message('start')
        for i, ligne in enumerate(self.crypte.RECETTE3):
            self.message('before', line=ligne, command=ligne, kind='file', history=f'{i + 1}/1')
            self.message('after', status='1' if i == echec else '0')

    def reussir_piquiers(self):
        self.etapes()
        # Les droits finaux sont vérifiés sans simulation dans les tests Linux ci-dessous.
        with patch.object(self.crypte, 'verifier_rempart'):
            self.message('end')

    def bash(self, lignes=None, avant_fin=None, setup='umask 022'):
        """Exécute vraiment les lignes et transmet leurs observations au collecteur."""
        atelier = self.crypte.zone(self.profil, 'j1') / 'atelier'
        with tempfile.TemporaryDirectory(prefix='mythodea-pic-nic-') as tmp:
            shell = BashSession(Path(tmp), atelier=atelier, setup=setup,
                                uid=os.getuid(), gid=os.getgid())
            try:
                self.message('start')
                shell.command('crypte_commence')
                lus = len(shell.events())
                sorties, modes = [], []
                for ligne in self.crypte.RECETTE3 if lignes is None else lignes:
                    sorties.append(shell.command(ligne))
                    p = atelier / 'rempart'
                    modes.append(stat.S_IMODE(p.stat().st_mode) if p.is_file() else None)
                    for e in shell.events()[lus:]:
                        self.message(e['event'], **{k: e[k] for k in
                                     ('line', 'command', 'status', 'history', 'kind')})
                    lus = len(shell.events())
                if avant_fin:
                    avant_fin(atelier)
                shell.command('crypte_fin')
                for e in shell.events()[lus:]:
                    self.message(e['event'], **{k: e[k] for k in
                                 ('line', 'command', 'status', 'history', 'kind')})
                return sorties, modes, shell.events()
            finally:
                shell.close()

    @unittest.skipUnless(sys.platform == 'linux', 'Bash et permissions Linux réels requis')
    def test_sequence_complete_permissions_et_sorties_visibles(self):
        self.assertEqual(self.crypte.RECETTE3, (
            'touch rempart', 'ls -l rempart', 'chmod 660 rempart',
            'ls -l rempart', 'chmod 600 rempart', 'ls -l rempart'))
        sorties, modes, evenements = self.bash()
        self.assertEqual(modes, [0o644, 0o644, 0o660, 0o660, 0o600, 0o600])
        for index, droits in ((1, '-rw-r--r--'), (3, '-rw-rw----'), (5, '-rw-------')):
            self.assertIn(droits, sorties[index])
        observations_ls = [e for e in evenements if e['event'] == 'before' and e['line'] == 'ls -l rempart']
        self.assertEqual(len(observations_ls), 3)
        self.assertEqual(len({e['history'] for e in observations_ls}), 3)
        self.assertEqual([e['status'] for e in evenements if e['event'] == 'after'], ['0'] * 6)
        self.assertEqual(self.crypte.charger(self.profil)['j1']['a_creer']['recette'], 'recette3')

    @unittest.skipUnless(sys.platform == 'linux', 'Bash Linux requis')
    def test_variations_interdites(self):
        recette = list(self.crypte.RECETTE3)
        variantes = []
        for index, ligne in ((0, 'touch autre'), (2, 'chmod 640 rempart'),
                             (4, 'chmod 660 rempart'), (4, 'chmod 600 ./rempart'),
                             (1, 'ls rempart')):
            variante = recette.copy()
            variante[index] = ligne
            variantes.append(variante)
        variantes += [recette[:i] + recette[i + 1:] for i in (1, 3, 5)]
        variantes += [recette + ['ls -l rempart'], recette + ['pwd'],
                      [recette[i] for i in (0, 1, 4, 3, 2, 5)],
                      recette[:4], recette[:1] + ['ls -l rempart; true'] + recette[2:]]
        for lignes in variantes:
            with self.subTest(lignes=lignes):
                with self.assertRaises(ValueError):
                    self.bash(lignes)
                d = self.crypte.charger(self.profil)['j1']
                self.assertIsNone(d['dernier_tour'])
                self.assertIsNone(d['a_creer'])

    def test_code_retour_non_nul_a_chacune_des_six_etapes(self):
        for index in range(6):
            with self.subTest(etape=index):
                self.etapes(echec=index)
                with self.assertRaises(ValueError):
                    self.message('end')
                self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    @unittest.skipUnless(sys.platform == 'linux', 'Bash Linux requis')
    def test_echec_reel_chmod(self):
        with tempfile.TemporaryDirectory(prefix='mythodea-chmod-echec-') as tmp:
            commande = Path(tmp) / 'chmod'
            commande.write_text('#!/bin/sh\nexit 9\n')
            subprocess.run(['/bin/chmod', '755', str(commande)], check=True)
            with self.assertRaisesRegex(ValueError, 'Commande échouée'):
                self.bash(setup=f'PATH="{tmp}:$PATH"')
            self.assertIsNone(self.crypte.charger(self.profil)['j1']['a_creer'])

    @unittest.skipUnless(sys.platform == 'linux', 'Permissions Linux réelles requises')
    def test_permissions_finales_incorrectes(self):
        for mode in ('660', '644', '700', '1600'):
            with self.subTest(mode=mode):
                def modifier(atelier):
                    subprocess.run(['chmod', mode, str(atelier / 'rempart')], check=True)
                with self.assertRaisesRegex(ValueError, 'permissions 600'):
                    self.bash(avant_fin=modifier)
                self.assertIsNone(self.crypte.charger(self.profil)['j1']['dernier_tour'])

    @unittest.skipUnless(sys.platform == 'linux', 'Fichiers et liens Linux requis')
    def test_fichier_final_incorrect(self):
        def non_vide(a):
            (a / 'rempart').write_text('inattendu')
        def absent(a):
            (a / 'rempart').unlink()
        def dossier(a):
            absent(a)
            (a / 'rempart').mkdir()
        def supplement(a):
            (a / 'autre').touch()
        def lien(a):
            absent(a)
            (a / 'rempart').symlink_to(self.racine / 'exterieur')
        for modifier in (non_vide, absent, dossier, supplement, lien):
            with self.subTest(cas=modifier.__name__):
                with self.assertRaises(ValueError):
                    self.bash(avant_fin=modifier)
                self.assertIsNone(self.crypte.charger(self.profil)['j1']['a_creer'])

    def test_recompense_pic_nic_hors_quota_et_recuperation(self):
        self.etat.sauvegarder_compteur_general('j1', 5)
        self.etat.sauvegarder_quota_normal('j1', 5)
        self.reussir_piquiers()
        with self.assertRaisesRegex(ValueError, 'attente'):
            self.message('start')
        self.creer()
        p = self.crypte.zone(self.profil, 'j1') / 'recompense/general6'
        fiche = self.generaux.lire_fiche_general(p)
        self.assertEqual((fiche['nom'], fiche['nom_affichage']), ('general6', 'pic-nic'))
        self.assertEqual([len(list((p / b).iterdir())) for b in self.config.ordre_blocs], [6, 7, 7, 0])
        self.assertEqual(len(list(p.glob('*/infanterie*/pique'))), 20)
        self.assertFalse(list(p.glob('*/*/arc')) + list(p.glob('*/*/cheval')))
        self.assertEqual(self.etat.initialiser_quota_normal('j1'), 5)
        self.assertEqual(self.rapports.nom_affichage_general(
            {'joueur': 'j1', 'nom': 'general6', 'fiche': fiche}), 'pic-nic')
        self.activer(8)
        with self.assertRaisesRegex(ValueError, 'attente'):
            self.message('start')
        cible = self.config.game_path / 'village/j1/garnison/1/general6'
        p.rename(cible)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertIsNone(self.crypte.charger(self.profil)['j1']['en_attente'])
        cible.rename(p)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general6'], 'repli')

    def test_cooldown_partage_avec_les_deux_recettes(self):
        # Les transitions 1->3, 3->2, 2->3 et 3->1 utilisent toutes le même délai.
        for index, reussir in enumerate((self.reussir, self.reussir_piquiers,
                                        self.reussir_archers, self.reussir_piquiers, self.reussir)):
            tour = 3 + index * 5
            if index:
                self.activer(tour - 1)
                with self.assertRaisesRegex(ValueError, f'tour {tour}'):
                    self.message('start')
            self.activer(tour)
            reussir()
            self.creer(tour)
            p = self.crypte.zone(self.profil, 'j1') / f'recompense/general{index + 1}'
            p.rename(self.config.game_path / 'village/j1/reserve' / p.name)
            self.assertEqual(self.crypte.charger(self.profil)['j1']['dernier_tour'], tour)

    def test_pdf_pic_nic_et_marqueurs(self):
        for j in ('j1', 'j2'):
            pdf = (self.crypte.zone(self.profil, j) / 'grimoire/recette3.pdf').read_bytes()
            self.assertIn(b'pic-nic', pdf)
            self.assertEqual(pdf.count(b'(ls -l rempart) Tj'), 3)
            for texte in (b'-rw-rw----', b'-rw-------', b'umask', b'20 piquiers',
                          b'proprietaire', b'groupe', b'autres'):
                self.assertIn(texte, pdf)
        pdf = self.crypte.recette_pdf({'debut': 'crypte_ouvre', 'fin': 'crypte_ferme'}, 'recette3')
        self.assertIn(b'crypte_ouvre', pdf)
        self.assertIn(b'crypte_ferme', pdf)
        self.assertNotIn(b'crypte_commence', pdf)


if __name__ == '__main__':
    unittest.main()
