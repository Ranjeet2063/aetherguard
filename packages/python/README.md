# AetherGuard Python SDK (`aetherguard-py`)

> **Deterministic Mathematical Invariant Firewall and Financial OS for Autonomous AI Agents**  
> Native bindings and safety guards for Python AI Agents (LangChain, CrewAI, AutoGPT, LlamaIndex).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.9+](https://img.shields.io/badge/Python-3.9+-brightgreen.svg)](https://python.org)
[![Security: STRIDE Verified](https://img.shields.io/badge/Security-STRIDE%20Verified-success.svg)](https://github.com/Ranjeet2063/aetherguard/blob/main/STRIDE_THREAT_MODEL.md)

---

## 🎯 Overview

Autonomous AI agents powered by Large Language Models (LLMs) are prone to prompt injections, goal-hijacking, and logical hallucinations. When AI agents are granted access to crypto wallets or smart contract execution keys, a single prompt injection can drain treasury reserves in seconds.

**AetherGuard** solves this by establishing a non-bypassable, mathematically enforced policy layer between autonomous agents and their private keys. Every transaction proposal is audited against formal mathematical invariants:
1. **Single Spend Caps** ($S \le C_{max}$)
2. **Rolling Window Budgets** ($\sum S \le B_{window}$)
3. **Mandatory Balance Floors** ($B - S \ge F_{min}$)
4. **Strict Whitelisting** (Approved Recipients, Target Contracts, Function Selectors)
5. **Emergency Circuit Breaker** (Instant Kill-Switch Freeze)
6. **Human Autonomy Thresholds** (Automatic escalation to human multisig if spend exceeds threshold)

---

## 🚀 Installation

```bash
pip install aetherguard
```

Or for local development:
```bash
git clone https://github.com/Ranjeet2063/aetherguard.git
cd aetherguard/packages/python
pip install -e .
```

---

## ⚡ Quickstart

### 1. Basic Invariant Verification

```python
from aetherguard import AetherGuardClient, conservative_policy, InvariantViolationError

# Configure conservative safety boundaries
policy = conservative_policy(
    min_balance_floor=100_000_000,       # 10 XLM floor
    max_single_spend=50_000_000,         # 5 XLM cap
    max_rolling_window_spend=150_000_000,# 15 XLM per 24 hours
    rolling_window_seconds=86400,
    allowed_recipients=["GBXY...TREASURY_RESERVE"]
)

client = AetherGuardClient(policy)

# AI agent proposes a spend
proposal = client.create_proposal(
    agent_id="agent-01",
    intent_prompt="Pay for compute resources",
    target_contract="C_PAYMENT_CONTRACT",
    function_name="transfer",
    recipient="GBXY...TREASURY_RESERVE",
    amount=30_000_000,
    asset_symbol="XLM"
)

# Intercept and verify against invariants
current_balance = 500_000_000 # 50 XLM
proof = client.evaluate_and_prove(proposal, current_balance)

print(f"Transaction Approved! Cryptographic Proof: {proof.invariant_digest_hex}")
```

---

## 🤖 Framework Integrations

### LangChain Tools

Protect any LangChain tool from rogue execution using `@guard_tool`:

```python
from aetherguard import AetherGuardClient, conservative_policy
from aetherguard.integrations import guard_tool

client = AetherGuardClient(conservative_policy())

@guard_tool(
    client=client,
    balance_provider=lambda: 500_000_000,
    target_contract="stellar-payment",
    function_name="transfer",
    catch_and_return_message=True # Feeds back safely to LLM on rejection
)
def pay_vendor(recipient: str, amount: int) -> str:
    # Actual on-chain wallet signing logic here
    return f"Paid {amount} to {recipient}"
```

### CrewAI Multi-Agent Pipelines

```python
from aetherguard.integrations import CrewAIGuard

guard = CrewAIGuard(client, balance_provider=lambda: 500_000_000)

# Verify multi-agent actions before execution
is_safe = guard.verify_action(
    action_name="Staking Rewards Distribution",
    recipient="G_STAKING_REWARDS_POOL",
    amount=20_000_000
)
```

### LlamaIndex Tools

```python
from aetherguard.integrations import guard_llamaindex_tool

@guard_llamaindex_tool(client=client, balance_provider=get_wallet_balance)
def retrieve_and_pay(chunk_id: str, recipient: str, amount: int):
    return pay_oracle_for_chunk(chunk_id, recipient, amount)
```

### AutoGPT Command Interceptor

```python
from aetherguard.integrations import AutoGPTGuard

guard = AutoGPTGuard(client, balance_provider=get_wallet_balance)
is_allowed = guard.intercept_command("pay_vendor", {"recipient": "GBXY...", "amount": 1000})
```

---

## 🧪 Testing

Run the full local unit test suite:
```bash
python3 -m unittest discover tests
```

---

## 🛡️ Formal Security Architecture

AetherGuard implements formal proofs based on Ramanujan invariant symmetries and Microsoft STRIDE threat modeling. Read the full formal specification in [STRIDE_THREAT_MODEL.md](https://github.com/Ranjeet2063/aetherguard/blob/main/STRIDE_THREAT_MODEL.md).

---

## 📄 License

MIT © Ranjeet2063
