# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Unit tests for AetherGuard Integrations (LangChain decorator & CrewAI guard).
"""

import unittest
from aetherguard import AetherGuardClient, InvariantPolicy
from aetherguard.integrations import guard_tool, CrewAIGuard


class TestIntegrations(unittest.TestCase):
    def setUp(self):
        self.policy = InvariantPolicy(
            max_single_spend=100,
            max_rolling_window_spend=500,
            rolling_window_seconds=300,
            min_balance_floor=50,
            allowed_recipients=["G_MERCHANT_CORP"],
        )
        self.client = AetherGuardClient(self.policy)
        self.balance = 1000

    def balance_provider(self):
        return self.balance

    def test_guard_tool_decorator_allowed(self):
        @guard_tool(
            client=self.client,
            balance_provider=self.balance_provider,
            target_contract="stellar-payment",
            function_name="transfer",
        )
        def send_payment(recipient: str, amount: int):
            return f"SENT_{amount}_TO_{recipient}"

        result = send_payment(recipient="G_MERCHANT_CORP", amount=50)
        self.assertEqual(result, "SENT_50_TO_G_MERCHANT_CORP")

    def test_guard_tool_decorator_blocked(self):
        @guard_tool(
            client=self.client,
            balance_provider=self.balance_provider,
            catch_and_return_message=True,
        )
        def send_payment(recipient: str, amount: int):
            return f"SENT_{amount}_TO_{recipient}"

        # Spend 150 > max_single_spend 100 -> should be blocked gracefully
        result = send_payment(recipient="G_MERCHANT_CORP", amount=150)
        self.assertIn("[AetherGuard REJECTED]", result)
        self.assertIn("SINGLE_SPEND_CAP_EXCEEDED", result)

    def test_crewai_guard(self):
        guard = CrewAIGuard(self.client, self.balance_provider)

        # Valid action
        allowed = guard.verify_action(
            action_name="Pay API Subscription",
            recipient="G_MERCHANT_CORP",
            amount=25,
        )
        self.assertTrue(allowed)

        # Invalid recipient
        with self.assertRaises(Exception) as ctx:
            guard.verify_action(
                action_name="Untrusted donation",
                recipient="G_UNKNOWN_ADDRESS",
                amount=10,
            )
        self.assertIn("UNAUTHORIZED_RECIPIENT", str(ctx.exception))

    def test_llamaindex_guard(self):
        from aetherguard.integrations import guard_llamaindex_tool

        @guard_llamaindex_tool(
            client=self.client,
            balance_provider=self.balance_provider,
            catch_and_return_message=True,
        )
        def query_and_pay(recipient: str, amount: int):
            return f"PAID_{amount}_TO_{recipient}"

        # Safe payment
        safe = query_and_pay(recipient="G_MERCHANT_CORP", amount=40)
        self.assertEqual(safe, "PAID_40_TO_G_MERCHANT_CORP")

        # Blocked payment (over cap 100)
        blocked = query_and_pay(recipient="G_MERCHANT_CORP", amount=200)
        self.assertIn("[AetherGuard Invariant Blocked]", blocked)

    def test_autogpt_guard(self):
        from aetherguard.integrations import AutoGPTGuard

        guard = AutoGPTGuard(self.client, self.balance_provider)

        # Compliant command
        ok = guard.intercept_command(
            command_name="execute_settlement",
            arguments={"recipient": "G_MERCHANT_CORP", "amount": 30},
        )
        self.assertTrue(ok)

        # Non-compliant command
        with self.assertRaises(Exception):
            guard.intercept_command(
                command_name="execute_settlement",
                arguments={"recipient": "G_MERCHANT_CORP", "amount": 400},
            )


if __name__ == "__main__":
    unittest.main()
