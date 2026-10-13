# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Core Client for Python
Mathematical Invariant Interceptor and Verifier for Autonomous AI Agents.
"""

import hashlib
import time
from dataclasses import dataclass
from typing import Optional, Any

from .types import InvariantPolicy, AgentTransactionProposal, ProofOfInvariant
from .errors import InvariantViolationError, InvariantFailureReason


@dataclass
class SpendEvent:
    timestamp: int
    amount: int


class AetherGuardClient:
    """
    Client that wraps an agent's financial actions with deterministic invariant proofs.
    """

    def __init__(self, policy: InvariantPolicy):
        self._policy = InvariantPolicy(
            max_single_spend=policy.max_single_spend,
            max_rolling_window_spend=policy.max_rolling_window_spend,
            rolling_window_seconds=policy.rolling_window_seconds,
            min_balance_floor=policy.min_balance_floor,
            allowed_recipients=list(policy.allowed_recipients or []),
            allowed_contracts=list(policy.allowed_contracts or []),
            allowed_functions=list(policy.allowed_functions or []),
            human_confirmation_threshold=policy.human_confirmation_threshold,
            is_emergency_paused=bool(policy.is_emergency_paused),
        )
        self._spend_history: list[SpendEvent] = []

    def get_policy(self) -> InvariantPolicy:
        """Returns the current active invariant policy."""
        return self._policy

    def update_policy(self, **kwargs: Any) -> None:
        """Updates fields of the active invariant policy dynamically."""
        for key, value in kwargs.items():
            if hasattr(self._policy, key):
                setattr(self._policy, key, value)
            else:
                raise AttributeError(f"InvariantPolicy has no attribute '{key}'")

    def reset_history(self) -> None:
        """Clears local spend history (useful for testing)."""
        self._spend_history.clear()

    def calculate_window_spend(self, now: int) -> int:
        """Calculates total atomic spend within the active rolling window."""
        window_start = now - self._policy.rolling_window_seconds
        return sum(
            event.amount
            for event in self._spend_history
            if window_start <= event.timestamp <= now
        )

    def create_proposal(
        self,
        agent_id: str,
        intent_prompt: str,
        target_contract: str,
        function_name: str,
        recipient: str,
        amount: int,
        asset_symbol: str,
        timestamp: Optional[int] = None,
    ) -> AgentTransactionProposal:
        """
        Creates a structured transaction proposal from an AI agent's execution intent.
        """
        ts = int(time.time()) if timestamp is None else timestamp
        hasher = hashlib.sha256()
        hasher.update(agent_id.encode("utf-8"))
        hasher.update(str(amount).encode("utf-8"))
        hasher.update(recipient.encode("utf-8"))
        hasher.update(str(ts).encode("utf-8"))
        proposal_hash = hasher.hexdigest()

        return AgentTransactionProposal(
            proposal_id=f"prop_{proposal_hash[:16]}",
            agent_id=agent_id,
            intent_prompt=intent_prompt,
            target_contract=target_contract,
            function_name=function_name,
            recipient=recipient,
            amount=amount,
            asset_symbol=asset_symbol,
            timestamp=ts,
        )

    def evaluate_and_prove(
        self,
        proposal: AgentTransactionProposal,
        current_account_balance: int,
    ) -> ProofOfInvariant:
        """
        Primary Invariant Gate.
        Intercepts untrusted agent proposals and verifies all mathematical boundary rules.
        """
        # 1. Emergency Pause Check
        if self._policy.is_emergency_paused:
            raise InvariantViolationError(
                InvariantFailureReason.EMERGENCY_PAUSE_ACTIVE,
                f"Emergency kill-switch is currently active for agent {proposal.agent_id}",
                {"agent_id": proposal.agent_id},
            )

        # 2. Single Spend Cap Check
        if proposal.amount > self._policy.max_single_spend:
            raise InvariantViolationError(
                InvariantFailureReason.SINGLE_SPEND_CAP_EXCEEDED,
                f"Attempted spend {proposal.amount} exceeds allowed cap {self._policy.max_single_spend}",
                {
                    "attempted": str(proposal.amount),
                    "cap": str(self._policy.max_single_spend),
                },
            )

        # 3. Recipient Whitelist Check
        if self._policy.allowed_recipients and proposal.recipient not in self._policy.allowed_recipients:
            raise InvariantViolationError(
                InvariantFailureReason.UNAUTHORIZED_RECIPIENT,
                f"Recipient '{proposal.recipient}' is not in the authorized whitelist",
                {"recipient": proposal.recipient},
            )

        # 4. Contract Whitelist Check
        if self._policy.allowed_contracts and proposal.target_contract not in self._policy.allowed_contracts:
            raise InvariantViolationError(
                InvariantFailureReason.UNAUTHORIZED_CONTRACT,
                f"Target contract '{proposal.target_contract}' is not authorized",
                {"contract": proposal.target_contract},
            )

        # 5. Function Whitelist Check
        if self._policy.allowed_functions and proposal.function_name not in self._policy.allowed_functions:
            raise InvariantViolationError(
                InvariantFailureReason.UNAUTHORIZED_FUNCTION,
                f"Function '{proposal.function_name}' is not authorized on '{proposal.target_contract}'",
                {"function": proposal.function_name},
            )

        # 6. Rolling Window Limit Check
        current_window_spend = self.calculate_window_spend(proposal.timestamp)
        projected_window_spend = current_window_spend + proposal.amount
        if projected_window_spend > self._policy.max_rolling_window_spend:
            raise InvariantViolationError(
                InvariantFailureReason.ROLLING_WINDOW_LIMIT_EXCEEDED,
                f"Window spend ({current_window_spend} + {proposal.amount}) exceeds limit {self._policy.max_rolling_window_spend}",
                {
                    "current_spent": str(current_window_spend),
                    "attempted": str(proposal.amount),
                    "window_limit": str(self._policy.max_rolling_window_spend),
                },
            )

        # 7. Balance Floor Invariant Check
        if current_account_balance < proposal.amount:
            raise InvariantViolationError(
                InvariantFailureReason.BALANCE_FLOOR_BREACHED,
                f"Insufficient balance: current {current_account_balance} < spend {proposal.amount}",
                {
                    "current_balance": str(current_account_balance),
                    "attempted": str(proposal.amount),
                },
            )

        projected_balance = current_account_balance - proposal.amount
        if projected_balance < self._policy.min_balance_floor:
            raise InvariantViolationError(
                InvariantFailureReason.BALANCE_FLOOR_BREACHED,
                f"Projected balance {projected_balance} breaches mandatory floor {self._policy.min_balance_floor}",
                {
                    "current_balance": str(current_account_balance),
                    "projected_balance": str(projected_balance),
                    "floor": str(self._policy.min_balance_floor),
                },
            )

        # 8. Human Escalation Check
        if (
            self._policy.human_confirmation_threshold is not None
            and proposal.amount >= self._policy.human_confirmation_threshold
        ):
            raise InvariantViolationError(
                InvariantFailureReason.HUMAN_CONFIRMATION_REQUIRED,
                f"Spend of {proposal.amount} exceeds automated autonomy limit {self._policy.human_confirmation_threshold}. Human signature required.",
                {
                    "amount": str(proposal.amount),
                    "threshold": str(self._policy.human_confirmation_threshold),
                },
            )

        # --- Invariants Formally Verified ---
        self._spend_history.append(
            SpendEvent(timestamp=proposal.timestamp, amount=proposal.amount)
        )

        # Prune old events beyond 2 rolling window cycles
        cutoff = proposal.timestamp - (self._policy.rolling_window_seconds * 2)
        self._spend_history = [e for e in self._spend_history if e.timestamp >= cutoff]

        remaining_rolling_budget = self._policy.max_rolling_window_spend - projected_window_spend

        # Compute deterministic cryptographic proof digest
        proof_hasher = hashlib.sha256()
        proof_hasher.update(proposal.proposal_id.encode("utf-8"))
        proof_hasher.update(str(projected_balance).encode("utf-8"))
        proof_hasher.update(str(remaining_rolling_budget).encode("utf-8"))
        proof_hasher.update(str(proposal.timestamp).encode("utf-8"))
        digest = proof_hasher.hexdigest()

        return ProofOfInvariant(
            proposal_id=proposal.proposal_id,
            verified_at=proposal.timestamp,
            spent_amount=str(proposal.amount),
            remaining_rolling_budget=str(remaining_rolling_budget),
            projected_balance=str(projected_balance),
            invariant_digest_hex=digest,
            status="APPROVED",
        )
