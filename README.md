<div align="center">

# ⚡ CASCADIA PROTOCOL
### **C**ausal **A**utonomous **S**taleness **C**ascade & **A**utomated **D**ependency **I**nvalidation **A**rchitecture

**Empirical Fact-Anchoring, Non-Deterministic LLM Consensus, and Topological Dependency Cascades on GenLayer**

[![GenLayer Intelligent Contract](https://img.shields.io/badge/GenLayer-Intelligent%20Contract-00f0ff?style=for-the-badge&logo=ethereum)](https://genlayer.com)
[![Studio Net Deployed](https://img.shields.io/badge/Deployed-0x037d35F...e4f7f-10b981?style=for-the-badge&logo=ethereum)](https://studio.genlayer.com)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://python.org)
[![Vite + Vanilla JS](https://img.shields.io/badge/Vite-Observability%20UI-646cff?style=for-the-badge&logo=vite)](https://vitejs.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-10b981?style=for-the-badge)](LICENSE)

</div>

---

## 🧭 Executive Summary

Decentralized finance, automated treasury execution, and autonomous governance agents routinely make irreversible smart contract decisions based on point-in-time oracle assertions. However, **real-world facts are volatile**: an enterprise credit facility approved on Monday becomes insolvent on Wednesday; a SOC 2 compliance certificate verified in January is revoked in March; a protocol collateral parameter validated during normal volatility collapses during a black swan event.

Traditional smart contracts have no native mechanism to track **causal dependencies** across multi-tier decisions. Once an action is approved, downstream logic assumes permanent validity until an explicit, costly external transaction manually intervenes.

**CASCADIA Protocol** solves this fundamental vulnerability by introducing a self-governing **Topological Causal Dependency Graph** natively hosted on GenLayer Intelligent Contracts:
1. **Empirical Fact Anchors (`ANCHOR`):** Ground-truth web observation nodes that monitor live HTTPS endpoints, documents, and registry states with SHA-256 fingerprinting and deterministic epoch-0 baseline pinning.
2. **Reasoned Causal Verdicts (`VERDICT`):** Multi-hop decisions evaluated by GenLayer non-deterministic LLM consensus committees (`gl.vm.run_nondet`).
3. **Reverse-Edge Staleness Cascades:** When an empirical anchor mutates, a topological breadth-first cascade instantly invalidates all downstream verdicts via pre-indexed reverse adjacency lists, deterministically freezing unauthorized smart contract actions in a single atomic transaction.

---

## 🏛️ System Architecture

```
                                  [ REAL WORLD ]
                        (Live Web / APIs / Registry Docs)
                                        │
                                        │ HTTPS Fetch & SHA-256 Digest
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GENLAYER INTELLIGENT CONTRACT LAYER                      │
│                                                                             │
│   ┌───────────────────────┐            ┌───────────────────────┐           │
│   │   ANCHOR (Depth 0)    │            │   ANCHOR (Depth 0)    │           │
│   │  SOC 2 Certification  │            │ Treasury Solvency >$1M│           │
│   │   [status: ACTIVE]    │            │   [status: ACTIVE]    │           │
│   └──────────┬────────────┘            └──────────┬────────────┘           │
│              │                                    │                        │
│              │ Causal Dependency                  │ Causal Dependency      │
│              ▼                                    │                        │
│   ┌───────────────────────┐                       │                        │
│   │   VERDICT (Depth 1)   │                       │                        │
│   │ Tier-1 Vendor Approval│                       │                        │
│   │   [status: VALID]     │                       │                        │
│   └──────────┬────────────┘                       │                        │
│              │                                    │                        │
│              │ Reverse-Edge Invalidation Path     │                        │
│              ▼                                    ▼                        │
│   ┌────────────────────────────────────────────────────────────┐           │
│   │                     VERDICT (Depth 2)                      │           │
│   │              Autonomous Treasury Disbursement              │           │
│   │                      [status: VALID]                       │           │
│   └──────────────────────────────┬─────────────────────────────┘           │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   │ is_verdict_valid(id) == True
                                   ▼
             ┌───────────────────────────────────────────┐
             │         EXTERNAL CONSUMER CONTRACTS       │
             │   DeFi Vaults / Payroll / Credit Pools   │
             │          [EXECUTES TRANSACTION]           │
             └───────────────────────────────────────────┘
```

When an external mutation occurs:
```
[External Web Change] ──> observe_anchor() ──> [ANCHOR: MUTATED]
                                                        │
                      ┌─────────────────────────────────┘
                      ▼ (Reverse-Edge Cascade Engine)
        [VERDICT L1: STALE] ──> [VERDICT L2: STALE] ──> is_verdict_valid() == False
                                                                 │
                                                                 ▼
                                                  [DOWNSTREAM EXECUTION HALTED]
```

---

## ✨ Key Architectural Innovations

### 1. Dual-Tier Node Semantics (`ANCHOR` vs `VERDICT`)
- **`ANCHOR` Nodes (Depth 0):** Represent empirical observations anchored to real-world URLs. They carry a factual hypothesis, web target URI, content hash, and observation epoch.
- **`VERDICT` Nodes (Depth $\ge 1$):** Represent reasoned judgements formulated by GenLayer validator consensus. Verdicts declare explicit upstream dependencies and can only be evaluated when all direct parents are active and valid.

### 2. Structured Non-Deterministic Consensus (`gl.vm.run_nondet`)
Rather than relying on brittle raw text matching across LLM outputs, CASCADIA extracts structured, actionable decision tuples:
- **Anchor Consensus:** Evaluates boolean `mutation_detected` and factual consistency.
- **Verdict Consensus:** Evaluates boolean `decision_outcome` and ordered dependency identifiers.
- Natural stylistic divergence in validator rationales is tolerated while guaranteeing cryptographic consensus on execution state.

### 3. Instantaneous Reverse-Edge Invalidation
Topological edges are dual-indexed upon creation:
- **Forward dependencies:** `child -> [parents]` (used for validation and depth computation)
- **Reverse dependents:** `parent -> [children]` (used for cascade invalidation)

When `observe_anchor` detects a mutation, breadth-first traversal traverses reverse edges and marks all dependent verdicts as `VERDICT_STALE`. No gas-expensive recursive graph crawls are needed at read time.

### 4. Genesis Baseline Pinning (Epoch 0 Invariant)
A critical flaw in naive oracle monitors is triggering false mutations upon initial contract deployment. CASCADIA enforces **Epoch-0 Baseline Pinning**: the initial observation records the ground truth digest without firing a mutation event, guaranteeing that staleness alerts only trigger on authentic subsequent state shifts.

### 5. Deterministic Guardrails & DoS Prevention
To guarantee bounded transaction execution and gas predictability:
- **Maximum Active Nodes:** 128
- **Maximum Graph Depth:** 32 layers
- **Maximum Fan-Out:** 32 children per node
- **DAG Acyclicity:** Formally verified via Kahn's cycle-detection algorithm prior to edge admission.

---

## 📊 State Machine Transitions

| Entity | Current State | Trigger Event | Next State | System Invariant |
| :--- | :--- | :--- | :--- | :--- |
| **ANCHOR** | *(Genesis)* | `create_anchor` | `ANCHOR_ACTIVE` | Baseline pinned at epoch 0 |
| **ANCHOR** | `ANCHOR_ACTIVE` | `observe_anchor` (Hash match) | `ANCHOR_ACTIVE` | Epoch incremented |
| **ANCHOR** | `ANCHOR_ACTIVE` | `observe_anchor` (Mutation) | `ANCHOR_MUTATED` | Triggers reverse-edge cascade |
| **ANCHOR** | `ANCHOR_ACTIVE` | `observe_anchor` (Unreachable) | `ANCHOR_DEGRADED` | Fails safe |
| **VERDICT**| *(Genesis)* | `create_verdict` | `VERDICT_INITIAL_STALE`| Requires initial evaluation |
| **VERDICT**| `INITIAL_STALE`| `evaluate_verdict` (True) | `VERDICT_VALID` | Upstream parents must be VALID |
| **VERDICT**| `INITIAL_STALE`| `evaluate_verdict` (False) | `VERDICT_INVALID` | Stored with consensus rationale |
| **VERDICT**| `VERDICT_VALID`| Parent Anchor mutated | `VERDICT_STALE` | Atomic reverse cascade |
| **VERDICT**| `VERDICT_STALE`| `re_evaluate_verdict` | `VERDICT_VALID` | Allowed only after parent recovery|

---

## 🖥️ Executive Observability Frontend

The CASCADIA frontend is engineered for compliance officers, risk managers, and protocol auditors:
- **Dark Obsidian Aesthetics:** Styled according to high-density executive telemetry design principles (`#080a0d` obsidian surface, cyan truth glows, emerald valid signals, and amber staleness indicators).
- **Interactive SVG DAG Canvas:** Smooth cubic bezier curves connecting layered nodes with real-time coordinate computation.
- **Node Detail Telemetry Drawer:** Deep-dive modal revealing definition fingerprints, content digests, depth, epochs, and dependency trees.
- **Simulated Mutation Engine:** One-click simulation enabling judges and reviewers to trigger synthetic mutations and watch staleness cascades ripple through the DAG in real time.
- **Web3 Wallet Client:** Built with `genlayer-js` supporting EIP-1193 wallet connection and direct interaction with GenLayer Studio Dev / StudioNet.

---

## 📁 Repository Structure

```
cascadia/
├── contracts/
│   └── cascadia.py              # GenLayer Intelligent Contract (998 LOC)
├── docs/
│   ├── CAUSAL_TOPOLOGY.md       # Formal topological & cascade specification
│   ├── STATE_MACHINE.md         # Exhaustive state transitions & invariants
│   ├── SECURITY_INVARIANTS.md   # Threat vectors, bounds, and DoS mitigations
│   ├── DEPLOYMENT_GUIDE.md      # StudioNet deployment and operational guide
│   └── API_REFERENCE.md         # Public transactions, views, and error reference
├── frontend/
│   ├── index.html               # SPA entrypoint and typography links
│   ├── package.json             # Frontend dependencies (genlayer-js, vite)
│   ├── vite.config.js           # Vite development and bundle configuration
│   ├── vercel.json              # Zero-config deployment manifest
│   ├── src/
│   │   ├── styles.css           # Obsidian theme and responsive token system
│   │   ├── topology.js          # SVG layout math & cascade simulation engine
│   │   └── main.js              # Telemetry dashboard & Web3 wallet client
│   └── test/
│       └── topology.test.js     # Node.js unit tests for layout and cascade logic
├── scripts/
│   ├── validate_topology.py     # Independent DAG acyclicity and bound verifier
│   ├── deploy_cascadia.py       # Contract deployment and RPC manifest utility
│   └── simulate_scenario.py     # End-to-end interactive mutation scenario runner
├── tests/
│   ├── conftest.py              # Test harness and GenLayer calldata mocks
│   └── test_cascadia.py         # Pytest suite covering all contract invariants
├── pyproject.toml               # Python project configuration
├── requirements.txt             # Testing dependencies (pytest, etc.)
├── LICENSE                      # MIT Open Source License
└── README.md                    # System specification and documentation
```

---

## 🚀 Quickstart & Verification

### 1. Verify Python Intelligent Contract Suite
```bash
# Install test requirements
pip install -r requirements.txt

# Run full invariant test suite
pytest -v tests/
```

### 2. Verify Frontend Topological Layout & Cascade Math
```bash
cd frontend
node --test test/topology.test.js
```

### 3. Run DAG Integrity & Acyclicity Verifier
```bash
python3 scripts/validate_topology.py
```

### 4. Run Interactive End-to-End Simulation
```bash
python3 scripts/simulate_scenario.py
```

### 5. Launch Executive Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🌐 Live Deployed Contract

| Parameter | Value |
| :--- | :--- |
| **Contract Address** | `0x037d35F587555cAdE69840e19a1e1b58C65e4f7f` |
| **Network** | GenLayer Studio Dev / StudioNet |
| **Chain ID** | `61999` |
| **Studio IDE** | [https://studio.genlayer.com](https://studio.genlayer.com) |
| **Status** | Active & Initialized |

---

## 🛠️ Deploying to GenLayer Studio

1. Open [GenLayer Studio](https://studio.genlayer.com).
2. Create a contract file named `cascadia.py`.
3. Paste the code from `contracts/cascadia.py`.
4. Click **Deploy Contract**.
5. The deployed contract address is ready for interaction via the frontend or CLI.

---

## 🛡️ Security & Invariant Guarantees

1. **Cycle Freedom:** Any transaction attempting to form a cyclic dependency is rejected at submission time via graph traversal before contract state mutates.
2. **Fail-Closed Consensus:** Stale verdicts immediately return `is_verdict_valid == False`. Downstream consumer contracts calling this view method will fail closed, ensuring financial safety.
3. **Immutability of Historical Proofs:** Every anchor mutation and verdict transition logs the consensus epoch, validator count, and content digest for complete forensic replayability.

---

## 👤 Author & Contributor Attribution

- **Architect & Developer:** `9ja_maxx`
- **GitHub:** [@9ja-maxx](https://github.com/9ja-maxx)
- **Email:** `297689616+9ja-maxx@users.noreply.github.com`
- **License:** MIT License
