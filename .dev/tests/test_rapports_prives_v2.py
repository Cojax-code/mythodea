"""Publication privée et diffusion reprenable ; fichiers et horloges isolés."""
import json
import random
import unittest
from unittest.mock import patch

import test_cycle_survie
from support_cycle import GelSimule


class RapportsPrives(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    activer = test_cycle_survie.CycleSurvie.activer
    general = test_cycle_survie.CycleSurvie.general

    def gestion(self):
        g = self.cycle_linux.Generations(self.profil, GelSimule(), horloge=lambda: 100)
        g.preparer()
        return g

    def suivi(self):
        return self.config.game_path / 'rapport/suivi_combats.log'

    def preparer(self, generation='g000001-123456789abc'):
        g = self.gestion()
        repertoire = self.config.game_path / '.systeme/generations' / generation
        with self.rapports.preparation_privee(repertoire / 'rapports'), \
                patch.object(self.etat, 'choisir_meteo_tour', return_value='clair'):
            self.rapports.preparer_rapports(self.profil)
            self.rapports.ecrire_rapport_long('SECRET GENERAL — ordre personnel')
            self.rapports.ecrire_rapport_court('BILAN VALIDÉ')
            self.rapports.ecrire_rapport_territoire('est_1', 'CHOC INITIAL — événement unique')
        self.cycle_linux.ecrire_json(repertoire / 'resultat.json', dict(tour=1))
        self.rapports.publier_preparation(self.profil, repertoire, g.gid, 100)
        return g, repertoire

    def test_calcul_prive_ne_touche_aucun_rapport_public(self):
        self.general(territoire='village', nombre=5)
        g = self.gestion()
        self.rapports.preparer_rapports(self.profil)
        self.rapports.ecrire_rapport_court('ANCIEN TOUR')
        avant = {p: p.read_bytes() for p in self.config.rapport_dir.rglob('*') if p.is_file()}
        original = self.survie._resoudre_tour_capture

        def resoudre(prive, hasard):
            resultat = original(prive, hasard)
            self.assertEqual({p: p.read_bytes() for p in avant}, avant)
            self.assertIn('Fin du tour', (g.generation / 'rapports/rapport_court.txt').read_text())
            return resultat

        with patch.object(self.survie, '_resoudre_tour_capture', side_effect=resoudre):
            self.survie.resoudre_tour_survie(self.profil, random.Random(9), g)
        self.assertNotIn('ANCIEN TOUR', self.config.rapport_court_path.read_text())
        self.assertIn('Fin du tour', self.config.rapport_court_path.read_text())
        self.assertIsNone(self.rapports._preparation.get())

    def test_resolution_interrompue_conserve_les_anciens_rapports(self):
        g = self.gestion()
        self.rapports.preparer_rapports(self.profil)
        avant = {p: p.read_bytes() for p in self.config.rapport_dir.rglob('*') if p.is_file()}
        with patch.object(self.survie, 'creer_vague_est', side_effect=RuntimeError('incident')):
            with self.assertRaisesRegex(RuntimeError, 'incident'):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
        self.assertEqual({p: p.read_bytes() for p in avant}, avant)
        self.assertIsNone(self.rapports._preparation.get())

    def test_publication_et_diffusion_sans_secret_ni_remplacement_inode(self):
        g, _ = self.preparer()
        inode = self.suivi().stat().st_ino
        self.assertEqual(self.suivi().read_bytes(), b'')
        self.rapports.diffuser(self.profil, g.gid, 100)
        debut = self.suivi().read_bytes()
        self.assertTrue(debut)
        self.assertNotIn(b'CHOC INITIAL', debut)
        g.attendre(dict(tour=1, phase='consultation', echeance=100))
        texte = self.suivi().read_text()
        self.assertEqual(texte.count('événement unique'), 1)
        self.assertNotIn('SECRET GENERAL', texte)
        self.assertEqual(self.suivi().stat().st_ino, inode)
        self.rapports.diffuser(self.profil, g.gid, 200, terminer=True)
        self.assertEqual(self.suivi().read_text(), texte)

    def test_append_interrompu_octet_utf8_repris_sans_perte_ni_doublon(self):
        g, _ = self.preparer()
        plan = json.loads((self.config.game_path / '.systeme/diffusion_rapports.json').read_text())
        attendu = ''.join(plan['evenements']).encode('utf-8')
        coupure = attendu.index('é'.encode('utf-8')) + 1
        with self.suivi().open('ab') as f:
            f.write(attendu[:coupure])
        reprise = self.gestion()
        self.rapports.diffuser(self.profil, reprise.gid, 200, terminer=True)
        self.assertEqual(self.suivi().read_bytes(), attendu)
        self.rapports.diffuser(self.profil, g.gid, 200, terminer=True)
        self.assertEqual(self.suivi().read_bytes(), attendu)

    def test_republication_meme_generation_ne_repete_pas_les_evenements(self):
        g, repertoire = self.preparer()
        self.rapports.diffuser(self.profil, g.gid, 200, terminer=True)
        avant = self.suivi().read_bytes()
        self.rapports.publier_preparation(self.profil, repertoire, g.gid, 300)
        self.rapports.diffuser(self.profil, g.gid, 400, terminer=True)
        self.assertEqual(self.suivi().read_bytes(), avant)

    def test_deux_tours_meme_inode_historique_conserve(self):
        g, _ = self.preparer()
        inode = self.suivi().stat().st_ino
        self.rapports.diffuser(self.profil, g.gid, 200, terminer=True)
        avant = self.suivi().read_bytes()
        g, _ = self.preparer('g000002-123456789abc')
        self.rapports.diffuser(self.profil, g.gid, 300, terminer=True)
        self.assertEqual(self.suivi().read_bytes(), avant + avant)
        self.assertEqual(self.suivi().stat().st_ino, inode)

    def test_journal_divergent_refuse_sans_effacement(self):
        g, _ = self.preparer()
        self.suivi().write_bytes(b'divergence')
        with self.assertRaisesRegex(RuntimeError, 'divergent'):
            self.rapports.diffuser(self.profil, g.gid, 200)
        self.assertEqual(self.suivi().read_bytes(), b'divergence')

    def test_zero_delai_diffuse_tout_sans_attente(self):
        self.profil['delai_evenements_combats_secondes'] = 0
        g, _ = self.preparer()
        self.rapports.diffuser(self.profil, g.gid, 100)
        self.assertIn('événement unique', self.suivi().read_text())

    def test_phase_actions_ne_diffuse_pas_les_evenements(self):
        g, _ = self.preparer()
        g.attendre(dict(tour=1, phase='actions', echeance=100))
        self.assertEqual(self.suivi().read_bytes(), b'')

    def test_exception_privee_absente_du_clocher(self):
        g = self.gestion()
        g.erreur(1, RuntimeError('SECRET DE RESOLUTION'))
        for p in (self.config.game_path / 'village/clocher').iterdir():
            self.assertNotIn('SECRET DE RESOLUTION', p.read_text())
        self.assertIn('SECRET DE RESOLUTION', self.etat.charger_cycle_survie(self.profil)['erreur'])


if __name__ == '__main__':
    unittest.main()
