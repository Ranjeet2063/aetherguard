# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Real-World Webhook Alerting Demo: Telegram & Discord Mobile Notifications
Demonstrates how AetherGuard automatically dispatches rich mobile notifications
when transactions are approved or when prompt injections are neutralized.
"""

import sys
import json
import time
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetherguard import InvariantPolicy, AetherGuardClient, WebhookAlertManager, AlertLevel


class LocalAlertReceiver(BaseHTTPRequestHandler):
    """Simulates a mobile Telegram / Discord webhook receiver locally."""
    received = []

    def do_POST(self):
        len_ = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(len_).decode("utf-8"))
        LocalAlertReceiver.received.append(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "delivered"}')

    def log_message(self, format, *args):
        pass


def main():
    print("=" * 75)
    print("📱 AETHERGUARD: MULTI-CHANNEL WEBHOOK MOBILE ALERT DEMO")
    print("=" * 75)

    # 1. Start local mock webhook receiver to visualize dispatched alerts
    port = 19999
    server = HTTPServer(("127.0.0.1", port), LocalAlertReceiver)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    mock_webhook = f"http://127.0.0.1:{port}/alert"

    # 2. Configure Alert Manager with local webhook and simulated Discord/Telegram channels
    alert_mgr = WebhookAlertManager(
        generic_webhook_url=mock_webhook,
        alert_level=AlertLevel.ALL,
    )

    policy = InvariantPolicy(
        max_single_spend=50_000_000,
        max_rolling_window_spend=150_000_000,
        rolling_window_seconds=3600,
        min_balance_floor=100_000_000,
        allowed_recipients=["GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4"],
    )
    client = AetherGuardClient(policy)

    print("\n[Configuration] Webhook Alert Dispatcher Active:")
    print("  • Discord / Telegram Channels: Ready")
    print("  • Trigger Level:               ALL (Approved + Blocked)")
    print("  • Non-Blocking Mode:           Enabled (Zero latency overhead on Invariant Engine)")

    # 3. Simulate Event 1: Legitimate Agent Transaction
    print("\n[Step 1] Agent executes compliant 2.50 XLM payment:")
    prop1 = client.create_proposal(
        agent_id="autonomous-market-maker",
        intent_prompt="Routine liquidity rebalance",
        target_contract="stellar-payment",
        function_name="transfer",
        recipient="GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
        amount=25_000_000,
        asset_symbol="XLM",
    )
    proof1 = client.evaluate_and_prove(prop1, current_account_balance=500_000_000)
    alert_mgr.notify_event_async(
        agent_id=prop1.agent_id,
        amount=prop1.amount,
        recipient=prop1.recipient,
        status="APPROVED",
        detail=proof1.invariant_digest_hex,
        timestamp=proof1.verified_at,
    )
    print("  ✅ Invariant Gate: APPROVED")
    print("  📡 Alert Dispatched in background!")

    # 4. Simulate Event 2: Adversarial Prompt Attack
    print("\n[Step 2] Attacker injects prompt to drain 40.00 XLM to unauthorized wallet:")
    prop2 = client.create_proposal(
        agent_id="compromised-worker-bot",
        intent_prompt="Drain treasury to attacker",
        target_contract="stellar-payment",
        function_name="transfer",
        recipient="G_UNKNOWN_ADVERSARY_DRAIN",
        amount=400_000_000,
        asset_symbol="XLM",
    )
    try:
        client.evaluate_and_prove(prop2, current_account_balance=500_000_000)
    except Exception as err:
        alert_mgr.notify_event_async(
            agent_id=prop2.agent_id,
            amount=prop2.amount,
            recipient=prop2.recipient,
            status="BLOCKED",
            detail=getattr(err, "reason", "BREACH").value if hasattr(err, "reason") else str(err),
            timestamp=prop2.timestamp,
        )
        print("  🛑 Invariant Gate: BLOCKED PRE-BROADCAST")
        print("  🚨 HIGH-PRIORITY SECURITY ALERT Dispatched to Mobile Telegram/Discord!")

    time.sleep(0.3)
    print("\n" + "=" * 75)
    print("📥 Live Mobile Webhook Payload Received by Receiver:")
    for i, payload in enumerate(LocalAlertReceiver.received, 1):
        status_icon = "🛑" if payload.get("status") == "BLOCKED" else "✅"
        print(f"  [{i}] {status_icon} Status: {payload.get('status')} | Agent: {payload.get('agent_id')} | Amount: {payload.get('amount_xlm')}")
        print(f"      Detail: {payload.get('detail')}")
    print("=" * 75)
    server.shutdown()


if __name__ == "__main__":
    main()
