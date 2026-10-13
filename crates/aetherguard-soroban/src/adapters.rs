/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use aetherguard_core::invariants::{DefiSwapPolicy, InvariantPolicy};
use serde::{Deserialize, Serialize};

/// Error types emitted during DEX & Lending Protocol Adapter verification.
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error, Serialize, Deserialize)]
pub enum ProtocolAdapterError {
    #[error("Target protocol address {0} is not in the verified whitelist")]
    UntrustedProtocolAddress(String),

    #[error("Swap token {0} is not in verified token whitelist")]
    UntrustedToken(String),

    #[error("Calculated slippage {actual_bps} bps exceeds maximum allowable boundary {max_bps} bps")]
    ExcessiveSlippage { actual_bps: u32, max_bps: u32 },

    #[error("Swap output amount {actual} is lower than required safety floor {min_floor}")]
    OutputBelowFloor { actual: u128, min_floor: u128 },

    #[error("Execution price {execution_price} deviates from reference oracle {oracle_price} by {deviation_bps} bps (max: {max_deviation_bps} bps)")]
    OracleDeviationExceeded {
        execution_price: u128,
        oracle_price: u128,
        deviation_bps: u32,
        max_deviation_bps: u32,
    },

    #[error("Blend post-borrow health factor {health_factor_bps} bps breaches minimum safety threshold {min_health_factor_bps} bps (Liquidation Danger)")]
    UnsafeHealthFactor {
        health_factor_bps: u32,
        min_health_factor_bps: u32,
    },

    #[error("Requested single transaction spend {amount} breaches single spend cap {cap}")]
    SingleSpendCapBreached { amount: u128, cap: u128 },

    #[error("Action would breach minimum balance floor {floor}")]
    BalanceFloorBreached { floor: u128 },

    #[error("Protocol is in emergency paused state")]
    ProtocolPaused,
}

// ============================================================================
// 1. SOROSWAP AMM ADAPTER
// ============================================================================

/// Native guard adapter for Soroswap Automated Market Maker (AMM) on Soroban.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SoroswapAdapter {
    pub router_contract: String,
    pub factory_contract: String,
}

impl SoroswapAdapter {
    pub fn new(router: impl Into<String>, factory: impl Into<String>) -> Self {
        Self {
            router_contract: router.into(),
            factory_contract: factory.into(),
        }
    }

    /// Verifies that an AI-proposed `swap_exact_tokens_for_tokens` satisfies all formal invariants:
    /// - Router contract is in policy whitelist.
    /// - Single spend cap is respected.
    /// - Slippage does not exceed max basis points.
    /// - Minimum output floor is maintained.
    pub fn validate_swap(
        &self,
        policy: &InvariantPolicy,
        swap_policy: &DefiSwapPolicy,
        token_in: &str,
        token_out: &str,
        amount_in: u128,
        amount_out_min: u128,
        expected_output: u128,
        reference_oracle_price: Option<u128>,
    ) -> Result<(), ProtocolAdapterError> {
        if policy.is_emergency_paused {
            return Err(ProtocolAdapterError::ProtocolPaused);
        }

        // Verify router contract is whitelisted
        if !policy.allowed_contracts.is_empty() && !policy.allowed_contracts.contains(&self.router_contract) {
            return Err(ProtocolAdapterError::UntrustedProtocolAddress(self.router_contract.clone()));
        }

        // Verify tokens are allowed
        if !policy.allowed_recipients.is_empty() && !policy.allowed_recipients.contains(token_in) {
            return Err(ProtocolAdapterError::UntrustedToken(token_in.to_string()));
        }
        if !policy.allowed_recipients.is_empty() && !policy.allowed_recipients.contains(token_out) {
            return Err(ProtocolAdapterError::UntrustedToken(token_out.to_string()));
        }

        // Enforce single spend cap on input token
        if amount_in > policy.max_single_spend {
            return Err(ProtocolAdapterError::SingleSpendCapBreached {
                amount: amount_in,
                cap: policy.max_single_spend,
            });
        }

        // Verify output floor
        if amount_out_min < swap_policy.min_output_floor {
            return Err(ProtocolAdapterError::OutputBelowFloor {
                actual: amount_out_min,
                min_floor: swap_policy.min_output_floor,
            });
        }

        // Verify slippage tolerance between expected output and min received
        if expected_output > 0 && amount_out_min < expected_output {
            let slippage = expected_output.saturating_sub(amount_out_min);
            let slippage_bps = ((slippage as u128 * 10_000) / expected_output) as u32;
            if slippage_bps > swap_policy.max_slippage_bps {
                return Err(ProtocolAdapterError::ExcessiveSlippage {
                    actual_bps: slippage_bps,
                    max_bps: swap_policy.max_slippage_bps,
                });
            }
        }

        // Optional Oracle TWAP deviation verification (anti-flash-loan / sandwich attack)
        if let Some(oracle_price) = reference_oracle_price {
            if oracle_price > 0 && amount_in > 0 {
                // Effective execution rate = (amount_out_min * 10^7) / amount_in
                let execution_rate = (amount_out_min * 10_000_000) / amount_in;
                let deviation = if execution_rate > oracle_price {
                    execution_rate.saturating_sub(oracle_price)
                } else {
                    oracle_price.saturating_sub(execution_rate)
                };
                let deviation_bps = ((deviation * 10_000) / oracle_price) as u32;
                if deviation_bps > swap_policy.max_oracle_deviation_bps {
                    return Err(ProtocolAdapterError::OracleDeviationExceeded {
                        execution_price: execution_rate,
                        oracle_price,
                        deviation_bps,
                        max_deviation_bps: swap_policy.max_oracle_deviation_bps,
                    });
                }
            }
        }

        Ok(())
    }
}

// ============================================================================
// 2. PHOENIX DEX ORDERBOOK ADAPTER
// ============================================================================

/// Native guard adapter for Phoenix Central Limit Order Book (CLOB) DEX on Soroban.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PhoenixDexAdapter {
    pub orderbook_contract: String,
}

impl PhoenixDexAdapter {
    pub fn new(orderbook: impl Into<String>) -> Self {
        Self {
            orderbook_contract: orderbook.into(),
        }
    }

    /// Verifies an AI agent's limit order placement against price band boundaries.
    pub fn validate_limit_order(
        &self,
        policy: &InvariantPolicy,
        order_amount: u128,
        limit_price: u128,
        oracle_mid_price: u128,
        max_spread_bps: u32,
    ) -> Result<(), ProtocolAdapterError> {
        if policy.is_emergency_paused {
            return Err(ProtocolAdapterError::ProtocolPaused);
        }

        if !policy.allowed_contracts.is_empty() && !policy.allowed_contracts.contains(&self.orderbook_contract) {
            return Err(ProtocolAdapterError::UntrustedProtocolAddress(self.orderbook_contract.clone()));
        }

        if order_amount > policy.max_single_spend {
            return Err(ProtocolAdapterError::SingleSpendCapBreached {
                amount: order_amount,
                cap: policy.max_single_spend,
            });
        }

        // Verify limit order price does not deviate excessively from market mid price
        if oracle_mid_price > 0 {
            let delta = if limit_price > oracle_mid_price {
                limit_price.saturating_sub(oracle_mid_price)
            } else {
                oracle_mid_price.saturating_sub(limit_price)
            };
            let spread_bps = ((delta * 10_000) / oracle_mid_price) as u32;
            if spread_bps > max_spread_bps {
                return Err(ProtocolAdapterError::OracleDeviationExceeded {
                    execution_price: limit_price,
                    oracle_price: oracle_mid_price,
                    deviation_bps: spread_bps,
                    max_deviation_bps: max_spread_bps,
                });
            }
        }

        Ok(())
    }
}

// ============================================================================
// 3. BLEND LENDING PROTOCOL ADAPTER
// ============================================================================

/// Native guard adapter for Blend Protocol (isolated and pooled lending/borrowing) on Soroban.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlendLendingAdapter {
    pub pool_contract: String,
    /// Minimum required health factor in basis points (e.g. 12500 = 1.25x / 125% collateralization)
    pub min_health_factor_bps: u32,
}

impl BlendLendingAdapter {
    pub fn new(pool: impl Into<String>, min_health_factor_bps: u32) -> Self {
        Self {
            pool_contract: pool.into(),
            min_health_factor_bps,
        }
    }

    /// Verifies that borrowing does not breach the safety health factor or liquidation thresholds.
    pub fn validate_borrow(
        &self,
        policy: &InvariantPolicy,
        borrow_amount: u128,
        projected_health_factor_bps: u32,
    ) -> Result<(), ProtocolAdapterError> {
        if policy.is_emergency_paused {
            return Err(ProtocolAdapterError::ProtocolPaused);
        }

        if !policy.allowed_contracts.is_empty() && !policy.allowed_contracts.contains(&self.pool_contract) {
            return Err(ProtocolAdapterError::UntrustedProtocolAddress(self.pool_contract.clone()));
        }

        if borrow_amount > policy.max_single_spend {
            return Err(ProtocolAdapterError::SingleSpendCapBreached {
                amount: borrow_amount,
                cap: policy.max_single_spend,
            });
        }

        // Guarantee that post-borrow health factor strictly respects the minimum safety boundary
        if projected_health_factor_bps < self.min_health_factor_bps {
            return Err(ProtocolAdapterError::UnsafeHealthFactor {
                health_factor_bps: projected_health_factor_bps,
                min_health_factor_bps: self.min_health_factor_bps,
            });
        }

        Ok(())
    }

    /// Verifies collateral withdrawal ensuring agent remains solvent and well-collateralized.
    pub fn validate_withdraw_collateral(
        &self,
        policy: &InvariantPolicy,
        _withdraw_amount: u128,
        projected_health_factor_bps: u32,
        current_treasury_reserve: u128,
    ) -> Result<(), ProtocolAdapterError> {
        if policy.is_emergency_paused {
            return Err(ProtocolAdapterError::ProtocolPaused);
        }

        if current_treasury_reserve < policy.min_balance_floor {
            return Err(ProtocolAdapterError::BalanceFloorBreached {
                floor: policy.min_balance_floor,
            });
        }

        if projected_health_factor_bps < self.min_health_factor_bps {
            return Err(ProtocolAdapterError::UnsafeHealthFactor {
                health_factor_bps: projected_health_factor_bps,
                min_health_factor_bps: self.min_health_factor_bps,
            });
        }

        Ok(())
    }
}

// ============================================================================
// UNIT TESTS & FORMAL SPECIFICATION VERIFICATION
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;

    fn test_policy() -> InvariantPolicy {
        let mut allowed_contracts = HashSet::new();
        allowed_contracts.insert("CB67ROUTER_SOROSWAP_TESTNET".to_string());
        allowed_contracts.insert("CB88ORDERBOOK_PHOENIX_TESTNET".to_string());
        allowed_contracts.insert("CB99POOL_BLEND_TESTNET".to_string());

        let mut allowed_recipients = HashSet::new();
        allowed_recipients.insert("USDC_CONTRACT".to_string());
        allowed_recipients.insert("XLM_CONTRACT".to_string());

        InvariantPolicy {
            max_single_spend: 10_000_000_000, // 1,000 units
            max_rolling_window_spend: 50_000_000_000,
            rolling_window_seconds: 3600,
            min_balance_floor: 5_000_000_000, // 500 units reserve
            allowed_recipients,
            allowed_contracts,
            allowed_functions: HashSet::new(),
            human_confirmation_threshold: None,
            defi_swap_policy: Some(DefiSwapPolicy::default()),
            is_emergency_paused: false,
        }
    }

    #[test]
    fn test_soroswap_valid_swap() {
        let policy = test_policy();
        let swap_policy = DefiSwapPolicy {
            max_slippage_bps: 100, // 1.0%
            max_oracle_deviation_bps: 200,
            min_output_floor: 90_000_000,
        };
        let adapter = SoroswapAdapter::new("CB67ROUTER_SOROSWAP_TESTNET", "CB67FACTORY");

        // Swap 100 USDC -> Expected 990 XLM, min output 985 XLM (~0.5% slippage)
        let result = adapter.validate_swap(
            &policy,
            &swap_policy,
            "USDC_CONTRACT",
            "XLM_CONTRACT",
            1_000_000_000,
            985_000_000,
            990_000_000,
            None,
        );
        assert!(result.is_ok());
    }

    #[test]
    fn test_soroswap_excessive_slippage_blocked() {
        let policy = test_policy();
        let swap_policy = DefiSwapPolicy {
            max_slippage_bps: 50, // 0.5% max
            max_oracle_deviation_bps: 200,
            min_output_floor: 50_000_000,
        };
        let adapter = SoroswapAdapter::new("CB67ROUTER_SOROSWAP_TESTNET", "CB67FACTORY");

        // Expected 1,000, min 950 (5% slippage -> breaches 0.5%)
        let result = adapter.validate_swap(
            &policy,
            &swap_policy,
            "USDC_CONTRACT",
            "XLM_CONTRACT",
            1_000_000_000,
            950_000_000,
            1_000_000_000,
            None,
        );
        assert!(matches!(result, Err(ProtocolAdapterError::ExcessiveSlippage { .. })));
    }

    #[test]
    fn test_blend_borrow_health_factor_enforcement() {
        let policy = test_policy();
        let adapter = BlendLendingAdapter::new("CB99POOL_BLEND_TESTNET", 13000); // 130% min health factor

        // Safe borrow with 1.45x (14500 bps) health factor
        let safe = adapter.validate_borrow(&policy, 500_000_000, 14500);
        assert!(safe.is_ok());

        // Dangerous borrow with 1.15x (11500 bps) health factor -> INTERCEPTED
        let dangerous = adapter.validate_borrow(&policy, 500_000_000, 11500);
        assert!(matches!(dangerous, Err(ProtocolAdapterError::UnsafeHealthFactor { .. })));
    }

    #[test]
    fn test_phoenix_dex_limit_order_spread_guard() {
        let policy = test_policy();
        let adapter = PhoenixDexAdapter::new("CB88ORDERBOOK_PHOENIX_TESTNET");

        // Order price 100 USDC, Oracle Mid 101 USDC (~1% spread, allowed under 300 bps)
        let ok = adapter.validate_limit_order(&policy, 500_000_000, 100_000_000, 101_000_000, 300);
        assert!(ok.is_ok());

        // Order price 80 USDC, Oracle Mid 100 USDC (20% spread -> manipulation blocked)
        let bad = adapter.validate_limit_order(&policy, 500_000_000, 80_000_000, 100_000_000, 300);
        assert!(matches!(bad, Err(ProtocolAdapterError::OracleDeviationExceeded { .. })));
    }
}
