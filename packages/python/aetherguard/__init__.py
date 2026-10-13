# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Python SDK
Mathematical Invariant Firewall and Financial OS for Autonomous AI Agents.
"""

from .types import InvariantPolicy, AgentTransactionProposal, ProofOfInvariant
from .errors import InvariantViolationError, InvariantFailureReason, AetherGuardError
from .policy import (
    PolicyValidationError,
    validate_policy,
    conservative_policy,
    micropayment_policy,
)
from .client import AetherGuardClient
from .gateway import run_gateway, InvariantGatewayHandler
from .alerts import WebhookAlertManager, AlertLevel

__version__ = "0.2.0"


def __getattr__(name: str):
    if name == "render_dashboard":
        from .monitor import render_dashboard
        return render_dashboard
    raise AttributeError(f"module 'aetherguard' has no attribute '{name}'")


__all__ = [
    "InvariantPolicy",
    "AgentTransactionProposal",
    "ProofOfInvariant",
    "InvariantViolationError",
    "InvariantFailureReason",
    "AetherGuardError",
    "PolicyValidationError",
    "validate_policy",
    "conservative_policy",
    "micropayment_policy",
    "AetherGuardClient",
    "run_gateway",
    "InvariantGatewayHandler",
    "render_dashboard",
    "WebhookAlertManager",
    "AlertLevel",
]
