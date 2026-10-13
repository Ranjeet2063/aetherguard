# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
Unit tests for AetherGuard DeFi Slippage & AMM Flash Loan / Oracle Protection Guard.
"""

import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from aetherguard import (
    AetherGuardClient,
    InvariantPolicy,
    DefiSwapPolicy,
    SwapParameters,
    InvariantViolationError,
    InvariantFailureReason,
    defi_arbitrage_policy,
    run_gateway,
)


class TestDefiGuard(unittest.TestCase):
    def setUp(self):
        self.policy = InvariantPolicy(
            max_single_spend=1_000_000_000,       # 100 XLM
            max_rolling_window_spend=5_000_000_000, # 500 XLM
            rolling_window_seconds=3600,
            min_balance_floor=50_000_000,          # 5 XLM
            allowed_recipients=["GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4"],
            allowed_contracts=["CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC"],
            defi_swap_policy=DefiSwapPolicy(
                max_slippage_bps=50,              # 0.5% max slippage
                max_oracle_deviation_bps=150,     # 1.5% max oracle deviation
                min_output_floor=1_000_000,       # 0.1 tokens minimum
            ),
        )
        self.client = AetherGuardClient(self.policy)

    def test_valid_swap_within_slippage_tolerance(self):
        # Swap 10 USDC (100_000_000 stroops).
        # Expected out: 100 XLM (1_000_000_000 stroops).
        # Min out: 99.6 XLM (996_000_000 stroops) -> 40 bps slippage <= 50 bps limit.
        proposal = self.client.create_swap_proposal(
            agent_id="arbitrage_bot_1",
            intent_prompt="Execute Soroswap USDC -> XLM arbitrage swap",
            target_contract="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            function_name="swap_exact_tokens",
            recipient="GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
            asset_in="USDC",
            asset_out="XLM",
            amount_in=100_000_000,
            expected_amount_out=1_000_000_000,
            min_amount_out=996_000_000,
            oracle_reference_price_bps=100_000, # 10.0 XLM/USDC
        )

        proof = self.client.evaluate_and_prove(proposal, current_account_balance=500_000_000)
        self.assertEqual(proof.status, "APPROVED")
        self.assertEqual(proof.spent_amount, "100000000")
        self.assertTrue(len(proof.invariant_digest_hex) > 0)

    def test_sandwich_attack_excessive_slippage_blocked(self):
        # MEV bot sandwich attack attempts to force 5.0% (500 bps) slippage tolerance
        proposal = self.client.create_swap_proposal(
            agent_id="tricked_bot",
            intent_prompt="Swap USDC with manipulated high slippage tolerance",
            target_contract="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            function_name="swap_exact_tokens",
            recipient="GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
            asset_in="USDC",
            asset_out="XLM",
            amount_in=100_000_000,
            expected_amount_out=1_000_000_000,
            min_amount_out=950_000_000, # 500 bps (5.0%) > 50 bps limit!
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=500_000_000)

        self.assertEqual(ctx.exception.reason, InvariantFailureReason.EXCESSIVE_SLIPPAGE)
        self.assertEqual(ctx.exception.details["calculated_bps"], "500")
        self.assertEqual(ctx.exception.details["max_bps"], "50")

    def test_flash_loan_oracle_manipulation_blocked(self):
        # Spot price in pool is distorted by a flash loan to 80 XLM / 10 USDC (80_000 bps)
        # Reference oracle indicates fair market price is 100_000 bps (10 XLM/USDC).
        # Implied deviation is 20% (2000 bps) > 1.5% (150 bps) allowable limit.
        proposal = self.client.create_swap_proposal(
            agent_id="skewed_pool_bot",
            intent_prompt="Swap USDC on manipulated pool",
            target_contract="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            function_name="swap_exact_tokens",
            recipient="GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
            asset_in="USDC",
            asset_out="XLM",
            amount_in=100_000_000,
            expected_amount_out=800_000_000,
            min_amount_out=798_000_000,
            oracle_reference_price_bps=100_000, # 20% divergence!
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=500_000_000)

        self.assertEqual(ctx.exception.reason, InvariantFailureReason.ORACLE_PRICE_DEVIATION_EXCEEDED)
        self.assertEqual(ctx.exception.details["calculated_deviation_bps"], "2000")
        self.assertEqual(ctx.exception.details["max_deviation_bps"], "150")

    def test_output_below_floor_blocked(self):
        # Minimum acceptable output breaches absolute policy floor
        proposal = self.client.create_swap_proposal(
            agent_id="micro_swap_bot",
            intent_prompt="Swap negligible dust",
            target_contract="CDLZFC3SYJYDZT7K67VZ75HPJVIEUVNIXF47ZG2FB2RMQQVU2HHGCYSC",
            function_name="swap_exact_tokens",
            recipient="GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
            asset_in="USDC",
            asset_out="XLM",
            amount_in=100_000,
            expected_amount_out=500_000,
            min_amount_out=499_000, # Below 1_000_000 floor!
        )

        with self.assertRaises(InvariantViolationError) as ctx:
            self.client.evaluate_and_prove(proposal, current_account_balance=500_000_000)

        self.assertEqual(ctx.exception.reason, InvariantFailureReason.OUTPUT_BELOW_FLOOR)

    def test_defi_arbitrage_preset_policy(self):
        policy = defi_arbitrage_policy(max_slippage_bps=30, max_oracle_deviation_bps=100)
        self.assertIsNotNone(policy.defi_swap_policy)
        self.assertEqual(policy.defi_swap_policy.max_slippage_bps, 30)
        self.assertEqual(policy.defi_swap_policy.max_oracle_deviation_bps, 100)


class TestGatewayDefiIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = InvariantPolicy(
            max_single_spend=500_000_000,
            max_rolling_window_spend=1_000_000_000,
            rolling_window_seconds=3600,
            min_balance_floor=50_000_000,
            defi_swap_policy=DefiSwapPolicy(
                max_slippage_bps=50,
                max_oracle_deviation_bps=200,
                min_output_floor=1,
            ),
        )
        cls.server = run_gateway(host="127.0.0.1", port=0, policy=cls.policy)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_gateway_evaluates_swap_and_blocks_sandwich(self):
        # 1. Valid swap passes
        url = f"http://127.0.0.1:{self.port}/evaluate"
        valid_payload = {
            "agent_id": "phoenix_agent",
            "amount": 50_000_000,
            "recipient": "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
            "swap_params": {
                "asset_in": "USDC",
                "asset_out": "XLM",
                "amount_in": 50_000_000,
                "expected_amount_out": 500_000_000,
                "min_amount_out": 498_000_000, # 40 bps slippage <= 50 bps
            },
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(valid_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as res:
            self.assertEqual(res.status, 200)
            data = json.loads(res.read().decode("utf-8"))
            self.assertEqual(data["status"], "APPROVED")

        # 2. Sandwich attack proposal is intercepted and blocked with 403 Forbidden
        attack_payload = {
            "agent_id": "exploited_agent",
            "amount": 50_000_000,
            "recipient": "GBBQSMW3W6H557ZTRG36X2WCKW3ZTXQ33TIX4X4C642N5Y5S2G2T75S4",
            "swap_params": {
                "asset_in": "USDC",
                "asset_out": "XLM",
                "amount_in": 50_000_000,
                "expected_amount_out": 500_000_000,
                "min_amount_out": 450_000_000, # 1000 bps (10% slippage!)
            },
        }
        req2 = urllib.request.Request(
            url,
            data=json.dumps(attack_payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req2)
            self.fail("Expected 403 Forbidden for excessive slippage")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)
            data = json.loads(e.read().decode("utf-8"))
            self.assertEqual(data["status"], "BLOCKED")
            self.assertEqual(data["reason"], "EXCESSIVE_SLIPPAGE")


if __name__ == "__main__":
    unittest.main()
