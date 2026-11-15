/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use aetherguard_core::{
    evaluate_proposals_batch, AgentTransactionProposal, AetherGuardEngine, EnclaveKeyVault,
    InvariantPolicy,
};
use std::time::Instant;

#[test]
fn test_high_throughput_concurrency_stress_load() {
    let policy = InvariantPolicy::builder()
        .max_single_spend(1_000_000_000)
        .max_rolling_window(500_000_000_000, 86400)
        .min_balance_floor(50_000_000)
        .allow_recipient("GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z")
        .allow_contract("CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC")
        .allow_function("swap_exact_tokens")
        .build();

    let vault = EnclaveKeyVault::generate();
    let engine = AetherGuardEngine::new(policy, vault);

    let num_proposals = 200;
    let mut proposals = Vec::with_capacity(num_proposals);
    let mut balances = Vec::with_capacity(num_proposals);

    for i in 0..num_proposals {
        let amount = if i % 10 == 0 {
            // Adversarial attempt exceeding single cap
            5_000_000_000
        } else {
            // Valid spend
            50_000_000
        };

        let prop = AgentTransactionProposal::new(
            &format!("agent_{i}"),
            "High-throughput stress batch transfer",
            "CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            "swap_exact_tokens",
            "GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z",
            amount,
            "USDC",
            1760000000 + i as i64,
        );

        proposals.push(prop);
        balances.push(10_000_000_000);
    }

    let start = Instant::now();
    let batch_res = evaluate_proposals_batch(&engine, &proposals, &balances);
    let duration = start.elapsed();

    assert_eq!(batch_res.total_processed, num_proposals);
    // Exactly 20 out of 200 were adversarial (> cap)
    assert_eq!(batch_res.failed_proposal_ids.len(), 20);
    assert_eq!(batch_res.passed_proofs.len(), 180);

    println!(
        "Stress Test: Evaluated {} proposals in {:.2?}. Throughput: {:.0} ops/sec",
        num_proposals,
        duration,
        num_proposals as f64 / duration.as_secs_f64()
    );
}
