# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Unit tests for AetherGuard Universal Local Invariant Gateway Proxy.
"""

import json
import threading
import urllib.request
import unittest

from aetherguard import InvariantPolicy
from aetherguard.gateway import run_gateway


class TestInvariantGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = InvariantPolicy(
            max_single_spend=1000,
            max_rolling_window_spend=3000,
            rolling_window_seconds=60,
            min_balance_floor=500,
            allowed_recipients=["G_ALICE_VALID"],
        )
        cls.port = 18787
        cls.host = "127.0.0.1"
        cls.server = run_gateway(host=cls.host, port=cls.port, policy=cls.policy)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _request(self, method: str, path: str, payload: dict = None) -> tuple[int, dict]:
        url = f"http://{self.host}:{self.port}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                body = json.loads(resp.read().decode("utf-8"))
                return status, body
        except urllib.error.HTTPError as err:
            status = err.code
            body = json.loads(err.read().decode("utf-8"))
            return status, body

    def test_health_check(self):
        status, body = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body.get("status"), "healthy")
        self.assertEqual(body.get("service"), "AetherGuard Invariant Gateway")

    def test_get_policy(self):
        status, body = self._request("GET", "/policy")
        self.assertEqual(status, 200)
        policy = body.get("policy", {})
        self.assertEqual(policy.get("max_single_spend"), 1000)
        self.assertEqual(policy.get("min_balance_floor"), 500)

    def test_evaluate_approved_proposal(self):
        status, body = self._request("POST", "/evaluate", {
            "agent_id": "curl-test-agent",
            "recipient": "G_ALICE_VALID",
            "amount": 400,
            "current_balance": 2000,
        })
        self.assertEqual(status, 200)
        self.assertEqual(body.get("status"), "APPROVED")
        self.assertEqual(body.get("spent_amount"), "400")
        self.assertEqual(body.get("projected_balance"), "1600")
        self.assertTrue(len(body.get("invariant_digest_hex", "")) == 64)

    def test_evaluate_blocked_single_spend(self):
        status, body = self._request("POST", "/evaluate", {
            "agent_id": "rogue-agent",
            "recipient": "G_ALICE_VALID",
            "amount": 1500,  # Cap is 1000
            "current_balance": 5000,
        })
        self.assertEqual(status, 403)
        self.assertEqual(body.get("status"), "BLOCKED")
        self.assertEqual(body.get("reason"), "SINGLE_SPEND_CAP_EXCEEDED")

    def test_evaluate_blocked_unauthorized_recipient(self):
        status, body = self._request("POST", "/evaluate", {
            "agent_id": "prompt-injected-agent",
            "recipient": "G_UNAUTHORIZED_PHISHING_DRAINER",
            "amount": 200,
            "current_balance": 5000,
        })
        self.assertEqual(status, 403)
        self.assertEqual(body.get("status"), "BLOCKED")
        self.assertEqual(body.get("reason"), "UNAUTHORIZED_RECIPIENT")


if __name__ == "__main__":
    unittest.main()
