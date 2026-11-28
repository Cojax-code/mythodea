"""Bash et PTY réels, sous /tmp, sans changer la configuration personnelle."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from test_crypte_scanner import BashSession, RECIPE, observations, verdict

TERMINAL = Path(__file__).resolve().parents[2] / 'bash/.interne/terminal.sh'


@unittest.skipUnless(sys.platform == 'linux', 'PTY Linux requis')
class TerminalPi(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='mythodea-terminal-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.root.chmod(0o755)
        self.script = self.root / 'terminal.sh'
        shutil.copyfile(TERMINAL, self.script)
        self.script.chmod(0o644)

    def session(self, extra=''):
        # Conserver le marqueur PTY de l'oracle, après avoir relevé le vrai PS1.
        setup = f'''
source '{self.script}'
ancien_prompt=0
PROMPT_COMMAND=('((ancien_prompt+=1))')
trap 'ancien_debug=present' DEBUG
_mythodea_prompt_test() {{ _mythodea_prompt; vrai_ps1=$PS1; PS1='CRYPTE_TEST> '; }}
_mythodea_installer_prompt
PROMPT_COMMAND[1]=_mythodea_prompt_test
{extra}
'''
        shell = BashSession(self.root, setup=setup)
        self.addCleanup(shell.close)
        return shell

    def test_hooks_existants_historique_et_recette_completent(self):
        shell = self.session()
        self.assertIn('present', shell.command('echo "$ancien_debug"'))
        self.assertIn('ANCIEN_OK', shell.command('(( ancien_prompt > 1 )) && echo ANCIEN_OK'))
        shell.command('crypte_commence')
        for commande in RECIPE:
            shell.command(commande)
        shell.command('crypte_fin')
        self.assertEqual(verdict(observations(shell.journal), shell.atelier), 'succes')
        self.assertIn('mkdir appel', shell.command('history 12'))

    def test_cwd_remplace_et_dossier_supprime(self):
        home = self.root / 'home'
        home.mkdir(mode=0o755)
        courant = home / 'general1'
        courant.mkdir(mode=0o755)
        (courant / 'version').write_text('ancien')
        shell = self.session(f"export HOME='{home}'")
        shell.command(f"cd '{courant}'")
        courant.rename(home / 'archive')
        courant.mkdir(mode=0o755)
        (courant / 'version').write_text('nouveau')
        shell.command(':')  # Le prochain retour à l'invite rafraîchit le cwd.
        self.assertIn('nouveau', shell.command('cat version'))
        shutil.rmtree(courant)
        self.assertIn('retour au home', shell.command(':'))
        self.assertIn(str(home), shell.command('pwd'))

    def test_couleurs_reactivation_redirection_et_donnees_non_fiables(self):
        shell = self.session()
        shell.command('export TERM=xterm-256color MYTHODEA_COULEURS=1')
        self.assertIn('\x1b[32m', shell.command("_mythodea_afficher 'Réussite : progression'"))
        self.assertIn('\\[\\e[36m\\]', shell.command('printf "%s\\n" "$vrai_ps1"'))
        shell.command('export MYTHODEA_COULEURS=0')
        self.assertNotIn('\x1b[32m', shell.command("_mythodea_afficher 'Réussite'"))
        shell.command('export MYTHODEA_COULEURS=1')
        self.assertIn('\x1b[32m', shell.command("_mythodea_afficher 'Réussite'"))
        sortie = shell.command("_mythodea_afficher $'Réussite\\e]0;INJECTION\\a' > propre; cat propre")
        self.assertNotIn('\x1b]', sortie)
        self.assertNotIn('\x1b[32m', sortie)


if __name__ == '__main__':
    unittest.main()
