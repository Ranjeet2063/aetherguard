# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Universal Agent HTTP Integration Demo: Any Agent (cURL / Python / Node / Go)
Demonstrates how ANY external AI agent connects to the AetherGuard Local Invariant Gateway
via standard HTTP POST requests without needing any SDK installed!
"""

import sys
import json
import threading
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetherguard import InvariantPolicy
from aetherguard.gateway import run_gateway


def main():
    print("=" * 75)
    print("🌐 AETHERGUARD: UNIVERSAL LOCAL INVARIANT GATEWAY PROXY DEMO")
    print("=" * 75)

    # 1. Spin up the local Invariant Gateway
    policy = InvariantPolicy(
        max_single_spend=50_000_000,          # 5 XLM
        max_rolling_window_spend=150_000_000,  # 15 XLM per hour
        rolling_window_seconds=3600,
        min_balance_floor=100_000_000,         # 10 XLM reserve floor
        allowed_recipients=["GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4"],
    )

    port = 8787
    server = run_gateway(host="127.0.0.1", port=port, policy=policy)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print(f"\n[Gateway Status] Invariant Gateway listening on http://127.0.0.1:{port}")
    print("  • Single Spend Cap:      5.00 XLM")
    print("  • Solvency Reserve Floor: 10.00 XLM")
    print("  • Whitelisted Address:   GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4")

    # Helper function simulating external cURL / fetch request
    def agent_request(payload: dict):
        url = f"http://127.0.0.1:{port}/evaluate"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    # 2. Agent 1 (Safe action)
    print("\n[Case 1] Node.js / Python Agent proposes safe 3 XLM payment:")
    code1, resp1 = agent_request({
        "agent_id": "claude-autonomous-analyst",
        "recipient": "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
        "amount": 30_000_000, # 3 XLM
        "current_balance": 500_000_000, # 50 XLM
    })
    print(f"  HTTP Response: {code1}")
    print(f"  Status:        {resp1.get('status')}")
    print(f"  Proof Digest:  {resp1.get('invariant_digest_hex')}")
    print(f"  Projected Bal: {int(resp1.get('projected_balance')) / 10_000_000} XLM")

    # 3. Agent 2 (Prompt injection / overspend)
    print("\n[Case 2] Prompt-injected Agent attempts unauthorized 50 XLM drain:")
    code2, resp2 = agent_request({
        "agent_id": "compromised-agent-99",
        "recipient": "G_ADVERSARY_WALLET_DRAIN",
        "amount": 500_000_000, # 50 XLM
        "current_balance": 500_000_000,
    })
    print(f"  HTTP Response: {code2} (FORBIDDEN)")
    print(f"  Status:        {resp2.get('status')}")
    print(f"  Blocked Reason:{resp2.get('reason')}")
    print(f"  Error Message: {resp2.get('error')}")

    # Shutdown
    server.shutdown()
    print("\n" + "=" * 75)
    print("🎉 Gateway Test Complete: Zero code changes needed in AI agents!")
    print("=" * 75)


if __name__ == "__main__":
    main()
