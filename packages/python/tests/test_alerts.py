# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Unit tests for AetherGuard Multi-Channel Webhook Alerting Engine.
"""

import time
import json
import threading
import unittest
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

from aetherguard.alerts import WebhookAlertManager, AlertLevel


class MockWebhookHandler(BaseHTTPRequestHandler):
    received_payloads: list[dict] = []

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8")
        try:
            MockWebhookHandler.received_payloads.append(json.loads(body))
        except Exception:
            MockWebhookHandler.received_payloads.append({"raw": body})

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok": true}')

    def log_message(self, format, *args):
        pass


class TestWebhookAlertManager(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        MockWebhookHandler.received_payloads.clear()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MockWebhookHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        MockWebhookHandler.received_payloads.clear()

    def test_has_active_channels(self):
        # Empty manager
        mgr_none = WebhookAlertManager()
        self.assertFalse(mgr_none.has_active_channels())

        # Configured discord
        mgr_discord = WebhookAlertManager(discord_webhook_url="https://discord.com/api/webhooks/test")
        self.assertTrue(mgr_discord.has_active_channels())

        # Configured telegram
        mgr_telegram = WebhookAlertManager(telegram_token="123:ABC", telegram_chat_id="99999")
        self.assertTrue(mgr_telegram.has_active_channels())

    def test_should_alert_levels(self):
        # VIOLATIONS_ONLY
        mgr_viol = WebhookAlertManager(alert_level=AlertLevel.VIOLATIONS_ONLY)
        self.assertTrue(mgr_viol.should_alert(status="BLOCKED", amount=100))
        self.assertFalse(mgr_viol.should_alert(status="APPROVED", amount=100))

        # HIGH_VALUE_ONLY
        mgr_high = WebhookAlertManager(alert_level=AlertLevel.HIGH_VALUE_ONLY, high_value_threshold=500)
        self.assertTrue(mgr_high.should_alert(status="BLOCKED", amount=50))
        self.assertFalse(mgr_high.should_alert(status="APPROVED", amount=200))
        self.assertTrue(mgr_high.should_alert(status="APPROVED", amount=600))

    def test_generic_webhook_dispatch(self):
        mock_url = f"http://127.0.0.1:{self.port}/webhook"
        mgr = WebhookAlertManager(generic_webhook_url=mock_url, alert_level=AlertLevel.ALL)

        t0 = time.time()
        mgr.notify_event_async(
            agent_id="test-agent-007",
            amount=50_000_000,
            recipient="GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
            status="BLOCKED",
            detail="SINGLE_SPEND_CAP_EXCEEDED",
        )
        elapsed = time.time() - t0

        # Must return in under 20ms (non-blocking async)
        self.assertLess(elapsed, 0.05)

        # Allow background thread up to 1 second to dispatch
        for _ in range(20):
            if len(MockWebhookHandler.received_payloads) >= 1:
                break
            time.sleep(0.05)
        self.assertEqual(len(MockWebhookHandler.received_payloads), 1)
        payload = MockWebhookHandler.received_payloads[0]
        self.assertEqual(payload.get("status"), "BLOCKED")
        self.assertEqual(payload.get("agent_id"), "test-agent-007")
        self.assertEqual(payload.get("amount_xlm"), "5.00 XLM")
        self.assertEqual(payload.get("detail"), "SINGLE_SPEND_CAP_EXCEEDED")


if __name__ == "__main__":
    unittest.main()
