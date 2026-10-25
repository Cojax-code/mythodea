"""Créations moteur avec vrais UID, sans comptes ajoutés ni plateau /game."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bouclier_vivant
import config
import generaux
import soldats
import unites


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'Linux et root requis')
class PermissionsUnites(unittest.TestCase):
    def test_creations_propagation_spore_et_regeneration_accessibles_au_proprietaire(self):
        with tempfile.TemporaryDirectory(prefix='audit-unites-') as dossier:
            racine = Path(dossier)
            racine.chmod(0o755)
            with patch.object(config, 'game_path', racine):
                armee = []
                for joueur, uid in (('j1', 60001), ('j2', 60002)):
                    chemin = racine / joueur / 'general1'
                    chemin.parent.mkdir()
                    generaux.creer_general(chemin, 'general1')
                    for p in (chemin, *(chemin / b for b in config.ordre_blocs)):
                        os.chown(p, uid, 0)
                        p.chmod(0o700)
                    armee.append(dict(joueur=joueur, nom='general1', chemin=chemin))
                g, ennemi = armee
                sauvageon = g['chemin'] / 'droite/sauvageon1'
                unites.creer_officielle(sauvageon, 'sauvageon', {'test': True})
                unites.creer_officielle(g['chemin'] / 'avant/Trop_gros_zombie1', 'Trop_gros_zombie', {'test': True})
                unites.creer_officielle(g['chemin'] / 'arriere/zombi1', 'zombie', {'test': True})
                unites.propager(g, 'arriere', 2, 1, 'test', 'duel')
                unites.creer_officielle(ennemi['chemin'] / 'avant/infanterie1', 'archer', {'test': True})
                bouclier_vivant.convertir_spore(g, ennemi, 'avant', 'spore')
                unites.memoriser_sauvageons([g], 'sauvageon')
                soldats.pertes(generaux.lire_blocs_general(g['chemin'])['droite'], 0)
                unites.regenerer_fuite(g, dict(game_path=racine))
                for bloc in config.ordre_blocs:
                    for unite in (g['chemin'] / bloc).iterdir():
                        self.assertEqual((unite.stat().st_uid, unite.stat().st_mode & 0o777), (60001, 0o700))
                        for fichier in unite.iterdir():
                            self.assertEqual((fichier.stat().st_uid, fichier.stat().st_mode & 0o777), (60001, 0o600))
                        code = ('import os,sys; os.setgroups([]); os.setgid(0); '
                                'os.setuid(int(sys.argv[1])); os.listdir(sys.argv[2])')
                        for uid, permis in ((60001, True), (60002, False)):
                            r = subprocess.run([sys.executable, '-c', code, str(uid), str(unite)], capture_output=True)
                            self.assertEqual(r.returncode == 0, permis)


if __name__ == '__main__':
    unittest.main()
