"""Lecture Bash réelle et coexistence avec le scanner Crypte, sans partie."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_crypte_scanner import BashSession, RECIPE, observations, verdict


REPLAY = Path(__file__).resolve().parents[2] / 'bash/.interne/replay.sh'


@unittest.skipUnless(sys.platform == 'linux', 'Bash et PTY Linux requis')
class Replay(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='mythodea-replay-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o755)
        self.script = self.root / 'replay.sh'
        shutil.copyfile(REPLAY, self.script)
        shutil.copyfile(REPLAY.with_name('terminal.sh'), self.root / 'terminal.sh')
        self.script.chmod(0o644)
        self.rapport = self.root / 'rapport avec espaces.txt'
        self.rapport.write_text('○ première ligne\n\\ -n %s × dernière ligne', encoding='utf-8')
        self.rapport.chmod(0o644)

    def lancer(self, delai):
        return subprocess.run(['bash', str(self.script), str(self.rapport)],
            env=dict(os.environ, MYTHODEA_DELAI=delai), capture_output=True, text=True, timeout=3)

    def session(self):
        shell = BashSession(self.root, setup=f"source '{self.script}'\nexport MYTHODEA_DELAI=0")
        self.addCleanup(shell.close)
        return shell

    def test_zero_delai_conserve_contenu_et_chemin_avec_espaces(self):
        result = self.lancer('0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, self.rapport.read_text() + '\n')

    def test_delais_invalides_refuses(self):
        for delai in ('-1', 'NaN', 'infinity', '0;false'):
            with self.subTest(delai=delai):
                result = self.lancer(delai)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(result.stdout)

    def test_hooks_preserves_et_crypte_apres_relecture(self):
        shell = self.session()
        shell.command('avant_debug=$(trap -p DEBUG); avant_int=$(trap -p INT); avant_prompt=$PROMPT_COMMAND')
        self.assertIn('première ligne', shell.command(f"replay '{self.rapport}'"))
        sortie = shell.command('[[ $(trap -p DEBUG) == "$avant_debug" && $(trap -p INT) == "$avant_int" && $PROMPT_COMMAND == "$avant_prompt" ]] && echo HOOKS_OK')
        self.assertIn('HOOKS_OK\r\n', sortie)
        shell.command('crypte_commence')
        for commande in RECIPE:
            shell.command(commande)
        shell.command('crypte_fin')
        self.assertEqual(verdict(observations(shell.journal), shell.atelier), 'succes')

    def test_ctrl_c_retour_invite_et_droits_joueur(self):
        shell = self.session()
        shell.command('export MYTHODEA_DELAI=30')
        os.write(shell.fd, f"replay '{self.rapport}'\n".encode())
        import select
        import time
        deadline, sortie = time.monotonic() + 3, b''
        while 'première ligne'.encode() not in sortie and time.monotonic() < deadline:
            if select.select([shell.fd], [], [], .1)[0]:
                sortie += os.read(shell.fd, 65536)
        self.assertIn('première ligne'.encode(), sortie)
        os.write(shell.fd, b'\x03')
        shell.wait_prompt()
        self.assertIn('SHELL_OK', shell.command('echo SHELL_OK'))
        self.rapport.chmod(0o600)
        if os.geteuid() == 0:
            self.assertIn('fichier lisible requis', shell.command(f"replay '{self.rapport}'"))

    def test_replay_pendant_recette_reste_commande_supplementaire(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command(f"replay '{self.rapport}'")
        for commande in RECIPE:
            shell.command(commande)
        shell.command('crypte_fin')
        self.assertNotEqual(verdict(observations(shell.journal), shell.atelier), 'succes')
