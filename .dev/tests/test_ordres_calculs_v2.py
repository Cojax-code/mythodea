"""Formules V2 confirmées, sans exécution d'effets en partie."""
import sys
import unittest
import random
from unittest.mock import Mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import ordres_calculs_v2 as calculs


class TestOrdresCalculsV2(unittest.TestCase):
    def test_muraille_meilleur_bilan_puis_position_numerique_origine(self):
        a, b = ('j1', 'general1'), ('j1', 'general2')
        positions = {a: '10', b: '2'}
        hasard = Mock()
        self.assertEqual(calculs.choisir_avant_muraille({a: 4, b: 3}, positions, hasard), a)
        self.assertEqual(calculs.choisir_avant_muraille({a: 4, b: 4}, positions, hasard), b)
        # Le nouvel engagement doit utiliser les bilans recalculés fournis.
        self.assertEqual(calculs.choisir_avant_muraille({a: -2, b: -1}, positions, hasard), b)
        self.assertIsNone(calculs.choisir_avant_muraille({}, {}, hasard))
        hasard.choice.assert_not_called()

    def test_muraille_egalite_hasard_reproductible_independant_du_parcours(self):
        a, b = ('j1', 'general1'), ('j2', 'general1')
        positions = {a: '2', b: '2'}
        choix = set()
        for graine in range(20):
            x = calculs.choisir_avant_muraille({a: 5, b: 5}, positions, random.Random(graine))
            y = calculs.choisir_avant_muraille({b: 5, a: 5}, positions, random.Random(graine))
            self.assertEqual(x, y)
            choix.add(x)
        self.assertEqual(choix, {a, b})

    def test_muraille_refuse_positions_et_bilans_invalides(self):
        identite = ('j1', 'general1')
        hasard = Mock()
        for position in (None, 'village', '0', '-1', '１'):
            with self.assertRaises(ValueError):
                calculs.choisir_avant_muraille({identite: 1}, {identite: position}, hasard)
        for bilan in (True, 1.5, '4'):
            with self.assertRaises(ValueError):
                calculs.choisir_avant_muraille({identite: bilan}, {identite: '1'}, hasard)
        hasard.choice.assert_not_called()

    def test_facteurs_moraux_exacts_et_entrees_invalides(self):
        from fractions import Fraction
        self.assertEqual(50 * calculs.facteur_cruelle(10), 45)
        self.assertEqual(31 * calculs.facteur_cruelle(10), Fraction(279, 10))
        self.assertEqual(calculs.facteur_discours_de_la_mort(Fraction(4692, 100)),
                         Fraction(12903, 250))
        for valeur in (True, -1, 2.5, '10'):
            with self.assertRaises(ValueError):
                calculs.facteur_cruelle(valeur)
            with self.assertRaises(ValueError):
                calculs.facteur_discours_de_la_mort(valeur)

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

    def test_derniere_charge_casse_et_absence_sans_autre_flanc(self):
        for flanc in ('G', 'g', 'D', 'd'):
            self.assertTrue(calculs.derniere_charge_possible(True, flanc, effectif_eligible=1))
            self.assertFalse(calculs.derniere_charge_possible(False, flanc, effectif_eligible=1))
            self.assertFalse(calculs.derniere_charge_possible(True, flanc, effectif_eligible=0))
        for valeur in (-1, True, 1.5, '1'):
            with self.assertRaises(ValueError):
                calculs.derniere_charge_possible(True, 'g', effectif_eligible=valeur)
        for flanc in ('', 'gd', 'gauche', ' G ', None):
            with self.assertRaises(ValueError):
                calculs.derniere_charge_possible(True, flanc)


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
