"""Tests sans plateau pour les règles spécifiées du Bouclier vivant."""
import random
import sys
from pathlib import Path
import unittest
from fractions import Fraction

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import bouclier_vivant as b


class BouclierVivant(unittest.TestCase):
    def test_usure_et_fraction(self):
        ok, restant = b.resistance_apres_choc(250, 150)
        self.assertTrue(ok)
        self.assertEqual(restant, Fraction(425, 2))  # 212,5
        ok, restant = b.resistance_apres_choc(restant, 50)
        self.assertTrue(ok)
        self.assertEqual(restant, 200)

    def test_egalite_ou_depassement_detruit(self):
        self.assertEqual(b.resistance_apres_choc(150, 150), (False, 0))
        self.assertEqual(b.resistance_apres_choc(150, 151), (False, 0))

    def test_spore_soldat_le_moins_experimente(self):
        soldats = [{"id": "veteran", "batailles": 6},
                   {"id": "debutant1", "batailles": 1},
                   {"id": "debutant2", "batailles": 1}]
        choisi = b.choisir_spore(soldats, random.Random(7))
        self.assertIn(choisi["id"], {"debutant1", "debutant2"})
        self.assertIsNone(b.choisir_spore([]))

    def test_destination_plus_nombreuse(self):
        effectifs = {"avant": 1, "arriere": 11, "droite": 4}
        self.assertEqual(b.bloc_destination_spore(effectifs, list(effectifs)), "arriere")
        self.assertIsNone(b.bloc_destination_spore(effectifs, []))

    def test_seul_bouclier_ne_gagne_pas(self):
        self.assertTrue(b.seulement_bouclier({"avant": {"Trop_gros_zombie": 1},
                                               "arriere": {"messager_du_QG": 1}}))
        self.assertFalse(b.seulement_bouclier({"avant": {"Trop_gros_zombie": 1},
                                                "arriere": {"zombie": 1}}))

    def test_bouclier_unique(self):
        with self.assertRaises(ValueError):
            b.verifier_un_seul_bouclier({"avant": {"Trop_gros_zombie": 1},
                                        "droite": {"Trop_gros_zombie": 1}})
        self.assertEqual(b.verifier_un_seul_bouclier({"avant": {"Trop_gros_zombie": 1}}), 1)


if __name__ == "__main__":
    unittest.main()
