"""Sanctions du moteur commun, sur plateau isolé et avec droits Unix simulés."""
import contextlib
import io
import shutil
import unittest
from unittest.mock import call, patch

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

    def verifier_home_sans_sanction(self, chemins):
        with patch.object(self.mouvements, "delai_sanction_repli") as calcul, \
                patch.object(self.mouvements, "envoyer_general_au_repli") as envoi:
            self.audit()
        calcul.assert_not_called()
        envoi.assert_not_called()
        for chemin in chemins:
            self.assertTrue((chemin / "avant/infanterie1/arc").is_file())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})
        self.assertFalse(list(self.config.repli_path.rglob("general*")))
        self.assertIn("Avertissement dans le home", self.config.rapport_long_path.read_text(encoding="utf-8"))

    def test_home_mauvais_proprietaire_sans_occurrence_correcte(self):
        general = self.general(territoire="home")
        mauvais = self.chemin("j2", territoire="home")
        general.rename(mauvais)
        self.proprietaires[mauvais] = "j1"
        self.verifier_home_sans_sanction([mauvais])
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "home"})

    def test_home_mauvais_proprietaire_avec_occurrence_correcte(self):
        general = self.general(territoire="est_3")
        mauvais = self.chemin("j2", territoire="home")
        shutil.copytree(general, mauvais)
        self.proprietaires[mauvais] = "j1"
        self.verifier_home_sans_sanction([general, mauvais])
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "est_3"})

    def test_home_proprietaire_inconnu_avertissement_uniquement(self):
        general = self.general(territoire="home")
        self.proprietaires[general] = None
        self.verifier_home_sans_sanction([general])

    def test_home_duplication_ne_masque_pas_occurrence_sur_carte(self):
        general = self.general(territoire="est_3")
        copie = self.chemin(territoire="home")
        shutil.copytree(general, copie)
        self.verifier_home_sans_sanction([general, copie])
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "est_3"})

    def test_home_sans_identite_officielle_reste_non_autorise(self):
        general = self.general(territoire="home")
        self.etat.sauvegarder_positions_generaux({})
        self.verifier_home_sans_sanction([general])
        self.assertEqual(self.etat.charger_positions_generaux(), {})

    def test_deplacement_vers_home_avertissement_et_position_reelle(self):
        general = self.general(territoire="est_3")
        home = self.chemin(territoire="home")
        general.rename(home)
        self.verifier_home_sans_sanction([home])
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "home"})

    def test_home_plusieurs_generaux_ne_sont_pas_un_conflit_emplacement(self):
        premier = self.general(territoire="home")
        second = self.general(nom="general2", territoire="home")
        with patch.object(self.mouvements, "envoyer_general_au_repli") as envoi:
            self.assertEqual(self.securite.securiser_emplacements_generaux(self.profil), set())
            self.audit()
        envoi.assert_not_called()
        self.assertTrue(premier.exists())
        self.assertTrue(second.exists())

    def test_home_general_en_attente_sans_envoi_ni_modification_delai(self):
        general = self.general(territoire="repli")
        home = self.chemin(territoire="home")
        general.rename(home)
        attentes = {"j1:general1": 2}
        self.etat.sauvegarder_attentes_repli(attentes, self.profil)
        with patch.object(self.mouvements, "envoyer_general_au_repli") as envoi, \
                patch.object(self.mouvements, "delai_sanction_repli") as calcul:
            self.audit()
        envoi.assert_not_called()
        calcul.assert_not_called()
        self.assertTrue(home.exists())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), attentes)
        self.assertEqual(self.etat.charger_positions_generaux(), {"j1:general1": "home"})

    def test_envoi_direct_depuis_home_ne_calcule_aucun_delai(self):
        general = self.general(territoire="home")
        with patch.object(self.mouvements, "delai_sanction_repli") as calcul:
            self.assertEqual(self.mouvements.envoyer_general_au_repli(
                "j1", "general1", general, self.profil), general)
        calcul.assert_not_called()
        self.assertTrue(general.exists())
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), {})

    def test_deja_repli_duplication_conserve_compteur_sans_calcul(self):
        general = self.general(territoire="repli")
        copie = self.chemin(territoire="est_3")
        shutil.copytree(general, copie)
        attentes = {"j1:general1": 2}
        self.etat.sauvegarder_attentes_repli(attentes, self.profil)
        with patch.object(self.mouvements, "delai_sanction_repli") as calcul:
            self.audit()
        calcul.assert_not_called()
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), attentes)
        self.assertTrue(general.exists())
        self.assertFalse(copie.exists())
        self.assertIn("délai conservé", self.config.rapport_long_path.read_text(encoding="utf-8"))

    def test_deja_repli_copie_chez_autre_joueur_conserve_compteur(self):
        general = self.general(territoire="repli")
        copie = self.chemin("j2", territoire="repli")
        shutil.copytree(general, copie)
        self.proprietaires[copie] = "j1"
        attentes = {"j1:general1": 2}
        self.etat.sauvegarder_attentes_repli(attentes, self.profil)
        with patch.object(self.mouvements, "delai_sanction_repli") as calcul:
            self.audit()
        calcul.assert_not_called()
        self.assertEqual(self.etat.charger_attentes_repli(self.profil), attentes)
        self.assertTrue(general.exists())
        self.assertFalse(copie.exists())

    def test_deja_repli_envoi_direct_conserve_compteur(self):
        general = self.general(territoire="repli")
        for compteur in (None, 2):
            with self.subTest(compteur=compteur):
                attentes = {} if compteur is None else {"j1:general1": compteur}
                self.etat.sauvegarder_attentes_repli(attentes, self.profil)
                with patch.object(self.mouvements, "delai_sanction_repli") as calcul:
                    self.mouvements.envoyer_general_au_repli("j1", "general1", general, self.profil)
                calcul.assert_not_called()
                self.assertEqual(self.etat.charger_attentes_repli(self.profil), attentes)


if __name__ == "__main__":
    unittest.main()
