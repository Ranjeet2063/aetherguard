# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard Type Definitions
Data classes and models representing mathematical policies, agent proposals, and cryptographic proofs.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class DefiSwapPolicy:
    """
    Mathematical boundary rules for decentralized AMM swaps and oracle verification.
    """
    max_slippage_bps: int = 100               # 1.0% maximum slippage tolerance
    max_oracle_deviation_bps: int = 200       # 2.0% maximum price deviation from oracle
    min_output_floor: int = 1                 # Absolute minimum output token floor

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DefiSwapPolicy":
        return cls(
            max_slippage_bps=int(data.get("max_slippage_bps", 100)),
            max_oracle_deviation_bps=int(data.get("max_oracle_deviation_bps", 200)),
            min_output_floor=int(data.get("min_output_floor", 1)),
        )


@dataclass
class SwapParameters:
    """
    Parameters describing a decentralized AMM swap operation (Soroswap, Phoenix, Stellar DEX).
    """
    asset_in: str
    asset_out: str
    amount_in: int
    expected_amount_out: int
    min_amount_out: int
    oracle_reference_price_bps: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SwapParameters":
        return cls(
            asset_in=str(data["asset_in"]),
            asset_out=str(data["asset_out"]),
            amount_in=int(data["amount_in"]),
            expected_amount_out=int(data["expected_amount_out"]),
            min_amount_out=int(data["min_amount_out"]),
            oracle_reference_price_bps=(
                int(data["oracle_reference_price_bps"])
                if data.get("oracle_reference_price_bps") is not None
                else None
            ),
        )


@dataclass
class InvariantPolicy:
    """
    Mathematical boundary rules governing an autonomous AI agent's wallet.
    All balance and spending amounts are in atomic units (e.g., stroops for Stellar / lumens).
    """
    max_single_spend: int
    max_rolling_window_spend: int
    rolling_window_seconds: int
    min_balance_floor: int
    allowed_recipients: list[str] = field(default_factory=list)
    allowed_contracts: list[str] = field(default_factory=list)
    allowed_functions: list[str] = field(default_factory=list)
    human_confirmation_threshold: Optional[int] = None
    defi_swap_policy: Optional[DefiSwapPolicy] = None
    is_emergency_paused: bool = False

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        if self.defi_swap_policy:
            res["defi_swap_policy"] = self.defi_swap_policy.to_dict()
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvariantPolicy":
        defi_policy = None
        if data.get("defi_swap_policy"):
            defi_policy = DefiSwapPolicy.from_dict(data["defi_swap_policy"])

        return cls(
            max_single_spend=int(data["max_single_spend"]),
            max_rolling_window_spend=int(data["max_rolling_window_spend"]),
            rolling_window_seconds=int(data["rolling_window_seconds"]),
            min_balance_floor=int(data["min_balance_floor"]),
            allowed_recipients=list(data.get("allowed_recipients", [])),
            allowed_contracts=list(data.get("allowed_contracts", [])),
            allowed_functions=list(data.get("allowed_functions", [])),
            human_confirmation_threshold=(
                int(data["human_confirmation_threshold"])
                if data.get("human_confirmation_threshold") is not None
                else None
            ),
            defi_swap_policy=defi_policy,
            is_emergency_paused=bool(data.get("is_emergency_paused", False)),
        )


@dataclass
class AgentTransactionProposal:
    """
    An untrusted execution intent emitted by an autonomous AI agent (LLM, LangChain, CrewAI).
    """
    proposal_id: str
    agent_id: str
    intent_prompt: str
    target_contract: str
    function_name: str
    recipient: str
    amount: int
    asset_symbol: str
    timestamp: int
    swap_params: Optional[SwapParameters] = None

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        if self.swap_params:
            res["swap_params"] = self.swap_params.to_dict()
        return res

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTransactionProposal":
        swap_params = None
        if data.get("swap_params"):
            swap_params = SwapParameters.from_dict(data["swap_params"])
        return cls(
            proposal_id=str(data["proposal_id"]),
            agent_id=str(data["agent_id"]),
            intent_prompt=str(data["intent_prompt"]),
            target_contract=str(data["target_contract"]),
            function_name=str(data["function_name"]),
            recipient=str(data["recipient"]),
            amount=int(data["amount"]),
            asset_symbol=str(data["asset_symbol"]),
            timestamp=int(data["timestamp"]),
            swap_params=swap_params,
        )


@dataclass
class ProofOfInvariant:
    """
    Cryptographic proof generated by the invariant verification engine when an operation is approved.
    """
    proposal_id: str
    verified_at: int
    spent_amount: str
    remaining_rolling_budget: str
    projected_balance: str
    invariant_digest_hex: str
    status: str = "APPROVED"
    enclave_signature_hex: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
