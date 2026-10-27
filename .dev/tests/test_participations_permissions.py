"""Permissions Linux réelles du lot B ; uniquement sous root et dans /tmp."""
import importlib
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == 'posix' and os.geteuid() == 0, 'Linux root requis')
class PermissionsParticipations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='mythodea-participations-')
        self.addCleanup(self.tmp.cleanup)
        self.racine = Path(self.tmp.name)
        self.racine.chmod(0o755)
        chemins = patch.object(sys, 'path', [str(Path(__file__).resolve().parents[2] / 'python'),
                                            *sys.path])
        chemins.start()
        self.addCleanup(chemins.stop)
        self.config = importlib.import_module('config')
        self.soldats = importlib.import_module('soldats')
        self.cycle = importlib.import_module('cycle_linux')
        self.public = self.racine / 'game'
        self.public.mkdir(mode=0o755)
        racine = patch.object(self.config, 'game_path', self.public)
        racine.start()
        self.addCleanup(racine.stop)
        fatigue = patch.object(self.config, 'fatigue_generaux_path',
                               self.public / '.systeme/fatigue_generaux.txt')
        fatigue.start()
        self.addCleanup(fatigue.stop)
        self.cycle.dossier_prive(self.public / '.systeme')
        self.generaux = []
        registre = {}
        # UID numériques seulement : aucun compte système créé ou modifié.
        for joueur, uid in (('j1', 62001), ('j2', 62002)):
            general = self.public / 'est_3' / joueur / '1/general1'
            bloc = general / 'avant'
            bloc.mkdir(parents=True)
            for dossier in (general, bloc):
                os.chown(dossier, uid, uid)
                dossier.chmod(0o700)
            unite = bloc / 'infanterie1'
            self.soldats.creer_dossier_unite(unite)
            self.soldats.ecrire_copie(unite / 'pique', '')
            identifiant = self.soldats.enregistrer(unite, registre, 'piquier')
            registre[identifiant].update(batailles=7, blessures=1)
            self.soldats.publier(unite, identifiant, registre[identifiant])
            self.generaux.append(dict(joueur=joueur, nom='general1', chemin=general))
        self.soldats.sauvegarder(registre)

    def contributions(self, generaux):
        return [(g, 'avant', [g['chemin'] / 'avant/infanterie1']) for g in generaux]

    def lisible(self, fichier, uid):
        resultat = subprocess.run(
            [sys.executable, '-B', '-c',
             'from pathlib import Path; import sys; Path(sys.argv[1]).read_bytes()', str(fichier)],
            user=uid, group=uid, extra_groups=[],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return resultat.returncode == 0

    def test_copie_privee_pertes_et_blessures_gardent_droits_reels(self):
        origine = self.contributions(self.generaux)
        for index, (_, _, unites) in enumerate(origine):
            self.assertTrue(self.lisible(unites[0] / 'blessures.txt', 62001 + index))
            self.assertFalse(self.lisible(unites[0] / 'blessures.txt', 62002 - index))
        prive = self.racine / 'prive'
        self.cycle.dossier_prive(prive)
        plateau = prive / 'game'
        self.cycle.copier(self.public, plateau)
        copies = [dict(g, chemin=plateau / g['chemin'].relative_to(self.public))
                  for g in self.generaux]
        with self.config.racines_generation(plateau, {}):
            with self.soldats.participation_temporaire(self.contributions(copies)) as groupe:
                a, b = groupe.participants
                groupe.appliquer_pertes([a.identifiant], 0, moral=0)
                groupe.appliquer_pertes([b.identifiant], 0, moral=100)
                self.assertFalse(a.chemin.exists())
                self.assertEqual((b.chemin / 'blessures.txt').read_text(), '2\n')
                for p in (b.chemin, *b.chemin.iterdir()):
                    infos = p.stat()
                    self.assertEqual((infos.st_uid, infos.st_gid), (62002, 62002))
                    self.assertEqual(stat.S_IMODE(infos.st_mode), 0o700 if p.is_dir() else 0o600)
                self.assertFalse(self.lisible(b.chemin / 'blessures.txt', 62002))
                etat = (plateau / '.systeme/soldats.json').stat()
                self.assertEqual((etat.st_uid, etat.st_gid, stat.S_IMODE(etat.st_mode)), (0, 0, 0o600))
        # Aucun résultat privé ni changement de droits n'a atteint le plateau public.
        for index, (_, _, unites) in enumerate(origine):
            self.assertEqual((unites[0] / 'blessures.txt').read_text(), '1\n')
            self.assertTrue(self.lisible(unites[0] / 'blessures.txt', 62001 + index))
            self.assertFalse(self.lisible(self.public / '.systeme/soldats.json', 62001 + index))

    def test_changement_uid_ou_gid_detecte_avant_toute_perte(self):
        with self.soldats.participation_temporaire(self.contributions(self.generaux)) as groupe:
            participant = groupe.participants[0]
            avant = self.soldats.charger()
            for uid, gid in ((62002, 62001), (62001, 62002)):
                os.chown(participant.chemin, uid, gid)
                try:
                    with self.assertRaisesRegex(RuntimeError, 'Propriétaire Linux'):
                        groupe.appliquer_pertes([participant.identifiant], 0, moral=0)
                    self.assertTrue(participant.chemin.is_dir())
                    self.assertEqual(self.soldats.charger(), avant)
                finally:
                    os.chown(participant.chemin, participant.uid, participant.gid)

    def test_vue_commune_pertes_et_controle_des_proprietaires_reels(self):
        import random
        import etat
        etat.sauvegarder_generaux_fatigues({'j2:general1'})
        with self.soldats.participation_temporaire(self.contributions(self.generaux)) as groupe:
            a, b = groupe.participants
            vue = self.soldats.VueParticipants(groupe, [
                (self.generaux[0], 'avant', (a.identifiant, b.identifiant))])
            infos = vue.blocs(self.generaux[0])['avant']
            self.assertEqual(infos['unites'], [a.chemin, b.chemin])
            self.assertEqual(vue.fatigue(self.generaux[0], infos), (False, True))
            self.assertEqual(vue.total(self.generaux[1]), 0)
            os.chown(b.chemin, a.uid, a.gid)
            try:
                with self.assertRaisesRegex(RuntimeError, 'Propriétaire Linux'):
                    vue.blocs(self.generaux[0])
            finally:
                os.chown(b.chemin, b.uid, b.gid)
            self.soldats.pertes(infos, 1, moral=0, aleatoire=random.Random(1))
            self.assertFalse(a.chemin.exists())
            self.assertEqual(vue.total(self.generaux[0]), 1)
            self.assertTrue(vue.fatigue(self.generaux[0], vue.blocs(self.generaux[0])['avant']))
            self.assertEqual(etat.charger_generaux_fatigues(), {'j2:general1'})
            self.assertEqual((b.chemin.stat().st_uid, b.chemin.stat().st_gid), (62002, 62002))
            self.assertTrue(self.lisible(b.chemin / 'blessures.txt', 62002))
            self.assertFalse(self.lisible(b.chemin / 'blessures.txt', 62001))
            self.assertEqual(self.soldats.charger()[b.identifiant]['batailles'], 7)
