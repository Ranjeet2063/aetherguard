# Stellar Community Fund (SCF) — Build Interest Form Answers

> **Instructions for Ranjeet**: Open [communityfund.stellar.org](https://communityfund.stellar.org) (or the [Direct Airtable Form](https://airtable.com/appymB1sbp5uidiGe/pagtmenJHv6N6LjXV/form)) and copy-paste each answer directly into the corresponding field.

---

### 1. Project Title
```text
AetherGuard
```

---

### 2. Project Description
```text
AetherGuard is the world's first high-performance mathematical invariant firewall and liquidity safety OS designed specifically for autonomous AI agents operating on Stellar and Soroban.

As AI models (ElizaOS, Anthropic Claude, OpenAI, and LangChain) manage on-chain treasuries and automated DeFi actions, they introduce a catastrophic vulnerability: they act on untrusted user prompts and web data. A single prompt injection or hallucination can cause an agent to drain its private key.

AetherGuard solves this on Stellar via the "Proposer vs. Signer Enclave Pattern":
1. The AI agent operates as an untrusted proposer with zero access to master private keys.
2. Invariant Firewall (Pure Rust): Deterministically validates spend velocity limits (rolling-window spend caps), per-tx spend ceilings, recipient whitelists, and balance reserve floors in sub-millisecond runtime.
3. Hardware/Isolated Signing Enclave: Only transactions satisfying mathematical invariants receive cryptographic signatures from the isolated Ed25519 vault before reaching the Soroban smart account.
```

---

### 3. Project Category
```text
Developer Tooling / Infrastructure & Security
```

---

### 4. Current Traction
```text
- Live Soroban Smart Contract Deployed on Testnet:
  - Contract ID: CCBUTMN6U7VKUAXAPMZXSQQW4LBJKHNEYBRGXPIY6CMO2O5WNC6TV7NP
  - Explorer Verification: https://stellar.expert/explorer/testnet/contract/CCBUTMN6U7VKUAXAPMZXSQQW4LBJKHNEYBRGXPIY6CMO2O5WNC6TV7NP
  - Deployment Tx: 2f93c86a6c52929d96d1ac514cc5e4322479e3429daae26799bdef6637932034
  - Optimized WASM size: 7.9 KB with 0.05% protocol micro-fee routing & event emissions.
- Live Interactive Web Playground: https://ranjeet2063.github.io/aetherguard
- Working Monorepo & Core Engine: Fully implemented pure Rust invariant engine (`aetherguard-core`), on-chain Soroban contract (`aetherguard-contract`), Soroban state bindings (`aetherguard-soroban`), and interactive demo CLI (`aetherguard-cli`).
- Automated CI: 100% passing automated test suite running on GitHub Actions (Rust unit tests, Bun test suite, typechecking, and container build).
- Published Production Packages on NPM Registry:
  1. `aetherguard-sdk` (v0.1.0): TypeScript/Bun SDK with instant verification digest generation (https://www.npmjs.com/package/aetherguard-sdk).
  2. `aetherguard-mcp` (v0.1.0): Anthropic Model Context Protocol server executable via `npx aetherguard-mcp` with Dockerfile (https://www.npmjs.com/package/aetherguard-mcp).
  3. `aetherguard-eliza-plugin` (v0.1.0): ElizaOS safety plugin tagged for autonomous agent autodiscovery (https://www.npmjs.com/package/aetherguard-eliza-plugin).
- Official GitHub Release v0.1.0: Standalone compiled Linux x86_64 binary release with SHA-256 verification (https://github.com/Ranjeet2063/aetherguard/releases/tag/v0.1.0).
- Upstream Ecosystem PRs:
  - ElizaOS (19.5k+ stars): PR #35834 submitted and code approved by reviewer `mtcow`.
  - Awesome MCP Servers (12k+ stars): PR #16256 live for official Anthropic ecosystem directory listing.
- Founder Track Record: Lead architect with 166+ merged PRs across open-source Web3/AI, Tenstorrent (Jim Keller's silicon compiler), and 22 merged PRs in Soroban smart contract projects.
- GitHub Repository: https://github.com/Ranjeet2063/aetherguard
```

---

### 5. Website / Repository URL
```text
Website & Web Playground: https://ranjeet2063.github.io/aetherguard
Repository: https://github.com/Ranjeet2063/aetherguard
Testnet Contract: https://stellar.expert/explorer/testnet/contract/CCBUTMN6U7VKUAXAPMZXSQQW4LBJKHNEYBRGXPIY6CMO2O5WNC6TV7NP
```

---

### 6. Planned Stellar Integration
```text
AetherGuard deeply leverages the native performance and security primitives of the Stellar and Soroban tech stack:
1. Soroban Smart Accounts (__check_auth hook): Validates cryptographically signed invariant proofs directly inside Soroban contract invocation hooks before balance state can transition.
2. Sub-Cent Microtransactions & Speed: AI agents require high-frequency micro-adjustments and rebalances. Stellar's 5-second finality and $0.00001 fees provide the optimal rails.
3. Protocol Treasury Routing: AetherGuard configures an autonomous 0.05% protocol micro-fee routed to a sovereign Stellar treasury account, creating perpetual maintenance revenue.
4. Cross-DEX Liquidity Guards: Native simulation adapters for Soroban AMMs (Phoenix, Soroswap, Blend) to prevent adverse slippage or flash drain attempts.
```

---

### 7. Build Track
```text
Open Track (or Developer Tooling RFP)
```

---

### 8. Submitter Type
```text
Individual / Open-Source Protocol Architect
```

---

### 9. Email
```text
guptakumarranjeet150@gmail.com
```

---

### 10. Team Description
```text
Lead Architect: Ranjeet Kumar Sah (@Ranjeet2063)
- GitHub: https://github.com/Ranjeet2063
- Track Record: 166+ merged Pull Requests across top open-source Web3 and AI repositories (Pull Shark Gold tier).
- Silicon & AI Engineering: Merged PR #55213 in Jim Keller's Tenstorrent (`tt-metal`), approved PR #30298 & active PR #35834 in ElizaOS (19.5k+ stars).
- Soroban Ecosystem Mastery: 22 merged PRs in zkpayroll (Soroban smart contracts & SDK), Axionvera, Trustless Work, and drydocs/tholos.
- Deep expertise in Rust systems programming, Soroban smart contract architecture, Ed25519 cryptography, and TypeScript/Bun SDK engineering.
```

---

### 11. Which countries or regions will your project target or operate in?
```text
Global / Not region-specific (Developer tooling and open-source infrastructure usable anywhere)
```

---

### 12. Where is your team based?
```text
Nepal
```

---

### 13. Will your project involve any local currencies, local payment rails, or local financial infrastructure?
```text
No
```

---

### 14. Which of the following best describes your product?
```text
Developer Tooling / Infrastructure / Security
```

---

### 15. Nigerian Financial Nexus / Exports
* Will your product process Nigerian Naira transactions?: `No`
* Is your product intended exclusively for markets outside Nigeria?: `Yes`

---

### 16. Referral Information
* Have you been working with someone from SDF or the community?: `No` (Independent Open-Source Builder)
* Referral Code: *(Leave blank if none)*

---

### 17. Budget & Deliverable Structure (3 Tranches — $100,000 USDC)
* **Tranche 1: MVP & Core Invariant Engine ($30,000 USDC)**
  - Rust Core Invariant Engine (`aetherguard-core`) with velocity caps and balance floors.
  - TypeScript SDK (`@aetherguard/sdk`) & MCP Server (`aetherguard-mcp`).
  - ElizaOS Safety Plugin (`@aetherguard/eliza-plugin`).
  - 100% Green CI automated test suite.
* **Tranche 2: Testnet Deployment, STRIDE Threat Model & Observability ($35,000 USDC)**
  - Formal STRIDE Threat Model & On-Chain Monitoring Plan per Stellar Developer guidelines.
  - Live Soroban Testnet Smart Account Contract deployment.
  - Web-Based Invariant Governance & Policy Dashboard.
  - Merged upstream ecosystem integration in ElizaOS.
* **Tranche 3: Mainnet Launch, Security Audit & Ecosystem Scale ($35,000 USDC)**
  - Accredited third-party smart contract security audit.
  - Production Mainnet Deployment on Stellar Public Network.
  - Soroban DEX liquidity guard adapters (Phoenix, Soroswap).
  - Developer documentation hub and community workshop.
