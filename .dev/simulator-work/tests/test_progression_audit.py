"""Parité de progression, déblocages et contrat des tirages isolés."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

from backend.app import create_app
from backend.runner import Runner
from backend.schema import InvalidConfiguration, LOCK
from tests.test_linux import ReferenceRunner
from tests.test_v20 import battle, profile


class ProgressionReference(ReferenceRunner):
    def command(self, operation, engine_path):
        command = super().command(operation, engine_path)
        command[command.index('/reference.py') - 1] = str(Path(__file__).with_name('reference_progression.py'))
        return command


class ProgressionContract(unittest.TestCase):
    def test_natural_and_reward_validate_before_execution(self):
        engine = Mock()
        client = create_app(engine).test_client()
        for endpoint, payload in (('natural', dict(level=-1, seed=None)),
                                  ('reward', dict(profile=profile(level=50), seed=None))):
            self.assertEqual(client.post('/api/simulator/' + endpoint, json=payload).status_code, 400)
            self.assertEqual(client.post('/api/simulator/' + endpoint, json=payload,
                headers={'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
        engine.natural.assert_not_called()
        engine.reward.assert_not_called()
        for value in (1, 'yes', []):
            data = battle()
            data['armies']['A']['generals'][0]['profile']['quest_heavy_cavalry'] = value
            self.assertEqual(client.post('/api/simulator/run', json=data).status_code, 400)


@unittest.skipUnless(sys.platform == 'linux', 'Bubblewrap réel requis')
class ProgressionEngine(unittest.TestCase):
    def test_supplementary_draw_is_one_official_roulette_on_selected_acquisitions(self):
        for nature, level in (('stratege', 14), ('instinctif', 14), ('hybride', 24)):
            for seed in (1, 7, 42):
                data = dict(profile=profile(nature=nature, level=level,
                    labels={'infanterie': 1}, unlocked_evolutions=[106]), seed=seed, slot='supplementaire')
                self.assertEqual(Runner().reward(data)['reward'],
                                 ProgressionReference().execute('generate', data))
        for changes in (dict(level=4), dict(level=24, zombie=True), dict(level=23)):
            with self.assertRaises(InvalidConfiguration):
                Runner().reward(dict(profile=profile(nature='hybride', **changes), seed=42, slot='supplementaire'))

    def test_natural_four_natures_levels_and_zombie_history(self):
        for nature in LOCK['catalog']['natures']:
            for level in (0, 1, 5, 10, 15):
                data = dict(nature=nature, level=level, seed=42)
                result = Runner().natural(data)
                self.assertEqual(result, Runner().natural(data))
                self.assertEqual(result['morale'], 0 if nature == 'stratege' else level // 2)
                self.assertTrue(2 * level <= result['pc'] <= 4 * level if nature != 'instinctif' else result['pc'] == 0)
                self.assertEqual(set(result), {'pc', 'morale', 'seed', 'engine_commit'})
                zombie = Runner().natural(dict(data, level=level + 3, zombie=True, zombie_levels=3))
                self.assertEqual((zombie['pc'], zombie['morale']), (result['pc'], result['morale']))

    def test_individual_reward_matches_official_engine(self):
        for nature in LOCK['catalog']['natures']:
            for level in (0, 4, 9, 14):
                for trait in ('leader', 'inventeur', 'charismatique'):
                    p = profile(nature=nature, level=level, trait=trait,
                                labels={'orc': 1}, unlocked_evolutions=[105])
                    data = dict(profile=p, seed=42)
                    before = copy.deepcopy(data)
                    result = Runner().reward(data)
                    expected = ProgressionReference().execute('generate', data)
                    self.assertEqual(result['reward'], expected)
                    self.assertEqual(data, before)
                    if level in (4, 9, 14):
                        self.assertIsNotNone(result['supplementary'])
        data = dict(profile=profile(zombie=True, zombie_levels=3), seed=42)
        self.assertEqual(Runner().reward(data)['reward'], ProgressionReference().execute('generate', data))

    def test_options_roulette_dominant_and_approved_weights(self):
        options = Runner().options()['natures']
        self.assertEqual(options['stratege']['reward_weights']['leader'],
                         dict(commandement=35, moral=10, unite=15, etiquette=40))
        for nature in options:
            self.assertIn('106', options[nature]['roulette_evolutions'])
            self.assertEqual('104' in options[nature]['roulette_evolutions'], nature in ('instinctif', 'hybride'))
            self.assertEqual('108' in options[nature]['roulette_evolutions'], nature in ('instinctif', 'hybride'))
        self.assertIn('108', options['hybride']['evolutions'])

    def test_chevalier_heavy_cavalry_and_messenger_need_acquisition(self):
        for unit, evolution, nature in (('chevalier_clinquant', 106, 'stratege'),
                                         ('cavalerie_lourde', 104, 'instinctif'),
                                         ('messager_du_QG', 110, 'stratege')):
            data = battle()
            g = data['armies']['A']['generals'][0]
            g['profile'].update(nature=nature, unlocked_evolutions=[])
            if unit == 'messager_du_QG':
                g['blocks']['avant'].update(count=15, messengers=1)
            else:
                g['blocks']['avant'].update(unit=unit, count=10)
            with self.assertRaises(InvalidConfiguration):
                Runner().run(data)
            g['profile']['unlocked_evolutions'] = [evolution]
            self.assertIn('after', Runner().run(data))
            if unit == 'messager_du_QG':
                g['blocks']['avant']['count'] = 16
                with self.assertRaises(InvalidConfiguration):
                    Runner().run(data)
        data = battle()
        g = data['armies']['A']['generals'][0]
        g['blocks']['avant'].update(unit='cavalerie_lourde', count=10)
        with self.assertRaises(InvalidConfiguration):
            Runner().run(data)
        g['profile']['quest_heavy_cavalry'] = True
        self.assertIn('after', Runner().run(data))

    def test_disabled_and_legacy_labels_keep_knowledge_and_rank(self):
        data = battle()
        p = data['armies']['A']['generals'][0]['profile']
        p.update(level=5, labels={'infanterie': 2}, permanent=['infanterie'], active=[])
        result = Runner().run(data)
        self.assertEqual(result['calculations'][0][0]['bonus_percent'], 0)
        self.assertEqual(result['configuration']['armies']['A']['generals'][0]['profile']['labels'], {'infanterie': 2})
        p['active'] = ['infanterie']
        self.assertEqual(Runner().run(data)['calculations'][0][0]['bonus_percent'], 20)
