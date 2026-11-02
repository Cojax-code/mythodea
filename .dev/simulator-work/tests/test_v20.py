"""Profils V2, capacités, sécurité et parité avec un montage indépendant du moteur."""
import copy
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock

from backend.app import create_app
from backend.runner import Runner, SimulationUnavailable
from tests.scenarios import multi
from tests.test_linux import ReferenceRunner


def profile(**changes):
    result = dict(level=10, nature='stratege', trait='leader', pc=20, morale=0,
                  labels={}, permanent=[], active=[], zombie=False, zombie_levels=0)
    result.update(changes)
    return result


def battle(a=1, b=1):
    data = multi(a, b, seed=71)
    for army in data['armies'].values():
        for general in army['generals']:
            general['profile'] = profile()
            general['qg'] = False
    return data


class ContractV20(unittest.TestCase):
    def test_profile_shape_and_untrusted_fields(self):
        engine = Mock()
        client = create_app(engine).test_client()
        changes = [dict(pc=True), dict(pc=-1), dict(pc=1001), dict(level=51), dict(level=2.5),
                   dict(morale=101), dict(nature='../../game'), dict(trait=[]), dict(zombie=1),
                   dict(labels={'<script>': 1}), dict(labels={'infanterie': 4}),
                   dict(labels={'infanterie': True}), dict(active=['unknown']),
                   dict(labels={'infanterie': 1}, active=['infanterie', 'infanterie']),
                   dict(permanent=['unknown']), dict(path='/game'), dict(command='id')]
        for change in changes:
            data = battle()
            data['armies']['A']['generals'][0]['profile'].update(change)
            with self.subTest(change=change):
                self.assertEqual(client.post('/api/simulator/run', json=data).status_code, 400)
        engine.run.assert_not_called()

    def test_duplicate_qg_and_retired_order_rejected(self):
        client = create_app(Mock()).test_client()
        data = battle(2)
        for g in data['armies']['A']['generals']:
            g['qg'] = True
        self.assertEqual(client.post('/api/simulator/run', json=data).status_code, 400)
        data = battle()
        data['armies']['A']['generals'][0]['order'] = '1-2'
        self.assertEqual(client.post('/api/simulator/run', json=data).status_code, 400)

    def test_generation_contract_and_cross_site(self):
        engine = Mock()
        engine.generate.return_value = {'profile': {}}
        client = create_app(engine).test_client()
        for data in ({'level': -1, 'seed': 0}, {'level': True, 'seed': 0}, {'level': 10, 'seed': -1},
                     {'level': 10, 'seed': 0, 'path': '/game'}):
            self.assertEqual(client.post('/api/simulator/generate', json=data).status_code, 400)
        self.assertEqual(client.post('/api/simulator/generate', json={'level': 10, 'seed': 0},
                                    headers={'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
        engine.generate.assert_not_called()
        self.assertEqual(client.post('/api/simulator/generate', json={'level': 10, 'seed': 0}).status_code, 200)


@unittest.skipUnless(sys.platform == 'linux', 'Véritable Bubblewrap requis')
class EngineV20(unittest.TestCase):
    def parity(self, data):
        actual = Runner().run(data)
        reference = ReferenceRunner().execute('simulate', data)
        self.assertEqual(actual['after'], reference['after'])
        self.assertEqual(actual['journal'], reference['journal'])
        self.assertEqual(actual, Runner().run(copy.deepcopy(data)))
        return actual

    def test_official_generation_levels_and_replay(self):
        for level in (0, 5, 10, 20, 50):
            data = {'level': level, 'seed': 21}
            generated = Runner().generate(data)
            self.assertEqual(generated, Runner().generate(data))
            self.assertEqual(generated['profile']['level'], level)
            scenario = battle()
            scenario['armies']['A']['generals'][0]['profile'] = generated['profile']
            self.parity(scenario)
        self.assertNotEqual(Runner().generate({'level': 10, 'seed': 21}), Runner().generate({'level': 10, 'seed': 22}))

    def test_pc_rank_active_labels_and_level_not_multiplier(self):
        data = battle()
        g = data['armies']['A']['generals'][0]
        g['profile'].update(labels={'infanterie': 2}, active=['infanterie'])
        result = self.parity(data)
        self.assertEqual(result['calculations'][0][0]['bonus_percent'], 20)
        g['profile']['level'] = 15
        self.assertEqual(self.parity(data)['after'], result['after'])
        g['profile']['active'] = []
        self.assertEqual(self.parity(data)['calculations'][0][0]['bonus_percent'], 0)
        g['profile'].update(pc=0, active=['infanterie'])
        self.assertEqual(self.parity(data)['calculations'][0][0]['bonus_percent'], 0)

    def test_qg_messenger_no_stacking_and_personal_bonus(self):
        data = battle(2)
        qg, ally = data['armies']['A']['generals']
        qg['qg'] = True
        qg['profile'].update(labels={'infanterie': 2}, active=['infanterie'])
        ally['profile']['pc'] = 59
        ally['blocks']['avant'].update(count=10, messengers=1)
        result = self.parity(data)
        self.assertEqual(result['qg_initial'][0]['pc_global'], 25)
        self.assertEqual(result['qg_initial'][0]['bonus_messager'], 5)
        self.assertEqual(result['calculations'][0][0]['bonus_percent'], 20)
        ally['blocks']['avant']['messengers'] = 2
        self.assertEqual(self.parity(data)['qg_initial'], result['qg_initial'])

    def test_qg_destroyed_no_successor_personal_labels_remain(self):
        data = battle(2)
        qg, ally = data['armies']['A']['generals']
        qg['qg'] = True
        qg['blocks']['avant']['count'] = 1
        qg['profile'].update(labels={'infanterie': 2}, active=['infanterie'])
        ally['profile'].update(pc=30, labels={'infanterie': 2}, active=['infanterie'])
        data['armies']['B']['generals'][0]['blocks']['avant']['unit'] = 'cavalier'
        result = self.parity(data)
        self.assertFalse(result['after']['A']['generals'][0]['alive'])
        self.assertEqual(result['calculations'][1][0]['bonus_percent'], 30)

    def test_chaman_extreme_malus_stays_on_official_one_percent_floor(self):
        data = battle()
        a, b = (data['armies'][c]['generals'][0] for c in ('A', 'B'))
        a['profile'].update(pc=100, labels={'chaman': 3}, active=['chaman'])
        b['profile']['nature'] = 'instinctif'
        b['blocks']['avant']['unit'] = 'orc_assaillant'
        result = self.parity(data)
        self.assertEqual(result['calculations'][0][1]['malus_percent'], 150)
        self.assertEqual(result['conditions']['value_floor_percent'], 1)

    def test_cruelle_uses_effective_morale_and_preserves_engine_rounding(self):
        data = battle()
        a, b = (data['armies'][c]['generals'][0] for c in ('A', 'B'))
        b['profile'].update(nature='instinctif', morale=75)
        a['profile'].update(pc=101, labels={'cruelle': 1}, active=['cruelle'])
        result = self.parity(data)
        observations = [o for o in result['morale_observations'] if o['owner'] == 'j2']
        self.assertEqual(observations[0]['morale'], 37.125)
        a['profile']['pc'] = 200
        result = self.parity(data)
        self.assertEqual(next(o['morale'] for o in result['morale_observations'] if o['owner'] == 'j2'), 0)

    def test_all_official_units_and_wounds(self):
        from backend.schema import CATALOG
        for unit in CATALOG['units']:
            data = battle()
            g = data['armies']['A']['generals'][0]
            g['profile'].update(nature='stratege_hybride', morale=75)
            g['blocks']['avant'].update(unit=unit, count=1 if unit in ('messager_du_QG', 'Trop_gros_zombie') else 10)
            if unit == 'Trop_gros_zombie':
                g['blocks']['arriere'].update(unit='zombie', count=10)
            with self.subTest(unit=unit):
                self.parity(data)
        data = battle()
        g = data['armies']['A']['generals'][0]
        g['profile'].update(nature='instinctif', morale=100)
        result = self.parity(data)
        self.assertGreater(sum(b['wounds'] for b in result['health']['A'][0]['blocks'].values()), 0)

    def test_four_generals_with_profiles_qg_and_multiple_blocks(self):
        data = battle(4, 4)
        for camp in data['armies'].values():
            for i, g in enumerate(camp['generals']):
                g['profile'].update(pc=20+i*7, nature='stratege_hybride', morale=20,
                                    labels={'infanterie': 2}, active=['infanterie'])
                g['qg'] = i == 3
                for block, unit in zip(g['blocks'], ('archer', 'piquier', 'orc_chaman', 'chevalier_clinquant')):
                    g['blocks'][block].update(unit=unit, count=4)
        self.parity(data)

    def test_engine_rejects_invalid_learning_capacity_and_units(self):
        client = create_app().test_client()
        cases = [profile(nature='instinctif', level=0, labels={'orc': 1}, active=['orc']),
                 profile(labels={'orc': 2}, permanent=['orc']),
                 profile(nature='instinctif', labels={'orc': 1, 'humain': 1}),
                 profile(zombie=False, zombie_levels=2), profile(zombie=True, zombie_levels=11)]
        for p in cases:
            data = battle()
            data['armies']['A']['generals'][0]['profile'] = p
            with self.subTest(profile=p):
                self.assertEqual(client.post('/api/simulator/run', json=data).status_code, 400)
        for block in ({'unit': 'orc_archer', 'count': 20}, {'unit': 'archer', 'count': 20, 'messengers': 1},
                      {'unit': 'archer', 'count': 10, 'shield': True}):
            data = battle()
            data['armies']['A']['generals'][0]['blocks']['avant'] = block
            self.assertEqual(client.post('/api/simulator/run', json=data).status_code, 400)

    def test_zombie_capacity_and_special_label_current_rules(self):
        data = battle()
        g = data['armies']['A']['generals'][0]
        g['profile'].update(nature='instinctif', zombie=True, zombie_levels=2,
                            labels={'infanterie': 1, 'mort_vivant': 1}, active=['infanterie', 'mort_vivant'])
        g['blocks']['avant'].update(unit='zombie', count=24)
        self.parity(data)
        g['profile']['labels'] = {'mort_vivant': 1, 'infanterie': 1}
        self.parity(data)
        g['profile']['labels']['mort_vivant'] = 2
        self.parity(data)

    def test_engine_symlink_hardlink_fifo_and_extra_files_refused(self):
        for attack in ('symlink', 'hardlink', 'fifo', 'extra'):
            with tempfile.TemporaryDirectory() as directory:
                source = Runner().engine
                engine = Path(directory) / 'engine'
                shutil.copytree(source, engine)
                target = engine / 'combats.py'
                if attack == 'extra':
                    (engine / 'sitecustomize.py').write_text('raise RuntimeError()')
                else:
                    original = Path(directory) / 'original.py'
                    target.rename(original)
                    if attack == 'symlink': target.symlink_to(original)
                    elif attack == 'hardlink': os.link(original, target)
                    else: os.mkfifo(target)
                with self.subTest(attack=attack), self.assertRaises(SimulationUnavailable):
                    Runner(engine).run(battle())
