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


    def test_confrontation_egalite_annule_deux_ordres_normaux(self):
        a = {"general": {"ordres": [{"identifiant": "1-2"}],
                         "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        b = {"general": {"ordres": [{"identifiant": "2-3"}],
                         "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        # Même catégorie nécessaire : deux ordres de catégories différentes
        # ne sont pas comparés entre eux.
        self.assertEqual(ordres_pipeline.confronter_intentions(
            a, b, "globale", 10, 10, self.cat)["camp_1"], [1002])
        duel_cat = {
            10: dict(jeton="2-1", categorie="duel", disponible=True, contre=False),
            11: dict(jeton="2-2", categorie="duel", disponible=True, contre=False),
        }
        a["general"]["ordres"] = [{"identifiant": "2-1"}]
        b["general"]["ordres"] = [{"identifiant": "2-2"}]
        self.assertEqual(ordres_pipeline.confronter_intentions(
            a, b, "duel", 10, 10, duel_cat),
            {"comparaison": 0, "camp_1": [], "camp_2": []})

    def test_contre_ordre_face_a_ordre_agissent_ensemble(self):
        cat = {
            10: dict(jeton="2-1", categorie="duel", disponible=True, contre=False),
            11: dict(jeton="2-2", categorie="duel", disponible=True, contre=True),
        }
        def donneur(jeton):
            return {"general": {
                "ordres": [{"identifiant": jeton}],
                "caracteristiques": {"nature": "instinctif", "evolutions_acquises": []}}}
        self.assertEqual(ordres_pipeline.confronter_intentions(
            donneur("2-1"), donneur("2-2"), "duel", 2, 12, cat),
            {"comparaison": -1, "camp_1": [10], "camp_2": [11]})

    def test_contre_ordre_sans_adversaire_et_rejet_entree_sans_fiche(self):
        cat = {11: dict(jeton="2-2", categorie="duel",
                        disponible=True, contre=True)}
        donneur = {"general": {
            "ordres": [{"identifiant": "2-2"}],
            "caracteristiques": {"nature": "stratege", "evolutions_acquises": []}}}
        self.assertEqual(ordres_pipeline.confronter_intentions(
            donneur, None, "duel", 9, 10, cat)["camp_1"], [11])
        with self.assertRaises(ValueError):
            ordres_pipeline.confronter_intentions(
                {"general": {"ordres": [{"identifiant": "2-2"}]}},
                None, "duel", 9, 10, cat)


if __name__ == "__main__":
    unittest.main()
