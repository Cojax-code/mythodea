"""Vraies exécutions Linux. Aucun mock de permissions ou de fonction de combat."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import unittest

from backend.app import create_app
from backend.runner import ROOT, Runner, SimulationTimeout, SimulationUnavailable
from tests.scenarios import scenario


class ReferenceRunner(Runner):
    def command(self, operation, engine_path):
        command = super().command(operation, engine_path)
        separator = command.index("--remount-ro")
        command[separator:separator] = ["--ro-bind", str(ROOT / "tests/reference_worker.py"), "/reference.py"]
        command[-2:] = ["/reference.py"]
        return command


@unittest.skipUnless(sys.platform == "linux", "Exige un véritable noyau Linux")
class LinuxIntegration(unittest.TestCase):
    def setUp(self):
        self.runner = Runner()

    def test_real_api_duel_and_repeat(self):
        client = create_app().test_client()
        first = client.post("/api/simulator/run", json=scenario())
        self.assertEqual(first.status_code, 200, first.text)
        result = first.json
        self.assertEqual(result["outcome"], "A")
        self.assertEqual(result["losses"], {"A": 10, "B": 20})
        self.assertFalse(result["after"]["B"]["alive"])
        self.assertTrue(result["engagements"][0]["chocs"])
        second = client.post("/api/simulator/run", json=scenario())
        self.assertEqual(result, second.json)

    def test_matches_unmodified_engine_directly(self):
        scenarios = [scenario(), scenario({"avant": ("piquier", 20)}, {"avant": ("archer", 20)}),
                     scenario({"avant": ("archer", 7)}, {"avant": ("archer", 7)}),
                     scenario({"gauche": ("cavalier", 10), "arriere": ("archer", 10)},
                              {"droite": ("archer", 10), "arriere": ("piquier", 10)}),
                     scenario({"avant": ("piquier", 3), "droite": ("archer", 5), "gauche": ("cavalier", 7), "arriere": ("archer", 5)},
                              {"avant": ("cavalier", 6), "droite": ("piquier", 4), "gauche": ("archer", 5), "arriere": ("piquier", 5)})]
        for count, block in ((14, "avant"), (15, "avant"), (20, "avant"), (15, "gauche")):
            scenarios.append(scenario({block: ("cavalerie_lourde", count)}, {"avant": ("archer", 20)}))
        for index, data in enumerate(scenarios):
            with self.subTest(scenario=index):
                reference = ReferenceRunner().execute("simulate", data)
                actual = self.runner.run(data)
                self.assertEqual(reference["after"], actual["after"])
                self.assertEqual(reference["journal"], actual["journal"])

    def test_heavy_cavalry_threshold_and_explanations(self):
        for count, expected, base in ((14, 4, 5), (15, 10, 10), (20, 15, 10)):
            result = self.runner.run(scenario({"avant": ("cavalerie_lourde", count)}, {"avant": ("archer", 20)}))
            self.assertEqual(result["after"]["A"]["total"], expected)
            self.assertEqual(result["engagements"][0]["chocs"][0]["values"]["1"], {"base": base, "advantage": 2})

    def test_seed_changes_random_tie_order_and_can_be_replayed(self):
        data = scenario({"gauche": ("archer", 5)}, {"droite": ("cavalier", 5)})
        journals = set()
        for seed in range(4):
            data["seed"] = seed
            result = self.runner.run(data)
            self.assertEqual(result, self.runner.run(data))
            journals.add(result["journal"])
        self.assertGreater(len(journals), 1)

    def test_private_files_readonly_engine_network_and_limits(self):
        with tempfile.TemporaryDirectory(prefix="mythodea-host-sentinel-") as directory, socket.socket() as listener:
            sentinel = Path(directory) / "real-save-sentinel.txt"
            sentinel.write_text("Cette sentinelle représente une sauvegarde hôte intouchable.")
            original = sentinel.read_bytes()
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            result = self.runner.execute("probe", {"host_paths": [str(sentinel), str(ROOT), str(Path.home())],
                                                    "host_port": listener.getsockname()[1]})
            for key in ("private_write", "host_hidden", "host_write_blocked", "engine_readonly", "network_isolated", "memory_limited", "file_limited"):
                self.assertTrue(result[key], result)
            self.assertEqual(result["uid"], 0)
            self.assertLessEqual(result["scratch_bytes"], 16 * 1024 * 1024)
            self.assertEqual(sentinel.read_bytes(), original)

    def test_parallel_scenarios_do_not_share_game_state(self):
        a = scenario()
        b = scenario({"avant": ("archer", 2)}, {"avant": ("cavalier", 20)})
        expected = [self.runner.run(data) for data in (a, b)]
        with ThreadPoolExecutor(max_workers=2) as executor:
            actual = list(executor.map(lambda data: Runner().run(data), (a, b)))
        self.assertEqual(expected, actual)

    def test_timeout_destroys_worker_and_next_simulation_succeeds(self):
        with self.assertRaises(SimulationTimeout):
            Runner(timeout=0.5).execute("timeout-probe", {})
        self.assertEqual(self.runner.run(scenario())["outcome"], "A")

    def test_changed_engine_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = Path(directory) / "engine"
            shutil.copytree(self.runner.engine, engine)
            (engine / "combats.py").write_text("raise RuntimeError('modified')")
            with self.assertRaises(SimulationUnavailable):
                Runner(engine).run(scenario())

    def test_generated_seed_is_returned_and_reusable(self):
        data = scenario(seed=None)
        result = self.runner.run(data)
        data["seed"] = result["seed"]
        replay = self.runner.run(data)
        self.assertEqual(result["journal"], replay["journal"])
        self.assertEqual(result["after"], replay["after"])

    def test_adapter_refuses_direct_execution_outside_container(self):
        from backend.engine_adapter import simulate
        with self.assertRaisesRegex(RuntimeError, "conteneur jetable"):
            simulate(scenario())


if __name__ == "__main__":
    unittest.main()
