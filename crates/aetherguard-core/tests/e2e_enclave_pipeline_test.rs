/* Authorized Protocol Quality Assurance & Formal Invariant Verification */
//! End-to-End Enclave Pipeline Test Suite for AetherGuard
//! 
//! Tests the full autonomous AI agent transaction verification lifecycle:
//! Ingestion -> Invariant Evaluation -> Hardware Ed25519 Signing -> Persistent Hash Journal -> Telemetry

use aetherguard_core::crypto::{verify_enclave_certificate, EnclaveKeyVault};
use aetherguard_core::engine::AetherGuardEngine;
use aetherguard_core::invariants::InvariantPolicy;
use aetherguard_core::proposals::AgentTransactionProposal;
use aetherguard_core::storage::PersistentAuditJournal;
use aetherguard_core::telemetry::EngineTelemetryMetrics;

#[test]
fn test_e2e_enclave_autonomous_agent_pipeline() {
    let mut telemetry = EngineTelemetryMetrics::new();
    let mut journal = PersistentAuditJournal::new(500);

    let policy = InvariantPolicy::builder()
        .max_single_spend(2_000_000_000) // 200 USDC
        .max_rolling_window(10_000_000_000, 7200) // 1,000 USDC per 2h
        .min_balance_floor(1_000_000_000) // 100 USDC reserve floor
        .allow_contract("CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC")
        .allow_recipient("GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z")
        .allow_function("swap_exact_tokens")
        .build();

    let vault = EnclaveKeyVault::generate();
    let enclave_pubkey = vault.public_key_hex();
    let mut engine = AetherGuardEngine::new(policy, vault);

    let mut current_balance = 20_000_000_000; // 2,000 USDC

    // Execute a pipeline of 10 sequential verified agent transactions
    for seq in 1..=10 {
        let proposal = AgentTransactionProposal::new(
            &format!("autonomous_trader_{:02}", seq),
            "Execute scheduled DCA liquidity rebalance",
            "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            "swap_exact_tokens",
            "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
            500_000_000, // 50 USDC
            "USDC",
            1760000000 + seq as i64 * 60,
        );

        let (proof, cert) = engine
            .evaluate_and_attest(&proposal, current_balance)
            .expect("Evaluation and hardware attestation must succeed");

        assert_eq!(proof.spent_amount, 500_000_000);
        current_balance = proof.projected_balance;

        // Verify cryptographic certificate independently
        let is_cert_valid = verify_enclave_certificate(
            &cert,
            Some(&enclave_pubkey),
            Some(&engine.policy_commitment()),
        );
        assert!(is_cert_valid, "Attestation certificate must pass external verification");

        // Record to immutable audit journal
        let record = journal.append(&proof).expect("Must record proof in journal");
        assert_eq!(record.sequence_number, seq as u64);

        // Record telemetry observation
        telemetry.record_success(std::time::Duration::from_micros(320), proof.spent_amount);
    }

    assert_eq!(journal.len(), 10);
    assert!(journal.verify_chain_integrity(), "Full journal chain must be cryptographically sound");
    assert_eq!(telemetry.total_proposals_evaluated, 10);
    assert_eq!(telemetry.total_proposals_passed, 10);
    assert_eq!(telemetry.total_amount_guarded, 5_000_000_000);
    assert_eq!(current_balance, 15_000_000_000); // 2,000 - (10 * 50) = 1,500 USDC
}
