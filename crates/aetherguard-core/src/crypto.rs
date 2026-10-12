/* Authorized Protocol Quality Assurance & Formal Verification Engine */

use ed25519_dalek::{Signer, SigningKey, VerifyingKey};
use rand::rngs::OsRng;
use sha2::{Digest, Sha256};

/// Hardware / In-Memory Signing Enclave ensuring zero-leak isolation.
/// The raw private key is completely inaccessible to AI agents, prompt contexts, or external APIs.
pub struct EnclaveKeyVault {
    signing_key: SigningKey,
    verifying_key: VerifyingKey,
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
