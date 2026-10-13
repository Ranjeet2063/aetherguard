# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
LangChain Integration Example: AetherGuard Invariant Protection
Demonstrates how to guard LangChain tools with deterministic financial invariants.
"""

import sys
from pathlib import Path

# Add package root to sys.path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetherguard import AetherGuardClient, InvariantPolicy
from aetherguard.integrations import guard_tool


# Mock wallet state
CURRENT_WALLET_BALANCE = 100_000_000  # 10 XLM in stroops


def get_wallet_balance() -> int:
    return CURRENT_WALLET_BALANCE


# 1. Setup policy
policy = InvariantPolicy(
    max_single_spend=10_000_000,          # 1 XLM max per action
    max_rolling_window_spend=30_000_000,  # 3 XLM max per hour
    rolling_window_seconds=3600,
    min_balance_floor=20_000_000,         # Always keep 2 XLM reserve
    allowed_recipients=["GBBQ...TRUSTED_DATA_PROVIDER"],
)
client = AetherGuardClient(policy)


# 2. Guard the LangChain payment tool with decorator
@guard_tool(
    client=client,
    balance_provider=get_wallet_balance,
    agent_id="langchain-research-assistant",
    target_contract="stellar-payment",
    function_name="transfer",
    catch_and_return_message=True,  # Inform the LLM gracefully of invariant rejections
)
def pay_for_premium_research_data(recipient: str, amount: int) -> str:
    """Simulated payment execution tool called by LangChain agent."""
    return f"Successfully transferred {amount} stroops to {recipient}"


def main():
    print("=== LangChain Tool Invariant Guard Example ===")

    # Test 1: Agent calls tool within limits
    print("\n1. LangChain Agent executes safe payment tool call:")
    res1 = pay_for_premium_research_data(
        recipient="GBBQ...TRUSTED_DATA_PROVIDER",
        amount=5_000_000,
    )
    print("Agent received:", res1)

    # Test 2: Agent gets manipulated or hallucinates an excessive payment
    print("\n2. LangChain Agent attempts overspending (15 XLM):")
    res2 = pay_for_premium_research_data(
        recipient="GBBQ...TRUSTED_DATA_PROVIDER",
        amount=15_000_000,
    )
    print("Agent received:", res2)

    # Test 3: Agent attempts paying an unauthorized address
    print("\n3. LangChain Agent attempts paying unauthorized address:")
    res3 = pay_for_premium_research_data(
        recipient="G_UNKNOWN_PHISHING_RECIPIENT",
        amount=1_000_000,
    )
    print("Agent received:", res3)


if __name__ == "__main__":
    main()
