/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use crate::crypto::{
    compute_invariant_digest, compute_policy_commitment, EnclaveAttestationCertificate,
    EnclaveKeyVault,
};
use crate::errors::AetherError;
use crate::invariants::{InvariantPolicy, ProofOfInvariant};
use crate::proposals::AgentTransactionProposal;

/// In-memory sliding window spend event
#[derive(Debug, Clone)]
struct SpendEvent {
    timestamp: i64,
    amount: u128,
}

/// The Central Firewall & Mathematical Invariant Evaluation Engine
pub struct AetherGuardEngine {
    policy: InvariantPolicy,
    vault: EnclaveKeyVault,
    spend_history: Vec<SpendEvent>,
    next_nonce: u64,
}

impl AetherGuardEngine {
    pub fn new(policy: InvariantPolicy, vault: EnclaveKeyVault) -> Self {
        Self {
            policy,
            vault,
            spend_history: Vec::new(),
            next_nonce: 0,
        }
    }

    pub fn policy(&self) -> &InvariantPolicy {
        &self.policy
    }

    pub fn enclave_public_key_hex(&self) -> String {
        self.vault.public_key_hex()
    }

    /// Compute Zero-Knowledge Policy Commitment for the active invariant boundaries
    pub fn policy_commitment(&self) -> String {
        compute_policy_commitment(&self.policy)
    }

    /// Calculate aggregate spend within the rolling window prior to this timestamp
    pub fn calculate_window_spend(&self, now: i64) -> u128 {
        let window_start = now - self.policy.rolling_window_seconds;
        self.spend_history
            .iter()
            .filter(|e| e.timestamp >= window_start && e.timestamp <= now)
            .map(|e| e.amount)
            .sum()
    }

    /// Primary Formal Verification Gate.
    /// Intercepts untrusted AI agent proposal, verifies all mathematical invariants,
    /// and generates a cryptographic proof of compliance if and only if all boundary conditions pass.
    pub fn evaluate_and_prove(
        &mut self,
        proposal: &AgentTransactionProposal,
        current_account_balance: u128,
    ) -> Result<ProofOfInvariant, AetherError> {
        // 1. Emergency Pause Invariant Check
        if self.policy.is_emergency_paused {
            return Err(AetherError::EmergencyPauseActive {
                agent_id: proposal.agent_id.clone(),
            });
        }

        // 2. Single Spend Cap Check
        if proposal.amount > self.policy.max_single_spend {
            return Err(AetherError::SingleSpendCapExceeded {
                attempted: proposal.amount,
                cap: self.policy.max_single_spend,
            });
        }

        // 3. Recipient Whitelist Invariant Check
        if !self.policy.allowed_recipients.is_empty()
            && !self.policy.allowed_recipients.contains(&proposal.recipient)
        {
            return Err(AetherError::UnauthorizedRecipient {
                recipient: proposal.recipient.clone(),
            });
        }

        // 4. Contract Whitelist Invariant Check
        if !self.policy.allowed_contracts.is_empty()
            && !self.policy.allowed_contracts.contains(&proposal.target_contract)
        {
            return Err(AetherError::UnauthorizedContract {
                contract: proposal.target_contract.clone(),
            });
        }

        // 5. Function Whitelist Invariant Check
        if !self.policy.allowed_functions.is_empty()
            && !self.policy.allowed_functions.contains(&proposal.function_name)
        {
            return Err(AetherError::UnauthorizedFunction {
                contract: proposal.target_contract.clone(),
                function: proposal.function_name.clone(),
            });
        }

        // 6. Rolling Window Budget Check
        let current_window_spend = self.calculate_window_spend(proposal.timestamp);
        let projected_window_spend = current_window_spend.saturating_add(proposal.amount);
        if projected_window_spend > self.policy.max_rolling_window_spend {
            return Err(AetherError::RollingWindowLimitExceeded {
                current_spent: current_window_spend,
                attempted: proposal.amount,
                window_limit: self.policy.max_rolling_window_spend,
                window_seconds: self.policy.rolling_window_seconds,
            });
        }

        // 7. Balance Floor Mathematical Invariant Check
        if current_account_balance < proposal.amount {
            return Err(AetherError::BalanceFloorBreached {
                current_balance: current_account_balance,
                projected_balance: 0,
                required_floor: self.policy.min_balance_floor,
            });
        }

        let projected_balance = current_account_balance - proposal.amount;
        if projected_balance < self.policy.min_balance_floor {
            return Err(AetherError::BalanceFloorBreached {
                current_balance: current_account_balance,
                projected_balance,
                required_floor: self.policy.min_balance_floor,
            });
        }

        // 8. Human Escalation Threshold Check
        if let Some(threshold) = self.policy.human_confirmation_threshold {
            if proposal.amount >= threshold {
                return Err(AetherError::HumanConfirmationRequired {
                    amount: proposal.amount,
                    threshold,
                });
            }
        }

        // 9. DeFi AMM Swap & Oracle Protection Invariant Checks
        if let Some(ref swap) = proposal.swap_params {
            let defi_policy = self
                .policy
                .defi_swap_policy
                .as_ref()
                .cloned()
                .unwrap_or_default();

            // 9a. Minimum Output Floor Check
            if swap.min_amount_out < defi_policy.min_output_floor {
                return Err(AetherError::OutputBelowFloor {
                    min_amount_out: swap.min_amount_out,
                    floor: defi_policy.min_output_floor,
                });
            }

            // 9b. Slippage Tolerance Invariant Check (Anti-Sandwich Guard)
            if swap.expected_amount_out > 0 && swap.min_amount_out < swap.expected_amount_out {
                let diff = swap.expected_amount_out - swap.min_amount_out;
                let calculated_bps = (diff.saturating_mul(10_000)) / swap.expected_amount_out;
                if calculated_bps > defi_policy.max_slippage_bps as u128 {
                    return Err(AetherError::ExcessiveSlippage {
                        calculated_bps: calculated_bps as u32,
                        max_bps: defi_policy.max_slippage_bps,
                    });
                }
            }

            // 9c. Oracle Price Deviation Check (Anti-Flash-Loan / Anti-Manipulation Guard)
            if let Some(oracle_price_bps) = swap.oracle_reference_price_bps {
                if swap.amount_in > 0 && oracle_price_bps > 0 {
                    let implied_price_bps = (swap.expected_amount_out.saturating_mul(10_000)) / swap.amount_in;
                    let diff = implied_price_bps.abs_diff(oracle_price_bps as u128);
                    let deviation_bps = (diff.saturating_mul(10_000)) / (oracle_price_bps as u128);
                    if deviation_bps > defi_policy.max_oracle_deviation_bps as u128 {
                        return Err(AetherError::OraclePriceDeviationExceeded {
                            calculated_bps: deviation_bps as u32,
                            max_bps: defi_policy.max_oracle_deviation_bps,
                        });
                    }
                }
            }
        }

        // --- All Invariants Proven Satisfied ---
        // Record spend into sliding window
        self.spend_history.push(SpendEvent {
            timestamp: proposal.timestamp,
            amount: proposal.amount,
        });

        // Prune old events outside 2x window
        let prune_cutoff = proposal.timestamp - (self.policy.rolling_window_seconds * 2);
        self.spend_history.retain(|e| e.timestamp >= prune_cutoff);

        let remaining_rolling_budget = self
            .policy
            .max_rolling_window_spend
            .saturating_sub(projected_window_spend);

        // Compute cryptographic proof digest
        let proposal_digest = proposal.digest();
        let invariant_digest = compute_invariant_digest(
            &proposal_digest,
            projected_balance,
            remaining_rolling_budget,
            proposal.timestamp,
        );

        // Enclave signs the attestation proof
        let signature_bytes = self.vault.sign_attestation(&invariant_digest);

        Ok(ProofOfInvariant {
            proposal_id: proposal.proposal_id.clone(),
            verified_at: proposal.timestamp,
            spent_amount: proposal.amount,
            remaining_rolling_budget,
            projected_balance,
            invariant_digest_hex: hex::encode(invariant_digest),
            enclave_signature_hex: Some(hex::encode(signature_bytes)),
        })
    }

    /// Primary Formal Verification & Enclave Attestation Gate.
    /// Intercepts untrusted AI agent proposal, verifies all mathematical invariants,
    /// and issues both a ProofOfInvariant and an EnclaveAttestationCertificate.
    pub fn evaluate_and_attest(
        &mut self,
        proposal: &AgentTransactionProposal,
        current_account_balance: u128,
    ) -> Result<(ProofOfInvariant, EnclaveAttestationCertificate), AetherError> {
        let proof = self.evaluate_and_prove(proposal, current_account_balance)?;
        self.next_nonce += 1;
        let nonce = self.next_nonce;
        let policy_commitment = self.policy_commitment();

        let certificate = self.vault.issue_certificate(
            &policy_commitment,
            &proof.proposal_id,
            &proposal.intent_prompt_hash,
            &proof.invariant_digest_hex,
            nonce,
            proof.verified_at,
        );

        Ok((proof, certificate))
    }
}
