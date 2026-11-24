"""Contrat de configuration progressive, avec le vrai moteur isolé."""
import sys
import unittest
from unittest.mock import Mock

from backend.app import create_app
from backend.runner import Runner
from backend.schema import InvalidConfiguration, validate, CATALOG
from tests.test_v20 import battle


class ConfigurationContract(unittest.TestCase):
    def test_options_reject_payload_and_cross_site(self):
        engine = Mock()
        client = create_app(engine).test_client()
        self.assertEqual(client.post('/api/simulator/options', json={'path': '/game'}).status_code, 400)
        self.assertEqual(client.post('/api/simulator/options', json={},
                                    headers={'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
        engine.options.assert_not_called()

    def test_unlocks_are_typed_and_unique(self):
        client = create_app(Mock()).test_client()
        for unlocks in ([True], [108, 108], [999], '108'):
            data = battle()
            data['armies']['A']['generals'][0]['profile']['unlocked_evolutions'] = unlocks
            with self.subTest(unlocks=unlocks):
                self.assertEqual(client.post('/api/simulator/run', json=data).status_code, 400)

    def test_label_slots_rank_and_reserved_zombie_slot(self):
        for nature in ('stratege', 'instinctif', 'hybride'):
            for level in (0, 4, 5, 9, 10):
                maximum = CATALOG['specific_states'][nature][level][0][0]
                data = battle()
                p = data['armies']['A']['generals'][0]['profile']
                names = ['orc', 'humain', 'infanterie', 'distance']
                p.update(level=level, nature=nature, labels=dict.fromkeys(names, 1), active=names[:maximum])
                validate(data)
                p['active'] = names[:maximum + 1]
                with self.assertRaises(InvalidConfiguration):
                    validate(data)
                p.update(zombie=True, active=names[:maximum] + ['mort_vivant'])
                p['labels']['mort_vivant'] = 1 + level // 5
                validate(data)
                p['labels']['mort_vivant'] += 1
                with self.assertRaises(InvalidConfiguration):
                    validate(data)

    def test_pc_not_capped_and_qg_block_checked(self):
        data = battle()
        g = data['armies']['A']['generals'][0]
        g['profile']['pc'] = 1500
        g.update(qg=True, qg_block='gauche')
        validate(data)
        g['qg_block'] = 'inconnu'
        with self.assertRaises(InvalidConfiguration):
            validate(data)


@unittest.skipUnless(sys.platform == 'linux', 'Véritable Bubblewrap requis')
class ConfigurationEngine(unittest.TestCase):
    def test_options_four_natures_and_capacities(self):
        options = Runner().options()
        self.assertEqual(set(options['natures']), {'stratege', 'instinctif', 'hybride'})
        self.assertEqual(options['zombie_capacities'][3], 26)
        self.assertEqual(options['normal_capacity'], 20)
        self.assertNotIn('108', options['natures']['stratege']['evolutions'])
        self.assertIn('108', options['natures']['instinctif']['evolutions'])
        for nature in ('hybride',):
            self.assertIn('108', options['natures'][nature]['evolutions'])
            self.assertIn('110', options['natures'][nature]['evolutions'])

    def test_special_units_require_nature_and_unlocks(self):
        for nature in ('stratege', 'instinctif', 'hybride'):
            data = battle()
            g = data['armies']['A']['generals'][0]
            g['profile'].update(level=0, nature=nature, unlocked_evolutions=[], corpse_available=False)
            g['blocks']['avant'].update(unit='orc_archer', count=10)
            with self.assertRaises(InvalidConfiguration):
                Runner().run(data)
            g['profile']['unlocked_evolutions'] = [108]
            if nature == 'stratege':
                with self.assertRaises(InvalidConfiguration):
                    Runner().run(data)
            else:
                self.assertEqual(Runner().run(data)['before']['A']['total'], 10)

    def test_generation_preserves_selected_type_and_level(self):
        for nature in ('stratege', 'instinctif', 'hybride'):
            for level in (0, 5, 10):
                payload = dict(level=level, seed=42, nature=nature, zombie=False, zombie_levels=0)
                result = Runner().generate(payload)
                self.assertEqual(result, Runner().generate(payload))
                self.assertEqual(result['profile']['nature'], nature)
                self.assertEqual(result['profile']['level'], level)
                if level == 0:
                    self.assertEqual(result['profile']['morale'], 0)
                    pc = result['profile']['pc']
                    self.assertEqual(pc, 0)
                    self.assertEqual(result['profile']['labels'], {})
                    self.assertEqual(result['unlocked_evolutions'], [])
        before = Runner().generate(dict(level=5, seed=42, nature='instinctif'))['profile']
        zombie = Runner().generate(dict(level=8, seed=42, nature='instinctif', zombie=True, zombie_levels=3))['profile']
        self.assertEqual((zombie['level'], zombie['zombie_levels'], zombie['zombie']), (8, 3, True))
        self.assertEqual((zombie['pc'], zombie['morale']), (before['pc'], before['morale']))

    def test_qg_block_is_placement_only(self):
        data = battle(2)
        qg = data['armies']['A']['generals'][0]
        qg.update(qg=True, qg_block='avant')
        qg['profile'].update(labels={'infanterie': 2}, active=['infanterie'])
        first = Runner().run(data)
        qg['qg_block'] = 'arriere'
        second = Runner().run(data)
        self.assertEqual(first['qg_initial'], second['qg_initial'])
        self.assertEqual(first['after'], second['after'])
        self.assertEqual(second['configuration']['armies']['A']['generals'][0]['qg_block'], 'arriere')

    def test_zombie_old_morale_has_no_effect(self):
        data = battle()
        g = data['armies']['A']['generals'][0]
        g['profile'].update(zombie=True, nature='instinctif', morale=100)
        g['blocks']['avant'].update(unit='zombie', count=20)
        with_morale = Runner().run(data)
        g['profile']['morale'] = 0
        without_morale = Runner().run(data)
        self.assertEqual(with_morale['after'], without_morale['after'])
        self.assertEqual(with_morale['health'], without_morale['health'])
        self.assertTrue(all(o['morale'] == 0 for o in with_morale['morale_observations'] if o['owner'] == 'j1'))

    def test_zombie_restrictions_and_shield(self):
        data = battle()
        g = data['armies']['A']['generals'][0]
        g['profile'].update(zombie=True, unlocked_evolutions=[], corpse_available=False)
        with self.assertRaises(InvalidConfiguration):
            Runner().run(data)  # Archers interdits au général zombie.
        g['blocks']['avant'].update(unit='zombie', count=10, shield=True)
        with self.assertRaises(InvalidConfiguration):
            Runner().run(data)  # Cadavre non déclaré.
        g['profile']['corpse_available'] = True
        result = Runner().run(data)
        self.assertEqual(result['before']['A']['generals'][0]['blocks']['avant']['Trop_gros_zombie'], 1)
        g['blocks']['droite']['shield'] = True
        with self.assertRaises(InvalidConfiguration):
            Runner().run(data)
        g['blocks']['droite']['shield'] = False
        g['blocks']['avant']['count'] = 0
        with self.assertRaises(InvalidConfiguration):
            Runner().run(data)
