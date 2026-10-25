"""Contrats du raccordement non destructif des ordres V2."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))
import ordres_pipeline


class PipelineOrdresTest(unittest.TestCase):
    def setUp(self):
        self.cat = {
            1002: dict(jeton="1-2", disponible=True, categorie="globale", contre=False),
            1003: dict(jeton="2-1", disponible=False, categorie="duel", contre=False),
            1006: dict(jeton="2-3", disponible=True, categorie="duel", contre=False),
        }

    @staticmethod
    def general(jeton, specification=None):
        return {"total_unites": 2, "ordres": [
            {"identifiant": jeton, "specification": specification}]}

    def test_pas_de_fusion_entre_generaux(self):
        forces = {"camp1": {"1": self.general("1-2"), "2": self.general("2-3")},
                  "camp2": {"1": self.general("2-1"), "2": None}}
        groupes = ordres_pipeline.ordres_par_donneur(forces, catalogue=self.cat)
        self.assertEqual([(g["camp"], g["position"], g["identifiants"]) for g in groupes],
                         [("camp1", "1", [1002]), ("camp1", "2", [1006])])

    def test_ordres_inactifs_et_specifications_non_validees_ignores(self):
        self.assertEqual(ordres_pipeline.ordres_du_general(
            self.general("2-1"), catalogue=self.cat), [])
        self.assertEqual(ordres_pipeline.ordres_du_general(
            self.general("2-3", 4), catalogue=self.cat), [])
        self.assertEqual(ordres_pipeline.ordres_du_general(
            self.general("1-2"), categorie="duel", catalogue=self.cat), [])

    def test_identifiants_dedoublonnes_et_ordre_conserve(self):
        general = {"ordres": [
            {"identifiant": "2-3", "specification": None},
            {"identifiant": "1-2", "specification": None},
            {"identifiant": "2-3", "specification": None}]}
        self.assertEqual(ordres_pipeline.ordres_du_general(general, catalogue=self.cat),
                         [1006, 1002])

    def test_jetons_ambigus_refuses(self):
        cat = dict(self.cat)
        cat[2000] = dict(cat[1002])
        with self.assertRaises(ValueError):
            ordres_pipeline.index_jetons(cat)


if __name__ == "__main__":
    unittest.main()
