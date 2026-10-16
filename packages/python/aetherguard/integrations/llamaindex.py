# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard LlamaIndex Integration
Tool wrappers and decorators to enforce mathematical invariant boundaries on LlamaIndex agents.
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from ..client import AetherGuardClient
from ..errors import InvariantViolationError
from ..types import EnclaveAttestationCertificate, ProofOfInvariant


def _payment_arguments(
    tool: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any]
) -> tuple[Any, Any]:
    """Find payment fields by parameter name, with positional compatibility fallback."""
    try:
        bound = inspect.signature(tool).bind_partial(*args, **kwargs)
        recipient = bound.arguments.get("recipient")
        amount = bound.arguments.get("amount")
        if recipient is not None or amount is not None:
            return recipient or "", amount or 0
    except (TypeError, ValueError):
        pass

    return (
        kwargs.get("recipient") or (args[0] if len(args) > 0 else ""),
        kwargs.get("amount") or (args[1] if len(args) > 1 else 0),
    )


def _amount_value(value: Any) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def guard_llamaindex_tool(
    client: AetherGuardClient,
    balance_provider: Callable[[], int],
    agent_id: str = "llamaindex-agent",
    target_contract: str = "stellar-payment",
    function_name: str = "transfer",
    asset_symbol: str = "XLM",
    catch_and_return_message: bool = True,
):
    """
    Decorator for LlamaIndex tool functions.
    Intercepts execution, audits proposals against mathematical invariants, and returns
    a graceful explanation back to the agent if rejected.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            recipient_value, amount_value = _payment_arguments(func, args, kwargs)
            recipient = str(recipient_value)
            amount = _amount_value(amount_value)

            intent = f"LlamaIndex agent tool call '{func.__name__}' -> {recipient} ({amount} {asset_symbol})"
            proposal = client.create_proposal(
                agent_id=agent_id,
                intent_prompt=intent,
                target_contract=target_contract,
                function_name=function_name,
                recipient=recipient,
                amount=amount,
                asset_symbol=asset_symbol,
            )

            current_balance = balance_provider()

            try:
                client.evaluate_and_prove(proposal, current_balance)
            except InvariantViolationError as err:
                if catch_and_return_message:
                    return f"[AetherGuard Invariant Blocked]: {err}"
                raise

            return func(*args, **kwargs)

        return wrapper

    return decorator


class AetherGuardLlamaIndexTool:
    """Class wrapper for LlamaIndex tools."""

    def __init__(
        self,
        tool_fn: Callable[..., Any],
        client: AetherGuardClient,
        balance_provider: Callable[[], int],
        agent_id: str = "llamaindex-agent",
        target_contract: str = "stellar-payment",
        function_name: str = "transfer",
        asset_symbol: str = "XLM",
    ):
        self.tool_fn = tool_fn
        self.client = client
        self.balance_provider = balance_provider
        self.agent_id = agent_id
        self.target_contract = target_contract
        self.function_name = function_name
        self.asset_symbol = asset_symbol
        functools.update_wrapper(self, tool_fn)
        try:
            self.__signature__ = inspect.signature(tool_fn)
        except (TypeError, ValueError):
            pass

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        recipient_value, amount_value = _payment_arguments(self.tool_fn, args, kwargs)
        recipient = str(recipient_value)
        amount = _amount_value(amount_value)

        proposal = self.client.create_proposal(
            agent_id=self.agent_id,
            intent_prompt=f"LlamaIndex tool call: send {amount} to {recipient}",
            target_contract=self.target_contract,
            function_name=self.function_name,
            recipient=recipient,
            amount=amount,
            asset_symbol=self.asset_symbol,
        )

        current_balance = self.balance_provider()
        self.client.evaluate_and_prove(proposal, current_balance)
        return self.tool_fn(*args, **kwargs)


class LlamaIndexActionGuard(AetherGuardLlamaIndexTool):
    """Guard a LlamaIndex tool and optionally expose its signed attestation."""

    def execute_with_attestation(
        self, *args: Any, **kwargs: Any
    ) -> tuple[Any, ProofOfInvariant, EnclaveAttestationCertificate]:
        """Attest before running the tool; return its output and signed evidence."""
        recipient_value, amount_value = _payment_arguments(self.tool_fn, args, kwargs)
        recipient = str(recipient_value)
        amount = _amount_value(amount_value)
        proposal = self.client.create_proposal(
            agent_id=self.agent_id,
            intent_prompt=f"LlamaIndex tool call: send {amount} to {recipient}",
            target_contract=self.target_contract,
            function_name=self.function_name,
            recipient=recipient,
            amount=amount,
            asset_symbol=self.asset_symbol,
        )
        proof, certificate = self.client.evaluate_and_attest(
            proposal, self.balance_provider()
        )
        result = self.tool_fn(*args, **kwargs)
        return result, proof, certificate

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        result, _, _ = self.execute_with_attestation(*args, **kwargs)
        return result
