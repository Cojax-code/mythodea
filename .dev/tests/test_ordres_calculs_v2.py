"""Formules V2 confirmées, sans exécution d'effets en partie."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import ordres_calculs_v2 as calculs


class TestOrdresCalculsV2(unittest.TestCase):
    def test_charge_suicidaire_pertes_du_seul_duel(self):
        for pertes, attendu in ((0, 0), (3, 0), (4, 1),
                                (7, 1), (8, 2), (20, 5)):
            with self.subTest(pertes=pertes):
                self.assertEqual(calculs.probabilite_charge_suicidaire(pertes),
                                 attendu)

    def test_ralliement_par_type_arrondi_inferieur(self):
        self.assertEqual(calculs.renforts_ralliement(
            {"archer": 6, "piquier": 5},
            {"archer"}), {"archer": 1})
        self.assertEqual(calculs.renforts_ralliement(
            {"archer": 6, "piquier": 5},
            {"archer", "piquier"}), {"archer": 1, "piquier": 1})
        self.assertEqual(calculs.renforts_ralliement(
            {"archer": 4, "piquier": 15},
            {"archer", "piquier"}), {"archer": 0, "piquier": 3})

    def test_entiers_positifs_requis(self):
        for valeur in (-1, 1.2, True, "20"):
            with self.subTest(valeur=valeur):
                with self.assertRaises(ValueError):
                    calculs.probabilite_charge_suicidaire(valeur)
                with self.assertRaises(ValueError):
                    calculs.renforts_ralliement({"archer": valeur}, {"archer"})


    def test_discours_mort_pourcentage_de_la_valeur_actuelle(self):
        from fractions import Fraction
        self.assertEqual(calculs.facteur_discours_de_la_mort(30), 33)
        self.assertEqual(calculs.facteur_discours_de_la_mort(31), Fraction(341, 10))
        self.assertEqual(calculs.facteur_discours_de_la_mort(0), 0)
        # Ne jamais choisir arbitrairement l'arrondi à ce stade.
        self.assertEqual(calculs.facteur_discours_de_la_mort(99), Fraction(1089, 10))

    def test_reserve_interceptions_repetables(self):
        for _ in range(3):
            self.assertTrue(calculs.reserve_peut_intercepter(True, 5))
        self.assertFalse(calculs.reserve_peut_intercepter(False, 5))
        self.assertFalse(calculs.reserve_peut_intercepter(True, 0))
        self.assertFalse(calculs.reserve_peut_intercepter(True, 5, deja_elimine=True))

    def test_derniere_charge_defaite_obligatoire(self):
        self.assertFalse(calculs.derniere_charge_possible(False, "G"))
        self.assertTrue(calculs.derniere_charge_possible(True, "D"))
        with self.assertRaises(ValueError):
            calculs.derniere_charge_possible(True, "GD")


    def test_rafale_tentatives_par_quatre_archers(self):
        for archers, tirs in ((0, 0), (3, 0), (4, 1), (7, 1),
                             (8, 2), (20, 5)):
            self.assertEqual(calculs.tentatives_rafale(archers), tirs)

    def test_confinement_neutralise_spore_et_son_bonus(self):
        self.assertEqual(calculs.conversions_spore(1), 1)
        self.assertEqual(calculs.conversions_spore(1, True), 2)
        self.assertEqual(calculs.conversions_spore(1, True, True), 0)
        self.assertEqual(calculs.conversions_spore(1, False, True), 0)

    def test_propagation_bonus_deux(self):
        self.assertEqual(calculs.conversions_propagation(4), 4)
        self.assertEqual(calculs.conversions_propagation(4, True), 6)


if __name__ == "__main__":
    unittest.main()
