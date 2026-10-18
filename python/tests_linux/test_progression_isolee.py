"""Droits réels des états privés et mémoires, exclusivement sous /tmp."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import formation
import progression
import soldats


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'Linux et root requis')
class ProgressionIsolee(unittest.TestCase):
    def test_etats_prives_et_manuel_non_modifiables_par_joueurs(self):
        with tempfile.TemporaryDirectory(prefix='mythodea-progression-') as dossier:
            racine = Path(dossier)
            racine.chmod(0o755)
            with patch.object(config, 'game_path', racine):
                progression.enregistrer_creation('j1', 'general1', progression.nouvelles_caracteristiques())
                unite = racine / 'infanterie1'
                unite.mkdir(mode=0o700)
                os.chown(unite, 60001, 0)
                (unite / 'arc').touch()
                infos = dict(type='archer', nombre=1, unites=[unite])
                self.assertEqual(soldats.pertes(infos, 0, 100), [])
                formation.publier_manuel(racine / 'ecole', 'allies', 0)

                def ouvrir(uid, chemin, mode='r', texte=''):
                    code = ('import os,sys; os.setgroups([]); os.setgid(0); '
                            'os.setuid(int(sys.argv[1])); '
                            'f=open(sys.argv[2],sys.argv[3]); '
                            'f.write(sys.argv[4]) if sys.argv[3] == "w" else f.read(); f.close()')
                    return subprocess.run([sys.executable, '-c', code, str(uid), str(chemin), mode, texte],
                                          capture_output=True).returncode

                for uid in (60001, 60002):
                    for nom in ('soldats.json', 'progression.json'):
                        chemin = racine / '.systeme' / nom
                        self.assertEqual((chemin.stat().st_uid, chemin.stat().st_mode & 0o777), (0, 0o600))
                        self.assertNotEqual(ouvrir(uid, chemin), 0)
                        self.assertNotEqual(ouvrir(uid, chemin, 'w', '{}'), 0)
                    manuel = racine / 'ecole/memoire_des_generaux.txt'
                    self.assertEqual(ouvrir(uid, manuel), 0)
                    self.assertNotEqual(ouvrir(uid, manuel, 'w', '001 201'), 0)
                # Même une copie de consultation modifiée par son propriétaire
                # ne peut rétablir une possibilité de sauvetage.
                self.assertEqual(ouvrir(60001, unite / 'blessures.txt', 'w', '0'), 0)
                self.assertEqual(len(soldats.pertes(infos, 0, 100)), 1)
                self.assertFalse(unite.exists())


if __name__ == '__main__':
    unittest.main()
