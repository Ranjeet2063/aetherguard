# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Error Definitions
Mathematical Invariant Violation Exceptions for Autonomous AI Agents.
"""

from enum import Enum
from typing import Any, Optional


class InvariantFailureReason(str, Enum):
    SINGLE_SPEND_CAP_EXCEEDED = "SINGLE_SPEND_CAP_EXCEEDED"
    ROLLING_WINDOW_LIMIT_EXCEEDED = "ROLLING_WINDOW_LIMIT_EXCEEDED"
    BALANCE_FLOOR_BREACHED = "BALANCE_FLOOR_BREACHED"
    UNAUTHORIZED_RECIPIENT = "UNAUTHORIZED_RECIPIENT"
    UNAUTHORIZED_CONTRACT = "UNAUTHORIZED_CONTRACT"
    UNAUTHORIZED_FUNCTION = "UNAUTHORIZED_FUNCTION"
    EMERGENCY_PAUSE_ACTIVE = "EMERGENCY_PAUSE_ACTIVE"
    HUMAN_CONFIRMATION_REQUIRED = "HUMAN_CONFIRMATION_REQUIRED"


class AetherGuardError(Exception):
    """Base exception for all AetherGuard errors."""
    pass


class InvariantViolationError(AetherGuardError):
    """
    Raised when an agent's proposed financial or contract operation violates
    pre-configured mathematical invariants.
    """

    def __init__(
        self,
        reason: InvariantFailureReason,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ):
        self.reason = reason
        self.details = details or {}
        full_message = f"[AetherGuard] Mathematical Invariant Violation ({reason.value}): {message}"
        super().__init__(full_message)
