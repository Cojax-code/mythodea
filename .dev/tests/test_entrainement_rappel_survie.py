"""Attribution initiale, entraînement et rappel sur générations isolées."""
import random
import shutil
import unittest
from unittest.mock import patch

import test_cycle_survie
from support_cycle import GelSimule


class EntrainementRappelSurvie(unittest.TestCase):
    setUp = test_cycle_survie.CycleSurvie.setUp
    general = test_cycle_survie.CycleSurvie.general
    activer = test_cycle_survie.CycleSurvie.activer

    def chemin(self, territoire='home', joueur='j1', reserve=False, place='1'):
        if territoire == 'home':
            return self.racine / 'home' / joueur / 'general1'
        if territoire == 'repli':
            return self.config.repli_path / joueur / 'general1'
        zones = self.generaux.zones_generaux_territoire(
            self.config.game_path / territoire, joueur, self.profil)
        return next(z['chemin'] for z in zones if (
            z['chemin'].name == 'reserve' if reserve else z.get('emplacement') == place)) / 'general1'

    def ajouter(self, chemin, numero=9):
        unite = chemin / 'avant' / f'infanterie{numero}'
        unite.mkdir()
        (unite / 'arc').touch()
        return unite

    def audit(self):
        self.securite.verifier_tous_les_deplacements(self.profil)

    def reference(self):
        return self.etat.charger_unites_actions(self.profil)

    def nouvelle_partie(self):
        for nom in ('cycle_survie.json', 'unites_actions.json'):
            (self.config.game_path / '.systeme' / nom).unlink(missing_ok=True)
        return self.survie.ouvrir_tour_survie(self.profil, lambda: 100)

    def resoudre(self):
        gestion = self.cycle_linux.Generations(self.profil, GelSimule())
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            return self.survie.resoudre_tour_survie(self.profil, random.Random(4), gestion)

    def test_nouvelle_partie_premiers_generaux_avant_actions_et_idempotence(self):
        original = self.etat.sauvegarder_cycle_survie
        def enregistrer(cycle, configuration):
            if cycle['phase'] == 'actions':
                for j in ('j1', 'j2'):
                    self.assertTrue(self.chemin(joueur=j).is_dir())
                    self.assertEqual(self.etat.lire_compteur_general(j), 1)
                    self.assertEqual(self.etat.initialiser_quota_normal(j), 1)
                    self.assertEqual(self.etat.charger_positions_generaux()[f'{j}:general1'], 'home')
            return original(cycle, configuration)
        with patch.object(self.etat, 'sauvegarder_cycle_survie', side_effect=enregistrer):
            cycle = self.nouvelle_partie()
        reference = self.reference()
        self.assertEqual(self.survie.ouvrir_tour_survie(self.profil, lambda: 500), cycle)
        self.assertEqual(self.reference(), reference)
        for j in ('j1', 'j2'):
            self.assertEqual([p.name for p in self.chemin(joueur=j).parent.glob('general*')], ['general1'])

    def test_actions_zero_premarque_sans_attribution_est_repare(self):
        self.activer(0)
        cycle = self.etat.charger_cycle_survie(self.profil)
        self.survie.ouvrir_tour_survie(self.profil)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil), cycle)
        for joueur in ('j1', 'j2'):
            self.assertTrue(self.chemin(joueur=joueur).exists())
            self.assertEqual(self.etat.lire_compteur_general(joueur), 1)

    def test_actions_legacy_zero_vierge_sans_reference(self):
        self.activer(0)
        (self.config.game_path / '.systeme/unites_actions.json').unlink()
        self.survie.ouvrir_tour_survie(self.profil)
        self.assertTrue(self.chemin().exists())
        self.assertIsNotNone(self.reference())

    def test_reprise_et_destruction_ne_reutilisent_pas_numero(self):
        self.nouvelle_partie()
        shutil.rmtree(self.chemin())
        positions = self.etat.charger_positions_generaux()
        positions.pop('j1:general1')
        self.etat.sauvegarder_positions_generaux(positions)
        self.survie.ouvrir_tour_survie(self.profil)
        self.assertFalse(self.chemin().exists())
        self.etat.sauvegarder_cycle_survie({'tour': 1, 'phase': 'a_preparer'}, self.profil)
        self.survie.ouvrir_tour_survie(self.profil)
        self.assertFalse(self.chemin().exists())
        self.assertTrue((self.chemin().parent / 'general2').exists())
        self.assertEqual(self.etat.lire_compteur_general('j1'), 2)
        self.assertNotIn('j1:general1', self.etat.charger_positions_generaux())

    def test_preparation_interrompue_non_rejouee(self):
        self.nouvelle_partie()
        self.etat.sauvegarder_cycle_survie({'tour': 0, 'phase': 'preparation'}, self.profil)
        with self.assertRaisesRegex(RuntimeError, 'interrompu'):
            self.survie.ouvrir_tour_survie(self.profil)
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)

    def test_ajouts_home_et_reserve_autorises(self):
        for numero, territoire, reserve in ((1, 'home', False), (2, 'village', True)):
            chemin = self.general(numero=numero, territoire=territoire, reserve=reserve, nombre=2)
            nouvelle = self.ajouter(chemin)
            self.audit()
            self.assertTrue(nouvelle.exists())
            self.assertEqual(self.generaux.total_general_depuis_chemin(chemin), 3)

    def test_ajouts_interdits_anciennes_unites_conservees(self):
        for numero, territoire, place in ((1, 'village', '1'), (2, 'est_1', '1'),
                (3, 'est_2', '1'), (4, 'est_3', '1'), (5, 'repli', '1'),
                (6, 'est_1', '5')):
            with self.subTest(territoire=territoire, place=place):
                chemin = self.general(numero=numero, territoire=territoire, place=place, nombre=2)
                ancienne = chemin / 'avant/infanterie1'
                ancienne.rename(chemin / 'arriere/infanterie77')
                nouvelle = self.ajouter(chemin)
                self.audit()
                self.assertFalse(nouvelle.exists())
                self.assertTrue((chemin / 'arriere/infanterie77/arc').exists())
                self.assertEqual(self.generaux.total_general_depuis_chemin(chemin), 2)
        self.assertIn('entraînement interdit hors home/réserve',
                      self.config.rapport_long_path.read_text(encoding='utf-8'))

    def test_finalisation_et_copie_ne_contournent_pas_inventaire(self):
        chemin = self.general(territoire='est_1', nombre=1)
        incomplet = chemin / 'avant/infanterie8'
        incomplet.mkdir()
        self.securite.memoriser_unites_actions(self.profil, 1)
        (incomplet / 'arc').touch()
        shutil.copytree(chemin / 'avant/infanterie1', chemin / 'avant/infanterie9')
        self.audit()
        self.assertFalse(incomplet.exists())
        self.assertFalse((chemin / 'avant/infanterie9').exists())
        self.assertTrue((chemin / 'avant/infanterie1/arc').exists())

    def test_recompense_crypte_refuse_ajouts_sans_supprimer_recompense(self):
        chemin = self.general(territoire='village', nombre=2)
        destination = self.config.game_path / 'village/j1/crypte/recompense/general1'
        self.survie.crypte.preparer(self.profil)
        chemin.rename(destination)
        donnees = self.survie.crypte.charger(self.profil)
        donnees['j1']['en_attente'] = 'general1'
        self.survie.crypte.sauver(self.profil, donnees)
        self.securite.memoriser_unites_actions(self.profil, 1)
        nouvelle = self.ajouter(destination)
        self.audit()
        self.assertFalse(nouvelle.exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(destination), 2)

    def test_deplacement_inter_partition_conserve_effectif_et_bloque_surplus(self):
        origine = self.general(territoire='home', nombre=2)
        destination = self.chemin('village')
        shutil.copytree(origine, destination)
        shutil.rmtree(origine)
        reference = self.reference()
        reference['generaux']['home/j1/general1']['device'] = -1
        self.etat.sauvegarder_unites_actions(self.profil, reference)
        self.audit()
        self.assertTrue(destination.exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(destination), 2)
        # Une autre traversée avec un renfort net reste un entraînement mobile.
        destination.rename(origine)
        self.etat.sauvegarder_positions_generaux({'j1:general1': 'home'})
        self.securite.memoriser_unites_actions(self.profil, 2)
        reference = self.reference()
        reference['generaux']['home/j1/general1']['device'] = -1
        self.etat.sauvegarder_unites_actions(self.profil, reference)
        self.ajouter(origine)
        origine.rename(destination)
        self.audit()
        self.assertTrue(origine.exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(origine), 3)

    def test_entrainement_home_deplacement_refuse_puis_tour_suivant_autorise(self):
        origine = self.general(territoire='home', nombre=2)
        self.ajouter(origine)
        destination = self.chemin('village')
        origine.rename(destination)
        self.audit()
        self.assertTrue(origine.exists())
        self.assertFalse(destination.exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(origine), 3)
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'home')
        self.assertEqual(self.etat.charger_generaux_fatigues(), set())
        self.activer(2)
        origine.rename(destination)
        self.audit()
        self.assertTrue(destination.exists())
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'village')

    def test_entrainement_reserve_bloque_meme_reorganisation_garnison(self):
        origine = self.general(territoire='village', reserve=True, nombre=2)
        self.ajouter(origine)
        destination = self.chemin('village')
        origine.rename(destination)
        self.audit()
        self.assertTrue(origine.exists())
        self.assertFalse(destination.exists())
        self.activer(2)
        origine.rename(destination)
        self.audit()
        self.assertTrue(destination.exists())

    def test_home_vers_reserve_apres_entrainement_attend_aussi(self):
        origine = self.general(territoire='home', nombre=2)
        self.ajouter(origine)
        origine.rename(self.chemin('village', reserve=True))
        self.audit()
        self.assertTrue(origine.exists())

    def test_entrainement_refuse_avant_collision_avec_general_innocent(self):
        origine = self.general(territoire='home', nombre=2)
        innocent = self.general('j2', territoire='village', nombre=2)
        self.ajouter(origine)
        origine.rename(self.chemin('village'))
        self.audit()
        self.assertTrue(origine.exists())
        self.assertTrue(innocent.exists())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})

    def test_sans_entrainement_mouvement_et_marche_forcee_inchanges(self):
        origine = self.general(territoire='village', nombre=2)
        origine.rename(self.chemin('est_2'))
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'est_2')
        self.assertEqual(self.etat.charger_generaux_fatigues(), {'j1:general1'})

    def test_rappel_est1_est2_sans_fatigue_et_retour_village(self):
        for joueur, territoire in (('j1', 'est_1'), ('j2', 'est_2')):
            origine = self.general(joueur, territoire=territoire, nombre=2)
            self.etat.sauvegarder_generaux_fatigues({f'{joueur}:general1'})
            origine.rename(self.chemin(joueur=joueur))
            self.audit()
            self.assertEqual(self.etat.charger_positions_generaux()[f'{joueur}:general1'], 'home')
            self.assertNotIn(f'{joueur}:general1', self.etat.charger_generaux_fatigues())
        self.activer(2)
        self.chemin().rename(self.chemin('village'))
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'village')
        self.activer(3)
        self.chemin('village').rename(self.chemin('est_1'))
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'est_1')

    def test_home_vers_front_apres_rappel_refuse(self):
        origine = self.general(territoire='est_2', nombre=2)
        origine.rename(self.chemin())
        self.audit()
        self.activer(2)
        self.chemin().rename(self.chemin('est_1'))
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'repli')

    def test_rappel_puis_renforcement_home_attente_normale(self):
        origine = self.general(territoire='est_1', nombre=2)
        origine.rename(self.chemin())
        self.ajouter(self.chemin())
        self.audit()
        self.assertEqual(self.generaux.total_general_depuis_chemin(self.chemin()), 3)
        self.activer(2)
        self.chemin().rename(self.chemin('village'))
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'village')

    def test_repli_ne_peut_pas_etre_rappele(self):
        origine = self.general(territoire='repli', nombre=2)
        self.etat.sauvegarder_attentes_repli({'j1:general1': 2}, self.profil)
        origine.rename(self.chemin())
        self.audit()
        self.assertTrue(origine.exists())
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'repli')
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {'j1:general1': 2})

    def test_rappel_adverse_non_enregistre(self):
        origine = self.general('j2', territoire='est_1', nombre=2)
        destination = self.chemin(joueur='j1')
        origine.rename(destination)
        with patch.object(self.securite, 'joueur_proprietaire_chemin', return_value='j2'):
            self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()['j2:general1'], 'est_1')
        self.assertNotIn('j1:general1', self.etat.charger_positions_generaux())

    def test_rappel_origine_invalide_non_enregistre(self):
        origine = self.general(territoire='est_1', nombre=2)
        self.etat.sauvegarder_positions_generaux({'j1:general1': 'position_invalide'})
        origine.rename(self.chemin())
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()['j1:general1'], 'position_invalide')
        self.assertIn('rappel refusé', self.config.rapport_long_path.read_text(encoding='utf-8'))

    def test_capture_privee_et_publication_debloquent_entrainement(self):
        self.nouvelle_partie()
        self.ajouter(self.chemin())
        self.chemin().rename(self.chemin('village'))
        self.resoudre()
        self.assertTrue(self.chemin().exists())
        self.assertEqual(self.reference()['tour'], 1)
        self.assertNotIn('capture', self.reference())
        self.etat.sauvegarder_cycle_survie({'tour': 1, 'phase': 'a_preparer'}, self.profil)
        self.survie.ouvrir_tour_survie(self.profil)
        self.chemin().rename(self.chemin('village'))
        self.resoudre()
        self.assertTrue(self.chemin('village').exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(self.chemin('village')), 1)

    def test_reprise_actions_preserve_reference_et_ajouts_detectes(self):
        chemin = self.general(territoire='est_1', nombre=2)
        avant = self.reference()
        self.ajouter(chemin)
        self.survie.ouvrir_tour_survie(self.profil)
        self.assertEqual(self.reference(), avant)
        self.resoudre()
        self.assertEqual(self.generaux.total_general_depuis_chemin(chemin), 2)

    def test_reference_absente_partie_existante_refusee_sans_recreation(self):
        self.general(territoire='est_1', nombre=2)
        (self.config.game_path / '.systeme/unites_actions.json').unlink()
        with self.assertRaisesRegex(RuntimeError, 'sans référence'):
            self.survie.ouvrir_tour_survie(self.profil)
        self.assertEqual(self.etat.lire_compteur_general('j1'), 1)

    def test_republication_sans_rejouer_entrainement(self):
        self.general(territoire='home', nombre=2)
        self.ajouter(self.chemin())
        self.chemin().rename(self.chemin('village'))
        with patch.object(self.rapports, 'publier_rapports_exploration', side_effect=RuntimeError('panne')):
            with self.assertRaisesRegex(RuntimeError, 'panne'):
                self.resoudre()
        import survie_admin
        cycle = self.etat.charger_cycle_survie(self.profil)
        with patch.object(survie_admin.cycle_linux, 'Linux', return_value=GelSimule()), \
                patch.object(self.securite, 'verifier_tous_les_deplacements', side_effect=AssertionError('rejeu')):
            survie_admin.republier(self.profil, cycle['generation'])
        self.assertTrue(self.chemin().exists())
        self.assertEqual(self.generaux.total_general_depuis_chemin(self.chemin()), 3)
        self.assertEqual(self.reference()['tour'], 2)


if __name__ == '__main__':
    unittest.main()
