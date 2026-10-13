# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Policy Module
Preconfigured mathematical policy presets and formal validation logic.
"""

from typing import Optional
from .types import InvariantPolicy


class PolicyValidationError(ValueError):
    """Raised when an InvariantPolicy contains mathematically inconsistent parameters."""
    pass


def validate_policy(policy: InvariantPolicy) -> None:
    """
    Formally validates the mathematical invariants of a policy configuration:
    1. All caps and floors must be non-negative.
    2. Single spend cap cannot exceed the rolling window spend cap.
    3. Rolling window duration must be strictly positive.
    4. If human confirmation threshold is specified, it must be > 0.
    """
    if policy.max_single_spend < 0:
        raise PolicyValidationError("max_single_spend cannot be negative")
    if policy.max_rolling_window_spend < 0:
        raise PolicyValidationError("max_rolling_window_spend cannot be negative")
    if policy.min_balance_floor < 0:
        raise PolicyValidationError("min_balance_floor cannot be negative")
    if policy.rolling_window_seconds <= 0:
        raise PolicyValidationError("rolling_window_seconds must be strictly positive (> 0)")
    if policy.max_single_spend > policy.max_rolling_window_spend:
        raise PolicyValidationError(
            f"max_single_spend ({policy.max_single_spend}) cannot exceed max_rolling_window_spend ({policy.max_rolling_window_spend})"
        )
    if policy.human_confirmation_threshold is not None:
        if policy.human_confirmation_threshold <= 0:
            raise PolicyValidationError("human_confirmation_threshold must be strictly positive (> 0)")


def conservative_policy(
    min_balance_floor: int = 100_000_000,  # 10 XLM in stroops (1 XLM = 10^7 stroops)
    max_single_spend: int = 50_000_000,    # 5 XLM
    max_rolling_window_spend: int = 200_000_000, # 20 XLM
    rolling_window_seconds: int = 86400,   # 24 hours
    allowed_recipients: Optional[list[str]] = None,
    allowed_contracts: Optional[list[str]] = None,
    allowed_functions: Optional[list[str]] = None,
) -> InvariantPolicy:
    """
    Creates a conservative security policy suited for autonomous agents with tight limits.
    """
    p = InvariantPolicy(
        max_single_spend=max_single_spend,
        max_rolling_window_spend=max_rolling_window_spend,
        rolling_window_seconds=rolling_window_seconds,
        min_balance_floor=min_balance_floor,
        allowed_recipients=allowed_recipients or [],
        allowed_contracts=allowed_contracts or [],
        allowed_functions=allowed_functions or [],
    )
    validate_policy(p)
    return p


def micropayment_policy(
    min_balance_floor: int = 10_000_000,  # 1 XLM
    max_single_spend: int = 1_000_000,    # 0.1 XLM
    max_rolling_window_spend: int = 10_000_000, # 1 XLM per hour
    rolling_window_seconds: int = 3600,   # 1 hour
    allowed_recipients: Optional[list[str]] = None,
) -> InvariantPolicy:
    """
    Creates a high-frequency micropayment policy for automated API calls, tipping, or data scraping.
    """
    p = InvariantPolicy(
        max_single_spend=max_single_spend,
        max_rolling_window_spend=max_rolling_window_spend,
        rolling_window_seconds=rolling_window_seconds,
        min_balance_floor=min_balance_floor,
        allowed_recipients=allowed_recipients or [],
    )
    validate_policy(p)
    return p
