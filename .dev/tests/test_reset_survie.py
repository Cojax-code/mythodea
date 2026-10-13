"""Copie Bash isolée : chemins temporaires, comptes/droits/montages simulés.

Le vrai contrôle Python du montage est testé dans test_stockage.py.
Aucun paramètre de redirection dangereux n'est exposé en production.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
BASH = (str(Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/bin/bash.exe')
        if os.name == 'nt' else shutil.which('bash'))


@unittest.skipUnless(BASH and Path(BASH).exists(), 'Bash requis')
class ResetSurvie(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mythodea-reset-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'depot avec espaces'
        self.game = self.root / 'game'
        self.home = self.root / 'home'
        self.cg = self.root / 'cgroup'
        self.state = self.root / 'simulation'
        for p in (self.repo / 'bash', self.repo / 'python', self.game, self.home,
                  self.cg, self.state, self.root / 'systemd'):
            p.mkdir(parents=True)
        (self.cg / 'cgroup.controllers').touch()
        for name in ('appels', 'processus', 'montages'):
            (self.state / name).touch()
        for name in ('reset_survie.sh', 'stockage.sh'):
            texte = (REPO / 'bash' / name).read_text(encoding='utf-8')
            # Redirection seulement de la copie : les vrais chemins restent inaccessibles.
            for original, cible in (('/home', self.home), ('/game', self.game),
                                    ('/sys/fs/cgroup', self.cg), ('/run/systemd/system', self.root / 'systemd')):
                texte = texte.replace(original, cible.as_posix())
            texte = texte.replace('$EUID', '${RESET_TEST_EUID}')
            (self.repo / 'bash' / name).write_text(texte, encoding='utf-8', newline='\n')
        config = (REPO / 'python/config.py').read_text(encoding='utf-8').replace('/game', self.game.as_posix())
        (self.repo / 'python/config.py').write_text(config, encoding='utf-8')
        (self.repo / 'python/crypte_installer.py').touch()
        self.envfile = self.root / 'simulation.bash'
        self.envfile.write_text(r'''
log() { printf '%s\n' "$*" >> "$RESET_STATE/appels"; }
getent() { [[ -f "$RESET_STATE/$1-$2" ]]; }
id() { case "$2" in j1) echo 1001 ;; j2) echo 1002 ;; *) return 1 ;; esac; }
useradd() {
    log "useradd $*"
    local joueur="${@: -1}"
    touch "$RESET_STATE/passwd-$joueur" "$RESET_STATE/group-$joueur"
    mkdir -p "$RESET_HOME/$joueur"
}
groupadd() { log "groupadd $*"; touch "$RESET_STATE/group-$1"; }
usermod() {
    log "usermod $*"
    if [[ ${RESET_NEW_LOCK:-0} == 1 ]]; then
        mkdir -p "$RESET_GAME/.systeme"
        echo 123 > "$RESET_GAME/.systeme/verrou_cycle_survie"
    fi
}
install() {
    log "install $*"
    [[ $# -eq 8 && $1 == -d && $2 == -o && $4 == -g && $6 == -m ]] || return 2
    mkdir -p -- "$8"
}
chown() { log "chown $*"; }
chmod() { log "chmod $*"; }
ps() { cat "$RESET_STATE/processus"; }
findmnt() { cat "$RESET_STATE/montages"; }
systemctl() { :; }
loginctl() { :; }
python3() {
    log "python3 $*"
    if [[ $1 == */crypte_installer.py ]]; then
        [[ -s "$RESET_GAME/.systeme/verrou_cycle_survie" ]] || return 93
        # Un moteur concurrent ne doit pas pouvoir recréer son verrou exclusif.
        if (set -o noclobber; echo concurrent > "$RESET_GAME/.systeme/verrou_cycle_survie") 2>/dev/null; then return 94; fi
        [[ ${RESET_INSTALL_FAIL:-0} == 0 ]] || return 9
        [[ ${RESET_LEGACY:-0} == 0 ]] || mkdir -p "$RESET_GAME/systeme"
        return 0
    fi
    [[ $# -eq 3 && $1 == -B && $2 == - ]] || return 2
    local code chemin="$3"
    code="$(cat)"
    if [[ "$code" == *config.verifier_partition_plateau* ]]; then
        if [[ ${RESET_MOUNT:-1} == 0 ]]; then echo 'point de montage absent' >&2; return 1; fi
        echo "${RESET_TARGET:-$RESET_GAME}"
        return 0
    fi
    if [[ ${OS:-} == Windows_NT ]]; then chemin="$(cygpath -m "$chemin")"; fi
    printf '%s\n' "$code" | "$RESET_PYTHON" -B - "$chemin"
}
# find -exec lance un binaire, pas une fonction Bash : énumération temporaire ici.
find() {
    log "find $*"
    [[ -s "$RESET_GAME/.systeme/verrou_cycle_survie" ]] || return 93
    [[ ( $1 == "$RESET_GAME" || $1 == "$RESET_GAME/.systeme" ) && $2 == -mindepth && $3 == 1 && $4 == -maxdepth && $5 == 1 ]] || return 90
    [[ ${*:6} == '! -name '* && ${*:9} == '-exec rm -rf --one-file-system -- {} +' ]] || return 91
    local entree exclu="$8"
    while IFS= read -r -d '' entree; do
        [[ ${entree##*/} == "$exclu" ]] || rm -rf --one-file-system -- "$entree"
    done < <(command find "$1" -mindepth 1 -maxdepth 1 -print0)
}
rm() {
    log "rm $*"
    local arg
    for arg in "$@"; do
        case "$arg" in -rf|-f|--one-file-system|--) ;; "$RESET_GAME"/*|"$RESET_HOME"/*) ;; *) return 92 ;; esac
    done
    command rm "$@"
}
''', encoding='utf-8', newline='\n')
        self.env = dict(os.environ, BASH_ENV=self.envfile.as_posix(), RESET_STATE=self.state.as_posix(),
                        RESET_HOME=self.home.as_posix(), RESET_GAME=self.game.as_posix(),
                        RESET_PYTHON=Path(sys.executable).as_posix(), RESET_TEST_EUID='0',
                        PYTHONDONTWRITEBYTECODE='1')
        self.env.pop('PYTHONPATH', None)

    def run_reset(self, **env):
        return subprocess.run([BASH, (self.repo / 'bash/reset_survie.sh').as_posix()],
                              cwd=self.root, env=dict(self.env, **env), capture_output=True,
                              text=True, encoding='utf-8', timeout=30)

    def calls(self):
        return (self.state / 'appels').read_text(encoding='utf-8')

    def refused(self, result, message):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)
        self.assertTrue(self.game.exists())
        self.assertNotIn('rm ', self.calls())

    def test_syntaxe_bash_scripts_administratifs(self):
        for name in ('reset_survie.sh', 'stockage.sh', 'instal.sh', 'nettoyage.sh', 'start.sh'):
            with self.subTest(name=name):
                result = subprocess.run([BASH, '-n', str(REPO / 'bash' / name)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_sans_root(self):
        self.refused(self.run_reset(RESET_TEST_EUID='1000'), 'sudo')
        self.assertEqual(self.calls(), '')

    def test_sans_montage(self):
        self.refused(self.run_reset(RESET_MOUNT='0'), 'point de montage')
        self.assertNotIn('useradd ', self.calls())

    def test_cibles_interdites_meme_si_controle_python_errone(self):
        for target in ('/', self.home.as_posix(), (self.home / 'j1').as_posix(), (self.home / 'j2').as_posix()):
            with self.subTest(target=target):
                self.refused(self.run_reset(RESET_TARGET=target), 'cible de nettoyage interdite')

    def test_verrous_et_gels_anciens_et_actuels(self):
        for directory in ('.systeme', 'systeme'):
            for name, content, message in (('verrou_cycle_survie', str(os.getpid()), 'encore actif'),
                                           ('verrou_cycle_survie', '99999999', 'verrou résiduel'),
                                           ('gel_survie.json', '{}', 'degeler --confirmer')):
                with self.subTest(directory=directory, name=name, content=content):
                    path = self.game / directory / name
                    path.parent.mkdir(exist_ok=True)
                    path.write_text(content)
                    self.refused(self.run_reset(), message)
                    self.assertEqual(path.read_text(), content)
                    path.unlink()

    def test_moteur_sans_verrou(self):
        (self.state / 'processus').write_text('python3 /depot/python/mythodea_v_1_5.py --mode survie\n')
        self.refused(self.run_reset(), 'encore actif')

    def test_gel_cgroup_sans_journal(self):
        (self.state / 'passwd-j1').touch()
        group = self.cg / 'user.slice/user-1001.slice'
        group.mkdir(parents=True)
        for name, content in (('cgroup.freeze', '1'), ('cgroup.events', 'populated 1\nfrozen 1\n')):
            with self.subTest(name=name):
                (group / name).write_text(content)
                self.refused(self.run_reset(), 'degeler --confirmer')
                (group / name).unlink()

    def test_sous_montage(self):
        (self.state / 'montages').write_text(self.game.as_posix() + '/village\n')
        self.refused(self.run_reset(), 'sous-montage')

    def test_verrou_apparu_avant_destruction(self):
        self.refused(self.run_reset(RESET_NEW_LOCK='1'), 'encore actif')

    def test_reset_cache_permissions_homes_crypte_et_idempotence(self):
        inode = self.game.stat().st_ino
        for legacy in ('systeme', 'clocher', 'communication', '.systeme/generations/ancienne',
                       'village/j1/poste', 'village/j2/clocher', 'village/j1/renforts'):
            (self.game / legacy).mkdir(parents=True, exist_ok=True)
        (self.game / '.cache').write_text('ancien')
        (self.game / 'rapport.txt').touch()
        for j in ('j1', 'j2'):
            home = self.home / j
            (home / '.ssh').mkdir(parents=True)
            for name in ('.ssh/authorized_keys', '.bashrc', '.profile', 'notes.txt'):
                (home / name).write_text('personnel intact')
            (home / 'general1').mkdir()
            (home / 'general_invalide').touch()
        for iteration in range(2):
            with self.subTest(iteration=iteration):
                (self.state / 'appels').write_text('')
                result = self.run_reset()
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('=== Reset Survie terminé ===', result.stdout)
                self.assertEqual(self.game.stat().st_ino, inode)
                self.assertEqual({p.name for p in self.game.iterdir()}, {'.systeme'})
                self.assertEqual(list((self.game / '.systeme').iterdir()), [])
                for j in ('j1', 'j2'):
                    home = self.home / j
                    self.assertEqual(list(home.glob('general*')), [])
                    for name in ('.ssh/authorized_keys', '.bashrc', '.profile', 'notes.txt'):
                        self.assertEqual((home / name).read_text(), 'personnel intact')
                    self.assertIn(f'usermod -aG mythodea_allies {j}', self.calls())
                    self.assertIn(f'install -d -o {j} -g {j} -m 700 {home.as_posix()}', self.calls())
                self.assertIn(f'chown root:root {self.game.as_posix()}', self.calls())
                self.assertIn(f'chmod 755 {self.game.as_posix()}', self.calls())
                self.assertIn(f'install -d -o root -g mythodea_allies -m 710 {self.game.as_posix()}/.systeme', self.calls())
                self.assertIn(f'install -d -o root -g root -m 700 {self.home.as_posix()}/.mythodea-publication', self.calls())
                self.assertIn('/python/crypte_installer.py', self.calls())
                self.assertNotIn('nettoyage.sh', self.calls())
                if iteration == 0:
                    self.assertIn('groupadd mythodea_allies', self.calls())
                    for j in ('j1', 'j2'):
                        self.assertIn(f'useradd --create-home --shell /bin/bash {j}', self.calls())
                else:
                    self.assertNotIn('useradd ', self.calls())
                    self.assertNotIn('groupadd ', self.calls())

    def test_echec_installation_et_controle_final(self):
        result = self.run_reset(RESET_INSTALL_FAIL='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('Reset Survie terminé', result.stdout)
        result = self.run_reset(RESET_LEGACY='1')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Ancienne structure incompatible', result.stderr)


if __name__ == '__main__':
    unittest.main()
