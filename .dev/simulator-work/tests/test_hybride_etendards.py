"""Contrats des capacités et parité des étendards avec le moteur non instrumenté."""
from collections import Counter
import sys
import unittest

from backend.runner import Runner
from backend.schema import CATALOG, InvalidConfiguration, validate_profile
from tests.test_linux import ReferenceRunner
from tests.test_v20 import battle, profile


class Capabilities(unittest.TestCase):
    def test_catalog_and_reachable_states(self):
        self.assertEqual(CATALOG['natures'], ['stratege', 'instinctif', 'hybride'])
        self.assertEqual(CATALOG['banners'], {
            '1': {'probability': 30, 'charges': 1},
            '2': {'probability': 50, 'charges': 2}})
        for nature in CATALOG['natures']:
            for level, states in enumerate(CATALOG['specific_states'][nature]):
                for slots in (1, 2, 3):
                    for banner in (0, 1, 2):
                        p = profile(nature=nature, level=level, active_slots=slots, banner_level=banner)
                        if [slots, banner] in states:
                            validate_profile(p)
                        else:
                            with self.assertRaises(InvalidConfiguration):
                                validate_profile(p)


@unittest.skipUnless(sys.platform == 'linux', 'Bubblewrap réel requis')
class Banners(unittest.TestCase):
    def test_normal_royal_hybrid_qg_and_both_modes_match_engine(self):
        for level, slots, banner in ((5, 1, 1), (10, 1, 2), (20, 3, 2)):
            for mode in ('OFF/OFF', 'OFF/DEF'):
                data = battle()
                data.update(seed=71, mode=mode, defender='B' if mode == 'OFF/DEF' else None)
                g = data['armies']['A']['generals'][0]
                g.update(qg=True, banner_block='avant')
                g['profile'] = profile(nature='hybride', level=level, pc=0,
                                       active_slots=slots, banner_level=banner)
                result = Runner().run(data)
                expected = ReferenceRunner().execute('simulate', data)
                self.assertEqual(result['after'], expected['after'])
                self.assertEqual(result['journal'], expected['journal'])
                self.assertIn('Étendard', result['journal'])
                saves = [s for s in result['saves'] if s['kind'] == 'banner']
                self.assertTrue(saves)
                self.assertTrue(all(n <= banner for n in Counter(s['soldier'] for s in saves).values()))
                self.assertTrue(all(0 <= s['remaining'] < banner for s in saves))
                self.assertEqual(result, Runner().run(data))

    def test_unavailable_banner_rejected(self):
        for p in (profile(level=0), profile(level=10),
                  profile(nature='hybride', level=20, zombie=True, active_slots=3, banner_level=2)):
            data = battle()
            data['armies']['A']['generals'][0].update(profile=p, banner_block='avant')
            with self.assertRaises(InvalidConfiguration):
                Runner().run(data)
