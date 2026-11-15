/* Authorized Protocol Quality Assurance & Formal Invariant Verification */
//! Property and Invariant Verification Test Suite for AetherGuard
//! 
//! Verifies Ramanujan state invariants across multi-enclave consensus:
//! - Journal Hash Chain Immutability
//! - Quorum Threshold Security Boundary
//! - Replay Protection and Nonce Monotonicity

use aetherguard_core::crypto::EnclaveKeyVault;
use aetherguard_core::engine::AetherGuardEngine;
use aetherguard_core::invariants::{InvariantPolicy, ProofOfInvariant};
use aetherguard_core::multisig::{MultiEnclaveAttestationCertificate, ThresholdQuorumPolicy};
use aetherguard_core::proposals::AgentTransactionProposal;
use aetherguard_core::storage::PersistentAuditJournal;

#[test]
fn test_invariant_journal_hash_chain_tamper_detection() {
    let mut journal = PersistentAuditJournal::new(100);

    for i in 1..=5 {
        let proof = ProofOfInvariant {
            proposal_id: format!("prop_{i}"),
            verified_at: 1760000000 + i as i64 * 10,
            spent_amount: 50_000_000 * i as u128,
            remaining_rolling_budget: 1_000_000_000,
            projected_balance: 1_000_000_000,
            invariant_digest_hex: format!("{:064x}", i),
            enclave_signature_hex: None,
        };
        journal.append(&proof).expect("Must append valid proof");
    }

    assert_eq!(journal.len(), 5);
    assert!(journal.verify_chain_integrity(), "Untampered chain must pass");

    // Tamper with record 2 in memory
    journal.records[2].spent_amount = 999_999_999;

    assert!(!journal.verify_chain_integrity(), "Tampered chain must be mathematically rejected");
}

#[test]
fn test_invariant_quorum_threshold_boundary() {
    let vault1 = EnclaveKeyVault::generate();
    let vault2 = EnclaveKeyVault::generate();
    let vault3 = EnclaveKeyVault::generate();

    let pk1 = vault1.public_key_hex();
    let pk2 = vault2.public_key_hex();
    let pk3 = vault3.public_key_hex();

    // Require 2 of 3 quorum
    let policy = ThresholdQuorumPolicy::new(2, vec![pk1.clone(), pk2.clone(), pk3.clone()]);
    let digest = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff";
    let digest_bytes = hex::decode(digest).unwrap();

    // 1 signature: must fail 2-of-3 quorum
    let cert_underflow = MultiEnclaveAttestationCertificate {
        proposal_id: "quorum_prop_01".into(),
        invariant_digest_hex: digest.into(),
        signatures: vec![(pk1.clone(), hex::encode(vault1.sign_attestation(&digest_bytes)))],
    };
    assert!(!policy.verify_quorum(&cert_underflow).unwrap(), "Under-threshold signatures must be rejected");

    // 2 signatures: meets 2-of-3 quorum
    let cert_valid = MultiEnclaveAttestationCertificate {
        proposal_id: "quorum_prop_02".into(),
        invariant_digest_hex: digest.into(),
        signatures: vec![
            (pk1, hex::encode(vault1.sign_attestation(&digest_bytes))),
            (pk2, hex::encode(vault2.sign_attestation(&digest_bytes))),
        ],
    };
    assert!(policy.verify_quorum(&cert_valid).unwrap(), "Threshold quorum must pass when required count is satisfied");
}

#[test]
fn test_invariant_denied_proposals_never_receive_attestation_proof() {
    let policy = InvariantPolicy::builder()
        .max_single_spend(100_000_000) // 10 USDC max single spend
        .max_rolling_window(500_000_000, 3600)
        .min_balance_floor(50_000_000)
        .allow_contract("CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC")
        .allow_recipient("GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z")
        .allow_function("swap_exact_tokens")
        .build();

    let vault = EnclaveKeyVault::generate();
    let mut engine = AetherGuardEngine::new(policy, vault);

    // Proposal exceeding single spend cap
    let proposal = AgentTransactionProposal::new(
        "rogue_agent",
        "Unauthorized excessive drain attempt",
        "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
        "swap_exact_tokens",
        "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
        500_000_000, // 50 USDC > 10 USDC cap
        "USDC",
        1760000000,
    );

    let result = engine.evaluate_and_prove(&proposal, 1_000_000_000);
    assert!(result.is_err(), "Proposal exceeding single spend cap must never receive a signed proof");
}
