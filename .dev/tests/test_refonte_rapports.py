"""Contrats des rapports V2 : validation, renouvellement et reprise atomique."""
import json
import random
import unittest
from unittest.mock import patch

import test_cycle_survie
import test_mythodea
from support_cycle import GelSimule


class RefonteRapports(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    activer = test_cycle_survie.CycleSurvie.activer
    general = test_cycle_survie.CycleSurvie.general

    def resoudre(self, tour=0):
        self.activer(tour)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, random.Random(5), gestion)
        return gestion

    def test_deux_tours_rapports_neufs_archives_cumulatives_et_extraction(self):
        self.resoudre()
        archive = self.config.game_path / '.systeme/archives.log'
        premier = archive.read_text()
        territoire = self.config.rapports_territoires_dir / 'est_1.txt'
        territoire.write_text('ANCIEN COMBAT')
        activites = self.config.game_path / 'village/j1/hotel_de_ville/rapport_activites.txt'
        activites.write_text('ANCIENNE ACTIVITÉ')
        self.resoudre(1)
        texte = archive.read_text()
        self.assertTrue(texte.startswith(premier))
        for vague in (1, 2):
            debut, fin = f'=== VAGUE {vague} DEBUT ===', f'=== VAGUE {vague} FIN ==='
            self.assertEqual(texte.count(debut), 1)
            self.assertEqual(texte.count(fin), 1)
            records = [json.loads(l) for l in texte.split(debut)[1].split(fin)[0].splitlines() if l]
            self.assertTrue(all(r['vague'] == vague for r in records))
            self.assertIn('ETAT_FINAL', {r['categorie'] for r in records})
        self.assertNotIn('ANCIEN', territoire.read_text())
        self.assertNotIn('ANCIENNE', activites.read_text())
        self.assertIn('VAGUE 2', activites.read_text())
        self.assertFalse((activites.parent.parent / activites.name).exists())
        for fichier in (archive, *self.config.rapport_dir.rglob('*.txt')):
            self.assertNotRegex(fichier.read_text().lower(), 'météo|meteo')
        self.assertTrue(self.config.meteo_path.exists())
        self.assertNotIn('[est_1]', (self.config.rapport_dir / 'suivi_combats.log').read_text())

    def test_archives_reprise_apres_remplacement_avant_retour(self):
        gestion = self.resoudre()
        destination = self.config.game_path / '.systeme/archives.log'
        attendu = destination.read_bytes()
        destination.unlink()
        original = self.etat.ecrire_prive

        def panne(chemin, texte):
            original(chemin, texte)
            if chemin == destination:
                raise RuntimeError('interruption après remplacement')

        with patch.object(self.etat, 'ecrire_prive', side_effect=panne):
            with self.assertRaisesRegex(RuntimeError, 'interruption'):
                self.rapports.publier_archives(self.profil, gestion.generation)
        self.rapports.publier_archives(self.profil, gestion.generation)
        self.assertEqual(destination.read_bytes(), attendu)
        fragment = gestion.generation / 'rapports/archives.log'
        fragment.write_text(fragment.read_text() + json.dumps(dict(vague=1, categorie='DIVERGENCE')) + '\n')
        with self.assertRaisesRegex(RuntimeError, 'divergentes'):
            self.rapports.publier_archives(self.profil, gestion.generation)
        self.assertEqual(destination.read_bytes(), attendu)

    def test_resolution_incomplete_necree_pas_archives(self):
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', side_effect=RuntimeError('panne')):
            with self.assertRaisesRegex(RuntimeError, 'panne'):
                self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertFalse((self.config.game_path / '.systeme/archives.log').exists())

    def test_combat_details_avant_recapitulatif_sans_meteo(self):
        self.activer(0)
        self.general(territoire='est_3', nombre=5)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        self.survie.resoudre_tour_survie(self.profil, random.Random(5), gestion)
        texte = (self.config.rapports_territoires_dir / 'est_3.txt').read_text()
        self.assertLess(texte.index('Forces initiales'), texte.index('CHOC INITIAL'))
        self.assertLess(texte.index('CHOC INITIAL'), texte.index('MANŒUVRE'))
        self.assertLess(texte.index('MANŒUVRE'), texte.index('RÉCAPITULATIF'))
        self.assertIn('→', texte)
        self.assertRegex(texte, '[○×]')
        self.rapports.diffuser(self.profil, gestion.gid, 999999999999, terminer=True)
        suivi = (self.config.rapport_dir / 'suivi_combats.log').read_text()
        self.assertNotIn('[est_2]', suivi)
        self.assertNotIn('[village]', suivi)
        self.assertLess(suivi.index('CHOC INITIAL'), suivi.index('RÉCAPITULATIF'))

    def test_gel_par_defaut_sans_attente_artificielle(self):
        self.assertEqual(self.config.configuration_mode('survie')['duree_gel_secondes'], 0)
        gel = GelSimule()
        gestion = self.cycle_linux.Generations(self.profil, gel, monotone=lambda: 0,
            dormir=lambda _: self.fail('Attente artificielle'))
        gestion.preparer()
        gestion.capturer(1)
        self.assertFalse(gel.gele)
        self.assertTrue(json.loads((gestion.generation / 'manifeste.json').read_text())['capture_validee'])

    def test_annonces_completes_sans_archives(self):
        texte = self.rapports.commandes_consultation(self.profil)
        for nom in ('rapport.txt', 'rapport_activites.txt', 'rapport_exploration.txt',
                    'etat_tour.log', 'replay ', 'suivi_combats.log'):
            self.assertIn(nom, texte)
        self.assertNotIn('.systeme', texte)
        self.assertNotIn('archives', texte)


class ArchivesClassiques(unittest.TestCase):
    setUp = test_mythodea.Regressions.setUp

    def test_classique_cumul_et_exception_sans_publication(self):
        for numero in (1, 2):
            with self.rapports.archives_classiques():
                self.rapports.preparer_rapports()
                self.rapports.ecrire_rapport_long(f'résultat classique {numero}')
        archive = self.config.rapport_long_path
        contenu = archive.read_text()
        for numero in (1, 2):
            self.assertEqual(contenu.count(f'=== VAGUE {numero} FIN ==='), 1)
            self.assertIn(f'résultat classique {numero}', contenu)
        with self.assertRaisesRegex(RuntimeError, 'panne'):
            with self.rapports.archives_classiques():
                self.rapports.preparer_rapports()
                self.rapports.ecrire_rapport_long('INVALIDE')
                raise RuntimeError('panne')
        self.assertEqual(archive.read_text(), contenu)
        self.assertFalse((self.config.rapport_dir / 'archives.log').exists())
