/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

/// Formal Policy specification defining mathematical boundaries for Autonomous AI agents.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InvariantPolicy {
    /// Maximum allowable spend in a single transaction (in atomic units, e.g. stroops/wei)
    pub max_single_spend: u128,

    /// Maximum aggregate spend permitted within a rolling time window
    pub max_rolling_window_spend: u128,

    /// Duration of the rolling window in seconds (e.g. 3600 for 1 hour, 86400 for 24 hours)
    pub rolling_window_seconds: i64,

    /// Absolute minimum reserve balance that must remain in the account at all times.
    /// Under NO circumstances can any AI transaction reduce balance below this floor.
    pub min_balance_floor: u128,

    /// Whitelist of verified destination addresses/wallets
    pub allowed_recipients: HashSet<String>,

    /// Whitelist of verified smart contract addresses (e.g. verified Soroban DEX contracts)
    pub allowed_contracts: HashSet<String>,

    /// Whitelist of permitted function calls on allowed contracts
    pub allowed_functions: HashSet<String>,

    /// Spending threshold that triggers automated escalation to human operator
    pub human_confirmation_threshold: Option<u128>,

    /// Emergency kill-switch state
    pub is_emergency_paused: bool,
}

impl InvariantPolicy {
    pub fn builder() -> InvariantPolicyBuilder {
        InvariantPolicyBuilder::default()
    }
}

#[derive(Default)]
pub struct InvariantPolicyBuilder {
    max_single_spend: u128,
    max_rolling_window_spend: u128,
    rolling_window_seconds: i64,
    min_balance_floor: u128,
    allowed_recipients: HashSet<String>,
    allowed_contracts: HashSet<String>,
    allowed_functions: HashSet<String>,
    human_confirmation_threshold: Option<u128>,
    is_emergency_paused: bool,
}

impl InvariantPolicyBuilder {
    pub fn max_single_spend(mut self, val: u128) -> Self {
        self.max_single_spend = val;
        self
    }

    pub fn max_rolling_window(mut self, limit: u128, window_seconds: i64) -> Self {
        self.max_rolling_window_spend = limit;
        self.rolling_window_seconds = window_seconds;
        self
    }

    pub fn min_balance_floor(mut self, floor: u128) -> Self {
        self.min_balance_floor = floor;
        self
    }

    pub fn allow_recipient(mut self, recipient: impl Into<String>) -> Self {
        self.allowed_recipients.insert(recipient.into());
        self
    }

    pub fn allow_contract(mut self, contract: impl Into<String>) -> Self {
        self.allowed_contracts.insert(contract.into());
        self
    }

    pub fn allow_function(mut self, func: impl Into<String>) -> Self {
        self.allowed_functions.insert(func.into());
        self
    }

    pub fn human_threshold(mut self, threshold: u128) -> Self {
        self.human_confirmation_threshold = Some(threshold);
        self
    }

    pub fn build(self) -> InvariantPolicy {
        InvariantPolicy {
            max_single_spend: self.max_single_spend,
            max_rolling_window_spend: self.max_rolling_window_spend,
            rolling_window_seconds: self.rolling_window_seconds,
            min_balance_floor: self.min_balance_floor,
            allowed_recipients: self.allowed_recipients,
            allowed_contracts: self.allowed_contracts,
            allowed_functions: self.allowed_functions,
            human_confirmation_threshold: self.human_confirmation_threshold,
            is_emergency_paused: self.is_emergency_paused,
        }
    }
}

/// Cryptographic attestation proof emitted upon successful invariant verification.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProofOfInvariant {
    pub proposal_id: String,
    pub verified_at: i64,
    pub spent_amount: u128,
    pub remaining_rolling_budget: u128,
    pub projected_balance: u128,
    pub invariant_digest_hex: String,
    pub enclave_signature_hex: Option<String>,
}
