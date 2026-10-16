"""Focused tests for the LlamaIndex integration."""

import inspect
import unittest

from aetherguard import AetherGuardClient, InvariantPolicy, verify_enclave_certificate
from aetherguard.errors import InvariantViolationError
from aetherguard.integrations import (
    AetherGuardLlamaIndexTool,
    LlamaIndexActionGuard,
    guard_llamaindex_tool,
)


class TestLlamaIndexIntegration(unittest.TestCase):
    def setUp(self):
        policy = InvariantPolicy(
            max_single_spend=100,
            max_rolling_window_spend=500,
            rolling_window_seconds=300,
            min_balance_floor=50,
            allowed_recipients=["G_MERCHANT_CORP"],
        )
        self.client = AetherGuardClient(policy)
        self.balance = 1_000

    def balance_provider(self):
        return self.balance

    def test_decorator_allows_and_preserves_function_metadata(self):
        @guard_llamaindex_tool(self.client, self.balance_provider)
        def pay(recipient: str, amount: int) -> str:
            """Pay a recipient."""
            return f"paid {amount} to {recipient}"

        self.assertEqual(pay.__name__, "pay")
        self.assertEqual(pay.__doc__, "Pay a recipient.")
        self.assertEqual(pay("G_MERCHANT_CORP", 40), "paid 40 to G_MERCHANT_CORP")

    def test_decorator_finds_named_fields_after_leading_tool_arguments(self):
        @guard_llamaindex_tool(self.client, self.balance_provider)
        def fetch(chunk_id: str, recipient: str, amount: int) -> str:
            return chunk_id

        self.assertEqual(fetch("doc-1", "G_MERCHANT_CORP", 40), "doc-1")

    def test_decorator_returns_block_message_or_raises(self):
        @guard_llamaindex_tool(self.client, self.balance_provider)
        def pay(recipient: str, amount: int) -> str:
            return "executed"

        blocked = pay(recipient="G_MERCHANT_CORP", amount=101)
        self.assertIn("[AetherGuard Invariant Blocked]", blocked)
        self.assertIn("SINGLE_SPEND_CAP_EXCEEDED", blocked)

        @guard_llamaindex_tool(
            self.client, self.balance_provider, catch_and_return_message=False
        )
        def strict_pay(recipient: str, amount: int) -> str:
            return "executed"

        with self.assertRaises(InvariantViolationError):
            strict_pay(recipient="G_MERCHANT_CORP", amount=101)

    def test_class_wrapper_gates_execution(self):
        calls = []

        def pay(chunk_id: str, recipient: str, amount: int) -> str:
            calls.append((chunk_id, recipient, amount))
            return "executed"

        guarded = AetherGuardLlamaIndexTool(
            pay, self.client, self.balance_provider, agent_id="test-agent"
        )
        self.assertEqual(guarded("doc-1", "G_MERCHANT_CORP", 40), "executed")
        self.assertEqual(calls, [("doc-1", "G_MERCHANT_CORP", 40)])

        with self.assertRaises(InvariantViolationError):
            guarded("doc-2", "G_MERCHANT_CORP", 101)
        self.assertEqual(len(calls), 1)

    def test_action_guard_preserves_tool_signature_and_metadata(self):
        def pay(chunk_id: str, recipient: str, amount: int) -> str:
            """Pay for a chunk."""
            return chunk_id

        guard = LlamaIndexActionGuard(pay, self.client, self.balance_provider)
        self.assertEqual(inspect.signature(guard), inspect.signature(pay))
        self.assertEqual(guard.__name__, pay.__name__)
        self.assertEqual(guard.__doc__, pay.__doc__)

    def test_action_guard_returns_signed_attestation_and_preserves_tool_output(self):
        calls = []

        def pay(chunk_id: str, recipient: str, amount: int) -> str:
            calls.append(chunk_id)
            return f"paid {chunk_id}"

        guard = LlamaIndexActionGuard(pay, self.client, self.balance_provider)
        result, proof, certificate = guard.execute_with_attestation(
            "doc-1", "G_MERCHANT_CORP", 40
        )
        self.assertEqual(result, "paid doc-1")
        self.assertEqual(proof.status, "APPROVED")
        self.assertEqual(proof.spent_amount, "40")
        self.assertEqual(proof.proposal_id, certificate.proposal_id)
        self.assertEqual(proof.invariant_digest_hex, certificate.invariant_digest_hex)
        self.assertTrue(proof.enclave_signature_hex)
        self.assertTrue(
            verify_enclave_certificate(
                certificate,
                expected_pubkey_hex=self.client.enclave_public_key_hex,
                expected_policy_commitment_hex=self.client.policy_commitment,
            )
        )
        self.assertEqual(guard("doc-2", "G_MERCHANT_CORP", 20), "paid doc-2")
        self.assertEqual(calls, ["doc-1", "doc-2"])

    def test_action_guard_rejection_prevents_tool_side_effects(self):
        calls = []

        def pay(chunk_id: str, recipient: str, amount: int) -> str:
            calls.append(chunk_id)
            return chunk_id

        guard = LlamaIndexActionGuard(pay, self.client, self.balance_provider)
        with self.assertRaises(InvariantViolationError):
            guard.execute_with_attestation("doc-1", "G_MERCHANT_CORP", 101)
        with self.assertRaises(InvariantViolationError):
            guard("doc-2", "G_UNKNOWN", 10)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
