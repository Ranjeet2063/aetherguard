/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use crate::errors::AetherError;
use crate::invariants::ProofOfInvariant;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::VecDeque;

/// A cryptographically authenticated audit record in the persistent journal.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AuditRecord {
    pub sequence_number: u64,
    pub timestamp: i64,
    pub proposal_id: String,
    pub spent_amount: u128,
    pub projected_balance: u128,
    pub previous_record_hash: String,
    pub current_record_hash: String,
    pub invariant_digest_hex: String,
}

impl AuditRecord {
    pub fn compute_hash(
        sequence_number: u64,
        timestamp: i64,
        proposal_id: &str,
        spent_amount: u128,
        projected_balance: u128,
        previous_record_hash: &str,
        invariant_digest_hex: &str,
    ) -> String {
        let mut hasher = Sha256::new();
        hasher.update(sequence_number.to_be_bytes());
        hasher.update(timestamp.to_be_bytes());
        hasher.update(proposal_id.as_bytes());
        hasher.update(spent_amount.to_be_bytes());
        hasher.update(projected_balance.to_be_bytes());
        hasher.update(previous_record_hash.as_bytes());
        hasher.update(invariant_digest_hex.as_bytes());
        hex::encode(hasher.finalize())
    }
}

/// Persistent, tamper-evident cryptographic audit journal and rolling window storage.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersistentAuditJournal {
    pub genesis_hash: String,
    pub latest_hash: String,
    pub sequence_counter: u64,
    pub records: VecDeque<AuditRecord>,
    pub max_retained_records: usize,
}

impl Default for PersistentAuditJournal {
    fn default() -> Self {
        Self::new(10_000)
    }
}

impl PersistentAuditJournal {
    pub fn new(max_retained_records: usize) -> Self {
        let genesis_hash = hex::encode(Sha256::digest(b"AETHERGUARD_GENESIS_STATE_ROOT_v1"));
        Self {
            latest_hash: genesis_hash.clone(),
            genesis_hash,
            sequence_counter: 0,
            records: VecDeque::new(),
            max_retained_records,
        }
    }

    pub fn len(&self) -> usize {
        self.records.len()
    }

    pub fn is_empty(&self) -> bool {
        self.records.is_empty()
    }

    /// Append a verified proof to the journal, computing the tamper-evident hash chain.
    pub fn append(&mut self, proof: &ProofOfInvariant) -> Result<AuditRecord, AetherError> {
        let sequence_number = self.sequence_counter + 1;
        let record_hash = AuditRecord::compute_hash(
            sequence_number,
            proof.verified_at,
            &proof.proposal_id,
            proof.spent_amount,
            proof.projected_balance,
            &self.latest_hash,
            &proof.invariant_digest_hex,
        );

        let record = AuditRecord {
            sequence_number,
            timestamp: proof.verified_at,
            proposal_id: proof.proposal_id.clone(),
            spent_amount: proof.spent_amount,
            projected_balance: proof.projected_balance,
            previous_record_hash: self.latest_hash.clone(),
            current_record_hash: record_hash.clone(),
            invariant_digest_hex: proof.invariant_digest_hex.clone(),
        };

        self.latest_hash = record_hash;
        self.sequence_counter = sequence_number;
        self.records.push_back(record.clone());

        if self.records.len() > self.max_retained_records {
            self.records.pop_front();
        }

        Ok(record)
    }

    /// Verify the entire cryptographic hash chain for integrity.
    pub fn verify_chain_integrity(&self) -> bool {
        let mut expected_prev = self.genesis_hash.clone();

        for record in &self.records {
            if record.previous_record_hash != expected_prev {
                return false;
            }

            let recomputed = AuditRecord::compute_hash(
                record.sequence_number,
                record.timestamp,
                &record.proposal_id,
                record.spent_amount,
                record.projected_balance,
                &record.previous_record_hash,
                &record.invariant_digest_hex,
            );

            if record.current_record_hash != recomputed {
                return false;
            }

            expected_prev = record.current_record_hash.clone();
        }

        true
    }

    /// Query aggregate spend in a specified time window.
    pub fn window_spend(&self, start_timestamp: i64, end_timestamp: i64) -> u128 {
        self.records
            .iter()
            .filter(|r| r.timestamp >= start_timestamp && r.timestamp <= end_timestamp)
            .map(|r| r.spent_amount)
            .sum()
    }
}
