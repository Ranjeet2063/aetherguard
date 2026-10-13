# Authorized Protocol Quality Assurance & Formal Verification Test Suite
"""
Unit test suite for Zero-Knowledge Invariant Attestation & Local Enclave (TEE) Verification.
Verifies Ed25519 hardware/enclave certificates, zero-knowledge policy commitments, anti-replay nonces,
and gateway verification routes.
"""

import unittest
import urllib.request
import json
import time

from aetherguard import (
    AetherGuardClient,
    conservative_policy,
    compute_policy_commitment,
    verify_enclave_certificate,
    EnclaveAttestationCertificate,
    run_gateway,
)


class TestZKAttestationAndEnclave(unittest.TestCase):
    def setUp(self):
        self.policy = conservative_policy()
        self.client = AetherGuardClient(self.policy)

    def test_certificate_generation_and_ed25519_verification(self):
        proposal = self.client.create_proposal(
            agent_id="attestation-test-agent",
            intent_prompt="Transfer 50 XLM to verified recipient",
            target_contract="C_CORE_ESCROW",
            function_name="transfer",
            recipient="G_AUDITED_VENDOR_VAULT_01",
            amount=500_000,
            asset_symbol="XLM",
        )

        proof, cert = self.client.evaluate_and_attest(
            proposal,
            current_account_balance=500_000_000,
        )

        self.assertEqual(proof.status, "APPROVED")
        self.assertEqual(cert.proposal_id, proposal.proposal_id)
        self.assertEqual(cert.nonce, 1)
        self.assertEqual(cert.enclave_public_key_hex, self.client.enclave_public_key_hex)
        self.assertEqual(cert.policy_commitment_hex, self.client.policy_commitment)

        # Independent verification with matching parameters
        self.assertTrue(verify_enclave_certificate(cert))
        self.assertTrue(
            verify_enclave_certificate(
                cert,
                expected_pubkey_hex=self.client.enclave_public_key_hex,
                expected_policy_commitment_hex=self.client.policy_commitment,
            )
        )

    def test_policy_commitment_determinism_and_hiding(self):
        commitment_1 = compute_policy_commitment(self.policy)
        commitment_2 = compute_policy_commitment(self.policy)
        self.assertEqual(commitment_1, commitment_2)

        # Modifying a policy parameter changes commitment deterministically
        modified_policy = conservative_policy()
        modified_policy.max_single_spend += 1000
        commitment_modified = compute_policy_commitment(modified_policy)
        self.assertNotEqual(commitment_1, commitment_modified)

        proposal = self.client.create_proposal(
            agent_id="test-agent",
            intent_prompt="Test commit",
            target_contract="C_CORE_ESCROW",
            function_name="transfer",
            recipient="G_AUDITED_VENDOR_VAULT_01",
            amount=100,
            asset_symbol="XLM",
        )
        _, cert = self.client.evaluate_and_attest(proposal, current_account_balance=500_000_000)

        # Verifying with mismatching expected policy commitment must fail
        self.assertFalse(
            verify_enclave_certificate(
                cert,
                expected_policy_commitment_hex=commitment_modified,
            )
        )

    def test_tampered_signature_rejected(self):
        proposal = self.client.create_proposal(
            agent_id="test-agent",
            intent_prompt="Tamper test",
            target_contract="C_CORE_ESCROW",
            function_name="transfer",
            recipient="G_AUDITED_VENDOR_VAULT_01",
            amount=100,
            asset_symbol="XLM",
        )
        _, cert = self.client.evaluate_and_attest(proposal, current_account_balance=500_000_000)

        # Tamper signature hex
        bad_sig = "00" * 64
        tampered_cert = EnclaveAttestationCertificate(
            enclave_public_key_hex=cert.enclave_public_key_hex,
            policy_commitment_hex=cert.policy_commitment_hex,
            proposal_id=cert.proposal_id,
            intent_prompt_hash=cert.intent_prompt_hash,
            invariant_digest_hex=cert.invariant_digest_hex,
            nonce=cert.nonce,
            issued_at=cert.issued_at,
            enclave_signature_hex=bad_sig,
        )
        self.assertFalse(verify_enclave_certificate(tampered_cert))

    def test_tampered_certificate_digest_fields_rejected(self):
        proposal = self.client.create_proposal(
            agent_id="test-agent",
            intent_prompt="Tamper digest fields",
            target_contract="C_CORE_ESCROW",
            function_name="transfer",
            recipient="G_AUDITED_VENDOR_VAULT_01",
            amount=100,
            asset_symbol="XLM",
        )
        _, cert = self.client.evaluate_and_attest(proposal, current_account_balance=500_000_000)

        # Tampering nonce
        tampered_nonce = EnclaveAttestationCertificate(
            enclave_public_key_hex=cert.enclave_public_key_hex,
            policy_commitment_hex=cert.policy_commitment_hex,
            proposal_id=cert.proposal_id,
            intent_prompt_hash=cert.intent_prompt_hash,
            invariant_digest_hex=cert.invariant_digest_hex,
            nonce=cert.nonce + 999,
            issued_at=cert.issued_at,
            enclave_signature_hex=cert.enclave_signature_hex,
        )
        self.assertFalse(verify_enclave_certificate(tampered_nonce))

        # Tampering invariant digest
        tampered_digest = EnclaveAttestationCertificate(
            enclave_public_key_hex=cert.enclave_public_key_hex,
            policy_commitment_hex=cert.policy_commitment_hex,
            proposal_id=cert.proposal_id,
            intent_prompt_hash=cert.intent_prompt_hash,
            invariant_digest_hex="deadbeef" * 8,
            nonce=cert.nonce,
            issued_at=cert.issued_at,
            enclave_signature_hex=cert.enclave_signature_hex,
        )
        self.assertFalse(verify_enclave_certificate(tampered_digest))

    def test_anti_replay_nonce_increments(self):
        nonces = []
        for i in range(3):
            prop = self.client.create_proposal(
                agent_id="test-agent",
                intent_prompt=f"Transfer sequence {i}",
                target_contract="C_CORE_ESCROW",
                function_name="transfer",
                recipient="G_AUDITED_VENDOR_VAULT_01",
                amount=50,
                asset_symbol="XLM",
            )
            _, cert = self.client.evaluate_and_attest(prop, current_account_balance=500_000_000)
            nonces.append(cert.nonce)

        self.assertEqual(nonces, [1, 2, 3])

    def test_gateway_verification_endpoint(self):
        import socket
        import threading

        # Find free port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("", 0))
        port = s.getsockname()[1]
        s.close()

        server = run_gateway(host="127.0.0.1", port=port, policy=conservative_policy())
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.1)

        try:
            # 1. Fetch enclave public key and policy commitment
            pubkey_req = urllib.request.Request(f"http://127.0.0.1:{port}/attestation/pubkey")
            with urllib.request.urlopen(pubkey_req) as resp:
                pubkey_data = json.loads(resp.read().decode())
                self.assertIn("enclave_public_key_hex", pubkey_data)
                self.assertIn("policy_commitment_hex", pubkey_data)
                enclave_pubkey = pubkey_data["enclave_public_key_hex"]

            # 2. Evaluate transaction and receive certificate
            eval_payload = {
                "agent_id": "test-agent-gw",
                "recipient": "G_AUDITED_VENDOR_VAULT_01",
                "amount": 250,
                "target_contract": "C_CORE_ESCROW",
            }
            eval_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/evaluate",
                data=json.dumps(eval_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(eval_req) as resp:
                eval_data = json.loads(resp.read().decode())
                self.assertEqual(eval_data["status"], "APPROVED")
                self.assertIn("certificate", eval_data)
                cert_data = eval_data["certificate"]

            # 3. Verify valid certificate via POST /verify
            verify_payload = {
                "certificate": cert_data,
                "expected_pubkey_hex": enclave_pubkey,
            }
            verify_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/verify",
                data=json.dumps(verify_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(verify_req) as resp:
                verify_res = json.loads(resp.read().decode())
                self.assertTrue(verify_res["is_valid"])
                self.assertEqual(verify_res["proposal_id"], cert_data["proposal_id"])

            # 4. Tampered certificate via POST /verify should return 400
            tampered_cert_payload = {
                "certificate": {**cert_data, "nonce": 99999},
                "expected_pubkey_hex": enclave_pubkey,
            }
            tampered_req = urllib.request.Request(
                f"http://127.0.0.1:{port}/verify",
                data=json.dumps(tampered_cert_payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(tampered_req) as resp:
                    self.fail("Expected HTTP 400 for tampered certificate")
            except urllib.error.HTTPError as err:
                self.assertEqual(err.code, 400)
                err_res = json.loads(err.read().decode())
                self.assertFalse(err_res["is_valid"])

        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
