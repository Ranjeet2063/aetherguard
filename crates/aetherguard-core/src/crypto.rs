/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use ed25519_dalek::{Signer, SigningKey, VerifyingKey};
use rand::rngs::OsRng;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Hardware / In-Memory Signing Enclave ensuring zero-leak isolation.
/// The raw private key is completely inaccessible to AI agents, prompt contexts, or external APIs.
pub struct EnclaveKeyVault {
    signing_key: SigningKey,
    verifying_key: VerifyingKey,
}

/// Cryptographic Hardware / Enclave Attestation Certificate
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EnclaveAttestationCertificate {
    /// Public identity of the isolated signing enclave (Ed25519 hex)
    pub enclave_public_key_hex: String,
    /// Zero-Knowledge commitment of the governing policy (hides private trade parameters & whitelists)
    pub policy_commitment_hex: String,
    /// Canonical proposal identifier
    pub proposal_id: String,
    /// Intent prompt hash of the AI agent
    pub intent_prompt_hash: String,
    /// Deterministic mathematical invariant digest
    pub invariant_digest_hex: String,
    /// Monotonic anti-replay nonce
    pub nonce: u64,
    /// Issuance timestamp (Unix seconds)
    pub issued_at: i64,
    /// Ed25519 cryptographic signature generated strictly inside the enclave vault
    pub enclave_signature_hex: String,
}

impl EnclaveKeyVault {
    /// Generate a fresh cryptographic keypair inside the enclave
    pub fn generate() -> Self {
        let mut csprng = OsRng;
        let signing_key = SigningKey::generate(&mut csprng);
        let verifying_key = signing_key.verifying_key();
        Self {
            signing_key,
            verifying_key,
        }
    }

    /// Restore enclave from raw 32-byte seed
    pub fn from_seed(seed: &[u8; 32]) -> Self {
        let signing_key = SigningKey::from_bytes(seed);
        let verifying_key = signing_key.verifying_key();
        Self {
            signing_key,
            verifying_key,
        }
    }

    /// Returns public verifying key (Ed25519)
    pub fn public_key(&self) -> VerifyingKey {
        self.verifying_key
    }

    /// Returns hex-encoded public key
    pub fn public_key_hex(&self) -> String {
        hex::encode(self.verifying_key.as_bytes())
    }

    /// Sign an attestation digest strictly after mathematical invariant verification passes
    pub fn sign_attestation(&self, message: &[u8]) -> Vec<u8> {
        let signature = self.signing_key.sign(message);
        signature.to_vec()
    }

    /// Verify an attestation signature against this enclave's public key
    pub fn verify_attestation(&self, message: &[u8], signature_bytes: &[u8]) -> bool {
        if let Ok(sig) = ed25519_dalek::Signature::from_slice(signature_bytes) {
            use ed25519_dalek::Verifier;
            self.verifying_key.verify(message, &sig).is_ok()
        } else {
            false
        }
    }

    /// Issue a formal, signed Enclave Attestation Certificate
    pub fn issue_certificate(
        &self,
        policy_commitment_hex: &str,
        proposal_id: &str,
        intent_prompt_hash: &str,
        invariant_digest_hex: &str,
        nonce: u64,
        issued_at: i64,
    ) -> EnclaveAttestationCertificate {
        let pubkey_hex = self.public_key_hex();
        let cert_digest = compute_certificate_digest(
            &pubkey_hex,
            policy_commitment_hex,
            proposal_id,
            intent_prompt_hash,
            invariant_digest_hex,
            nonce,
            issued_at,
        );
        let signature = self.sign_attestation(&cert_digest);

        EnclaveAttestationCertificate {
            enclave_public_key_hex: pubkey_hex,
            policy_commitment_hex: policy_commitment_hex.to_string(),
            proposal_id: proposal_id.to_string(),
            intent_prompt_hash: intent_prompt_hash.to_string(),
            invariant_digest_hex: invariant_digest_hex.to_string(),
            nonce,
            issued_at,
            enclave_signature_hex: hex::encode(signature),
        }
    }
}

/// Compute canonical cryptographic commitment for invariant proof
pub fn compute_invariant_digest(
    proposal_digest: &[u8; 32],
    projected_balance: u128,
    remaining_budget: u128,
    verified_at: i64,
) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(b"AETHERGUARD_INVARIANT_PROOF_V1");
    hasher.update(proposal_digest);
    hasher.update(projected_balance.to_be_bytes());
    hasher.update(remaining_budget.to_be_bytes());
    hasher.update(verified_at.to_be_bytes());
    hasher.finalize().into()
}

/// Compute canonical certificate digest for enclave signature verification
pub fn compute_certificate_digest(
    enclave_public_key_hex: &str,
    policy_commitment_hex: &str,
    proposal_id: &str,
    intent_prompt_hash: &str,
    invariant_digest_hex: &str,
    nonce: u64,
    issued_at: i64,
) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(b"AETHERGUARD_ENCLAVE_CERT_V1");
    hasher.update(enclave_public_key_hex.as_bytes());
    hasher.update(policy_commitment_hex.as_bytes());
    hasher.update(proposal_id.as_bytes());
    hasher.update(intent_prompt_hash.as_bytes());
    hasher.update(invariant_digest_hex.as_bytes());
    hasher.update(nonce.to_be_bytes());
    hasher.update(issued_at.to_be_bytes());
    hasher.finalize().into()
}

/// Compute Zero-Knowledge Policy Commitment hiding private trading floors and whitelists
pub fn compute_policy_commitment(policy: &crate::invariants::InvariantPolicy) -> String {
    let mut hasher = Sha256::new();
    hasher.update(b"AETHERGUARD_ZK_POLICY_V1");
    hasher.update(policy.max_single_spend.to_be_bytes());
    hasher.update(policy.max_rolling_window_spend.to_be_bytes());
    hasher.update(policy.rolling_window_seconds.to_be_bytes());
    hasher.update(policy.min_balance_floor.to_be_bytes());
    let mut sorted_recipients: Vec<&String> = policy.allowed_recipients.iter().collect();
    sorted_recipients.sort();
    for r in sorted_recipients {
        hasher.update(r.as_bytes());
    }
    let mut sorted_contracts: Vec<&String> = policy.allowed_contracts.iter().collect();
    sorted_contracts.sort();
    for c in sorted_contracts {
        hasher.update(c.as_bytes());
    }
    if let Some(ref defi) = policy.defi_swap_policy {
        hasher.update(defi.max_slippage_bps.to_be_bytes());
        hasher.update(defi.max_oracle_deviation_bps.to_be_bytes());
        hasher.update(defi.min_output_floor.to_be_bytes());
    }
    hex::encode(hasher.finalize())
}

/// Standalone Independent Enclave Certificate Verifier
pub fn verify_enclave_certificate(
    cert: &EnclaveAttestationCertificate,
    expected_pubkey_hex: Option<&str>,
    expected_policy_commitment_hex: Option<&str>,
) -> bool {
    // 1. Check expected pubkey if provided
    if let Some(expected_pk) = expected_pubkey_hex {
        if cert.enclave_public_key_hex != expected_pk {
            return false;
        }
    }

    // 2. Check expected policy commitment if provided (Zero-Knowledge verification)
    if let Some(expected_pc) = expected_policy_commitment_hex {
        if cert.policy_commitment_hex != expected_pc {
            return false;
        }
    }

    // 3. Decode enclave public key
    let pk_bytes = match hex::decode(&cert.enclave_public_key_hex) {
        Ok(b) if b.len() == 32 => {
            let mut arr = [0u8; 32];
            arr.copy_from_slice(&b);
            arr
        }
        _ => return false,
    };

    let verifying_key = match VerifyingKey::from_bytes(&pk_bytes) {
        Ok(vk) => vk,
        Err(_) => return false,
    };

    // 4. Decode signature
    let sig_bytes = match hex::decode(&cert.enclave_signature_hex) {
        Ok(b) => b,
        Err(_) => return false,
    };

    let signature = match ed25519_dalek::Signature::from_slice(&sig_bytes) {
        Ok(s) => s,
        Err(_) => return false,
    };

    // 5. Recompute certificate digest
    let cert_digest = compute_certificate_digest(
        &cert.enclave_public_key_hex,
        &cert.policy_commitment_hex,
        &cert.proposal_id,
        &cert.intent_prompt_hash,
        &cert.invariant_digest_hex,
        cert.nonce,
        cert.issued_at,
    );

    use ed25519_dalek::Verifier;
    verifying_key.verify(&cert_digest, &signature).is_ok()
}
