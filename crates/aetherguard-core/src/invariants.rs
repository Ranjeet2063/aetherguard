/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

/// DeFi AMM Swap & Oracle Protection Invariant boundaries
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DefiSwapPolicy {
    /// Maximum allowable slippage in basis points (e.g. 50 = 0.5%, 100 = 1.0%)
    pub max_slippage_bps: u32,
    /// Maximum allowable divergence from reference TWAP / Oracle price in basis points (e.g. 150 = 1.5%)
    pub max_oracle_deviation_bps: u32,
    /// Absolute minimum output token floor required from any swap
    pub min_output_floor: u128,
}

impl Default for DefiSwapPolicy {
    fn default() -> Self {
        Self {
            max_slippage_bps: 100,           // 1.0% default max slippage
            max_oracle_deviation_bps: 200,   // 2.0% default oracle deviation
            min_output_floor: 1,             // Minimum 1 atomic unit floor
        }
    }
}

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

    /// Optional DeFi Swap & Oracle slippage invariants
    pub defi_swap_policy: Option<DefiSwapPolicy>,

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
    defi_swap_policy: Option<DefiSwapPolicy>,
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

    pub fn defi_swap_policy(mut self, policy: DefiSwapPolicy) -> Self {
        self.defi_swap_policy = Some(policy);
        self
    }

    pub fn max_slippage_bps(mut self, bps: u32) -> Self {
        let mut defi = self.defi_swap_policy.unwrap_or_default();
        defi.max_slippage_bps = bps;
        self.defi_swap_policy = Some(defi);
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
            defi_swap_policy: self.defi_swap_policy,
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
