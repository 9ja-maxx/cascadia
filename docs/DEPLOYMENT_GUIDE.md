# CASCADIA PROTOCOL — Deployment & Operations Guide

This document provides complete instructions for deploying, configuring, and operating the **CASCADIA Protocol** on the GenLayer Intelligent Contract platform (Local Devnet, Studio Dev, or StudioNet).

---

## 1. Prerequisites

- **Python 3.10+** (with `pytest`)
- **Node.js 18+** (with `npm`)
- **Web3 Wallet** (MetaMask, Rabby, or Coinbase Wallet configured for GenLayer Devnet)
- **GenLayer Studio Account** (accessible at [https://studio.genlayer.com](https://studio.genlayer.com))

---

## 2. Deploying the Intelligent Contract via GenLayer Studio

GenLayer Intelligent Contracts execute non-deterministic consensus algorithms using on-chain LLMs and web observation oracles. Follow these steps to deploy `contracts/cascadia.py`:

### Step 1: Open GenLayer Studio
1. Navigate to [https://studio.genlayer.com](https://studio.genlayer.com).
2. Connect your Web3 wallet and ensure the network is set to **GenLayer Studio Dev** (Chain ID: `61999` or testnet target).
3. Ensure you have testnet funds from the faucet.

### Step 2: Create Contract Source File
1. In the Studio file explorer, click **New Contract**.
2. Name the file `cascadia.py`.
3. Open `contracts/cascadia.py` from this repository and copy its entire contents.
4. Paste the code into the Studio editor.

### Step 3: Compile & Deploy
1. Click the **Deploy** tab in GenLayer Studio.
2. The constructor arguments default to empty (`[]`).
3. Click **Deploy Contract**.
4. Confirm the transaction in your connected wallet.
5. The contract is deployed to Studio Dev / StudioNet:
   - **Live Contract Address:** `0x037d35F587555cAdE69840e19a1e1b58C65e4f7f`
   - **Target Network:** GenLayer Studio Dev (Chain ID: `61999`)
   - **Explorer / Verification:** Verified via GenLayer Studio

---

## 3. Configuring the Executive Observability Frontend

The frontend provides real-time SVG topological graph visualization, interactive node inspection, and direct on-chain transaction execution against GenLayer Studio Dev.

### Step 1: Configure Environment
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Copy the sample environment file (or configure directly in browser settings):
   ```bash
   echo "VITE_CASCADIA_CONTRACT_ADDRESS=0xYourDeployedContractAddress" > .env.local
   ```
   *(Alternatively, you can paste the contract address directly into the UI header Settings modal at runtime).*

### Step 2: Install Dependencies & Run Locally
```bash
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

### Step 3: Deploying Frontend to Vercel

The repository is configured for zero-config Vercel deployment with root and frontend `vercel.json` configurations.

#### Option A: Via Vercel Web Dashboard (Recommended)
1. Navigate to [https://vercel.com/new](https://vercel.com/new).
2. Import your GitHub repository: `9ja-maxx/cascadia`.
3. Vercel automatically detects the Vite configuration:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `./` (or `frontend`)
   - **Build Command:** `npm run build`
   - **Output Directory:** `frontend/dist` (or `dist` if root directory is set to `frontend`)
4. Add the following **Environment Variables**:
   - `VITE_CASCADIA_CONTRACT_ADDRESS`: `0x037d35F587555cAdE69840e19a1e1b58C65e4f7f`
   - `VITE_GENLAYER_CHAIN_ID`: `61999`
   - `VITE_GENLAYER_RPC_URL`: `https://studio-dev.genlayer.com/api`
5. Click **Deploy**.

#### Option B: Via Vercel CLI
```bash
# Install Vercel CLI if needed
npm install -g vercel

# Deploy from repository root
vercel --prod
```

---

## 4. Operational Playbook: Executing a Scenario

### Phase A: Anchor Genesis (Epoch 0)
1. In the Cascadia dashboard, click **"New Anchor"**.
2. Specify:
   - **Anchor ID:** `anchor-soc2-compliance`
   - **Title:** `Acme Corp SOC 2 Compliance`
   - **Hypothesis:** `Acme Corporation maintains active SOC 2 Type II compliance.`
   - **Web Target URI:** `https://registry.example.org/acme-soc2`
3. Click **"Deploy Anchor"**.
4. Validators fetch the URI content, record the SHA-256 content digest, and establish the factual baseline at epoch 0 (`ANCHOR_ACTIVE`).

### Phase B: Verdict Establishment
1. Click **"New Verdict"**.
2. Specify:
   - **Verdict ID:** `verdict-tier1-vendor`
   - **Title:** `Tier-1 Procurement Approval`
   - **Inquiry:** `Is Acme Corp authorized for Tier-1 vendor purchase orders?`
   - **Dependencies:** Select `anchor-soc2-compliance`.
3. Submit transaction. GenLayer consensus validators execute LLM reasoning over the upstream anchor and transition the node to `VERDICT_VALID`.

### Phase C: Observe External Mutation
1. To test real-time staleness cascades, trigger `observe_anchor("anchor-soc2-compliance")`.
2. When external content at the target URI changes or the audit expires, validators reach consensus on `ANCHOR_MUTATED`.
3. The reverse-edge cascade engine immediately propagates across dependent edges:
   - `anchor-soc2-compliance` -> `ANCHOR_MUTATED`
   - `verdict-tier1-vendor` -> `VERDICT_STALE`
4. Downstream smart contracts querying `is_verdict_valid("verdict-tier1-vendor")` will immediately receive `False`, halting unauthorized enterprise actions deterministically!

---

## 5. Automated Verification & Testing

To run the local contract test suite:
```bash
pytest -v tests/
```

To run the frontend topology layout tests:
```bash
cd frontend && node --test test/topology.test.js
```

To run topological acyclicity validation:
```bash
python3 scripts/validate_topology.py
```

To populate or verify live on-chain anchors and verdicts:
```bash
PRIVATE_KEY=0x... node scripts/populate_txns.cjs
```


