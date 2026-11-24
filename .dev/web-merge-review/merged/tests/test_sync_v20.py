"""Régressions ciblées de la synchronisation et parité sans adaptateur."""
import sys
import json
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from backend.runner import Runner
from backend.schema import LOCK
from tests.test_linux import ReferenceRunner
from tests.test_v20 import battle, profile


class GenerationReference(ReferenceRunner):
    def command(self, operation, engine_path):
        command = super().command(operation, engine_path)
        command[command.index('/reference.py') - 1] = str(
            Path(__file__).with_name('reference_generation.py'))
        return command


@unittest.skipUnless(sys.platform == 'linux', 'Bubblewrap réel requis')
class Synchronisation(unittest.TestCase):
    def test_local_preparation_requires_opt_in_and_exact_sources(self):
        from scripts.prepare_engine import prepare
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, destination = root / 'source', root / 'output'
            (source / 'python').mkdir(parents=True)
            for name, content in Runner().verify_engine().items():
                (source / 'python' / name).write_bytes(content)
            # Conserver la couverture du mode local avec un verrou local explicite.
            (root / 'backend').mkdir()
            local_lock = dict(LOCK, source_state='working-tree')
            (root / 'backend/engine.lock.json').write_text(json.dumps(local_lock), encoding='utf-8')
            with patch('scripts.prepare_engine.ROOT', root):
                with self.assertRaises(SystemExit):
                    prepare(source, destination)
                with patch('scripts.prepare_engine.subprocess.check_output', return_value='0' * 40):
                    with self.assertRaises(SystemExit):
                        prepare(source, destination, working_tree=True)
                with (source / 'python/combats.py').open('ab') as stream:
                    stream.write(b'\n# Unvalidated change\n')
                with patch('scripts.prepare_engine.subprocess.check_output', return_value=LOCK['commit']):
                    with self.assertRaises(SystemExit):
                        prepare(source, destination, working_tree=True)
                self.assertFalse(destination.exists())

    def test_published_preparation_uses_verified_git_blobs(self):
        from scripts.prepare_engine import prepare
        contents = Runner().verify_engine()
        self.assertEqual(LOCK['source_state'], 'git')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            destination = Path(directory) / 'output'
            # Une modification de la copie de travail ne doit pas être extraite.
            (source / 'python').mkdir(parents=True)
            (source / 'python/combats.py').write_bytes(b'uncommitted change')

            def git_blob(command):
                name = command[-1].removeprefix(LOCK['commit'] + ':python/')
                self.assertEqual(command, ['git', '-C', str(source), 'show',
                                           LOCK['commit'] + ':python/' + name])
                return contents[name]

            with patch('scripts.prepare_engine.subprocess.check_output', side_effect=git_blob):
                prepare(source, destination)
            self.assertEqual({p.name: p.read_bytes() for p in destination.iterdir()}, contents)
            with self.assertRaises(SystemExit):
                prepare(source, destination)  # Ne jamais remplacer une extraction existante.
            with self.assertRaises(SystemExit):
                prepare(source, Path(directory) / 'local', working_tree=True)
            invalid = Path(directory) / 'invalid'
            with patch('scripts.prepare_engine.subprocess.check_output', return_value=b'altered blob'):
                with self.assertRaises(SystemExit):
                    prepare(source, invalid)
            self.assertFalse(invalid.exists())

    def parity(self, data):
        actual = Runner().run(data)
        reference = ReferenceRunner().execute('simulate', data)
        self.assertEqual(actual['after'], reference['after'])
        self.assertEqual(actual['journal'], reference['journal'])
        self.assertEqual(actual['engine_revision'], LOCK['revision'])
        return actual

    def test_generation_official_profiles_many_known_labels_remain_playable(self):
        for seed in (1, 5, 21, 42):
            payload = {'level': 50, 'seed': seed}
            generated = Runner().generate(payload)
            reference = GenerationReference().execute('generate', payload)
            self.assertEqual(generated['profile'], reference['profile'])
            self.assertEqual(generated['unlocked_evolutions'], reference['unlocked_evolutions'])
            self.assertEqual(generated['engine_revision'], LOCK['revision'])
            data = battle()
            data['armies']['A']['generals'][0]['profile'] = generated['profile']
            self.parity(data)

    def test_roulette_labels_before_level_five_and_above_school_capacity(self):
        data = battle()
        data['armies']['A']['generals'][0]['profile'] = profile(
            nature='instinctif', level=1, pc=10,
            labels={'orc': 1, 'humain': 1, 'infanterie': 1}, active=['infanterie'])
        self.parity(data)

    def test_zombie_slot_cannot_activate_second_ordinary_label(self):
        from backend.schema import InvalidConfiguration
        data = battle()
        general = data['armies']['A']['generals'][0]
        general['profile'] = profile(nature='instinctif', zombie=True,
            labels={'orc': 1, 'infanterie': 1, 'mort_vivant': 1}, active=['orc', 'infanterie'])
        with self.assertRaises(InvalidConfiguration):
            Runner().run(data)
        general['profile']['active'] = ['orc', 'mort_vivant']
        general['blocks']['avant'].update(unit='zombie')
        self.parity(data)

    def null_battle(self, a=1, b=1):
        data = battle(a, b)
        for army in data['armies'].values():
            general = army['generals'][0]
            general['profile'].update(nature='stratege_hybride', pc=200,
                                      labels={'chaman': 1}, active=['chaman'])
            general['blocks']['avant'].update(unit='orc_archer', count=10)
            general['profile']['unlocked_evolutions'] = [108]
        return data

    def test_impasse_modes_keep_survivors_and_do_not_claim_retreat(self):
        for mode, defender, camps in (('OFF/OFF', None, ['j1', 'j2']),
                                      ('OFF/DEF', 'A', ['j2']), ('OFF/DEF', 'B', ['j1'])):
            data = self.null_battle()
            data.update(mode=mode, defender=defender)
            result = self.parity(data)
            self.assertEqual(result['outcome'], 'contested')
            self.assertEqual(result['losses'], {'A': 0, 'B': 0})
            self.assertEqual(result['engagements'], [])
            self.assertEqual(result['battle_resolution']['camps_retraite'], camps)
            self.assertFalse(result['conditions']['retreats'])
            self.assertNotIn('Limite de rounds', result['journal'])

    def test_null_pair_does_not_block_other_general_or_block(self):
        data = self.null_battle(2)
        result = self.parity(data)
        self.assertGreater(len(result['engagements']), 0)
        self.assertEqual(result['engagements'][0]['general_1'], 'general2')
        self.assertEqual(result['after']['B']['total'], 0)
        data = self.null_battle()
        data['armies']['A']['generals'][0]['blocks']['arriere'].update(unit='archer', count=1)
        result = self.parity(data)
        self.assertEqual(result['after']['B']['total'], 0)
        self.assertFalse(result['battle_resolution'].get('impasse', False))

    def test_personal_qg_chaman_not_amplified_by_messenger(self):
        data = battle(2)
        qg, ally = data['armies']['A']['generals']
        qg['qg'] = True
        qg['profile'].update(pc=100, labels={'chaman': 1}, active=['chaman'])
        ally['profile']['pc'] = 100
        ally['profile']['unlocked_evolutions'] = [110]
        ally['blocks']['avant'].update(count=10, messengers=1)
        enemy = data['armies']['B']['generals'][0]
        enemy['profile']['nature'] = 'instinctif'
        enemy['blocks']['avant']['unit'] = 'orc_assaillant'
        enemy['profile']['unlocked_evolutions'] = [107]
        result = self.parity(data)
        self.assertEqual(result['qg_initial'][0]['pc_global'], 110)
        self.assertEqual(result['calculations'][0][1]['malus_percent'], 50)
