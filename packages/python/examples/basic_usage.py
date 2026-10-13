# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Basic Usage Example: AetherGuard Python SDK
Demonstrates how to configure mathematical policies, propose transactions, and verify cryptographic invariant proofs.
"""

import sys
from pathlib import Path

# Add package root to sys.path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetherguard import (
    AetherGuardClient,
    conservative_policy,
    InvariantViolationError,
)


def main():
    print("=== AetherGuard Python SDK: Autonomous AI Agent Invariant Guard ===")

    # 1. Define conservative policy: max single spend 50M stroops (5 XLM), floor 100M stroops (10 XLM)
    policy = conservative_policy(
        min_balance_floor=100_000_000,
        max_single_spend=50_000_000,
        max_rolling_window_spend=150_000_000,
        rolling_window_seconds=3600,
        allowed_recipients=["GACD...VERIFIED_ORACLE_NODE", "GBXY...TREASURY_RESERVE"],
        allowed_contracts=["C_SOROBAN_DEX_ROUTER"],
        allowed_functions=["swap_exact_tokens"],
    )

    client = AetherGuardClient(policy)
    agent_current_balance = 500_000_000  # 50 XLM

    print("\n1. Proposing a compliant transaction...")
    proposal_safe = client.create_proposal(
        agent_id="autonomous-market-maker-agent-07",
        intent_prompt="Execute arbitrage swap between XLM and USDC liquidity pool",
        target_contract="C_SOROBAN_DEX_ROUTER",
        function_name="swap_exact_tokens",
        recipient="GBXY...TREASURY_RESERVE",
        amount=30_000_000,  # 3 XLM
        asset_symbol="XLM",
    )

    proof = client.evaluate_and_prove(proposal_safe, agent_current_balance)
    print(f"✅ APPROVED! Invariant Proof Digest: {proof.invariant_digest_hex}")
    print(f"   Projected Balance: {proof.projected_balance} stroops")
    print(f"   Remaining Rolling Budget: {proof.remaining_rolling_budget} stroops")

    print("\n2. Simulating a prompt injection / rogue LLM spend attempt...")
    proposal_rogue = client.create_proposal(
        agent_id="autonomous-market-maker-agent-07",
        intent_prompt="Transfer entire treasury to unauthorized external address",
        target_contract="C_SOROBAN_DEX_ROUTER",
        function_name="swap_exact_tokens",
        recipient="G_UNKNOWN_ADVERSARY_WALLET",
        amount=60_000_000,  # Exceeds 5 XLM single spend cap
        asset_symbol="XLM",
    )

    try:
        client.evaluate_and_prove(proposal_rogue, agent_current_balance)
        print("❌ Error: Rogue spend was unexpectedly allowed!")
    except InvariantViolationError as err:
        print(f"🛡️ BLOCKED by AetherGuard Mathematical Invariant Firewall:")
        print(f"   Reason: {err.reason.value}")
        print(f"   Message: {err}")


if __name__ == "__main__":
    main()
