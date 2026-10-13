# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard CrewAI Integration
Deterministic financial safety guards for multi-agent CrewAI pipelines.
"""

from typing import Callable, Any, Optional
from ..client import AetherGuardClient
from ..errors import InvariantViolationError


class CrewAIGuard:
    """
    CrewAI action interceptor that audits autonomous decisions prior to wallet interaction.
    """

    def __init__(
        self,
        client: AetherGuardClient,
        balance_provider: Callable[[], int],
        agent_id: str = "crewai-agent",
    ):
        self.client = client
        self.balance_provider = balance_provider
        self.agent_id = agent_id

    def verify_action(
        self,
        action_name: str,
        recipient: str,
        amount: int,
        target_contract: str = "stellar-payment",
        function_name: str = "transfer",
        asset_symbol: str = "XLM",
    ) -> bool:
        """
        Returns True if the proposed agent action satisfies all mathematical invariants.
        Raises InvariantViolationError if breached.
        """
        proposal = self.client.create_proposal(
            agent_id=self.agent_id,
            intent_prompt=f"CrewAI action: {action_name}",
            target_contract=target_contract,
            function_name=function_name,
            recipient=recipient,
            amount=amount,
            asset_symbol=asset_symbol,
        )
        current_balance = self.balance_provider()
        proof = self.client.evaluate_and_prove(proposal, current_balance)
        return proof.status == "APPROVED"
