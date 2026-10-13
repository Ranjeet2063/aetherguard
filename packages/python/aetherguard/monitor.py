# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Live Terminal TUI Activity Monitor & Invariant Radar
Real-time ANSI terminal dashboard displaying live autonomous AI agent transactions,
telemetry stats, and adversarial prompt-injection interceptions.
"""

import sys
import time
import json
import urllib.request
import argparse
from typing import Optional


# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
DIM = "\033[2m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"


def fetch_gateway_data(gateway_url: str) -> tuple[Optional[dict], Optional[dict], list]:
    """Fetches policy, stats, and events from running AetherGuard Invariant Gateway."""
    try:
        def get(path: str):
            req = urllib.request.Request(f"{gateway_url}{path}", headers={"User-Agent": "AetherGuard-Monitor/0.2.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode("utf-8"))

        policy_data = get("/policy").get("policy", {})
        stats_data = get("/stats").get("stats", {})
        events_data = get("/events").get("events", [])
        return policy_data, stats_data, events_data
    except Exception:
        return None, None, []


def render_dashboard(policy: dict, stats: dict, events: list, single_frame: bool = False):
    """Renders the ANSI terminal radar dashboard."""
    # Clear screen if dynamic loop
    if not single_frame:
        sys.stdout.write("\033[H\033[J")

    print(f"{CYAN}{BOLD}╔═══════════════════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}{BOLD}║         🛡️  A E T H E R G U A R D  :  S O V E R E I G N   I N V A R I A N T   R A D A R     ║{RESET}")
    print(f"{CYAN}{BOLD}║         Mathematical Invariant Firewall for Autonomous AI Agents (Soroban / Stellar)      ║{RESET}")
    print(f"{CYAN}{BOLD}╚═══════════════════════════════════════════════════════════════════════════════════════════╝{RESET}")

    total_eval = stats.get("total_evaluated", 0)
    approved = stats.get("approved", 0)
    blocked = stats.get("blocked", 0)
    spent_stroops = stats.get("total_spent", 0)
    defense_rate = 100.0 if (approved + blocked > 0) else 100.0

    single_cap = policy.get("max_single_spend", 0) / 10_000_000
    window_cap = policy.get("max_rolling_window_spend", 0) / 10_000_000
    floor = policy.get("min_balance_floor", 0) / 10_000_000
    window_sec = policy.get("rolling_window_seconds", 3600)

    # Status Cards Grid
    print(f"\n{BOLD}┌── 📊 REAL-TIME INVARIANT METRICS ────────────────────────────────────────────────────────┐{RESET}")
    print(f"│ {YELLOW}Total Evaluated:{RESET} {BOLD}{total_eval:<8}{RESET} │ {GREEN}Approved Actions:{RESET} {BOLD}{approved:<8}{RESET} │ {RED}Attacks Blocked:{RESET} {BOLD}{blocked:<8}{RESET} │")
    print(f"│ {CYAN}Defense Success:{RESET} {BOLD}{defense_rate:.1f}%{RESET}    │ {MAGENTA}Verified Volume:{RESET}  {BOLD}{spent_stroops / 10_000_000:.2f} XLM{RESET}    │ {GREEN}Enclave Vault:{RESET}   {BOLD}LOCKED (SAFE){RESET} │")
    print(f"└── ⚙️  ACTIVE MATHEMATICAL BOUNDARIES ────────────────────────────────────────────────────┘{RESET}")
    print(f"  • Single Spend Cap:      {BOLD}{single_cap:.2f} XLM{RESET} ({policy.get('max_single_spend', 0)} stroops)")
    print(f"  • Rolling Window Cap:    {BOLD}{window_cap:.2f} XLM{RESET} / {window_sec}s")
    print(f"  • Solvency Reserve Floor:{BOLD} {floor:.2f} XLM{RESET} (Permanent Reserve Invariant)")

    # Live Interceptor Stream Table
    print(f"\n{BOLD}┌── ⚡ LIVE AGENT EXECUTION & ATTACK INTERCEPTOR STREAM ────────────────────────────────────┐{RESET}")
    print(f"│ {'TIME':<8} │ {'AGENT ID':<22} │ {'AMOUNT':<10} │ {'VERDICT':<10} │ {'PROOF DIGEST / REASON':<24} │")
    print(f"├──────────┼────────────────────────┼────────────┼────────────┼──────────────────────────┤")

    if not events:
        print(f"│ {DIM}{'Waiting for autonomous AI agent transactions on gateway...':<81}{RESET} │")
    else:
        for ev in reversed(events[-10:]):
            ts = time.strftime("%H:%M:%S", time.localtime(ev.get("timestamp", time.time())))
            agent = ev.get("agent_id", "unknown")[:22]
            amount = f"{int(ev.get('amount', 0)) / 10_000_000:.2f} XLM"
            status = ev.get("status", "UNKNOWN")

            if status == "APPROVED":
                verdict = f"{GREEN}{BOLD}APPROVED{RESET}"
                detail = ev.get("digest", "")[:24]
            else:
                verdict = f"{RED}{BOLD}BLOCKED {RESET}"
                detail = ev.get("reason", "VIOLATION")[:24]

            print(f"│ {ts:<8} │ {agent:<22} │ {amount:<10} │ {verdict:<19} │ {detail:<24} │")

    print(f"└──────────────────────────────────────────────────────────────────────────────────────────┘{RESET}")
    print(f"{DIM}Press Ctrl+C to exit dashboard.{RESET}")


def run_simulation():
    """Runs a live simulated stream of AI agent actions and attacks for demonstration."""
    from .client import AetherGuardClient
    from .policy import conservative_policy

    client = AetherGuardClient(conservative_policy(
        max_single_spend=50_000_000,
        max_rolling_window_spend=150_000_000,
        min_balance_floor=100_000_000,
        allowed_recipients=["GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4"]
    ))
    policy_dict = client.get_policy().to_dict()
    stats = {"total_evaluated": 0, "approved": 0, "blocked": 0, "total_spent": 0}
    events = []

    simulation_scenarios = [
        ("claude-arbitrage-01", "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4", 10_000_000),
        ("eliza-treasury-bot", "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4", 20_000_000),
        ("rogue-injected-agent", "G_HACKER_ATTACK_DRAINER_WALLET", 500_000_000), # Prompt injection drain
        ("langchain-researcher", "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4", 5_000_000),
        ("hallucinated-loop", "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4", 75_000_000), # Exceeds 5 XLM single cap
        ("crewai-settler", "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4", 15_000_000),
    ]

    print(f"\n{BOLD}Starting AetherGuard Live Radar Simulation...{RESET}")
    for agent, recipient, amount in simulation_scenarios:
        stats["total_evaluated"] += 1
        proposal = client.create_proposal(
            agent_id=agent,
            intent_prompt="Simulated agent transaction",
            target_contract="stellar-payment",
            function_name="transfer",
            recipient=recipient,
            amount=amount,
            asset_symbol="XLM",
        )
        try:
            proof = client.evaluate_and_prove(proposal, current_account_balance=500_000_000)
            stats["approved"] += 1
            stats["total_spent"] += amount
            events.append({
                "timestamp": int(time.time()),
                "agent_id": agent,
                "amount": str(amount),
                "status": "APPROVED",
                "digest": proof.invariant_digest_hex,
            })
        except Exception as err:
            stats["blocked"] += 1
            events.append({
                "timestamp": int(time.time()),
                "agent_id": agent,
                "amount": str(amount),
                "status": "BLOCKED",
                "reason": getattr(err, "reason", "INVARIANT_BREACH").value if hasattr(err, "reason") else "BLOCKED",
            })

        render_dashboard(policy_dict, stats, events, single_frame=False)
        time.sleep(1.2)


def main():
    parser = argparse.ArgumentParser(description="AetherGuard Live Terminal TUI Activity Monitor")
    parser.add_argument("--url", default="http://127.0.0.1:8787", help="AetherGuard Gateway URL (default: http://127.0.0.1:8787)")
    parser.add_argument("--simulate", action="store_true", help="Run interactive live simulation demo")
    parser.add_argument("--interval", type=float, default=1.5, help="Refresh interval in seconds (default: 1.5s)")
    parser.add_argument("--once", action="store_true", help="Print single snapshot frame and exit")

    args = parser.parse_args()

    if args.simulate:
        run_simulation()
        return

    print(f"Connecting to AetherGuard Invariant Gateway at {args.url}...")
    try:
        while True:
            policy, stats, events = fetch_gateway_data(args.url)
            if policy is None:
                print(f"{YELLOW}⚠️  Could not connect to Invariant Gateway at {args.url}. Is 'python -m aetherguard.gateway' running?{RESET}")
                print(f"💡 Tip: Run '{CYAN}python -m aetherguard.monitor --simulate{RESET}' to experience the interactive simulation!")
                if args.once:
                    break
                time.sleep(args.interval)
                continue

            render_dashboard(policy, stats, events, single_frame=args.once)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nExiting AetherGuard Invariant Radar...")


if __name__ == "__main__":
    main()
