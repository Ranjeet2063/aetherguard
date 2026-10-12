/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use thiserror::Error;

#[derive(Error, Debug, Clone, PartialEq, Eq)]
pub enum AetherError {
    #[error("Mathematical Invariant Violation: Single transaction spend {attempted} exceeds allowed cap {cap}")]
    SingleSpendCapExceeded { attempted: u128, cap: u128 },

    #[error("Mathematical Invariant Violation: Rolling window spend ({current_spent} + {attempted}) exceeds limit {window_limit} within {window_seconds}s")]
    RollingWindowLimitExceeded {
        current_spent: u128,
        attempted: u128,
        window_limit: u128,
        window_seconds: i64,
    },

    #[error("Mathematical Invariant Violation: Account balance floor breached. Current: {current_balance}, After transaction: {projected_balance}, Minimum required floor: {required_floor}")]
    BalanceFloorBreached {
        current_balance: u128,
        projected_balance: u128,
        required_floor: u128,
    },

    #[error("Boundary Security Failure: Target contract '{contract}' is not in the authorized contract whitelist")]
    UnauthorizedContract { contract: String },

    #[error("Boundary Security Failure: Function '{function}' is not authorized on contract '{contract}'")]
    UnauthorizedFunction { contract: String, function: String },

    #[error("Boundary Security Failure: Recipient '{recipient}' is not in the authorized recipient whitelist")]
    UnauthorizedRecipient { recipient: String },

    #[error("Attestation Failure: Cryptographic verification of proposal integrity failed")]
    CryptographicVerificationFailed,

    #[error("Policy Lockout: Agent '{agent_id}' has triggered emergency security pause")]
    EmergencyPauseActive { agent_id: String },

    #[error("Escalation Required: Transaction of {amount} exceeds automated autonomy limit {threshold}. Operator confirmation required.")]
    HumanConfirmationRequired { amount: u128, threshold: u128 },
}
