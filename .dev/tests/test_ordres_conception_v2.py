"""Vérifie la frontière entre conception des ordres et moteur actif."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))

import catalogues
import ordres_conception


class OrdresConceptionTest(unittest.TestCase):
    def test_vingt_et_un_ordres_non_executables(self):
        fiches = ordres_conception.ORDRES_EN_CONCEPTION
        self.assertEqual(len(fiches), 21)
        self.assertTrue(all(f["disponible"] is False for f in fiches.values()))

    def test_categories_et_contre_ordres_confirmes(self):
        fiches = ordres_conception.ORDRES_EN_CONCEPTION
        self.assertEqual({nom for nom, f in fiches.items() if f["contre"]},
                         {"retrait_tactique", "confinement", "chat_man", "derniere_charge"})
        self.assertEqual(fiches["derniere_charge"]["categorie"], "duel")
        self.assertEqual(fiches["muraille_humaine"]["categorie"], "globale")
        self.assertEqual(fiches["reserve_strategique"]["categorie"], "globale")

    def test_pas_d_activation_indirecte(self):
        noms_actifs = {fiche["nom"] for fiche in catalogues.ORDRES.values()
                      if fiche["disponible"]}
        self.assertFalse(noms_actifs.intersection(ordres_conception.ORDRES_EN_CONCEPTION))
        self.assertEqual({ordre["jeton"] for ordre in catalogues.ORDRES.values()
                          if ordre["disponible"]}, {"1-2"})

    def test_registre_immuable(self):
        with self.assertRaises(TypeError):
            ordres_conception.ORDRES_EN_CONCEPTION["nouveau"] = {}
        with self.assertRaises(TypeError):
            ordres_conception.ORDRES_EN_CONCEPTION["derniere_charge"]["disponible"] = True


if __name__ == "__main__":
    unittest.main()
