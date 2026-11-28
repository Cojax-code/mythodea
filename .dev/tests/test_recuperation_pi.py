"""Pannes injectées sur disques temporaires ; aucun plateau Raspberry utilisé."""
import importlib
import json
import os
import signal
import sys
import unittest
from unittest.mock import patch

import test_generations_survie as generations


class RecuperationPi(unittest.TestCase):
    general = generations.GenerationsSurvie.general
    activer = generations.GenerationsSurvie.activer
    gestion = generations.GenerationsSurvie.gestion

    def setUp(self):
        generations.GenerationsSurvie.setUp(self)
        sys.modules.pop('survie_admin', None)
        self.admin = importlib.import_module('survie_admin')

    def interrompre(self, phase='capture'):
        self.chemin = self.general(territoire='village', reserve=True)
        (self.chemin / 'info/notes.txt').write_text('action à conserver')
        self.g = self.gestion()
        cible = 'copier' if phase == 'capture' else None
        contexte = (patch.object(self.cycle_linux, cible, side_effect=OSError('panne')) if cible else
                    patch.object(self.survie, '_resoudre_tour_capture', side_effect=OSError('panne')))
        with contexte, self.assertRaisesRegex(OSError, 'panne'):
            self.survie.resoudre_tour_survie(self.profil, gestion=self.g)

    def etats(self):
        return {n: (self.config.game_path / '.systeme' / n).read_bytes()
                for n in self.config.ETATS_METIER if (self.config.game_path / '.systeme' / n).exists()}

    def test_capture_dry_run_puis_reprise_conserve_actions_et_compteurs(self):
        self.interrompre()
        avant = self.etats()
        plan = self.admin.rollback(self.profil, dry_run=True)
        self.assertEqual(plan['restaures'], [])
        self.assertFalse(list(self.g.generation.glob('recuperation-*')))
        self.admin.rollback(self.profil, gestion=self.g)
        self.assertEqual(self.etats(), avant)
        self.assertEqual((self.chemin / 'info/notes.txt').read_text(), 'action à conserver')
        cycle = self.etat.charger_cycle_survie(self.profil)
        self.assertEqual((cycle['tour'], cycle['phase']), (1, 'actions'))
        self.assertTrue(list(self.g.generation.glob('recuperation-*/prete.json')))
        self.assertFalse(self.gel.gele)
        with self.assertRaises(RuntimeError):
            self.admin.rollback(self.profil, gestion=self.g)

    def test_resolution_privee_abandonnee_sans_double_progression(self):
        self.interrompre('resolution')
        generation = self.g.generation
        self.admin.rollback(self.profil, gestion=self.g)
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=self.g)
        import progression
        self.assertEqual(progression.charger()['j1:general1']['progression_formation'], 1)
        self.assertTrue(generation.is_dir())
        self.assertNotEqual(self.g.generation, generation)

    def test_seconde_interruption_recuperation_puis_nouvel_essai(self):
        self.interrompre()
        avant = self.etats()
        with patch.object(self.cycle_linux, 'copier', side_effect=OSError('sauvegarde interrompue')):
            with self.assertRaises(OSError):
                self.admin.rollback(self.profil, gestion=self.g)
        self.assertFalse(self.gel.gele)
        self.assertEqual(self.etats(), avant)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'recuperation')
        self.admin.rollback(self.profil, gestion=self.g)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'actions')

    def test_publication_ou_resultat_interdisent_rollback(self):
        self.interrompre()
        for nom, texte in [('publication.json', '{}'), ('publication.interrompu-1', '{}'),
                           ('resultat.json', '{"resolution_terminee": true}')]:
            chemin = self.g.generation / nom
            chemin.write_text(texte)
            with self.assertRaises(RuntimeError):
                self.admin.rollback(self.profil, dry_run=True)
            chemin.unlink()

    def test_generation_active_reference_fausse_et_moteur_actif_refuses(self):
        self.interrompre()
        cycle = self.etat.charger_cycle_survie(self.profil)
        cycle['generation_active'] = self.g.generation.name
        self.etat.sauvegarder_cycle_survie(cycle, self.profil)
        with self.assertRaisesRegex(RuntimeError, 'déjà validée'):
            self.admin.rollback(self.profil, dry_run=True)
        del cycle['generation_active']
        self.etat.sauvegarder_cycle_survie(cycle, self.profil)
        self.etat.sauvegarder_unites_actions(self.profil, {'tour': 900})
        with self.assertRaisesRegex(RuntimeError, 'Référence'):
            self.admin.rollback(self.profil, dry_run=True)
        with self.etat.verrou_cycle_survie(self.profil), self.assertRaisesRegex(RuntimeError, 'encore présent'):
            self.admin.rollback(self.profil, dry_run=True)

    def test_annonce_apres_validation_ne_transforme_pas_consultation_en_panne(self):
        g = self.gestion()
        def annoncer(message):
            if isinstance(message, str) and message.startswith('PHASE DE CONSULTATION'):
                raise OSError('terminal fermé')
        with patch.object(g.backend, 'annoncer', side_effect=annoncer):
            with self.assertRaises(OSError):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'consultation')

    def test_republication_apres_archivage_sans_double_vague(self):
        g = self.gestion()
        original = g.marquer
        def panne(tour, phase, **kw):
            if phase == 'consultation':
                raise OSError('validation interrompue')
            return original(tour, phase, **kw)
        with patch.object(g, 'marquer', side_effect=panne):
            with self.assertRaisesRegex(OSError, 'validation interrompue'):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
        archives = self.config.rapport_long_path.read_bytes()
        from support_cycle import GelSimule
        with patch.object(self.cycle_linux, 'Linux', return_value=GelSimule()), \
                patch.object(self.survie, '_resoudre_tour_capture', side_effect=AssertionError('combat rejoué')):
            self.admin.republier(self.profil, g.generation.name)
        self.assertEqual(self.config.rapport_long_path.read_bytes(), archives)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'consultation')

    def test_ctrl_c_differe_jusqua_publication_sans_marquer_recuperation(self):
        g = self.gestion()
        original = self.survie._resoudre_tour_capture
        def interrompre(*a, **kw):
            signal.raise_signal(signal.SIGINT)
            return original(*a, **kw)
        with patch.object(self.survie, '_resoudre_tour_capture', side_effect=interrompre):
            with self.assertRaises(KeyboardInterrupt):
                self.survie.resoudre_tour_survie(self.profil, gestion=g)
        self.assertFalse(self.gel.gele)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'consultation')

    def test_clocher_droits_installes_avant_rename(self):
        g = self.gestion()
        with patch.object(self.etat, 'ecrire_prive', wraps=self.etat.ecrire_prive) as ecrire:
            g.afficher(4, 'consultation')
        self.assertEqual(ecrire.call_args.kwargs, {'gid': g.gid, 'mode': 0o640})


if __name__ == '__main__':
    unittest.main()
