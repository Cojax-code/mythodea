"""Règles de sélection des futurs ordres V2 (sans effets de combat)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import commandement


CAT = {
    1: dict(categorie='duel', disponible=True, contre=False),
    2: dict(categorie='duel', disponible=True, contre=False),
    3: dict(categorie='duel', disponible=True, contre=True),
    4: dict(categorie='duel', disponible=True, contre=True),
    5: dict(categorie='globale', disponible=True, contre=False),
}


class TestConfrontationOrdres(unittest.TestCase):
    def confrontation(self, a, b, points):
        return commandement.confronter_donneurs(
            a, 'stratege', (), b, 'stratege', (), 'duel', points, CAT)

    def test_egalite_de_deux_ordres_normaux(self):
        self.assertEqual(self.confrontation([1], [2], 0), ([], []))

    def test_ordre_gagnant(self):
        self.assertEqual(self.confrontation([1], [2], 1), ([1], []))

    def test_ordre_et_contre_ordre_les_deux_agissent(self):
        self.assertEqual(self.confrontation([1], [3], 1), ([1], [3]))
        self.assertEqual(self.confrontation([1], [3], -1), ([1], [3]))
        self.assertEqual(self.confrontation([1], [3], 0), ([1], [3]))

    def test_contre_ordre_sans_ordre_adverse(self):
        self.assertEqual(self.confrontation([3], [], 1), ([3], []))
        self.assertEqual(self.confrontation([3], [], 0), ([3], []))

    def test_contre_ordre_perdant(self):
        self.assertEqual(self.confrontation([3], [4], -1), ([3], []))

    def test_cumul_meme_general(self):
        self.assertEqual(self.confrontation([1, 2], [], 0), ([1, 2], []))

    def test_pas_de_cumul_mixte_un_meme_general(self):
        self.assertEqual(self.confrontation([1, 3], [], -1), ([], []))

    def test_comparaison_seule_ne_signifie_pas_absence_adversaire(self):
        self.assertEqual(commandement.ordres_applicables(
            [3], 'stratege', 'duel', comparaison=1, catalogue=CAT), [])

    def test_categorie_validee(self):
        with self.assertRaises(ValueError):
            commandement.confronter_donneurs(
                [1], 'stratege', (), [], 'stratege', (), 'inconnue', 0, CAT)

    def test_memes_regles_dans_les_trois_categories(self):
        for categorie in ('globale', 'duel', 'individuelle'):
            catalogue = {i: dict(o, categorie=categorie) for i, o in CAT.items()}
            def confronter(a, b, comparaison):
                return commandement.confronter_donneurs(a, 'stratege', (), b, 'stratege', (),
                                                        categorie, comparaison, catalogue)
            with self.subTest(categorie=categorie):
                self.assertEqual(confronter([1, 2], [5], 1), ([1, 2], []))
                self.assertEqual(confronter([1, 2], [5], 0), ([], []))
                for comparaison in (-1, 0, 1):
                    self.assertEqual(confronter([1], [3], comparaison), ([1], [3]))
                    self.assertEqual(confronter([3], [], comparaison), ([3], []))
                    self.assertEqual(confronter([1, 3], [], comparaison), ([], []))

    def test_donneur_personnel_ne_cumule_pas_avec_qg(self):
        general, qg = dict(ordres=[1]), dict(ordres=[2])
        donneur = commandement.donneur_duel(general, qg, lambda g: g['ordres'])
        self.assertEqual(self.confrontation(donneur['ordres'], [], 1), ([1], []))
        general['ordres'] = []
        donneur = commandement.donneur_duel(general, qg, lambda g: g['ordres'])
        self.assertEqual(self.confrontation(donneur['ordres'], [], 1), ([2], []))

    def test_ordres_des_generaux_sans_qg_non_transmis(self):
        a = dict(nature='stratege', points_commandement=200, ordres=[5])
        b = dict(nature='stratege', points_commandement=1, ordres=[5])
        self.assertEqual(commandement.confronter_globaux(
            [a], None, a['ordres'], [b], b, b['ordres'], CAT), ([], [5]))

    def test_ordres_desactives_exclus_avant_comparaison(self):
        catalogue = dict(CAT, **{})
        catalogue[1] = dict(CAT[1], disponible=False)
        self.assertEqual(commandement.confronter_donneurs(
            [1], 'stratege', (), [3], 'stratege', (), 'duel', 1, catalogue), ([], [3]))


if __name__ == '__main__':
    unittest.main()
