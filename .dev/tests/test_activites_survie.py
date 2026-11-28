"""Rapports personnels et alertes sur plateaux temporaires uniquement."""
import importlib
import os
import random
import unittest
from unittest.mock import Mock, patch

import test_complements_moteur
from support_cycle import GelSimule


class ActivitesSurvie(unittest.TestCase):
    setUp = test_complements_moteur.ComplementsMoteur.setUp
    activer = test_complements_moteur.ComplementsMoteur.activer
    general = test_complements_moteur.ComplementsMoteur.general
    creer = test_complements_moteur.ComplementsMoteur.creer
    modules = test_complements_moteur.ComplementsMoteur.modules
    infos = test_complements_moteur.ComplementsMoteur.infos
    forge = test_complements_moteur.ComplementsMoteur.forge

    def rapport(self, joueur='j1'):
        return self.config.game_path / 'village' / joueur / 'hotel_de_ville/rapport_activites.txt'

    def resolution(self, tour=1):
        self.modules()
        self.etat.sauvegarder_cycle_survie(dict(tour=tour, phase='resolution'), self.profil)
        self.rapports.preparer_activites(self.profil, tour)

    def test_arrivee_caserne_capture_privee_trois_clotures_et_remplacement(self):
        self.modules()
        self.formation.ouvrir_tour(self.profil, 1)
        general = self.creer(territoire='home', nature='stratege')
        destination = self.config.game_path / 'village/j1/caserne_militaire/general1'
        general['chemin'].rename(destination)
        general['chemin'] = destination
        for tour in (1, 2, 3):
            if tour > 1:
                self.activer(tour)
            gestion = self.cycle_linux.Generations(self.profil, GelSimule())
            gestion.permissions_actions()
            self.formation.ouvrir_tour(self.profil, tour)
            with patch.object(self.survie, 'creer_vague_est', return_value=[]):
                self.survie.resoudre_tour_survie(self.profil, random.Random(5), gestion)
            fiche = self.progression.charger()['j1:general1']
            self.assertEqual((fiche['niveau'], fiche['progression_formation']), (tour // 3, tour % 3))
            texte = self.rapport().read_text()
            self.assertEqual(texte.count('+1 point'), 1)
            self.assertIn(f'progression {tour % 3}/3', texte)
            self.assertNotIn(f'TOUR {tour - 1}', texte)
            self.assertNotIn('general1', self.rapport('j2').read_text())
            if tour == 3:
                self.assertIn('niveau 1 gagné', texte)
                self.assertNotIn('emplacement(s) d’étiquettes actives débloqué(s)', texte)
                self.assertIn('récompense', texte)
        self.assertFalse(list(self.config.game_path.rglob('formation_resultat.txt')))

    def test_sejour_quitte_et_refus_ouverture_conserves_sans_doublon(self):
        g = self.creer(territoire='village', place='ecole_officiers/1', nature='stratege')
        self.formation.preparer_demandes(g)
        (g['chemin'] / 'info/lire_les_memoires.txt').write_text('a 999 201')
        self.formation.ouvrir_tour(self.profil, 1)
        alertes = self.formation.alertes_actions(self.profil, 1)
        self.assertTrue(any('invalide' in a['message'] for a in alertes))
        self.assertTrue(all(a['joueur'] == 'j1' for a in alertes))
        self.resolution()
        self.formation.clore_tour(self.profil, 1)
        self.formation.resoudre_tour(self.profil, 1)
        avant = self.rapport().read_bytes()
        self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.rapport().read_bytes(), avant)
        self.assertIn('emplacement 001..003', avant.decode())
        (g['chemin'] / 'info/lire_les_memoires.txt').write_text('001')
        self.formation.ouvrir_tour(self.profil, 2)
        g['chemin'].rename(self.config.game_path / 'village/j1/garnison/1/general1')
        self.formation.clore_tour(self.profil, 2)
        self.resolution(2)
        self.formation.resoudre_tour(self.profil, 2)
        self.assertNotIn('Mémoire', self.rapport().read_text())
        self.assertNotIn('2:j1:general1', self.formation.charger()['valides'])

    def test_ecole_ecriture_lecture_et_rang_officiels(self):
        g = self.creer(territoire='village', place='ecole_officiers/1', nature='stratege')
        self.resolution()
        self.formation.commencer_sejour(1, g, 'ecole_officiers', 'allies', [1], ecrire='e 001 2001')
        self.formation.valider_sejour(1, g, 'ecole_officiers', 'allies', [1], True)
        self.formation.commencer_sejour(2, g, 'ecole_officiers', 'allies', [1], lire='a 001 2001')
        self.formation.valider_sejour(2, g, 'ecole_officiers', 'allies', [1], True)
        texte = self.rapport().read_text()
        self.assertIn('Mémoire 001 écrite : ID 2001', texte)
        self.assertIn('Mémoire 001 lue : ID 2001', texte)
        self.assertIn('infanterie apprise ou améliorée, niveau 1', texte)
        avant = self.rapport().read_bytes()
        self.assertFalse(self.formation.valider_sejour(2, g, 'ecole_officiers', 'allies', [1], True))
        self.assertEqual(self.rapport().read_bytes(), avant)

    def test_hopital_compte_les_blesses_effectivement_soignes(self):
        g = self.creer(territoire='village', place='hopital/1', nombre=2)
        self.combats.supprimer_unites(self.infos(g), 1, g)
        self.resolution()
        presences = self.formation.relever_unites(g, initialiser=True)
        self.formation.commencer_sejour(1, g, 'hopital', 'allies', [1], unites=presences)
        self.formation.valider_sejour(1, g, 'hopital', 'allies', [1], True, unites=presences)
        self.assertIn('1 unité(s) effectivement soignée(s), 1 blessure(s) supprimée(s)', self.rapport().read_text())

    def test_arrivee_tardive_hopital_signalee_une_fois(self):
        self.modules()
        self.formation.ouvrir_tour(self.profil, 1)
        self.creer(territoire='village', place='hopital/1')
        self.formation.clore_tour(self.profil, 1)
        self.resolution()
        for _ in range(2):
            self.formation.resoudre_tour(self.profil, 1)
        self.assertEqual(self.rapport().read_text().count('effectivement soignée'), 1)
        self.assertNotIn('séjour incomplet', self.rapport().read_text())

    def test_forge_resultat_et_identites_conserves(self):
        g = self.forge()
        self.resolution()
        presences = self.formation.relever_unites(g, initialiser=True)
        avant = self.soldats.charger()
        self.formation.commencer_sejour(1, g, 'forge', 'allies', [1], unites=presences,
                                        eligibles_forge=presences)
        self.formation.valider_sejour(1, g, 'forge', 'allies', [1], True, unites=presences)
        apres = self.soldats.charger()
        self.assertEqual(avant.keys(), apres.keys())
        for identite in presences:
            self.assertEqual(apres[identite]['blessures'], avant[identite]['blessures'])
        self.assertIn('1 cavalier(s) léger(s) transformé(s)', self.rapport().read_text())

    def test_forge_prerequis_signale_immediatement_sans_operation(self):
        self.forge(technologie=False)
        avant = self.progression.charger()
        alertes = self.formation.alertes_actions(self.profil, 1)
        self.assertEqual(len(alertes), 1)
        self.assertEqual((alertes[0]['joueur'], alertes[0]['categorie']), ('j1', 'FORGE'))
        self.assertIn('technologie 104', alertes[0]['message'])
        self.assertEqual(self.progression.charger(), avant)
        self.assertFalse(self.formation.charger()['valides'])

    def test_rapport_inchange_actions_consultation_et_protection_parent(self):
        self.resolution()
        self.rapports.noter_resultat('j1', 'INCIDENTS', 'officiel', self.profil)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        avant = self.rapport().read_bytes()
        for phase in ('actions', 'consultation'):
            self.etat.sauvegarder_cycle_survie(dict(tour=1, phase=phase), self.profil)
            self.rapports.noter_resultat('j1', 'INCIDENTS', 'interdit', self.profil)
            getattr(gestion, 'permissions_' + phase)()
            gestion.proteger_activites()
            self.assertEqual(self.rapport().read_bytes(), avant)
        self.chown.assert_any_call(self.rapport().parent, 0, 1001)
        self.chmod.assert_any_call(self.rapport().parent, 0o750)
        self.chown.assert_any_call(self.rapport(), 0, 1001)
        self.chmod.assert_any_call(self.rapport(), 0o640)

    def test_interruption_resolution_ne_revele_pas_rapport_prive(self):
        self.creer(territoire='village', reserve=True)
        self.rapports.preparer_activites(self.profil, 0)
        ancien = self.rapport().read_bytes()
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', side_effect=RuntimeError('interruption')):
            with self.assertRaisesRegex(RuntimeError, 'interruption'):
                self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertEqual(self.rapport().read_bytes(), ancien)
        prive = gestion.generation / 'travail/game/village/j1/hotel_de_ville/rapport_activites.txt'
        self.assertIn('+1 point', prive.read_text())
        with self.assertRaises(RuntimeError):
            self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        self.assertEqual(self.rapport().read_bytes(), ancien)

    def test_alertes_actions_ciblees_et_dedoublonnees_apres_reprise(self):
        g = self.creer(territoire='village', place='ecole_officiers/1')
        self.formation.preparer_demandes(g)
        (g['chemin'] / 'info/lire_les_memoires.txt').write_text('999')
        backend = GelSimule()
        backend.alerter = Mock()
        gestion = self.cycle_linux.Generations(self.profil, backend)
        gestion.alerter_batiments(1)
        importlib.reload(self.formation)
        gestion.alerter_batiments(1)
        backend.alerter.assert_called_once()
        messages = backend.alerter.call_args.args[0]
        self.assertEqual(set(messages), {1001})
        self.assertIn('ALERTE MYTHODEA', messages[1001])
        self.assertFalse(self.formation.charger()['valides'])

    def test_republication_reutilise_rapport_termine_sans_nouveau_gain(self):
        self.creer(territoire='village', reserve=True)
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', return_value=[]), \
                patch.object(self.rapports, 'publier_rapports_exploration', side_effect=OSError('panne')):
            with self.assertRaisesRegex(OSError, 'panne'):
                self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        attendu = (gestion.generation / 'travail/game/village/j1/hotel_de_ville/rapport_activites.txt').read_bytes()
        admin = importlib.import_module('survie_admin')
        with patch.object(admin.cycle_linux, 'Linux', return_value=GelSimule()), \
                patch.object(self.formation, 'resoudre_tour', side_effect=AssertionError('séjour rejoué')), \
                patch.object(self.progression, 'valider_evenement', side_effect=AssertionError('gain rejoué')):
            admin.republier(self.profil, gestion.generation.name)
        self.assertEqual(self.rapport().read_bytes(), attendu)
        self.assertEqual(attendu.decode().count('+1 point'), 1)
        self.assertEqual(self.progression.charger()['j1:general1']['progression_formation'], 1)

    def test_audit_incidents_personnels_et_unites_rejetees(self):
        g = self.creer(territoire='est_3')
        unite = g['chemin'] / 'avant/invalide'
        unite.mkdir()
        self.resolution()
        self.generaux.lire_blocs_general(g['chemin'])
        self.assertIn('avant/invalide rejetée', self.rapport().read_text())
        destination = self.config.game_path / 'village/j1/garnison/1/general1'
        g['chemin'].rename(destination)
        self.securite.verifier_tous_les_deplacements(self.profil)
        texte = self.rapport().read_text()
        self.assertIn('déplacement interdit', texte)
        self.assertIn('[REPLI]', texte)
        self.assertNotIn('general1', self.rapport('j2').read_text())

    @unittest.skipUnless(os.name == 'posix', 'Liens Linux requis')
    def test_rapport_lie_refuse_et_demande_fifo_non_bloquante(self):
        g = self.creer(territoire='village', place='ecole_officiers/1')
        self.resolution()
        os.link(self.rapport(), self.rapport().with_suffix('.lien'))
        with self.assertRaises(RuntimeError):
            self.rapports.noter_activite(self.profil, 'j1', 'TEST', 'interdit')
        demande = g['chemin'] / 'info/lire_les_memoires.txt'
        os.mkfifo(demande)
        with self.assertRaises(ValueError):
            self.formation.lire_demande(self.profil, demande)


if __name__ == '__main__':
    unittest.main()
