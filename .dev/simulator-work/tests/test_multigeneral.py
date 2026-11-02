"""Placement, enchaînement et observations vérifiés contre le vrai moteur Linux."""
import copy
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

from backend.app import create_app
from backend.runner import Runner
from tests.scenarios import multi, scenario
from tests.test_linux import ReferenceRunner


class MultiValidation(unittest.TestCase):
    def test_strict_positions_orders_and_armies(self):
        runner = Mock()
        client = create_app(runner).test_client()
        mutations = [lambda a: a.update(generals=[]), lambda a: a.update(generals=a["generals"] * 3),
                     lambda a: a.update(generals={}), lambda a: a.update(blocks={}),
                     lambda a: a["generals"][0].update(position=True),
                     lambda a: a["generals"][0].update(position=0),
                     lambda a: a["generals"][0].update(position=5),
                     lambda a: a["generals"][0].update(position="1"),
                     lambda a: a["generals"][0].update(position=2),
                     lambda a: a["generals"][0].update(order="1-1"),
                     lambda a: a["generals"][0].update(order=["1-2"]),
                     lambda a: a["generals"][0].update(path="/game"),
                     lambda a: a["generals"][0]["blocks"]["avant"].update(count=0),
                     lambda a: a["generals"][0]["blocks"]["avant"].update(count=21)]
        for mutation in mutations:
            data = multi()
            mutation(data["armies"]["A"])
            with self.subTest(data=data):
                self.assertEqual(client.post("/api/simulator/run", json=data).status_code, 400)
        runner.run.assert_not_called()
        self.assertEqual(client.get("/api/simulator/catalog").json["max_generals_per_camp"], 4)


@unittest.skipUnless(sys.platform == "linux", "Exige un véritable noyau Linux")
class MultiLinux(unittest.TestCase):
    def assert_reference(self, data):
        actual = Runner().run(data)
        reference = ReferenceRunner().execute("simulate", data)
        self.assertEqual(actual["after"], reference["after"])
        self.assertEqual(actual["journal"], reference["journal"])
        self.assertEqual(actual["outcome"], {"j1": "A", "j2": "B", "neutre": "mutual_destruction", "conteste": "contested"}[reference["control"]])
        for camp in ("A", "B"):
            self.assertEqual(actual["losses"][camp], actual["before"][camp]["total"] - actual["after"][camp]["total"])
        return actual

    def test_requested_sizes_front_and_range_match_direct_engine(self):
        for a, b in ((1, 2), (2, 2), (3, 4), (4, 4)):
            for frontal in (False,):
                with self.subTest(a=a, b=b, frontal=frontal):
                    result = self.assert_reference(multi(a, b, frontal=frontal))
                    self.assertTrue(result["engagements"])
                    self.assertGreater(result["after"]["B"]["destroyed_generals"], 0)

    def test_positions_have_gaps_and_identity_is_not_placement(self):
        data = multi(2, 2)
        data["armies"]["A"]["generals"][0]["position"] = 4
        data["armies"]["B"]["generals"][0]["position"] = 3
        result = self.assert_reference(data)
        first = result["engagements"][0]["participants"]
        self.assertEqual([(p["name"], p["position"]) for p in first], [("general2", 2), ("general2", 2)])
        data["armies"]["A"]["generals"][0]["order"] = "1-2"
        response = create_app().test_client().post("/api/simulator/run", json=data)
        self.assertEqual(response.status_code, 400)

    def test_survivor_continues_and_unengaged_general_is_explained(self):
        data = multi(1, 2)
        for general in data["armies"]["B"]["generals"]:
            general["blocks"]["avant"]["count"] = 5
        result = self.assert_reference(data)
        self.assertEqual([e["general_1"] for e in result["engagements"]], ["general1", "general1"])
        self.assertEqual(result["engagements"][0]["final_1"], result["engagements"][1]["initial_1"])
        data = multi(4, 1)
        result = self.assert_reference(data)
        absent = [e for e in result["explanations"] if e["kind"] == "absence"]
        self.assertEqual([e["general"] for e in absent], ["general2", "general3", "general4"])

    def test_explanations_follow_real_actions_and_target_changes(self):
        data = multi(2, 2)
        # L'avant élimine l'arrière. Le flanc adverse détruit ensuite notre flanc,
        # puis devient la cible de l'avant au tour suivant.
        a = scenario({"avant": ("archer", 15), "gauche": ("cavalier", 5)},
                     {"droite": ("archer", 11), "arriere": ("piquier", 1)})
        for camp in ("A", "B"):
            data["armies"][camp]["generals"][0]["blocks"] = a["armies"][camp]["blocks"]
        result = self.assert_reference(data)
        decisions = [e for e in result["explanations"] if e["kind"] == "target"]
        actions = [(e, action) for e in result["engagements"] for action in e["manoeuvres"]]
        self.assertEqual(len(decisions), len(actions))
        self.assertTrue(any(e["previous_target"] and e["previous_target"] != e["target"] for e in decisions))
        self.assertTrue(any(all(c["advantage"] != 2 for c in e["candidates"]) for e in decisions))
        lines = result["journal"].splitlines(keepends=True)
        for decision, (engagement, action) in zip(decisions, actions):
            self.assertEqual(decision["target"], action["bloc_defenseur"])
            self.assertEqual(decision["block"], action["bloc_attaquant"])
            self.assertEqual(decision["attacker"], action["joueur_attaquant"])
            candidates = decision["candidates"]
            advantaged = [c for c in candidates if c["advantage"] == 2]
            expected = advantaged[0] if advantaged else min(candidates, key=lambda c: c["count"])
            self.assertEqual(decision["target"], expected["block"])
            following = "".join(lines[decision["line"]:decision["line"] + 8])
            self.assertIn(f"{decision['attacker']} {decision['general']} {decision['block']} attaque", following)
        offsets = [e["line"] for e in result["explanations"]]
        self.assertEqual(offsets, sorted(offsets))
        self.assertLessEqual(max(offsets), len(lines))

    def test_fixed_seed_and_concurrent_multigeneral_workers(self):
        a, b = multi(4, 4, seed=42), multi(3, 4, seed=7, frontal=False)
        # Plusieurs blocs et départages aléatoires, avec 160 unités au maximum.
        blocks = scenario({"avant": ("cavalerie_lourde", 5), "droite": ("archer", 5),
                           "gauche": ("cavalier", 5), "arriere": ("piquier", 5)})["armies"]["A"]["blocks"]
        for camp in a["armies"].values():
            for general in camp["generals"]:
                general["blocks"] = copy.deepcopy(blocks)
        enemy_blocks = scenario({"avant": ("piquier", 5), "droite": ("cavalier", 5),
                                 "gauche": ("archer", 5), "arriere": ("archer", 5)})["armies"]["A"]["blocks"]
        for general in a["armies"]["B"]["generals"]:
            general["blocks"] = copy.deepcopy(enemy_blocks)
        expected = [self.assert_reference(data) for data in (a, b)]
        self.assertTrue(any(e["manoeuvres"] for e in expected[0]["engagements"]))
        with tempfile.TemporaryDirectory(prefix="mythodea-multi-sentinel-") as directory:
            sentinel = Path(directory) / "host-save.txt"
            sentinel.write_bytes(b"Host save must remain intact")
            original = sentinel.read_bytes()
            with ThreadPoolExecutor(max_workers=2) as pool:
                actual = list(pool.map(lambda data: Runner().run(data), (a, b)))
            self.assertEqual(sentinel.read_bytes(), original)
        self.assertEqual(expected, actual)

    def test_real_http_multigeneral(self):
        response = create_app().test_client().post("/api/simulator/run", json=multi(4, 4, frontal=False))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json["conditions"]["orders"], [])
        self.assertEqual(len(response.json["before"]["A"]["generals"]), 4)
