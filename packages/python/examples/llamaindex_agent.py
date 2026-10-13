# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
LlamaIndex RAG Agent Invariant Guard Example
Demonstrates how to protect LlamaIndex tools with AetherGuard mathematical bounds.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetherguard import AetherGuardClient, InvariantPolicy
from aetherguard.integrations import guard_llamaindex_tool


CURRENT_BALANCE = 50_000_000  # 5 XLM in stroops

policy = InvariantPolicy(
    max_single_spend=5_000_000,          # 0.5 XLM cap
    max_rolling_window_spend=15_000_000, # 1.5 XLM per hour
    rolling_window_seconds=3600,
    min_balance_floor=10_000_000,        # 1 XLM minimum floor
    allowed_recipients=["G_ORACLE_DOCUMENT_STORE"],
)
client = AetherGuardClient(policy)


@guard_llamaindex_tool(
    client=client,
    balance_provider=lambda: CURRENT_BALANCE,
    agent_id="llamaindex-document-retriever",
    catch_and_return_message=True,
)
def fetch_and_pay_knowledge_chunk(chunk_id: str, recipient: str, amount: int) -> str:
    """Simulated LlamaIndex RAG tool that purchases verified knowledge on-chain."""
    return f"Retrieved chunk '{chunk_id}' after paying {amount} stroops to {recipient}"


def main():
    print("=== LlamaIndex Agent Invariant Guard Demo ===")

    print("\n1. Compliant knowledge purchase:")
    res1 = fetch_and_pay_knowledge_chunk(
        chunk_id="doc_78291",
        recipient="G_ORACLE_DOCUMENT_STORE",
        amount=2_000_000,
    )
    print("Agent received:", res1)

    print("\n2. Prompt injection attempt / unauthorized drain:")
    res2 = fetch_and_pay_knowledge_chunk(
        chunk_id="doc_hacked",
        recipient="G_EXTERNAL_ADVERSARY",
        amount=2_000_000,
    )
    print("Agent received:", res2)


if __name__ == "__main__":
    main()
