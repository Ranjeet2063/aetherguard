# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
CrewAI Multi-Agent Pipeline Guard Example
Demonstrates how to integrate AetherGuard into multi-agent systems like CrewAI or AutoGPT.
"""

import sys
from pathlib import Path

# Add package root to sys.path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetherguard import AetherGuardClient, InvariantPolicy, InvariantViolationError
from aetherguard.integrations import CrewAIGuard


def main():
    print("=== CrewAI Multi-Agent Invariant Guard Example ===")

    # Treasury wallet balance
    treasury_balance = 500_000_000  # 50 XLM in stroops

    policy = InvariantPolicy(
        max_single_spend=50_000_000,
        max_rolling_window_spend=100_000_000,
        rolling_window_seconds=1800,
        min_balance_floor=100_000_000,
        allowed_recipients=["G_STAKING_REWARDS_POOL"],
    )
    client = AetherGuardClient(policy)
    guard = CrewAIGuard(client, lambda: treasury_balance, agent_id="crewai-treasury-manager")

    print("\n1. Verifying CrewAI agent action (Staking Rewards Distribution)...")
    try:
        ok = guard.verify_action(
            action_name="Distribute weekly staking rewards",
            recipient="G_STAKING_REWARDS_POOL",
            amount=20_000_000,
        )
        print("CrewAI action permitted:", ok)
    except InvariantViolationError as err:
        print("CrewAI action rejected:", err)

    print("\n2. Verifying malicious / untrusted multi-agent action...")
    try:
        guard.verify_action(
            action_name="Arbitrary liquidity transfer",
            recipient="G_UNKNOWN_ROUTING_CONTRACT",
            amount=20_000_000,
        )
        print("Action permitted!")
    except InvariantViolationError as err:
        print("CrewAI action successfully blocked by Invariant Firewall:")
        print(f"Reason: {err.reason.value}")


if __name__ == "__main__":
    main()
