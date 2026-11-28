"""Contrats validés après les essais Pi : option B, reprise et noms officiels."""
import importlib
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

import test_crypte


class CorrectionsPi(unittest.TestCase):
    setUp = test_crypte.Crypte.setUp
    activer = test_crypte.Crypte.activer
    message = test_crypte.Crypte.message
    commande = test_crypte.Crypte.commande
    reussir = test_crypte.Crypte.reussir
    etapes_archers = test_crypte.Crypte.etapes_archers
    reussir_archers = test_crypte.Crypte.reussir_archers
    gestion = test_crypte.Crypte.gestion

    def recompense(self, nom='amelie_poulin1'):
        return self.crypte.zone(self.profil, 'j1') / 'recompense' / nom

    def test_reprise_construction_conserve_profil_et_soldats(self):
        soldats = importlib.import_module('soldats')
        with patch.object(soldats, 'publier', side_effect=OSError('coupure')):
            with self.assertRaisesRegex(OSError, 'coupure'):
                self.reussir()
        avant = soldats.charger()
        self.assertEqual(len(avant), 20)
        self.assertFalse(self.recompense().exists())
        self.crypte.reprendre_livraisons(self.profil)
        self.assertEqual(set(soldats.charger()), set(avant))
        self.assertEqual(len(self.crypte.charger(self.profil)['j1']['attributions']), 1)
        self.assertEqual(len(list(self.recompense().glob('*/*/identifiant_soldat.txt'))), 20)
        self.crypte.reprendre_livraisons(self.profil)
        self.assertEqual(set(soldats.charger()), set(avant))

    def test_reprise_apres_renommage_ne_recree_pas_general_deplace(self):
        original = self.cycle_linux.renommer_sans_ecraser
        def interrompre(source, destination):
            original(source, destination)
            raise OSError('après mv')
        with patch.object(self.cycle_linux, 'renommer_sans_ecraser', side_effect=interrompre):
            with self.assertRaisesRegex(OSError, 'après mv'):
                self.reussir()
        destination = self.config.game_path / 'village/j1/caserne_militaire/amelie_poulin1'
        self.recompense().rename(destination)
        avant = {str(p.relative_to(destination)): p.read_bytes() for p in destination.glob('*/*/identifiant_soldat.txt')}
        self.crypte.reprendre_livraisons(self.profil)
        self.assertFalse(self.recompense().exists())
        self.assertTrue(destination.exists())
        self.assertEqual(avant, {str(p.relative_to(destination)): p.read_bytes() for p in destination.glob('*/*/identifiant_soldat.txt')})
        self.assertEqual(len(self.crypte.charger(self.profil)['j1']['attributions']), 1)

    def test_destination_existante_jamais_ecrasee(self):
        original = self.cycle_linux.renommer_sans_ecraser
        def collision(source, destination):
            destination.mkdir()
            (destination / 'personnel').write_text('à préserver')
            return original(source, destination)
        with patch.object(self.cycle_linux, 'renommer_sans_ecraser', side_effect=collision):
            with self.assertRaises(OSError):
                self.reussir()
        self.assertEqual((self.recompense() / 'personnel').read_text(), 'à préserver')
        with self.assertRaises(OSError):
            self.crypte.reprendre_livraisons(self.profil)

    def test_mobilisation_immediate_caserne_et_preparation_unique(self):
        self.reussir()
        destination = self.config.game_path / 'village/j1/caserne_militaire/amelie_poulin1'
        self.recompense().rename(destination)
        with patch.object(self.survie, 'creer_vague_est', return_value=[]):
            self.survie.resoudre_tour_survie(self.profil, gestion=self.gestion())
        profil = importlib.import_module('progression').charger()['j1:amelie_poulin1']
        self.assertEqual(profil['progression_formation'], 1)
        rapport = self.config.game_path / 'village/j1/hotel_de_ville/rapport_activites.txt'
        self.assertEqual(rapport.read_text().count('préparation terminée'), 1)
        self.assertEqual(rapport.read_text().count('créé et attribué'), 1)
        self.assertEqual(self.etat.lire_compteur_general('j1'), 0)

    def test_sortie_immediate_village_refusee(self):
        self.reussir()
        destination = self.config.game_path / 'est_1/j1/1/amelie_poulin1'
        self.recompense().rename(destination)
        self.securite.verifier_tous_les_deplacements(self.profil)
        self.assertEqual(self.etat.charger_positions_generaux()['j1:amelie_poulin1'], 'repli')
        self.assertTrue((self.profil['repli_path'] / 'j1/amelie_poulin1').is_dir())

    def test_faux_special_supprime_et_fichier_personnel_home_preserve(self):
        faux = self.config.game_path / 'village/j1/caserne_militaire/pic_nic1'
        self.generaux.creer_general(faux, faux.name)
        home = self.racine / 'home/j1'
        personnel = home / 'pic_nic_notes'
        personnel.write_text('notes personnelles')
        self.securite.supprimer_generaux_non_autorises(self.profil)
        self.assertFalse(faux.exists())
        self.assertNotIn(personnel, self.cycle_linux.entrees_home(home))
        self.assertEqual(personnel.read_text(), 'notes personnelles')

    def test_capture_special_home_et_rollback_sans_double_attribution(self):
        self.reussir()
        home = self.racine / 'home/j1'
        self.recompense().rename(home / 'amelie_poulin1')
        self.assertIn(home / 'amelie_poulin1', self.cycle_linux.entrees_home(home))
        gestion = self.gestion()
        with patch.object(self.survie, '_resoudre_tour_capture', side_effect=OSError('interruption')):
            with self.assertRaisesRegex(OSError, 'interruption'):
                self.survie.resoudre_tour_survie(self.profil, gestion=gestion)
        admin = importlib.import_module('survie_admin')
        soldats = importlib.import_module('soldats')
        avant = set(soldats.charger())
        admin.rollback(self.profil, dry_run=True)
        admin.rollback(self.profil, gestion=gestion)
        self.assertTrue((home / 'amelie_poulin1').is_dir())
        self.crypte.reprendre_livraisons(self.profil)
        self.assertEqual(set(soldats.charger()), avant)
        self.assertFalse(self.recompense().exists())
        self.assertEqual(len(self.crypte.charger(self.profil)['j1']['attributions']), 1)
        self.assertEqual(self.etat.charger_cycle_survie(self.profil)['phase'], 'actions')

    def test_migration_delais_avec_historique_et_sans_preuve(self):
        d = self.crypte.charger(self.profil)
        for fiche in d.values():
            fiche.pop('derniers_tours')
            fiche['dernier_tour'] = 9
        d['j1']['attributions'] = [dict(id='ancien', tour=9, recette='recette2', general='general4')]
        self.crypte.sauver(self.profil, d)
        actuel = self.crypte.charger(self.profil)
        self.assertEqual(actuel['j1']['derniers_tours'], dict(recette1=None, recette2=9, recette3=None))
        self.assertEqual(actuel['j2']['derniers_tours'], dict.fromkeys(self.crypte.RECETTES, 9))
        self.assertEqual(actuel['j1']['attributions'][0]['general'], 'general4')

    def test_tableau_unicode_noms_longs_et_ansi(self):
        r = self.rapports
        territoire = self.config.game_path / 'est_1'
        r.ecrire_entete_tableau_affrontements(territoire, 'Tour', ('allies', 'bot'))
        r.ecrire_ligne_affrontement_territoire(territoire, 12345,
            dict(final_1=14, final_2=0, initial_1=20, initial_2=100,
                 joueur_1='j1', joueur_2='bot', general_1='amelie_poulin12345_日本',
                 general_2='general123456', camp_1='allies'))
        r.ecrire_fin_tableau_affrontements(territoire)
        lignes = r._tableaux['est_1']['lignes']
        self.assertEqual(len({r.largeur_visible(l) for l in lignes}), 1)
        self.assertEqual(r.largeur_visible('\x1b[31m○ → ×\x1b[0m'), 5)

    @unittest.skipUnless(os.name == 'posix', 'Socket et /proc Linux requis')
    def test_nettoyage_residus_inactifs_dry_run_idempotent_socket_active_refusee(self):
        admin = importlib.import_module('survie_admin')
        fichier = self.config.game_path / '.systeme/communication/crypte.sock'
        fichier.parent.mkdir(exist_ok=True)
        canal = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(canal.close)
        canal.bind(str(fichier))
        with self.assertRaisesRegex(RuntimeError, 'active'):
            admin.nettoyer_residus(self.profil, dry_run=True)
        canal.close()
        plan = admin.nettoyer_residus(self.profil, dry_run=True)
        self.assertIn('communication/crypte.sock', plan['operations'])
        self.assertTrue(fichier.exists())
        admin.nettoyer_residus(self.profil)
        self.assertFalse(fichier.exists())
        self.assertEqual(admin.nettoyer_residus(self.profil)['operations'], [])

    @unittest.skipUnless(os.name == 'posix', '/proc Linux requis')
    def test_residus_verrou_actif_et_objet_inattendu_refuses(self):
        admin = importlib.import_module('survie_admin')
        with self.etat.verrou_cycle_survie(self.profil):
            with self.assertRaisesRegex(RuntimeError, 'encore présent'):
                admin.nettoyer_residus(self.profil, dry_run=True)
        fichier = self.config.game_path / '.systeme/communication/crypte.sock'
        fichier.parent.mkdir(exist_ok=True)
        fichier.write_text('fichier personnel, pas une socket')
        with self.assertRaisesRegex(RuntimeError, 'type ou propriétaire'):
            admin.nettoyer_residus(self.profil)
        self.assertEqual(fichier.read_text(), 'fichier personnel, pas une socket')


if __name__ == '__main__':
    unittest.main()
