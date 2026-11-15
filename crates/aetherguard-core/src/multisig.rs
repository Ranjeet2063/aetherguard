/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use crate::errors::AetherError;
use ed25519_dalek::{Signature, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use std::collections::HashSet;

/// Threshold Multi-Signature policy for high-value autonomous agent proposals.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThresholdQuorumPolicy {
    pub required_signatures: usize,
    pub authorized_enclave_public_keys: HashSet<String>,
}

/// An aggregated multi-enclave cryptographic attestation certificate.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct MultiEnclaveAttestationCertificate {
    pub proposal_id: String,
    pub invariant_digest_hex: String,
    pub signatures: Vec<(String, String)>, // (public_key_hex, signature_hex)
}

impl ThresholdQuorumPolicy {
    pub fn new(required_signatures: usize, authorized_keys: Vec<String>) -> Self {
        Self {
            required_signatures,
            authorized_enclave_public_keys: authorized_keys.into_iter().collect(),
        }
    }

    /// Verify an aggregate multi-signature attestation against the quorum policy.
    pub fn verify_quorum(
        &self,
        cert: &MultiEnclaveAttestationCertificate,
    ) -> Result<bool, AetherError> {
        let digest_bytes = hex::decode(&cert.invariant_digest_hex)
            .map_err(|_| AetherError::ThresholdQuorumFailed("Invalid invariant digest hex".into()))?;

        let mut valid_signatures = 0;
        let mut seen_keys = HashSet::new();

        for (pubkey_hex, sig_hex) in &cert.signatures {
            if !self.authorized_enclave_public_keys.contains(pubkey_hex) {
                continue;
            }
            if seen_keys.contains(pubkey_hex) {
                continue; // Prevent double-counting duplicate signatures
            }

            let pk_bytes = match hex::decode(pubkey_hex) {
                Ok(b) if b.len() == 32 => b,
                _ => continue,
            };
            let sig_bytes = match hex::decode(sig_hex) {
                Ok(b) if b.len() == 64 => b,
                _ => continue,
            };

            let mut pk_arr = [0u8; 32];
            pk_arr.copy_from_slice(&pk_bytes);
            let verifying_key = match VerifyingKey::from_bytes(&pk_arr) {
                Ok(k) => k,
                Err(_) => continue,
            };

            let mut sig_arr = [0u8; 64];
            sig_arr.copy_from_slice(&sig_bytes);
            let signature = Signature::from_bytes(&sig_arr);

            if verifying_key.verify(&digest_bytes, &signature).is_ok() {
                valid_signatures += 1;
                seen_keys.insert(pubkey_hex.clone());
            }
        }

        Ok(valid_signatures >= self.required_signatures)
    }
}
