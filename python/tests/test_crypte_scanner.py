"""Prototype Crypte : vrais Bash interactifs et signaux de terminal, sans partie.

Le journal du shell est une observation NON fiable, jamais une autorisation de jeu.
L'oracle ci-dessous vérifie la séquence observée ; il ne crée aucune récompense.
"""
import json
import os
from pathlib import Path
import select
import shutil
import signal
import sys
import tempfile
import time
import unittest

if sys.platform == 'linux':
    import pty


SCRIPT = Path(__file__).resolve().parents[2] / 'bash/prototype_crypte_scan.sh'
RECIPE = ('mkdir appel', 'touch appel/cavalerie', 'cp appel/cavalerie appel/offrande',
          'mv appel/offrande appel/poulin')
PROMPT = b'CRYPTE_TEST> '
FIELDS = ('event', 'line', 'command', 'status', 'cwd', 'history', 'kind', 'pid')


def observations(path):
    data = path.read_bytes().split(b'\0')
    if data[-1] != b'' or (len(data) - 1) % len(FIELDS):
        raise AssertionError('Journal tronqué : aucune réussite admissible')
    return [dict(zip(FIELDS, (s.decode() for s in data[i:i + len(FIELDS)])))
            for i in range(0, len(data) - 1, len(FIELDS))]


def verdict(events, atelier):
    """Vérification pédagogique seulement, séparée du scanner Bash."""
    step, pending, started, ended, failure = 0, False, False, False, None
    for event in events:
        kind = event['event']
        if kind == 'start':
            if started:
                failure = failure or 'double debut'
            started = True
        elif kind == 'before':
            if event['cwd'] != str(atelier):
                failure = failure or 'hors atelier'
            if not event['history'].endswith('/1'):
                failure = failure or 'historique indisponible'
            if event['line'] == 'crypte_fin' and event['command'] == 'crypte_fin':
                continue
            if step >= len(RECIPE) or event['line'] != RECIPE[step]:
                failure = failure or 'ligne inattendue'
            elif event['kind'] != 'file' or event['command'] != RECIPE[step]:
                failure = failure or 'commande remplacee'
            if pending:
                failure = failure or 'plusieurs commandes avant invite'
            pending = True
        elif kind == 'after':
            if not pending:
                failure = failure or 'resultat sans commande'
            if event['status'] != '0':
                failure = failure or 'code retour ' + event['status']
            pending = False
            step += 1
        elif kind in ('interrupt', 'close', 'refused', 'unobserved'):
            failure = failure or kind
        elif kind == 'component':
            failure = failure or 'commande supplementaire'
        elif kind == 'end':
            if ended or not started or pending or step != len(RECIPE):
                failure = failure or 'fin prematuree ou repetee'
            ended = True
    return failure or ('succes' if ended else 'inachevee')


class BashSession:
    def __init__(self, root, setup='', source=SCRIPT, atelier=None, uid=65534, gid=65534, groups=()):
        self.atelier = atelier or root / 'atelier'
        self.atelier.mkdir(exist_ok=True)
        self.journal = root / 'observations.bin'
        self.journal.touch()
        # Reproduit un script administrateur hors du home et de l'atelier.
        admin = root / 'admin'
        admin.mkdir(mode=0o755)
        script = admin / 'scanner.sh'
        shutil.copyfile(source, script)
        script.chmod(0o444)
        rc = admin / 'bashrc'
        rc.write_text(f"PS1='CRYPTE_TEST> '\nPS2='CRYPTE_SUITE> '\n"
                      f"HISTFILE=/dev/null\nexec 9>>'{self.journal}'\n"
                      f"cd -- '{self.atelier}'\n{setup}\nsource '{script}'\n")
        rc.chmod(0o444)
        if os.geteuid() == 0:
            # Aucun compte à créer : UID nobody dans un bac à sable temporaire.
            root.chmod(0o755)
            os.chown(self.atelier, uid, gid)
            os.chown(self.journal, uid, gid)
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            if os.geteuid() == 0:
                os.setgroups(list(groups))
                os.setgid(gid)
                os.setuid(uid)
            os.execve('/bin/bash', ['bash', '--noprofile', '--rcfile', str(rc), '-i'],
                      {**os.environ, 'TERM': 'dumb', 'LC_ALL': 'C'})
        self.output = b''
        self.wait_prompt()

    def wait_prompt(self, timeout=5):
        deadline = time.monotonic() + timeout
        data = b''
        while time.monotonic() < deadline:
            ready, _, _ = select.select([self.fd], [], [], max(0, min(.1, deadline - time.monotonic())))
            if ready:
                data += os.read(self.fd, 65536)
                if data.endswith(PROMPT):
                    self.output += data
                    return data.decode(errors='replace')
        raise AssertionError(f'Pas de retour à l’invite : {data!r}')

    def command(self, line):
        os.write(self.fd, line.encode() + b'\n')
        return self.wait_prompt()

    def events(self):
        return observations(self.journal)

    def close(self):
        if self.pid is None:
            return
        if self.fd is not None:
            os.close(self.fd)  # véritable fermeture du terminal, SIGHUP
            self.fd = None
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if os.waitpid(self.pid, os.WNOHANG)[0]:
                self.pid = None
                return
            # Attente du processus de test, indépendante du timer moteur simulé.
            select.select([], [], [], .01)
        os.kill(self.pid, signal.SIGKILL)
        os.waitpid(self.pid, 0)
        self.pid = None


@unittest.skipUnless(sys.platform == 'linux' and shutil.which('bash'), 'Bash et PTY Linux requis')
class ScannerCrypte(unittest.TestCase):
    def session(self, setup=''):
        temporary = tempfile.TemporaryDirectory(prefix='mythodea-crypte-scan-')
        self.addCleanup(temporary.cleanup)
        shell = BashSession(Path(temporary.name), setup)
        self.addCleanup(shell.close)
        return shell

    def check(self, shell, expected):
        events = shell.events()
        self.assertEqual(verdict(events, shell.atelier), expected, json.dumps(events, indent=2))
        self.report(shell, expected)

    def report(self, shell, expected):
        # Export facultatif de preuves : choisi par l'administrateur des tests.
        if destination := os.environ.get('CRYPTE_TEST_REPORT'):
            with open(destination, 'a') as output:
                output.write(json.dumps({'test': self.id(), 'verdict': expected,
                                         'events': shell.events()}) + '\n')

    def test_01_sequence_exacte(self):
        shell = self.session()
        shell.command('crypte_commence')
        for line in RECIPE:
            shell.command(line)
        shell.command('crypte_fin')
        self.check(shell, 'succes')
        self.assertEqual(sorted(p.name for p in (shell.atelier / 'appel').iterdir()),
                         ['cavalerie', 'poulin'])
        for nom in ('cavalerie', 'poulin'):
            self.assertEqual((shell.atelier / 'appel' / nom).read_bytes(), b'')

    def test_02_commande_supplementaire(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command(RECIPE[0])
        shell.command('ls')
        shell.command('crypte_fin')
        self.check(shell, 'ligne inattendue')

    def test_03_mauvaise_commande(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command('mkdir autre')
        shell.command('crypte_fin')
        self.check(shell, 'ligne inattendue')

    def test_04_bonne_commande_echoue(self):
        shell = self.session()
        (shell.atelier / 'appel').mkdir()
        shell.command('crypte_commence')
        shell.command(RECIPE[0])
        shell.command('crypte_fin')
        self.check(shell, 'code retour 1')

    def test_05_point_virgule(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command('mkdir appel; touch appel/cavalerie')
        shell.command('crypte_fin')
        self.check(shell, 'ligne inattendue')

    def test_06_pipeline(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command('mkdir appel | cat')
        shell.command('crypte_fin')
        self.check(shell, 'ligne inattendue')

    def test_07_alias_et_fonction(self):
        for setup in ("alias mkdir='mkdir -v'", 'mkdir() { command mkdir "$@"; }'):
            with self.subTest(setup=setup):
                shell = self.session(setup)
                shell.command('crypte_commence')
                shell.command(RECIPE[0])
                shell.command('crypte_fin')
                self.check(shell, 'commande remplacee')

    def test_08_ctrl_c_commande(self):
        # Une commande attendue réellement bloquée : touch sur un FIFO ouvert par
        # redirection serait une autre ligne. Un wrapper PATH garde la ligne exacte.
        shell = self.session()
        binary = shell.atelier.parent / 'bin'
        binary.mkdir()
        slow = binary / 'mkdir'
        slow.write_text('#!/bin/bash\necho COMMANDE_EN_COURS\nexec sleep 30\n')
        slow.chmod(0o755)
        shell.command(f'PATH={binary}:$PATH')
        shell.command('crypte_commence')
        os.write(shell.fd, b'mkdir appel\n')
        deadline = time.monotonic() + 5
        data = b''
        while b'COMMANDE_EN_COURS' not in data and time.monotonic() < deadline:
            if select.select([shell.fd], [], [], .1)[0]:
                data += os.read(shell.fd, 4096)
        self.assertIn(b'COMMANDE_EN_COURS', data)
        os.write(shell.fd, b'\x03')
        shell.wait_prompt()
        shell.command('crypte_fin')
        # Avec job control, SIGINT est adressé au groupe de la commande ; Bash
        # peut seulement en recevoir le statut 128 + SIGINT, pas son trap INT.
        self.check(shell, 'code retour 130')

    def test_09_ctrl_c_invite(self):
        shell = self.session()
        shell.command('crypte_commence')
        os.write(shell.fd, b'texte non execute\x03')
        shell.wait_prompt()
        shell.command('crypte_fin')
        self.check(shell, 'interrupt')

    def test_10_fermeture_session(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command(RECIPE[0])
        shell.close()
        # La fermeture du PTY ne garantit pas l'exécution d'un trap EXIT/HUP.
        # Seule une fin explicite peut valider ; la disparition de session sera
        # aussi à observer par le futur collecteur, jamais seulement par Bash.
        self.assertNotIn('end', [e['event'] for e in shell.events()])
        self.assertNotEqual(verdict(shell.events(), shell.atelier), 'succes')
        self.report(shell, verdict(shell.events(), shell.atelier))

    def test_11_sous_shell(self):
        shell = self.session()
        shell.command('crypte_commence')
        os.write(shell.fd, b'bash --noprofile --norc\n')
        # Le sous-shell lit exit puis le parent retrouve son invite officielle.
        os.write(shell.fd, b'exit\n')
        shell.wait_prompt()
        shell.command('crypte_fin')
        self.check(shell, 'ligne inattendue')

    def test_12_changement_repertoire(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command('cd ..')
        shell.command('crypte_fin')
        self.check(shell, 'ligne inattendue')

    def test_13_historique_desactive_ou_modifie(self):
        for command in ('set +o history', 'history -c', "HISTCONTROL=ignorespace"):
            with self.subTest(command=command):
                shell = self.session()
                shell.command('crypte_commence')
                shell.command(command)
                shell.command(RECIPE[0])
                shell.command('crypte_fin')
                self.check(shell, 'ligne inattendue')

    def test_14_fin_prematuree(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command(RECIPE[0])
        shell.command('crypte_fin')
        self.check(shell, 'fin prematuree ou repetee')

    def test_15_erreur_syntaxe_pendant_recette(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command(RECIPE[0])
        shell.command(')')
        for line in RECIPE[1:]:
            shell.command(line)
        shell.command('crypte_fin')
        self.assertNotEqual(verdict(shell.events(), shell.atelier), 'succes',
                            json.dumps(shell.events(), indent=2))
        self.report(shell, verdict(shell.events(), shell.atelier))

    def test_16_historique_initialement_desactive(self):
        shell = self.session('set +o history\nHISTCONTROL=ignoreboth\nHISTIGNORE="*"')
        shell.command('crypte_commence')
        for line in RECIPE:
            shell.command(line)
        shell.command('crypte_fin')
        self.check(shell, 'succes')
        result = shell.command('[[ -o history ]]; printf "HIST=%s:%s:%s\\n" "$?" "$HISTCONTROL" "$HISTIGNORE"')
        self.assertIn('HIST=1:ignoreboth:*', result)

    @unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0,
                         'root requis pour installer le script puis tester sous UID nobody')
    def test_17_script_administrateur_non_modifiable(self):
        shell = self.session()
        script = shell.atelier.parent / 'admin/scanner.sh'
        self.assertEqual(script.stat().st_uid, 0)
        self.assertEqual(script.stat().st_mode & 0o777, 0o444)
        output = shell.command(f'chmod u+w {script}')
        self.assertIn('Operation not permitted', output)
        output = shell.command(f'echo falsification >> {script}')
        self.assertIn('Permission denied', output)
        output = shell.command(f'rm -f {script}')
        self.assertIn('Permission denied', output)
        shell.command('crypte_commence')
        for line in RECIPE:
            shell.command(line)
        shell.command('crypte_fin')
        self.check(shell, 'succes')
        self.assertEqual(shell.events()[0]['kind'], '65534')

    def test_18_pas_de_troncature_historique(self):
        for size in (5000, -1, 0):
            with self.subTest(size=size):
                shell = self.session(f'HISTSIZE={size}')
                shell.command('crypte_commence')
                for line in RECIPE:
                    shell.command(line)
                shell.command('crypte_fin')
                self.check(shell, 'succes')
                self.assertIn(f'SIZE={size}', shell.command('printf "SIZE=%s\\n" "$HISTSIZE"'))

    def test_19_fin_apres_quatre_commandes_et_ctrl_c_refusee(self):
        shell = self.session()
        shell.command('crypte_commence')
        for line in RECIPE:
            shell.command(line)
        os.write(shell.fd, b'\x03')
        shell.wait_prompt()
        shell.command('crypte_fin')
        self.check(shell, 'interrupt')

    def test_20_fermeture_apres_quatre_commandes_ne_valide_pas(self):
        shell = self.session()
        shell.command('crypte_commence')
        for line in RECIPE:
            shell.command(line)
        shell.close()
        self.assertNotIn('end', [e['event'] for e in shell.events()])
        self.assertNotEqual(verdict(shell.events(), shell.atelier), 'succes')
        self.report(shell, verdict(shell.events(), shell.atelier))

    def test_21_commande_sur_ligne_de_demarrage(self):
        for setup in ('', 'set +o history'):
            with self.subTest(setup=setup):
                shell = self.session(setup)
                shell.command('crypte_commence; ls')
                for ligne in RECIPE:
                    shell.command(ligne)
                shell.command('crypte_fin')
                self.assertNotEqual(verdict(shell.events(), shell.atelier), 'succes',
                                    json.dumps(shell.events(), indent=2))

    def test_pipeline_une_etape_deux_commandes_et_deux_codes(self):
        shell = self.session()
        shell.command('crypte_commence')
        shell.command('lsblk > a.txt')
        sortie = shell.command('cat a.txt | grep "NAME"')
        self.assertRegex(sortie, r'NAME\s+MAJ:MIN')
        shell.command('crypte_fin')
        pipeline = [e for e in shell.events() if e['line'] == 'cat a.txt | grep "NAME"']
        self.assertEqual([(e['event'], e['command'], e['kind']) for e in pipeline],
                         [('before', 'cat a.txt', 'file'), ('component', 'grep "NAME"', 'file')])
        self.assertEqual([e['command'] for e in shell.events() if e['event'] == 'after'], ['0', '0 0'])

    def test_pipeline_code_cat_non_masque_par_grep(self):
        shell = self.session()
        binary = shell.atelier.parent / 'bin'
        binary.mkdir()
        faux_cat = binary / 'cat'
        faux_cat.write_text('#!/bin/bash\nprintf "NAME\\n"\nexit 7\n')
        faux_cat.chmod(0o755)
        shell.command(f'PATH={binary}:$PATH')
        shell.command('crypte_commence')
        shell.command('cat a.txt | grep "NAME"')
        shell.command('crypte_fin')
        apres = [e for e in shell.events() if e['event'] == 'after']
        self.assertEqual([(e['status'], e['command']) for e in apres], [('0', '7 0')])

    def test_pipeline_remplacement_grep_observe(self):
        for setup, genre in (("alias grep='grep -v'", 'alias'),
                              ('grep() { command grep "$@"; }', 'function')):
            with self.subTest(setup=setup):
                shell = self.session(setup)
                shell.command('crypte_commence')
                shell.command('lsblk > a.txt')
                shell.command('cat a.txt | grep "NAME"')
                shell.command('crypte_fin')
                composants = [e for e in shell.events() if e['event'] == 'component']
                self.assertEqual(len(composants), 1)
                self.assertEqual(composants[0]['kind'], genre)
                if genre == 'alias':
                    self.assertNotEqual(composants[0]['command'], 'grep "NAME"')


if __name__ == '__main__':
    unittest.main()
