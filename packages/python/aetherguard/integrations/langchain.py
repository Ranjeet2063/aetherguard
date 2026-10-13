# Authorized Protocol Quality Assurance & Formal Verification Engine
"""
AetherGuard LangChain Integration
Tool wrappers and decorators to enforce mathematical invariant boundaries on LangChain agents.
"""

import functools
from typing import Callable, Any, Optional

from ..client import AetherGuardClient
from ..errors import InvariantViolationError


def guard_tool(
    client: AetherGuardClient,
    balance_provider: Callable[[], int],
    agent_id: str = "langchain-agent",
    target_contract: str = "stellar-payment",
    function_name: str = "transfer",
    asset_symbol: str = "XLM",
    catch_and_return_message: bool = True,
):
    """
    Decorator to wrap any Python / LangChain tool function with AetherGuard verification.

    Args:
        client: Configured AetherGuardClient instance.
        balance_provider: Callable returning the current wallet balance in atomic units.
        agent_id: Identifier for the calling AI agent.
        target_contract: Target contract or protocol identifier.
        function_name: Function being called on-chain.
        asset_symbol: Token or asset symbol (default: 'XLM').
        catch_and_return_message: If True, catches InvariantViolationError and returns a
                                  descriptive string back to the LLM agent rather than crashing.
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract recipient and amount from kwargs or positional args
            recipient = kwargs.get("recipient") or (args[0] if len(args) > 0 else "")
            amount_val = kwargs.get("amount") or (args[1] if len(args) > 1 else 0)

            try:
                amount = int(amount_val)
            except (ValueError, TypeError):
                amount = 0

            intent = f"Tool execution '{func.__name__}' for recipient '{recipient}' with amount {amount}"
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
                proof = client.evaluate_and_prove(proposal, current_balance)
            except InvariantViolationError as err:
                if catch_and_return_message:
                    return f"[AetherGuard REJECTED] {err}"
                raise

            # Execution approved: forward to underlying function and pass proof if accepted
            return func(*args, **kwargs)

        return wrapper
    return decorator


class AetherGuardLangChainTool:
    """
    Class wrapper for LangChain BaseTool instances.
    """
    def __init__(
        self,
        tool: Any,
        client: AetherGuardClient,
        balance_provider: Callable[[], int],
        agent_id: str = "langchain-agent",
        target_contract: str = "stellar-payment",
        function_name: str = "transfer",
        asset_symbol: str = "XLM",
    ):
        self.tool = tool
        self.client = client
        self.balance_provider = balance_provider
        self.agent_id = agent_id
        self.target_contract = target_contract
        self.function_name = function_name
        self.asset_symbol = asset_symbol

    def run(self, recipient: str, amount: int, **kwargs: Any) -> Any:
        proposal = self.client.create_proposal(
            agent_id=self.agent_id,
            intent_prompt=f"LangChain tool run: send {amount} to {recipient}",
            target_contract=self.target_contract,
            function_name=self.function_name,
            recipient=recipient,
            amount=int(amount),
            asset_symbol=self.asset_symbol,
        )
        current_balance = self.balance_provider()
        proof = self.client.evaluate_and_prove(proposal, current_balance)

        if hasattr(self.tool, "run"):
            return self.tool.run(recipient=recipient, amount=amount, **kwargs)
        elif callable(self.tool):
            return self.tool(recipient=recipient, amount=amount, **kwargs)
        raise TypeError("Underlying tool is neither callable nor implements .run()")
