# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Unit tests for AetherGuard Python Client and Invariant Verification Engine.
"""

import unittest
from aetherguard import (
    AetherGuardClient,
    InvariantPolicy,
    InvariantViolationError,
    InvariantFailureReason,
    conservative_policy,
    micropayment_policy,
    validate_policy,
    PolicyValidationError,
)


class TestAetherGuardClient(unittest.TestCase):
    def setUp(self):
        self.policy = InvariantPolicy(
            max_single_spend=1000,
            max_rolling_window_spend=3000,
            rolling_window_seconds=60,
            min_balance_floor=500,
            allowed_recipients=["G_ALICE_VALID", "G_BOB_VALID"],
            allowed_contracts=["C_PAYMENT_CONTRACT"],
            allowed_functions=["transfer", "swap"],
            human_confirmation_threshold=2500,
            is_emergency_paused=False,
        )
        self.client = AetherGuardClient(self.policy)

    def test_successful_evaluation(self):
        proposal = self.client.create_proposal(
            agent_id="test_agent_01",
            intent_prompt="Payment to Alice for compute resources",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=500,
            asset_symbol="XLM",
            timestamp=1000,
        )

        proof = self.client.evaluate_and_prove(proposal, current_account_balance=2000)

        self.assertEqual(proof.status, "APPROVED")
        self.assertEqual(proof.spent_amount, "500")
        self.assertEqual(proof.projected_balance, "1500")
        self.assertEqual(proof.remaining_rolling_budget, "2500")
        self.assertTrue(len(proof.invariant_digest_hex) == 64)

    def test_emergency_pause_active(self):
        self.client.update_policy(is_emergency_paused=True)
        proposal = self.client.create_proposal(
            agent_id="test_agent_01",
            intent_prompt="Payment attempt during emergency freeze",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=100,
            asset_symbol="XLM",
            timestamp=1000,
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=2000)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.EMERGENCY_PAUSE_ACTIVE)

    def test_single_spend_cap_exceeded(self):
        proposal = self.client.create_proposal(
            agent_id="test_agent_01",
            intent_prompt="Massive overspend proposal",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=1001,  # max is 1000
            asset_symbol="XLM",
            timestamp=1000,
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=10000)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.SINGLE_SPEND_CAP_EXCEEDED)

    def test_unauthorized_recipient(self):
        proposal = self.client.create_proposal(
            agent_id="test_agent_01",
            intent_prompt="Unauthorized transfer",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_UNAUTHORIZED_MALLORY",
            amount=100,
            asset_symbol="XLM",
            timestamp=1000,
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=5000)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.UNAUTHORIZED_RECIPIENT)

    def test_unauthorized_contract(self):
        proposal = self.client.create_proposal(
            agent_id="test_agent_01",
            intent_prompt="Interact with untrusted dApp",
            target_contract="C_SHADY_PROTOCOL",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=100,
            asset_symbol="XLM",
            timestamp=1000,
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=5000)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.UNAUTHORIZED_CONTRACT)

    def test_unauthorized_function(self):
        proposal = self.client.create_proposal(
            agent_id="test_agent_01",
            intent_prompt="Invoke unauthorized administrative delegatecall",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="drain_vault",
            recipient="G_ALICE_VALID",
            amount=100,
            asset_symbol="XLM",
            timestamp=1000,
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=5000)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.UNAUTHORIZED_FUNCTION)

    def test_rolling_window_limit_exceeded(self):
        # Window limit is 3000 over 60s
        # 1. First spend 900
        prop1 = self.client.create_proposal(
            agent_id="agent_01",
            intent_prompt="Payment 1",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=900,
            asset_symbol="XLM",
            timestamp=100,
        )
        self.client.evaluate_and_prove(prop1, current_account_balance=10000)

        # 2. Second spend 900
        prop2 = self.client.create_proposal(
            agent_id="agent_01",
            intent_prompt="Payment 2",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=900,
            asset_symbol="XLM",
            timestamp=110,
        )
        self.client.evaluate_and_prove(prop2, current_account_balance=9100)

        # 3. Third spend 900 -> total spent is 2700
        prop3 = self.client.create_proposal(
            agent_id="agent_01",
            intent_prompt="Payment 3",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=900,
            asset_symbol="XLM",
            timestamp=120,
        )
        self.client.evaluate_and_prove(prop3, current_account_balance=8200)

        # 4. Fourth spend of 400 would push total to 3100 (> 3000) -> breach!
        prop4 = self.client.create_proposal(
            agent_id="agent_01",
            intent_prompt="Payment 4",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=400,
            asset_symbol="XLM",
            timestamp=130,
        )
        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(prop4, current_account_balance=7300)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.ROLLING_WINDOW_LIMIT_EXCEEDED)

    def test_rolling_window_expiry(self):
        # Window is 60 seconds
        prop1 = self.client.create_proposal(
            agent_id="agent_01",
            intent_prompt="Payment 1",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=1000,
            asset_symbol="XLM",
            timestamp=100,
        )
        self.client.evaluate_and_prove(prop1, current_account_balance=5000)

        # After 70 seconds (timestamp 170), the first spend of 1000 is outside window [110, 170]
        window_spend = self.client.calculate_window_spend(170)
        self.assertEqual(window_spend, 0)

    def test_balance_floor_breached(self):
        # min_balance_floor is 500
        proposal = self.client.create_proposal(
            agent_id="agent_01",
            intent_prompt="Payment that threatens account floor",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=600,
            asset_symbol="XLM",
            timestamp=100,
        )

        # If current balance is 1000, 1000 - 600 = 400 < 500 floor -> Breached!
        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=1000)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.BALANCE_FLOOR_BREACHED)

    def test_human_confirmation_threshold(self):
        # human_confirmation_threshold is 2500, but cap is 1000 in setup.
        # Let's adjust cap to 3000 to test human escalation threshold
        self.client.update_policy(max_single_spend=3000)
        proposal = self.client.create_proposal(
            agent_id="agent_01",
            intent_prompt="Large strategic rebalance",
            target_contract="C_PAYMENT_CONTRACT",
            function_name="transfer",
            recipient="G_ALICE_VALID",
            amount=2600,
            asset_symbol="XLM",
            timestamp=100,
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=10000)
        self.assertEqual(ctx.exception.reason, InvariantFailureReason.HUMAN_CONFIRMATION_REQUIRED)

    def test_policy_validation_rules(self):
        # Negative single spend
        with self.assertRaises(PolicyValidationError):
            validate_policy(InvariantPolicy(
                max_single_spend=-1,
                max_rolling_window_spend=100,
                rolling_window_seconds=60,
                min_balance_floor=0
            ))

        # Single spend > Rolling window spend
        with self.assertRaises(PolicyValidationError):
            validate_policy(InvariantPolicy(
                max_single_spend=500,
                max_rolling_window_spend=200,
                rolling_window_seconds=60,
                min_balance_floor=0
            ))

        # Valid conservative policy helper
        p = conservative_policy()
        self.assertGreater(p.max_rolling_window_spend, p.max_single_spend)


if __name__ == "__main__":
    unittest.main()
