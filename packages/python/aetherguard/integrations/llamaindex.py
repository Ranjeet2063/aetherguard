# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard LlamaIndex Integration
Tool wrappers and decorators to enforce mathematical invariant boundaries on LlamaIndex agents.
"""

import functools
from typing import Callable, Any, Optional

from ..client import AetherGuardClient
from ..errors import InvariantViolationError


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
    Decorator for LlamaIndex tool functions (used with FunctionTool.from_defaults).
    Intercepts execution, audits proposals against mathematical invariants, and returns
    a graceful explanation back to the agent if rejected.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            recipient = kwargs.get("recipient") or (args[0] if len(args) > 0 else "")
            amount_val = kwargs.get("amount") or (args[1] if len(args) > 1 else 0)

            try:
                amount = int(amount_val)
            except (ValueError, TypeError):
                amount = 0

            intent = f"LlamaIndex agent tool call '{func.__name__}' -> {recipient} ({amount} {asset_symbol})"
            proposal = client.create_proposal(
                agent_id=agent_id,
                intent_prompt=intent,
                target_contract=target_contract,
                function_name=function_name,
                recipient=str(recipient),
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
    """
    Class wrapper for LlamaIndex tools.
    """
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

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        recipient = kwargs.get("recipient") or (args[0] if len(args) > 0 else "")
        amount_val = kwargs.get("amount") or (args[1] if len(args) > 1 else 0)

        try:
            amount = int(amount_val)
        except (ValueError, TypeError):
            amount = 0

        proposal = self.client.create_proposal(
            agent_id=self.agent_id,
            intent_prompt=f"LlamaIndex tool call: send {amount} to {recipient}",
            target_contract=self.target_contract,
            function_name=self.function_name,
            recipient=str(recipient),
            amount=amount,
            asset_symbol=self.asset_symbol,
        )

        current_balance = self.balance_provider()
        self.client.evaluate_and_prove(proposal, current_balance)
        return self.tool_fn(*args, **kwargs)
