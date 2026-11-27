"""Rapports et récompenses : vrais UID Linux, exclusivement dans un tmpdir."""
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import crypte
import cycle_linux
import etat
import plateau
import rapports


@unittest.skipUnless(sys.platform == 'linux' and os.geteuid() == 0, 'Linux et root requis')
class PermissionsActivites(unittest.TestCase):
    def executer(self, uid, code, *chemins, attendu=0, groupes=()):
        prefixe = f'import os,sys,pathlib; os.setgroups({list(groupes)!r}); os.setgid(int(sys.argv[1])); os.setuid(int(sys.argv[1])); '
        resultat = subprocess.run([sys.executable, '-c', prefixe + code, str(uid), *map(str, chemins)],
                                  capture_output=True, text=True, timeout=5)
        self.assertEqual(resultat.returncode == 0, attendu == 0, resultat.stderr)

    def test_migration_ancien_journal_prive_et_reprise_sans_doublon(self):
        with tempfile.TemporaryDirectory(prefix='mythodea-migration-rapports-') as dossier:
            racine = Path(dossier)
            ancien = racine / 'rapport/rapport_long.txt'
            ancien.parent.mkdir()
            texte = 'Météo du tour : pluie\nEffet actuel de la météo : aucun\nAction validée\n'
            etat.ecrire_prive(ancien, texte)
            clocher = racine / 'village/clocher'
            clocher.mkdir(parents=True)
            for nom in ('etat_tour.txt', 'suivi_tour.log'):
                (clocher / nom).write_text('ancien état')
            configuration = dict(game_path=racine, joueurs=())
            rapports.migrer_anciens_rapports(configuration)
            archive = racine / '.systeme/archives.log'
            contenu = archive.read_bytes()
            self.assertNotIn('météo', contenu.decode().lower())
            self.assertIn('Action validée', contenu.decode())
            self.assertFalse(ancien.exists())
            self.assertFalse(list(clocher.iterdir()))
            # Reconstitue l'interruption après remplacement et avant unlink.
            etat.ecrire_prive(ancien, texte)
            rapports.migrer_anciens_rapports(configuration)
            self.assertEqual(archive.read_bytes(), contenu)
            self.assertFalse(ancien.exists())
            self.assertEqual((archive.stat().st_uid, archive.stat().st_gid, archive.stat().st_mode & 0o777),
                             (0, 0, 0o600))

    def test_archives_root_privees_meme_avec_traversee_alliee(self):
        with tempfile.TemporaryDirectory(prefix='mythodea-archives-') as dossier:
            racine = Path(dossier)
            racine.chmod(0o755)
            systeme = racine / '.systeme'
            systeme.mkdir()
            os.chown(systeme, 0, 60003)
            systeme.chmod(0o710)
            generation = systeme / 'generations/g000000-123456789abc'
            cycle_linux.dossier_prive(generation.parent)
            cycle_linux.dossier_prive(generation)
            etat.ecrire_prive(generation / 'resultat.json', json.dumps(dict(tour=0, resolution_terminee=True)))
            etat.ecrire_prive(generation / 'rapports/archives.log', json.dumps(dict(vague=1, categorie='TEST', message='secret')) + '\n')
            rapports.publier_archives(dict(game_path=racine), generation)
            archive = systeme / 'archives.log'
            infos = archive.stat()
            self.assertEqual((infos.st_uid, infos.st_gid, infos.st_mode & 0o777), (0, 0, 0o600))
            for uid in (60001, 60002):
                # Le parent est traversable : ce sont bien les droits du fichier
                # et l'absence d'écriture du dossier qui protègent les archives.
                self.executer(uid, 'assert pathlib.Path(sys.argv[2]).stat().st_uid == 0', archive, groupes=(60003,))
                for code in ('pathlib.Path(sys.argv[2]).read_text()',
                             'pathlib.Path(sys.argv[2]).write_text("faux")',
                             'pathlib.Path(sys.argv[2]).unlink()',
                             'os.rename(sys.argv[2], sys.argv[2]+".ancien")'):
                    self.executer(uid, code, archive, attendu=1, groupes=(60003,))

    def test_rapports_non_falsifiables_et_recompense_deplacable_seulement_en_actions(self):
        with tempfile.TemporaryDirectory(prefix='mythodea-rapports-') as dossier:
            racine = Path(dossier)
            racine.chmod(0o755)
            jeu = racine / 'game'
            jeu.mkdir()
            homes = {j: racine / 'homes' / j for j in ('j1', 'j2')}
            for p in homes.values():
                p.mkdir(parents=True)
            identites = {'j1': 60001, 'j2': 60002, 'mythodea_allies': 60003, 'root': 0}
            with patch.object(config, 'game_path', jeu), \
                    config.racines_generation(jeu, homes), \
                    patch('pwd.getpwnam', side_effect=lambda j: SimpleNamespace(pw_uid=identites[j])), \
                    patch('grp.getgrnam', side_effect=lambda j: SimpleNamespace(gr_gid=identites[j])):
                c = config.configuration_mode('survie')
                c['homes'] = homes
                plateau.reparer_structure(c)
                crypte.preparer(c)
                rapports.preparer_activites(c, 1)
                rapports.noter_activite(c, 'j1', 'TEST', 'secret-j1')
                rapports.noter_activite(c, 'j2', 'TEST', 'secret-j2')
                gestion = cycle_linux.Generations(c, backend=object())
                gestion.proteger_activites()
                rapport = jeu / 'village/j1/hotel_de_ville/rapport_activites.txt'
                autre = jeu / 'village/j2/hotel_de_ville/rapport_activites.txt'
                self.executer(60001, 'assert "secret-j1" in pathlib.Path(sys.argv[2]).read_text()', rapport)
                for code, chemin in (
                    ('pathlib.Path(sys.argv[2]).read_text()', autre),
                    ('pathlib.Path(sys.argv[2]).write_text("faux")', rapport),
                    ('pathlib.Path(sys.argv[2]).unlink()', rapport),
                    ('os.rename(sys.argv[2], sys.argv[2]+".ancien")', rapport),
                    ('os.chmod(sys.argv[2], 0o777)', rapport.parent),
                ):
                    self.executer(60001, code, chemin, attendu=1)
                attente = jeu / 'village/j1/crypte/recompense/general1'
                attente.mkdir()
                (attente / 'info').mkdir()
                (attente / 'info/fiche.txt').write_text('identité conservée')
                os.chown(attente, 60001, 60001)
                os.chown(attente / 'info', 60001, 60001)
                os.chown(attente / 'info/fiche.txt', 60001, 60001)
                attente.chmod(0o700)
                (attente / 'info').chmod(0o700)
                (attente / 'info/fiche.txt').chmod(0o600)
                cible = jeu / 'village/j1/garnison/1/general1'
                gestion.permissions_consultation()
                gestion.proteger_activites()
                self.assertEqual(attente.stat().st_mode & 0o777, 0o500)
                self.executer(60001, 'os.rename(sys.argv[2], sys.argv[3])', attente, cible, attendu=1)
                self.executer(60002, 'os.listdir(sys.argv[2])', attente, attendu=1)
                etat.sauvegarder_cycle_survie(dict(tour=1, phase='actions'), c)
                gestion.permissions_actions()
                self.assertEqual(attente.stat().st_mode & 0o777, 0o700)
                self.assertEqual((rapport.stat().st_uid, rapport.stat().st_gid, rapport.stat().st_mode & 0o777),
                                 (0, 60001, 0o640))
                self.executer(60001, 'os.rename(sys.argv[2], sys.argv[3])', attente, cible)
                self.executer(60001, 'pathlib.Path(sys.argv[2]).unlink()', rapport, attendu=1)
                self.assertEqual((cible / 'info/fiche.txt').read_text(), 'identité conservée')
                self.executer(60001, 'pathlib.Path(sys.argv[2]).read_text()', cible / 'info/fiche.txt')


if __name__ == '__main__':
    unittest.main()
