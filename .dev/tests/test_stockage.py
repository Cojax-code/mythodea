"""Contrôles de montage simulés : aucune partition ni donnée réelle modifiée."""
import contextlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]


class Stockage(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(sys, 'path', [str(REPO / 'python'), *sys.path]))
        self.stack.enter_context(patch.dict(sys.modules))
        sys.modules.pop('config', None)
        self.config = importlib.import_module('config')

    def verifier(self, target='/game', fsroot='/', options='rw,relatime',
                 devices=None, existe=True, lien=False, erreur=None):
        devices = devices or {'/game': 2, '/': 1, '/home': 1}
        sortie = json.dumps({'filesystems': [{'target': target, 'fsroot': fsroot, 'options': options}]})
        with patch.object(Path, 'is_dir', return_value=existe), \
                patch.object(Path, 'is_symlink', return_value=lien), \
                patch.object(Path, 'stat', autospec=True, side_effect=lambda p: SimpleNamespace(st_dev=devices[p.as_posix()])), \
                patch.object(subprocess, 'run', return_value=SimpleNamespace(stdout=sortie), side_effect=erreur) as commande:
            self.config.verifier_partition_plateau()
        return commande

    def test_racine_officielle_et_profils(self):
        self.assertEqual(self.config.game_path, Path('/game'))
        for mode in ('classique', 'survie'):
            profil = self.config.configuration_mode(mode)
            self.assertEqual(profil['game_path'], Path('/game'))
            self.assertEqual(profil['game_public_path'], Path('/game'))
            self.assertTrue(all(p.is_relative_to(Path('/game')) for p in profil['territoires']))
            self.assertEqual(profil['repli_path'], Path('/game/repli'))

    def test_partition_distincte_acceptee_sans_ecriture(self):
        commande = self.verifier()
        self.assertEqual(commande.call_args.args[0],
                         ['findmnt', '--json', '--mountpoint', '/game', '--output', 'TARGET,FSROOT,OPTIONS'])

    def test_absence_montage_ou_outil_refusee(self):
        for error in (subprocess.CalledProcessError(1, 'findmnt'), FileNotFoundError()):
            with self.subTest(error=type(error).__name__), self.assertRaisesRegex(RuntimeError, 'point de montage'):
                self.verifier(erreur=error)

    def test_racines_dangereuses_refusees_avant_findmnt(self):
        for racine in ('/', '/home', '/home/j1', '/home/j2', '/ailleurs'):
            with self.subTest(racine=racine), patch.object(self.config, 'game_path', Path(racine)), \
                    patch.object(subprocess, 'run') as commande:
                with self.assertRaisesRegex(RuntimeError, 'interdite'):
                    self.config.verifier_partition_plateau()
                commande.assert_not_called()

    def test_dossier_absent_et_symlink_refuses(self):
        for options in ({'existe': False}, {'lien': True}):
            with self.subTest(options=options), self.assertRaisesRegex(RuntimeError, 'sans lien'):
                self.verifier(**options)

    def test_cible_parent_bind_sous_dossier_et_lecture_seule_refuses(self):
        for options in ({'target': '/'}, {'target': '/home'}, {'fsroot': '/donnees'}, {'options': 'ro'}):
            with self.subTest(options=options), self.assertRaisesRegex(RuntimeError, 'partition entière'):
                self.verifier(**options)

    def test_meme_filesystem_que_racine_ou_homes_refuse(self):
        for devices in ({'/game': 1, '/': 1, '/home': 2}, {'/game': 2, '/': 1, '/home': 2}):
            with self.subTest(devices=devices), self.assertRaisesRegex(RuntimeError, 'distincte'):
                self.verifier(devices=devices)

    def test_pas_ancien_chemin_dans_moteur_actif(self):
        for racine in (REPO / 'python', REPO / 'bash'):
            for fichier in racine.rglob('*'):
                if fichier.suffix in ('.py', '.sh', '.txt'):
                    with self.subTest(fichier=fichier.relative_to(REPO)):
                        self.assertNotIn('/home/game', fichier.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
