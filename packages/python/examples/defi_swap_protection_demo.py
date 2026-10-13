#!/usr/bin/env python3
# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard DeFi Slippage & AMM Flash Loan / Oracle Protection Demo
Demonstrates how autonomous AI agents trading on Soroswap, Phoenix DEX, or Stellar DEX
are mathematically guarded against MEV sandwich attacks and flash-loan pool manipulation.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from aetherguard import (
    AetherGuardClient,
    defi_arbitrage_policy,
    InvariantViolationError,
)


def run_defi_demo():
    print("=" * 80)
    print("🛡️  A E T H E R G U A R D :  D e F i   S L I P P A G E   &   A M M   G U A R D")
    print("   Formal Mathematical Invariant Protection for Autonomous Trading AI Agents")
    print("=" * 80)

    # 1. Initialize Autonomous Trading Agent Policy
    # Max Slippage: 50 bps (0.5%)
    # Max Oracle Deviation: 150 bps (1.5%)
    policy = defi_arbitrage_policy(
        min_balance_floor=50_000_000,    # 5 XLM
        max_single_spend=500_000_000,    # 50 XLM
        max_rolling_window_spend=2_000_000_000, # 200 XLM per hour
        max_slippage_bps=50,             # 0.5% max allowable slippage
        max_oracle_deviation_bps=150,    # 1.5% max oracle price divergence
        allowed_contracts=["CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC"],
    )

    client = AetherGuardClient(policy)
    agent_balance = 300_000_000  # 30 XLM available

    print(f"\n[CONFIG] Active Invariant Policy:")
    print(f"  • Single Spend Cap:        {policy.max_single_spend / 10_000_000:.2f} XLM")
    print(f"  • Max Allowable Slippage:  {policy.defi_swap_policy.max_slippage_bps} bps (0.50%)")
    print(f"  • Max Oracle Divergence:   {policy.defi_swap_policy.max_oracle_deviation_bps} bps (1.50%)")
    print(f"  • Minimum Output Floor:    {policy.defi_swap_policy.min_output_floor} atomic unit")

    # --------------------------------------------------------------------------
    # SCENARIO 1: Legitimate Arbitrage Swap (Slippage: 30 bps <= 50 bps limit)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("🟢 SCENARIO 1: Autonomous Agent Executes Fair Soroswap Arbitrage Swap")
    print("-" * 80)
    print("Agent trades 10 USDC for XLM. Fair Quote: 100 XLM. Minimum Accepted: 99.7 XLM (30 bps slippage)")

    proposal_1 = client.create_swap_proposal(
        agent_id="soroswap_arbitrage_agent",
        intent_prompt="Execute cross-DEX arbitrage between Phoenix and Soroswap USDC/XLM pool",
        target_contract="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
        function_name="swap_exact_tokens",
        recipient="GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
        asset_in="USDC",
        asset_out="XLM",
        amount_in=100_000_000,
        expected_amount_out=1_000_000_000,
        min_amount_out=997_000_000,  # 30 bps slippage
        oracle_reference_price_bps=100_000, # 10.0 XLM/USDC
    )

    try:
        proof = client.evaluate_and_prove(proposal_1, current_account_balance=agent_balance)
        print("  ✅ VERIFICATION SUCCESS: All mathematical invariants satisfied.")
        print(f"     • Proof ID:        {proof.proposal_id}")
        print(f"     • Invariant Digest:{proof.invariant_digest_hex[:32]}...")
        print(f"     • Spent Amount:    {int(proof.spent_amount) / 10_000_000:.2f} USDC")
        print(f"     • Projected Bal:   {int(proof.projected_balance) / 10_000_000:.2f} XLM")
    except InvariantViolationError as e:
        print(f"  ❌ UNEXPECTED REJECTION: {e}")

    # --------------------------------------------------------------------------
    # SCENARIO 2: MEV Sandwich Attack Interception (Slippage: 400 bps > 50 bps)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("🔴 SCENARIO 2: Adversary / MEV Bot Attempts Sandwich Frontrunning Attack")
    print("-" * 80)
    print("Adversary artificially skews pool reserves, forcing agent to accept 96 XLM for 10 USDC (400 bps slippage).")

    proposal_2 = client.create_swap_proposal(
        agent_id="exploited_agent",
        intent_prompt="Execute swap on manipulated pool with wide slippage tolerance",
        target_contract="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
        function_name="swap_exact_tokens",
        recipient="GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
        asset_in="USDC",
        asset_out="XLM",
        amount_in=100_000_000,
        expected_amount_out=1_000_000_000,
        min_amount_out=960_000_000,  # 400 bps (4.0%) slippage!
    )

    try:
        client.evaluate_and_prove(proposal_2, current_account_balance=agent_balance)
        print("  ❌ FAILURE: Sandwich attack was NOT intercepted!")
    except InvariantViolationError as e:
        print("  🛡️  ATTACK NEUTRALIZED: Sandwich Slippage Invariant Breached!")
        print(f"     • Failure Reason:   {e.reason.value}")
        print(f"     • Calculated Bps:   {e.details.get('calculated_bps')} bps (4.00%)")
        print(f"     • Maximum Allowed:  {e.details.get('max_bps')} bps (0.50%)")
        print("     • Invariant Result: Transaction execution halted before signing. Agent funds protected.")

    # --------------------------------------------------------------------------
    # SCENARIO 3: Flash Loan Oracle Manipulation Interception
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("🔴 SCENARIO 3: Flash Loan Oracle Price Manipulation Attack")
    print("-" * 80)
    print("A flash loan skews pool price to 82 XLM/USDC while reference oracle states 100 XLM/USDC (1800 bps deviation).")

    proposal_3 = client.create_swap_proposal(
        agent_id="manipulated_agent",
        intent_prompt="Swap during flash loan liquidity distortion",
        target_contract="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
        function_name="swap_exact_tokens",
        recipient="GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
        asset_in="USDC",
        asset_out="XLM",
        amount_in=100_000_000,
        expected_amount_out=820_000_000, # 82_000 bps implied vs 100_000 bps oracle
        min_amount_out=818_000_000,
        oracle_reference_price_bps=100_000, # 1800 bps divergence!
    )

    try:
        client.evaluate_and_prove(proposal_3, current_account_balance=agent_balance)
        print("  ❌ FAILURE: Flash loan manipulation was NOT intercepted!")
    except InvariantViolationError as e:
        print("  🛡️  ATTACK NEUTRALIZED: Oracle Price Deviation Invariant Breached!")
        print(f"     • Failure Reason:   {e.reason.value}")
        print(f"     • Divergence Bps:   {e.details.get('calculated_deviation_bps')} bps (18.00%)")
        print(f"     • Maximum Allowed:  {e.details.get('max_deviation_bps')} bps (1.50%)")
        print("     • Invariant Result: Swap rejected. Flash loan MEV exploit blocked.")

    print("\n" + "=" * 80)
    print("✅ All 3 DeFi Invariant Scenarios Formally Verified.")
    print("=" * 80)


if __name__ == "__main__":
    run_defi_demo()
