/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use crate::engine::AetherGuardEngine;
use crate::invariants::ProofOfInvariant;
use crate::proposals::AgentTransactionProposal;

/// Batch result container for high-throughput AI agent swarm proposal evaluation.
#[derive(Debug, Clone)]
pub struct BatchEvaluationResult {
    pub total_processed: usize,
    pub passed_proofs: Vec<ProofOfInvariant>,
    pub failed_proposal_ids: Vec<(String, String)>, // (proposal_id, error_reason)
}

/// Evaluates a collection of independent proposals in parallel using standard library thread scopes.
pub fn evaluate_proposals_batch(
    engine: &AetherGuardEngine,
    proposals: &[AgentTransactionProposal],
    initial_balances: &[u128],
) -> BatchEvaluationResult {
    assert_eq!(
        proposals.len(),
        initial_balances.len(),
        "Proposals and initial_balances must have matching cardinality"
    );

    let mut passed_proofs = Vec::new();
    let mut failed_proposal_ids = Vec::new();

    // Divide workload across chunks
    let chunk_size = (proposals.len() + 3) / 4;
    let chunks: Vec<(&[AgentTransactionProposal], &[u128])> = proposals
        .chunks(chunk_size.max(1))
        .zip(initial_balances.chunks(chunk_size.max(1)))
        .collect();

    let mut thread_results = Vec::new();

    std::thread::scope(|s| {
        let mut handles = Vec::new();

        for (p_chunk, b_chunk) in chunks {
            let engine_clone = engine.clone();
            let handle = s.spawn(move || {
                let mut local_passed = Vec::new();
                let mut local_failed = Vec::new();

                for (prop, bal) in p_chunk.iter().zip(b_chunk.iter()) {
                    let mut local_eng = engine_clone.clone();
                    match local_eng.evaluate_and_prove(prop, *bal) {
                        Ok(proof) => local_passed.push(proof),
                        Err(err) => local_failed.push((prop.proposal_id.clone(), err.to_string())),
                    }
                }

                (local_passed, local_failed)
            });
            handles.push(handle);
        }

        for handle in handles {
            if let Ok(res) = handle.join() {
                thread_results.push(res);
            }
        }
    });

    for (p, f) in thread_results {
        passed_proofs.extend(p);
        failed_proposal_ids.extend(f);
    }

    BatchEvaluationResult {
        total_processed: proposals.len(),
        passed_proofs,
        failed_proposal_ids,
    }
}
