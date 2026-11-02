"""Les ordres retirés ne doivent plus intervenir dans la refonte V2.

Les scénarios de l'ancien contrat sont conservés dans .dev/historique/.
"""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import catalogues
import commandement


class OrdresRetires(unittest.TestCase):
    def test_ids_historiques_non_recycles(self):
        self.assertTrue(set(range(1001, 1006)).isdisjoint(catalogues.EVOLUTIONS))
        self.assertTrue(set(range(1001, 1006)).isdisjoint(catalogues.ETIQUETTES_ECOLE))

    def test_catalogue_et_confrontations_supprimes(self):
        self.assertFalse(hasattr(catalogues, 'ORDRES'))
        for nom in ('confronter_donneurs', 'confronter_globaux', 'ordres_applicables', 'donneur_duel'):
            self.assertFalse(hasattr(commandement, nom))
