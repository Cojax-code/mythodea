"""Gains isolés du simulateur et règles de la progression officielle."""
from copy import deepcopy
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'python'))
import catalogues
import progression
import commandement


class AuditProgression(unittest.TestCase):
    def test_gains_naturels_sans_acquisition_ni_mutation(self):
        for nature in progression.NATURES:
            for level in (0, 1, 5, 10, 15):
                fiche = progression.nouvelles_caracteristiques(random.Random(42))
                fiche.update(nature=nature, etiquettes={'orc': 1}, evolutions_acquises=[105])
                initial = deepcopy(fiche)
                for n in range(1, level + 1):
                    fiche['niveau'] = n
                    before = deepcopy(fiche)
                    fiche = progression.appliquer_gains_naturels(fiche, Mock(randint=lambda a, b: 3))
                    self.assertEqual(before['etiquettes'], fiche['etiquettes'])
                self.assertEqual(fiche['points_commandement'], 0 if nature == 'instinctif' else 3 * level)
                self.assertEqual(fiche['moral'], 0 if nature == 'stratege' else level // 2)
                self.assertEqual(fiche['etiquettes'], initial['etiquettes'])
                self.assertEqual(fiche['evolutions_acquises'], [105])
                fiche['etat_zombie'] = True
                self.assertEqual(progression.appliquer_gains_naturels(fiche, random.Random(0)), fiche)

    def test_moral_stratege_roulette_dix_pour_cent(self):
        for trait, pc_weight in (('charismatique', 40), ('leader', 35), ('inventeur', 15)):
            for ticket in range(pc_weight + 1, pc_weight + 11):
                fiche = progression.nouvelles_caracteristiques(random.Random(0))
                fiche.update(nature='stratege', trait_inne=trait)
                rng = Mock(randint=Mock(side_effect=[3, ticket, 4]))
                result, reward = progression.monter_niveau(fiche, rng)
                self.assertEqual(reward, ('force_caractere', 4))
                self.assertEqual((result['points_commandement'], result['moral']), (3, 4))
                self.assertEqual((fiche['points_commandement'], fiche['moral']), (0, 0))

    def test_chevalier_et_cavalerie_ids_officiels(self):
        for nature in progression.NATURES:
            fiche = dict(nature=nature, moral=0, evolutions_acquises=[])
            roulette = progression.evolutions_eligibles(fiche, apprentissage=False)
            self.assertIn(106, roulette)
            self.assertEqual(104 in roulette, nature in ('instinctif', 'hybride'))
        self.assertEqual(catalogues.UNITES[10]['places'], 5)

    def test_instantane_qg_refuse_nature_interdite(self):
        from unittest.mock import patch
        qg = dict(joueur='j1', nom='general1', camp='allies')
        for nature, zombie in (('instinctif', False), ('hybride', True), ('stratege', True)):
            with patch.object(progression, 'caracteristiques_general',
                              return_value=dict(nature=nature, etat_zombie=zombie)):
                with self.assertRaises(ValueError):
                    commandement.instantane_qg_territorial(qg, [qg])
