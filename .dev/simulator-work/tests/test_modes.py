"""Modes officiels et régression des priorités de manœuvre, sans moteur substitué."""
import copy
from concurrent.futures import ThreadPoolExecutor
import sys
import unittest
from unittest.mock import Mock

from backend.app import create_app
from backend.runner import Runner
from tests.scenarios import multi, scenario
from tests.test_linux import ReferenceRunner


class ModeValidation(unittest.TestCase):
    def test_invalid_modes_and_defenders_never_execute(self):
        runner = Mock()
        client = create_app(runner).test_client()
        for fields in ({"mode": "OFF/DEF"}, {"defender": "A"},
                       {"mode": "DEF/DEF", "defender": "A"},
                       {"mode": True, "defender": None}, {"mode": [], "defender": None},
                       {"mode": "OFF/OFF", "defender": "A"},
                       {"mode": "OFF/DEF", "defender": None},
                       {"mode": "OFF/DEF", "defender": "j1"},
                       {"mode": "OFF/DEF", "defender": {}},
                       {"mode": "OFF/DEF", "defender": "../../game"}):
            with self.subTest(fields=fields):
                data = multi()
                data.update(fields)
                self.assertEqual(client.post("/api/simulator/run", json=data).status_code, 400)
        runner.run.assert_not_called()
        self.assertEqual(client.get("/api/simulator/catalog").json["modes"], ["OFF/OFF", "OFF/DEF"])


@unittest.skipUnless(sys.platform == "linux", "Exige un véritable noyau Linux")
class ModeLinux(unittest.TestCase):
    def test_off_def_both_defenders_match_direct_engine(self):
        for size in (1, 2, 4):
            for frontal in (False,):
                base = multi(size, max(2, size), seed=123, frontal=frontal)
                ordinary = Runner().run(base)
                for defender, owner in (("A", "j1"), ("B", "j2")):
                    with self.subTest(size=size, frontal=frontal, defender=defender):
                        data = dict(base, mode="OFF/DEF", defender=defender)
                        actual = Runner().run(data)
                        reference = ReferenceRunner().execute("simulate", data)
                        self.assertEqual(actual["after"], reference["after"])
                        self.assertEqual(actual["journal"], reference["journal"])
                        self.assertEqual(actual["conditions"]["mode"], "OFF/DEF")
                        self.assertEqual(actual["conditions"]["defender"], defender)
                        self.assertIn(f"Défenseur : {owner}", actual["journal"])
                        # Le moteur verrouillé n'applique aucun bonus de défense.
                        for key in ("after", "losses", "outcome", "engagements"):
                            self.assertEqual(actual[key], ordinary[key])

    def test_explicit_off_off_preserves_historical_results(self):
        for data in (scenario(), multi(3, 4, frontal=False)):
            historical = Runner().run(data)
            explicit = Runner().run(dict(data, mode="OFF/OFF", defender=None))
            for key in historical.keys() - {"configuration"}:
                self.assertEqual(historical[key], explicit[key])

    def test_off_def_replay_and_independent_workers(self):
        data = multi(4, 4, seed=17)
        combat = scenario({"avant": ("archer", 15), "gauche": ("cavalier", 5)},
                          {"droite": ("archer", 11), "arriere": ("piquier", 1)})
        for camp in ("A", "B"):
            for general in data["armies"][camp]["generals"]:
                general["blocks"] = copy.deepcopy(combat["armies"][camp]["blocks"])
        requests = [dict(data, mode="OFF/DEF", defender=camp) for camp in ("A", "B")]
        expected = [Runner().run(request) for request in requests]
        with ThreadPoolExecutor(max_workers=2) as pool:
            actual = list(pool.map(lambda request: Runner().run(request), requests))
        self.assertEqual(expected, actual)
        self.assertTrue(expected[0]["engagements"][0]["manoeuvres"])

    def test_engaged_front_can_act_once_in_first_manoeuvre_turn(self):
        data = scenario({"avant": ("archer", 10), "gauche": ("piquier", 10)},
                        {"avant": ("piquier", 1), "droite": ("archer", 15)})
        result = Runner().run(data)
        self.assertEqual(result["journal"], ReferenceRunner().execute("simulate", data)["journal"])
        engagement = result["engagements"][0]
        self.assertEqual(engagement["chocs"][0]["bloc_1"], "avant")
        front_actions = [a for a in engagement["manoeuvres"] if a["joueur_attaquant"] == "j1" and a["bloc_attaquant"] == "avant"]
        self.assertEqual(len(front_actions), 1)
        self.assertEqual(front_actions[0]["tour"], 1)
        self.assertEqual(engagement["manoeuvres"][-1], front_actions[0])
        order = next(e for e in result["explanations"] if e["kind"] == "order")
        self.assertFalse(order["initiative"]["j1"])
        self.assertEqual(order["actions"][-1], ["j1", "avant"])
        self.assertEqual(len(order["actions"]), len(set(map(tuple, order["actions"]))))
        self.assertIn("dès la fin du premier tour", order["text"])
        self.assertIn("au plus une fois par tour de manœuvre", order["text"])

    def test_real_http_off_def(self):
        for defender in ("A", "B"):
            response = create_app().test_client().post("/api/simulator/run", json=dict(multi(2, 3), mode="OFF/DEF", defender=defender))
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json["conditions"]["defender"], defender)
            self.assertEqual(len(response.json["after"]["B"]["generals"]), 3)
