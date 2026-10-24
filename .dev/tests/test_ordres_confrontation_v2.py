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


if __name__ == '__main__':
    unittest.main()
