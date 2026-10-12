"""Cloud transport acceptance using a fake injected host; no real external calls."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from codex.agent_policy import RoutingError, plan, load_registry
from codex.cloud_bridge import execute_cloud
from codex.tests.test_agent_policy import request, item


def registry():
    data = load_registry()
    data["providers"].append({"id": "example-cloud", "adapter": "host-unconfigured", "enabled": True,
                              "models": [{"id": "safe", "quality_tier": 3, "relative_cost": 3,
                                          "capabilities": ["code_edit", "research"], "efforts": ["low", "medium", "high"],
                                          "attested": True}]})
    return data


class FakeCloud:
    def __init__(self, **kwargs):
        self.supported = kwargs.get("supported", True)
        self.status = kwargs.get("status", "completed")
        self.missing_proof = kwargs.get("missing_proof", False)
        self.bad_path = kwargs.get("bad_path", False)
        self.calls = []
        self.lock = threading.Lock()
    def supports(self, provider, model, capability):
        return self.supported and provider == "example-cloud" and model == "safe"
    def execute(self, task, *, target_repository):
        with self.lock:
            self.calls.append(task["id"])
        return {"id": task["id"], "status": self.status,
                "run_id": "cloud-job-" + task["id"] + "-12345",
                "verified": not self.missing_proof,
                "changed_paths": ["unowned/path" if self.bad_path else task["paths"][0] + "/verified.txt"],
                "usage": {"input_tokens": 100, "output_tokens": 25, "cached_input_tokens": 50}}


class CloudTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Path(self.temp.name) / "budget"

    def _plan(self, mode="parallel"):
        return plan(request([item("first", "src/channels", "Implement channel navigation and verify regression tests"),
                             item("second", "src/movies", "Implement movie catalogue and verify regression tests")],
                            providers=["example-cloud"], preference=mode), registry())

    def test_two_independently_attested_cloud_jobs_parallel(self):
        host = FakeCloud()
        result = execute_cloud(self._plan(), host, self.ledger)
        self.assertEqual(result["mode"], "parallel")
        self.assertEqual(len(host.calls), 2)
        self.assertEqual([x["status"] for x in result["workers"]], ["completed", "completed"])
        self.assertEqual(result["accounting"]["accounted_tokens"], 250)
        self.assertEqual(result["accounting"]["observed_jobs"], 2)

    def test_serial_failure_stops_second_cloud_job(self):
        host = FakeCloud(status="failed")
        result = execute_cloud(self._plan("serial"), host, self.ledger)
        self.assertEqual(host.calls, ["first"])
        self.assertEqual(result["workers"][1]["status"], "not_started")

    def test_serial_quota_blocked_stops_and_preserves_accounting(self):
        host = FakeCloud(status="quota_blocked")
        result = execute_cloud(self._plan("serial"), host, self.ledger)
        self.assertEqual(host.calls, ["first"])
        self.assertEqual([w["status"] for w in result["workers"]],
                         ["quota_blocked", "not_started"])
        self.assertEqual(result["workers"][0]["provider"], "example-cloud")
        self.assertEqual(result["accounting"]["accounted_tokens"], 125)
        self.assertEqual(result["accounting"]["observed_jobs"], 1)
        self.assertEqual(result["accounting"]["not_started_jobs"], 1)
        self.assertEqual(result["accounting"]["conservative_jobs"], 0)
        self.assertIsNone(result["accounting"]["soft_limit"])
        self.assertIn("no automatic merge", result["integration"])

    def test_unverified_quota_claim_is_never_accepted_as_provider_proof(self):
        host = FakeCloud(status="quota_blocked", missing_proof=True)
        result = execute_cloud(self._plan("serial"), host, self.ledger)
        self.assertEqual(host.calls, ["first"])
        self.assertEqual(result["workers"][0]["status"], "unverified_result")
        self.assertEqual(result["workers"][1]["status"], "not_started")
        self.assertEqual(result["accounting"]["accounted_tokens"], 125)

    def test_unverified_cloud_result_and_scope_violation_are_not_success(self):
        self.assertEqual(execute_cloud(self._plan("single"), FakeCloud(missing_proof=True), self.ledger)["workers"][0]["status"], "unverified_result")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(execute_cloud(self._plan("single"), FakeCloud(bad_path=True), Path(tmp) / "budget")["workers"][0]["status"], "scope_violation")

    def test_missing_connector_blocks_before_reservation_or_launch(self):
        host = FakeCloud(supported=False)
        with self.assertRaisesRegex(RoutingError, "verified capability"):
            execute_cloud(self._plan(), host, self.ledger)
        self.assertEqual(host.calls, [])
        self.assertFalse(self.ledger.exists())


if __name__ == "__main__":
    unittest.main()
