#!/usr/bin/env python3
# Authorized Protocol Quality Assurance & Formal Verification Test Suite
"""
AetherGuard Demo: Zero-Knowledge Invariant Attestation & Local Enclave Verification
Demonstrates cryptographic hardware/enclave certificates, zero-knowledge policy commitments,
and independent verification for autonomous AI agent actions.
"""

import sys
import json
from aetherguard import (
    AetherGuardClient,
    conservative_policy,
    compute_policy_commitment,
    verify_enclave_certificate,
    EnclaveAttestationCertificate,
)


def print_banner():
    print("=" * 80)
    print("🛡️  A E T H E R G U A R D  :  Z K   A T T E S T A T I O N   E N C L A V E  🛡️")
    print("    Hardware / TEE Enclave Attestation & Zero-Knowledge Policy Commitments")
    print("=" * 80)
    print()


def main():
    print_banner()

    # 1. Initialize Invariant Firewall with Conservative Policy
    policy = conservative_policy(
        min_balance_floor=100_000_000,   # 10 XLM reserve floor
        max_single_spend=50_000_000,     # 5 XLM single spend cap
        max_rolling_window_spend=200_000_000, # 20 XLM rolling window cap
        allowed_recipients=["G_AUDITED_ORACLE_VAULT_01", "G_SECURE_TREASURY_02"],
        allowed_contracts=["C_CORE_ESCROW", "C_AMM_ROUTER"],
        allowed_functions=["transfer", "swap_exact_tokens_for_tokens"],
    )
    client = AetherGuardClient(policy)

    print("🔑 Step 1: Enclave Keypair & Zero-Knowledge Policy Commitment")
    print(f"   • Enclave Ed25519 Public Key: {client.enclave_public_key_hex}")
    
    # Compute Zero-Knowledge Policy Commitment
    policy_commitment = client.policy_commitment
    print(f"   • ZK Policy Commitment:       {policy_commitment}")
    print("     ↳ (Hides whitelist addresses & caps while cryptographically binding invariant rules)")
    print()

    # 2. AI Agent Proposes an Approved Treasury Transfer
    print("🤖 Step 2: Autonomous AI Agent Submits Transaction Proposal")
    proposal = client.create_proposal(
        agent_id="autonomous-arbitrage-agent-01",
        intent_prompt="Execute routine treasury rebalancing to audited vault",
        target_contract="C_CORE_ESCROW",
        function_name="transfer",
        recipient="G_AUDITED_ORACLE_VAULT_01",
        amount=15_000_000,  # 1.5 XLM
        asset_symbol="XLM",
    )
    print(f"   • Proposal ID: {proposal.proposal_id}")
    print(f"   • Recipient:   {proposal.recipient}")
    print(f"   • Amount:      {proposal.amount / 10_000_000:.2f} XLM ({proposal.amount} stroops)")
    print()

    # 3. Enclave Evaluates Invariants and Issues Hardware Certificate
    print("🔒 Step 3: Enclave Invariant Evaluation & Attestation Issuance")
    current_balance = 500_000_000  # 50 XLM simulated balance
    proof, certificate = client.evaluate_and_attest(proposal, current_account_balance=current_balance)

    print(f"   • Invariant Verdict:  {proof.status} ✅")
    print(f"   • Invariant Digest:   {proof.invariant_digest_hex}")
    print(f"   • Certificate Nonce:  {certificate.nonce} (Anti-replay sequence)")
    print(f"   • Ed25519 Signature:  {certificate.enclave_signature_hex[:32]}...{certificate.enclave_signature_hex[-16:]}")
    print()

    # 4. Independent 3rd-Party Verification
    print("🔎 Step 4: Independent 3rd-Party Attestation Verification")
    is_valid = verify_enclave_certificate(
        certificate,
        expected_pubkey_hex=client.enclave_public_key_hex,
        expected_policy_commitment_hex=policy_commitment,
    )
    print(f"   • Independent Verification Result: {is_valid} (Signature & Invariant In-Bounds) ✅")
    assert is_valid, "Valid certificate verification failed!"
    print()

    # 5. Tamper Resistance Demonstration
    print("🛑 Step 5: Adversarial Tamper Resistance & Replay Proofs")

    # Scenario A: Corrupted Signature
    corrupted_sig_cert = EnclaveAttestationCertificate(
        enclave_public_key_hex=certificate.enclave_public_key_hex,
        policy_commitment_hex=certificate.policy_commitment_hex,
        proposal_id=certificate.proposal_id,
        intent_prompt_hash=certificate.intent_prompt_hash,
        invariant_digest_hex=certificate.invariant_digest_hex,
        nonce=certificate.nonce,
        issued_at=certificate.issued_at,
        enclave_signature_hex="aa" * 64,
    )
    sig_check = verify_enclave_certificate(corrupted_sig_cert)
    print(f"   [Attack A] Forged Enclave Signature:   Rejected = {not sig_check} 🛡️")
    assert not sig_check, "Forged signature was not rejected!"

    # Scenario B: Tampered Nonce (Replay Attack)
    replayed_nonce_cert = EnclaveAttestationCertificate(
        enclave_public_key_hex=certificate.enclave_public_key_hex,
        policy_commitment_hex=certificate.policy_commitment_hex,
        proposal_id=certificate.proposal_id,
        intent_prompt_hash=certificate.intent_prompt_hash,
        invariant_digest_hex=certificate.invariant_digest_hex,
        nonce=certificate.nonce + 100,  # Stale or forged nonce
        issued_at=certificate.issued_at,
        enclave_signature_hex=certificate.enclave_signature_hex,
    )
    nonce_check = verify_enclave_certificate(replayed_nonce_cert)
    print(f"   [Attack B] Stale / Replayed Nonce:      Rejected = {not nonce_check} 🛡️")
    assert not nonce_check, "Tampered nonce was not rejected!"

    # Scenario C: Fake Policy Commitment (Bypassing Limits)
    fake_policy = conservative_policy()
    fake_policy.max_single_spend = 1_000_000_000  # 100 XLM relaxed cap
    fake_commitment = compute_policy_commitment(fake_policy)
    policy_check = verify_enclave_certificate(
        certificate,
        expected_policy_commitment_hex=fake_commitment,
    )
    print(f"   [Attack C] Rogue Policy Commitment:    Rejected = {not policy_check} 🛡️")
    assert not policy_check, "Rogue policy commitment was not rejected!"
    print()

    print("=" * 80)
    print("✨ ALL ZERO-KNOWLEDGE ENCLAVE ATTESTATION VERIFICATIONS PASSED 100% GREEN! ✨")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
