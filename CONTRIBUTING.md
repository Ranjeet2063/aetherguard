# Contributing to AetherGuard 🛡️

First off, thank you for considering contributing to **AetherGuard**! 

AetherGuard is building the **world's first mathematical invariant firewall and financial operating system for autonomous AI agents on the Stellar network**. We welcome developers, researchers, and security auditors from all backgrounds to help shape the future of safe autonomous finance.

---

## 🌟 Why Contribute?

- **Shape the AI Agent Economy**: Help solve the #1 blocker preventing AI agents from managing real treasury capital (prompt injection, rogue swaps, drainer exploits).
- **Stellar Community Recognition**: Stellar Foundation and ecosystem builders actively monitor and support AetherGuard contributors.
- **Fast Maintainer SLA**: All Pull Requests and Issues are reviewed within **24 hours**.
- **Wall of Fame**: Every merged contributor is permanently featured on the README Wall of Fame and credited in release notes.

---

## 🚀 Quickstart for Local Development

### Prerequisites
- [Rust](https://rustup.rs/) (1.80+ or latest stable)
- [Python](https://www.python.org/) (3.9+)
- [Bun](https://bun.sh/) or Node.js (18+)
- [Git](https://git-scm.com/)

### 1. Clone the Repository
```bash
git clone https://github.com/Ranjeet2063/aetherguard.git
cd aetherguard
```

### 2. Run the Verification Suites

Verify Rust crates in under 10 seconds:
```bash
cargo test --all
```

Verify Python AI Agent SDK:
```bash
PYTHONPATH=packages/python python3 -m unittest discover packages/python/tests
```

Verify Interactive Terminal Dashboard:
```bash
cargo run -p aetherguard-cli -- demo
```

---

## 🎯 High-Priority Areas for Contributions

We maintain actively curated [Good First Issues](https://github.com/Ranjeet2063/aetherguard/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) for new contributors:

1. **DeFi Protocol Adapters (`crates/aetherguard-soroban`)**:
   - Adding guard adapters for other Soroban DEXs (e.g. Aquarius AMM, Comet, Aqua).
   - Adding yield aggregator invariant checks.
2. **AI Framework Integrations (`packages/python`)**:
   - LlamaIndex query engine tool guards.
   - CrewAI agent wallet guards.
   - LangChain custom tool wrappers.
3. **ElizaOS & MCP Plugins (`packages/eliza-plugin`, `packages/mcp-server`)**:
   - Additional tool definitions for model context protocols.
   - Prompt injection simulation test suites.
4. **Documentation & Tutorials**:
   - Guides, cookbooks, architecture diagrams, and video walkthroughs.

---

## 🛠️ Contribution Workflow

1. **Pick an Issue**: Browse open issues or submit an issue proposal to discuss new features.
2. **Fork and Branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. **Commit Cleanly**:
   - Write clear, concise commit messages (e.g. `feat(adapters): add aquarius amm swap guard`).
   - Ensure all automated unit tests pass locally before pushing.
4. **Open a Pull Request**:
   - Reference the issue (e.g. `Closes #12`).
   - Describe the changes and include testing evidence.

---

## 📜 Code of Conduct

We are committed to providing a friendly, safe, and welcoming environment for everyone, regardless of experience level, background, or identity. Please treat fellow contributors with respect.

---

Thank you for building the autonomous future with us! 🛡️
