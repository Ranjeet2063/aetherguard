/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use serde::{Deserialize, Serialize};

/// Protocol Fee & Settlement Configuration.
/// Routes the 0.05% protocol micro-fee directly to the protocol founder treasury.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProtocolFeeConfig {
    /// Recipient account address for protocol fees
    pub fee_treasury_address: String,
    /// Basis points (5 = 0.05%, 10 = 0.10%)
    pub fee_basis_points: u32,
    /// Lifetime volume processed through the protocol
    pub total_volume_settled: u128,
    /// Lifetime protocol fees accrued
    pub total_fees_collected: u128,
}

impl ProtocolFeeConfig {
    pub fn new(treasury: impl Into<String>) -> Self {
        Self {
            fee_treasury_address: treasury.into(),
            fee_basis_points: 5, // 0.05% standard micro-fee
            total_volume_settled: 0,
            total_fees_collected: 0,
        }
    }

    /// Calculate protocol micro-fee for a given settlement amount
    pub fn calculate_fee(&self, amount: u128) -> u128 {
        (amount * self.fee_basis_points as u128) / 10_000
    }

    /// Settle a transaction, recording volume and updating accrued fee revenue
    pub fn record_settlement(&mut self, amount: u128) -> u128 {
        let fee = self.calculate_fee(amount);
        self.total_volume_settled = self.total_volume_settled.saturating_add(amount);
        self.total_fees_collected = self.total_fees_collected.saturating_add(fee);
        fee
    }
}

/// Soroban On-Chain Policy State Representation
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AetherSorobanPolicyState {
    pub operator_address: String,
    pub enclave_public_key_hex: String,
    pub max_single_spend: u128,
    pub max_rolling_window_spend: u128,
    pub rolling_window_seconds: i64,
    pub min_balance_floor: u128,
    pub is_paused: bool,
    pub fee_config: ProtocolFeeConfig,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_protocol_fee_calculation() {
        let mut config = ProtocolFeeConfig::new("GDQP2KPQGKIHYJGXNUIYOMHARUARCA7DJT5FO2FFOOKY3IF53Q7L5G6Z");

        // 10,000 USDC volume -> 0.05% = 5 USDC
        let volume = 100_000_000_000; // 10,000 USDC (7 decimals)
        let fee = config.record_settlement(volume);

        assert_eq!(fee, 50_000_000); // 5 USDC (0.05%)
        assert_eq!(config.total_volume_settled, volume);
        assert_eq!(config.total_fees_collected, 50_000_000);
    }
}
