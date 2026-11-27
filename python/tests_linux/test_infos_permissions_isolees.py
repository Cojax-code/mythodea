"""UID/GID, droits et copies réels sous /tmp, sans comptes ni plateau de jeu."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cycle_linux
import generaux


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'Linux et root requis')
class InfosPermissions(unittest.TestCase):
    def test_migration_copie_deplacement_et_actions_de_deux_uid(self):
        with tempfile.TemporaryDirectory(prefix='mythodea-infos-') as temporaire:
            racine = Path(temporaire)
            racine.chmod(0o755)
            general = racine / 'general1'
            general.mkdir(mode=0o700)
            os.chown(general, 60001, 60001)
            for nom in ('avant', 'arriere', 'gauche', 'droite', 'notes'):
                p = general / nom
                p.mkdir(mode=0o700)
                os.chown(p, 60001, 60001)
            fiche = general / 'fiche.txt'
            fiche.write_text('evolution_apprise=201\nevolutions_acquises=104\n')
            os.chown(fiche, 60001, 60001)
            fiche.chmod(0o640)
            choix = general / 'QG.txt'
            choix.touch(mode=0o600)
            os.chown(choix, 60001, 60001)
            note = general / 'notes/personnel'
            note.write_text('a conserver')
            os.chown(note, 60001, 60001)
            note.chmod(0o400)
            inode = note.stat().st_ino
            generaux.migrer_infos_general(general)
            self.assertEqual((general / 'info/notes/personnel').stat().st_ino, inode)
            for relatif, mode in (('info', 0o700), ('info/fiche.txt', 0o640),
                                  ('info/QG.txt', 0o600), ('info/notes/personnel', 0o400)):
                infos = (general / relatif).stat()
                self.assertEqual((infos.st_uid, infos.st_gid, infos.st_mode & 0o777),
                                 (60001, 60001, mode))
            copie = racine / 'capture'
            cycle_linux.copier(general, copie)
            publie = racine / 'publication'
            copie.rename(publie)
            code = ('import os,sys; os.setgroups([]); os.setgid(int(sys.argv[1])); '
                    'os.setuid(int(sys.argv[1])); '
                    'p=sys.argv[2]; open(p+"/info/fiche.txt").read(); '
                    'open(p+"/info/QG.txt","w").write("choix"); '
                    'os.mkdir(p+"/avant/infanterie1"); '
                    'open(p+"/avant/infanterie1/arc","w").close()')
            for uid, succes in ((60002, False), (60001, True)):
                resultat = subprocess.run([sys.executable, '-c', code, str(uid), str(publie)],
                                          capture_output=True)
                self.assertEqual(resultat.returncode == 0, succes, resultat.stderr)
            self.assertEqual((publie / 'info/fiche.txt').stat().st_mode & 0o777, 0o640)
            self.assertEqual((publie / 'info/notes/personnel').read_text(), 'a conserver')
