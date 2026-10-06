"""Sanctions du moteur commun, sur plateau isolé et avec droits Unix simulés."""
import contextlib
import io
import unittest
from unittest.mock import call

import test_village


class SanctionsRepli(unittest.TestCase):
    def setUp(self):
        test_village.Village.setUp(self)
        self.contextes.enter_context(contextlib.redirect_stdout(io.StringIO()))

    chemin = test_village.Village.chemin
    general = test_village.Village.general
    audit = test_village.Village.audit

    def test_distances_minimales_et_arrondi_dans_les_deux_modes(self):
        for lieu, attendu in (("village", 0), ("est_1", 1), ("est_2", 1), ("est_3", 2)):
            self.assertEqual(self.mouvements.delai_sanction_repli("j1", lieu, self.profil), attendu)
        classique = self.config.configuration_mode("classique")
        for joueur, lieux in (("j1", ("base1", "terrain1", "terrain2", "terrain3", "base2")),
                             ("j2", ("base2", "terrain3", "terrain2", "terrain1", "base1"))):
            for lieu, attendu in zip(lieux, (0, 1, 1, 2, 2)):
                self.assertEqual(self.mouvements.delai_sanction_repli(joueur, lieu, classique), attendu)
        self.profil["territoires"].extend(self.config.game_path / f"est_{n}" for n in (4, 5))
        self.profil["carte_territoires"].update({"est_3": ["est_2", "est_4"],
                                                "est_4": ["est_3", "est_5"], "est_5": ["est_4"]})
        self.assertEqual(self.mouvements.delai_sanction_repli("j1", "est_5", self.profil), 3)

    def test_collision_delai_persistant_actions_bloquees_puis_retour(self):
        self.general(territoire="est_3")
        self.general("j2", territoire="est_3")
        self.audit()
        self.assertEqual(self.etat.charger_attentes_repli(self.profil),
                         {"j1:general1": 2, "j2:general1": 2})
        fichier = self.config.game_path / "systeme/attente_repli.txt"
        self.assertIn(call(fichier, 0, 0), self.chown.call_args_list)
        self.assertIn(call(fichier, 0o600), self.chmod.call_args_list)
        for restant in (1, 0):
            # Même un retour à la bonne destination reste interdit pendant l'attente.
            self.chemin(territoire="repli").rename(self.chemin())
            self.audit()
            self.assertFalse(self.chemin().exists())
            self.assertTrue(self.chemin(territoire="repli").exists())
            self.assertEqual(self.etat.charger_attentes_repli(self.profil).get("j1:general1", 0), restant)
        self.chemin(territoire="repli").rename(self.chemin())
        self.audit()
        self.assertEqual(self.etat.charger_positions_generaux()["j1:general1"], "village")
        self.assertTrue((self.chemin() / "avant/infanterie1/arc").exists())

    def test_reparation_et_scan_ne_decrementent_pas(self):
        self.general(territoire="est_2")
        self.general("j2", territoire="est_2")
        self.audit()
        attentes = self.etat.charger_attentes_repli(self.profil)
        self.plateau.reparer_structure(self.profil)
        self.generaux.scanner_ordres_surnombre(self.profil)
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), attentes)

    def test_sortie_prematuree_ne_sanctionne_pas_un_occupant_innocent(self):
        general = self.general(territoire="est_3")
        self.mouvements.envoyer_general_au_repli("j1", "general1", general, self.profil)
        positions = self.etat.charger_positions_generaux()
        positions["j1:general1"] = "repli"
        self.etat.sauvegarder_positions_generaux(positions)
        occupant = self.general("j2")
        self.chemin(territoire="repli").rename(self.chemin())
        self.audit()
        self.assertTrue(occupant.exists())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {"j1:general1": 1})

    def test_copie_chez_adversaire_sanctionne_depuis_le_lieu_de_la_copie(self):
        general = self.general(territoire="village")
        copie = self.general("j2", territoire="est_3")
        self.proprietaires[copie] = "j1"
        self.audit()
        self.assertFalse(general.exists())
        self.assertFalse(copie.exists())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {"j1:general1": 2})

    def test_mauvais_proprietaire_utilise_lieu_constatation(self):
        general = self.general(territoire="village")
        mauvais = self.chemin("j2", territoire="est_3")
        general.rename(mauvais)
        self.proprietaires[mauvais] = "j1"
        self.audit()
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {"j1:general1": 2})

    def test_distance_speciale_ou_inaccessible_refusee(self):
        for lieu in ("home", "repli", "inconnu"):
            with self.assertRaisesRegex(ValueError, "non définie"):
                self.mouvements.delai_sanction_repli("j1", lieu, self.profil)
        self.profil["carte_territoires"]["est_3"] = []
        with self.assertRaisesRegex(ValueError, "Aucun chemin"):
            self.mouvements.delai_sanction_repli("j1", "est_3", self.profil)


if __name__ == "__main__":
    unittest.main()
