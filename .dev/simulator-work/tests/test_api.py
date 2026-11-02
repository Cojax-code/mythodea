import copy
import threading
import unittest
from unittest.mock import Mock

from backend.app import create_app
from backend.runner import SimulationTimeout, SimulationUnavailable
from tests.scenarios import scenario


class API(unittest.TestCase):
    def setUp(self):
        self.runner = Mock()
        self.runner.run.return_value = {"outcome": "A"}
        self.app = create_app(self.runner)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_valid_scenario_reaches_runner(self):
        data = scenario()
        self.assertEqual(self.client.post("/api/simulator/run", json=data).status_code, 200)
        self.runner.run.assert_called_once_with(data)

    def test_invalid_configuration_never_executes(self):
        mutations = [lambda p: p.update(path="/game"), lambda p: p.update(command="touch /game/x"),
                     lambda p: p.update(seed=True), lambda p: p.update(seed=-1),
                     lambda p: p.update(seed=2**32), lambda p: p.update(seed=1.5),
                     lambda p: p["armies"].update(C=p["armies"]["A"]),
                     lambda p: p["armies"]["A"].update(fatigue=True),
                     lambda p: p["armies"]["A"]["blocks"].pop("avant"),
                     lambda p: p["armies"]["A"]["blocks"]["avant"].update(unit="../../game"),
                     lambda p: p["armies"]["A"]["blocks"]["avant"].update(count=21),
                     lambda p: p["armies"]["A"]["blocks"]["avant"].update(count=-1),
                     lambda p: p["armies"]["A"]["blocks"]["avant"].update(count=True),
                     lambda p: p["armies"]["A"]["blocks"]["avant"].update(count="3"),
                     lambda p: p["armies"]["A"]["blocks"]["avant"].update(count=0),
                     lambda p: p["armies"]["A"]["blocks"]["droite"].update(count=1)]
        for mutation in mutations:
            data = copy.deepcopy(scenario())
            mutation(data)
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/api/simulator/run", json=data).status_code, 400)
        self.runner.run.assert_not_called()

    def test_malformed_and_large_requests(self):
        self.assertEqual(self.client.post("/api/simulator/run", data="{", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/simulator/run", data="x").status_code, 400)
        self.assertEqual(self.client.post("/api/simulator/run", data="x" * 8193, content_type="application/json").status_code, 413)
        self.runner.run.assert_not_called()

    def test_files_are_allowlisted(self):
        for path in ("/", "/simulateur.html", "/css/style.css", "/js/simulateur.js", "/aide.html"):
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200, path)
        for path in ("/backend/engine.lock.json", "/.git/config", "/.runtime/engine/config.py", "/../README.md"):
            self.assertEqual(self.client.get(path).status_code, 404, path)

    def test_fail_closed_and_timeout_are_not_battle_outcomes(self):
        for error, status in ((SimulationUnavailable("sensitive path"), 503), (SimulationTimeout("Délai dépassé"), 504)):
            self.runner.run.side_effect = error
            with self.assertLogs(level="ERROR") if status == 503 else self.subTest(status=status):
                response = self.client.post("/api/simulator/run", json=scenario())
            self.assertEqual(response.status_code, status)
            self.assertNotIn("outcome", response.json)
            self.assertNotIn("sensitive path", response.text)
        self.runner.run.side_effect = None
        self.assertEqual(self.client.post("/api/simulator/run", json=scenario()).status_code, 200)

    def test_simultaneous_requests_are_bounded(self):
        entered, release = threading.Event(), threading.Event()

        def wait(_payload):
            entered.set()
            release.wait(5)
            return {"outcome": "A"}

        self.runner.run.side_effect = wait
        thread = threading.Thread(target=lambda: self.app.test_client().post("/api/simulator/run", json=scenario()))
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            self.assertEqual(self.client.post("/api/simulator/run", json=scenario()).status_code, 429)
        finally:
            release.set()
            thread.join(5)

    def test_cross_site_request_refused(self):
        self.assertEqual(self.client.post("/api/simulator/run", json=scenario(), headers={"Sec-Fetch-Site": "cross-site"}).status_code, 403)
        self.runner.run.assert_not_called()

    def test_untrusted_host_refused(self):
        response = self.client.post("/api/simulator/run", json=scenario(), headers={"Host": "foreign.example"})
        self.assertEqual(response.status_code, 400)
        self.runner.run.assert_not_called()
