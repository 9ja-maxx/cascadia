/**
 * CASCADIA PROTOCOL — Executive Observability Client
 * 100% Live On-Chain Synchronization with GenLayer Intelligent Contracts
 * Zero Mock Data • Zero Simulated Fallbacks
 */

import { createClient, isSuccessful } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";
import { TransactionHashVariant } from "genlayer-js/types";
import {
  calculateNodePositions,
  generateBezierPath,
  buildGraphEdges,
  computeTopologyStats
} from "./topology.js";

// Configurable deployment parameters wired to deployed contract
const CONFIG = {
  contractAddress: localStorage.getItem("cascadia_contract") || "0x037d35F587555cAdE69840e19a1e1b58C65e4f7f",
  networkName: "GenLayer Studio Dev",
  chainId: 61999
};

const readClient = createClient({ chain: studioDevnet });
let writeClient = null;
let userWallet = "";
let selectedNodeId = null;
let isSyncing = false;
let activeModal = null;
let actionFeedback = "";
let effectiveStatusResult = null;

// 100% Live On-Chain State (Empty by default until synced from blockchain)
let topologyNodes = [];
let topologyEdges = [];

// Node ID tracking across transactions for this deployed contract
function getKnownNodeIds() {
  try {
    const raw = localStorage.getItem(`cascadia_nodes_${CONFIG.contractAddress}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function rememberNodeId(id) {
  const ids = getKnownNodeIds();
  if (!ids.includes(id)) {
    ids.push(id);
    localStorage.setItem(`cascadia_nodes_${CONFIG.contractAddress}`, JSON.stringify(ids));
  }
}

// -----------------------------------------------------------------------------
// Core On-Chain Contract Communication
// -----------------------------------------------------------------------------

async function executeRead(method, args = []) {
  if (!CONFIG.contractAddress || CONFIG.contractAddress === "0x0000000000000000000000000000000000000000") {
    return null;
  }
  try {
    const raw = await readClient.readContract({
      address: CONFIG.contractAddress,
      functionName: method,
      args,
      jsonSafeReturn: true,
      transactionHashVariant: TransactionHashVariant.LATEST_NONFINAL
    });
    return typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch (err) {
    console.error(`Read failed on ${method}:`, err);
    return null;
  }
}

async function executeWrite(method, args) {
  if (!writeClient) await connectWallet();
  actionFeedback = `Submitting on-chain transaction: ${method}...`;
  renderApp();

  const txHash = await writeClient.writeContract({
    address: CONFIG.contractAddress,
    functionName: method,
    args,
    value: BigInt(0)
  });

  actionFeedback = `Transaction broadcast (${txHash.slice(0, 10)}…). Awaiting validator consensus...`;
  renderApp();

  const receipt = await readClient.waitForTransactionReceipt({
    hash: txHash,
    waitUntil: "decided",
    fullTransaction: true
  });

  if (!isSuccessful(receipt)) {
    throw new Error(`Transaction reverted: ${receipt?.statusName || "CONSENSUS_REVERTED"}`);
  }

  actionFeedback = `Transaction confirmed on-chain! Synced.`;
  await refreshOnChainState();
  return txHash;
}

async function connectWallet() {
  if (!window.ethereum) throw new Error("No EIP-1193 browser wallet detected.");
  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  if (!accounts?.[0]) throw new Error("No account authorized.");
  userWallet = accounts[0].toLowerCase();
  writeClient = createClient({
    chain: studioDevnet,
    account: userWallet,
    provider: window.ethereum
  });
  await refreshOnChainState();
}

async function refreshOnChainState() {
  isSyncing = true;
  renderApp();

  const knownIds = new Set(getKnownNodeIds());

  // Query curator indexes if wallet is connected
  if (userWallet && CONFIG.contractAddress) {
    try {
      const userAnchors = await executeRead("get_curator_anchors", [userWallet]) || [];
      const userVerdicts = await executeRead("get_curator_verdicts", [userWallet]) || [];
      userAnchors.forEach((id) => { knownIds.add(id); rememberNodeId(id); });
      userVerdicts.forEach((id) => { knownIds.add(id); rememberNodeId(id); });
    } catch (e) {
      console.warn("Could not query curator index:", e);
    }
  }

  const loadedNodes = [];

  for (const id of Array.from(knownIds)) {
    try {
      // Try loading as anchor first
      const anchorData = await executeRead("get_anchor", [id]);
      if (anchorData && anchorData.anchor_id) {
        loadedNodes.push({
          id: anchorData.anchor_id,
          kind: "ANCHOR",
          title: anchorData.anchor_id,
          hypothesis: anchorData.tracked_hypothesis,
          uri: anchorData.uri,
          status: anchorData.status,
          epoch: anchorData.epoch,
          depth: 0,
          custodian: anchorData.custodian,
          content_digest: anchorData.content_digest,
          semantic_snapshot: anchorData.semantic_snapshot,
          definition_fingerprint: anchorData.definition_fingerprint,
          epoch_fingerprint: anchorData.epoch_fingerprint
        });
        continue;
      }
    } catch {
      // Not an anchor
    }

    try {
      // Try loading as verdict
      const verdictData = await executeRead("get_verdict", [id]);
      if (verdictData && verdictData.verdict_id) {
        loadedNodes.push({
          id: verdictData.verdict_id,
          kind: "VERDICT",
          title: verdictData.verdict_id,
          inquiry: verdictData.inquiry,
          dependencies: verdictData.dependencies || [],
          status: verdictData.status,
          effective_status: verdictData.effective_status,
          epoch: verdictData.epoch,
          depth: verdictData.topology_depth || 1,
          curator: verdictData.curator,
          adjudication: verdictData.adjudication,
          definition_fingerprint: verdictData.definition_fingerprint,
          epoch_fingerprint: verdictData.epoch_fingerprint
        });
      }
    } catch {
      // Not a verdict
    }
  }

  topologyNodes = loadedNodes;
  topologyEdges = buildGraphEdges(topologyNodes);

  if (topologyNodes.length > 0 && (!selectedNodeId || !topologyNodes.some((n) => n.id === selectedNodeId))) {
    selectedNodeId = topologyNodes[0].id;
  }

  isSyncing = false;
  renderApp();
}

// -----------------------------------------------------------------------------
// UI Rendering Engine (100% Real On-Chain)
// -----------------------------------------------------------------------------

function renderApp() {
  const appEl = document.getElementById("app");
  const stats = computeTopologyStats(topologyNodes);
  const selectedNode = topologyNodes.find((n) => n.id === selectedNodeId) || null;

  appEl.innerHTML = `
    <!-- Top Navigation -->
    <header class="topbar">
      <div class="brand-cluster">
        <a class="brand-logo" href="#">
          <span class="brand-icon">C</span>
          CASCADIA
        </a>
        <div class="network-pill">
          <span class="pulse-dot"></span>
          ${CONFIG.networkName}
        </div>
      </div>

      <nav class="nav-links">
        <a class="nav-item active" href="#">Topological Graph</a>
        <a class="nav-item" href="#anchors">Anchors (${stats.anchors})</a>
        <a class="nav-item" href="#verdicts">Verdicts (${stats.verdicts})</a>
      </nav>

      <div class="nav-cta-cluster">
        <button class="btn btn-secondary" id="btn-anchor-modal">+ Anchor Truth</button>
        <button class="btn btn-primary" id="btn-verdict-modal">+ Formulate Verdict</button>
        <button class="btn btn-wallet" id="btn-wallet">
          ${userWallet ? `${userWallet.slice(0, 6)}…${userWallet.slice(-4)}` : "Connect Wallet"}
        </button>
      </div>
    </header>

    <!-- Executive Overview Strip -->
    <section class="dashboard-header">
      <div class="dashboard-title-row">
        <div class="dashboard-heading">
          <h1>Causal Truth Mesh</h1>
          <p>Autonomous monitoring of real-world facts with deterministic reverse-edge staleness cascades on GenLayer.</p>
        </div>
      </div>

      <!-- Live Telemetry Stats -->
      <div class="stats-grid">
        <div class="stat-card cyan">
          <div class="stat-label">Total On-Chain Nodes</div>
          <div class="stat-value">${stats.totalNodes}</div>
          <div class="stat-desc">Live on GenLayer contract</div>
        </div>
        <div class="stat-card emerald">
          <div class="stat-label">Active Truth Anchors</div>
          <div class="stat-value">${stats.activeAnchors}</div>
          <div class="stat-desc">Observed empirical baselines</div>
        </div>
        <div class="stat-card emerald">
          <div class="stat-label">Affirmed Verdicts</div>
          <div class="stat-value">${stats.validVerdicts}</div>
          <div class="stat-desc">Consensus verified decisions</div>
        </div>
        <div class="stat-card amber">
          <div class="stat-label">Cascaded Staleness</div>
          <div class="stat-value">${stats.staleCount}</div>
          <div class="stat-desc">Invalidated by upstream shifts</div>
        </div>
      </div>
    </section>

    <!-- Topological Canvas Area -->
    <main class="topology-container">
      <!-- Live Contract Status Bar (Zero Mock Data) -->
      <div class="live-contract-bar">
        <div class="contract-info">
          <span class="live-badge">LIVE ON-CHAIN</span>
          <span class="contract-address">Contract: <code>${CONFIG.contractAddress}</code></span>
          ${isSyncing ? `<span style="color: var(--cyan-bright); font-size: 0.8rem;">⟳ Syncing blockchain state...</span>` : ""}
          ${actionFeedback ? `<span style="color: var(--emerald); font-size: 0.8rem; font-weight: 500;">${actionFeedback}</span>` : ""}
        </div>
        <div class="contract-actions">
          <button class="btn btn-secondary btn-sm" id="btn-refresh-chain">⟳ Refresh State</button>
          <button class="btn btn-secondary btn-sm" id="btn-config-contract">Settings</button>
        </div>
      </div>

      <div class="canvas-wrapper">
        <div class="canvas-toolbar">
          <div class="canvas-legend">
            <div class="legend-item"><span class="legend-swatch cyan"></span> Genesis / Pending</div>
            <div class="legend-item"><span class="legend-swatch emerald"></span> Active / Valid</div>
            <div class="legend-item"><span class="legend-swatch amber"></span> Mutated / Stale</div>
          </div>
        </div>

        <div class="dag-canvas" id="dag-canvas">
          ${topologyNodes.length === 0 ? renderEmptyState() : `
            ${renderTopologySVG(topologyNodes, topologyEdges)}
            ${renderTopologyNodeCards(topologyNodes)}
          `}
        </div>
      </div>
    </main>

    <!-- Slide-over Telemetry Drawer -->
    <aside class="telemetry-drawer ${selectedNode ? 'open' : ''}" id="telemetry-drawer">
      ${renderTelemetryDrawer(selectedNode)}
    </aside>

    <!-- Modals -->
    ${renderModals()}

    <footer class="footer">
      <span>CASCADIA PROTOCOL • DEPLOYED AT ${CONFIG.contractAddress} • GENLAYER STUDIO DEV (CHAIN ID 61999)</span>
    </footer>
  `;

  bindEvents();
}

function renderEmptyState() {
  return `
    <div class="empty-state-card">
      <div class="empty-state-icon">⚡</div>
      <h3>No On-Chain Nodes Registered Yet</h3>
      <p>Contract <code>${CONFIG.contractAddress}</code> is deployed and active on GenLayer Studio Dev. Register your first empirical anchor to establish real on-chain ground truth.</p>
      <div class="empty-state-actions">
        <button class="btn btn-primary" id="btn-empty-anchor">+ Register First Anchor</button>
        ${!userWallet ? `<button class="btn btn-secondary" id="btn-empty-wallet">Connect Wallet</button>` : ""}
      </div>
    </div>
  `;
}

function renderTopologySVG(nodes, edges) {
  const positions = calculateNodePositions(nodes);
  const pathElements = edges.map(([parent, child]) => {
    const start = positions.get(parent);
    const end = positions.get(child);
    if (!start || !end) return "";

    const pathD = generateBezierPath(start.x + 130, start.y, end.x - 130, end.y);
    const parentNode = nodes.find((n) => n.id === parent);
    const isStale = parentNode?.status?.includes("MUTATED") || parentNode?.status?.includes("STALE");

    return `<path class="dag-edge ${isStale ? 'stale' : 'active'}" d="${pathD}" />`;
  }).join("");

  return `<svg class="dag-svg" viewBox="0 0 1000 480" preserveAspectRatio="none">${pathElements}</svg>`;
}

function renderTopologyNodeCards(nodes) {
  const positions = calculateNodePositions(nodes);
  return nodes.map((node) => {
    const pos = positions.get(node.id) || { x: 200, y: 200 };
    const statusClass = node.status?.toLowerCase().replace("anchor_", "").replace("verdict_", "") || "genesis";
    const isSelected = node.id === selectedNodeId;

    return `
      <div class="node-card ${isSelected ? 'selected' : ''}" 
           style="left: ${pos.x}px; top: ${pos.y}px;" 
           data-node-id="${node.id}">
        <div class="node-header">
          <span class="node-kind">${node.kind}</span>
          <span class="status-pill ${statusClass}">${node.status}</span>
        </div>
        <div class="node-title">${node.title || node.id}</div>
        <div class="node-claim">${node.hypothesis || node.inquiry || ""}</div>
        <div class="node-footer">
          <span>Epoch: ${node.epoch ?? 0}</span>
          <span>Depth: ${node.depth ?? 0}</span>
        </div>
      </div>
    `;
  }).join("");
}

function renderTelemetryDrawer(node) {
  if (!node) {
    return `
      <div class="drawer-header">
        <div class="drawer-title">Node Telemetry</div>
      </div>
      <div class="drawer-body">
        <p style="color: var(--text-secondary); font-size: 0.9rem;">Select any node from the DAG to view on-chain proofs and trigger validator actions.</p>
      </div>
    `;
  }

  const isAnchor = node.kind === "ANCHOR";

  return `
    <div class="drawer-header">
      <div class="drawer-title">${node.title || node.id}</div>
      <button class="drawer-close" id="btn-close-drawer">✕</button>
    </div>

    <div class="drawer-body">
      <div class="detail-block">
        <div class="detail-label">NODE IDENTIFIER</div>
        <div class="detail-value">${node.id}</div>
      </div>

      <div class="detail-block">
        <div class="detail-label">NODE CLASSIFICATION</div>
        <div class="detail-value"><span class="node-kind">${node.kind}</span> (Depth ${node.depth})</div>
      </div>

      <div class="detail-block">
        <div class="detail-label">ON-CHAIN STATUS</div>
        <div class="detail-value">
          <span class="status-pill ${node.status?.toLowerCase().replace("anchor_", "").replace("verdict_", "")}">
            ${node.status}
          </span>
        </div>
      </div>

      ${isAnchor ? `
        <div class="detail-block">
          <div class="detail-label">OBSERVED HTTPS ENDPOINT</div>
          <div class="detail-value" style="font-family: var(--font-mono); font-size: 0.78rem; word-break: break-all;">
            <a href="${node.uri}" target="_blank" rel="noopener" style="color: var(--cyan-bright);">${node.uri}</a>
          </div>
        </div>

        <div class="detail-block">
          <div class="detail-label">TRACKED FACTUAL HYPOTHESIS</div>
          <div class="detail-value">${node.hypothesis}</div>
        </div>

        <div class="detail-block">
          <div class="detail-label">CONTENT DIGEST (SHA-256)</div>
          <div class="detail-value" style="font-family: var(--font-mono); font-size: 0.75rem; word-break: break-all;">
            ${node.content_digest || "Pending first audit on-chain"}
          </div>
        </div>
      ` : `
        <div class="detail-block">
          <div class="detail-label">REASONED INQUIRY</div>
          <div class="detail-value">${node.inquiry}</div>
        </div>

        <div class="detail-block">
          <div class="detail-label">DECLARED UPSTREAM DEPENDENCIES</div>
          <div class="detail-value">
            ${node.dependencies?.length ? node.dependencies.map((d) => `<span class="dep-pill">${d}</span>`).join(" ") : "None"}
          </div>
        </div>

        <div class="detail-block">
          <div class="detail-label">EFFECTIVE RECURSIVE STATUS</div>
          <div class="detail-value">
            <span class="status-pill">${node.effective_status || node.status}</span>
          </div>
        </div>
      `}

      <div class="detail-block">
        <div class="detail-label">DEFINITION FINGERPRINT</div>
        <div class="detail-value" style="font-family: var(--font-mono); font-size: 0.75rem; word-break: break-all;">
          ${node.definition_fingerprint || "—"}
        </div>
      </div>

      ${effectiveStatusResult ? `
        <div class="detail-block" style="background: rgba(0,240,255,0.06); padding: 0.75rem; border-radius: 6px;">
          <div class="detail-label">ON-CHAIN VERIFICATION RESULT</div>
          <div class="detail-value" style="color: var(--cyan-bright); font-weight: 600;">
            ${effectiveStatusResult}
          </div>
        </div>
      ` : ""}

      <!-- Real On-Chain Action Operations -->
      <div class="drawer-actions">
        ${isAnchor ? `
          <button class="btn btn-primary" id="btn-audit-anchor" style="width: 100%; margin-bottom: 0.5rem;">
            ⚡ Run On-Chain Web Observation (Audit)
          </button>
        ` : `
          <button class="btn btn-primary" id="btn-adjudicate-verdict" style="width: 100%; margin-bottom: 0.5rem;">
            ⚡ Run On-Chain LLM Consensus (Adjudicate)
          </button>
          <button class="btn btn-secondary" id="btn-verify-effective" style="width: 100%; margin-bottom: 0.5rem;">
            🔍 Check Recursive Health (Zero Gas)
          </button>
        `}
      </div>
    </div>
  `;
}

function renderModals() {
  if (!activeModal) return "";

  if (activeModal === "anchor") {
    return `
      <div class="modal-backdrop" id="modal-backdrop">
        <div class="modal-dialog">
          <div class="modal-header">
            <div class="modal-title">Anchor Empirical Ground Truth</div>
            <button class="modal-close" id="btn-modal-close">✕</button>
          </div>
          <form id="form-create-anchor" class="modal-body">
            <div class="form-group">
              <label class="form-label">Anchor Identifier</label>
              <input type="text" class="form-input" id="inp-anchor-id" placeholder="e.g. anchor-compliance-iso" required />
            </div>
            <div class="form-group">
              <label class="form-label">Observed Web Endpoint (HTTPS)</label>
              <input type="url" class="form-input" id="inp-anchor-uri" placeholder="https://registry.example.org/cert.json" required />
            </div>
            <div class="form-group">
              <label class="form-label">Tracked Empirical Hypothesis</label>
              <textarea class="form-textarea" id="inp-anchor-hypothesis" rows="3" placeholder="State the exact factual claim that validators must continuously verify against the URL..." required></textarea>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" id="btn-modal-cancel">Cancel</button>
              <button type="submit" class="btn btn-primary">Register Anchor On-Chain</button>
            </div>
          </form>
        </div>
      </div>
    `;
  }

  if (activeModal === "verdict") {
    return `
      <div class="modal-backdrop" id="modal-backdrop">
        <div class="modal-dialog">
          <div class="modal-header">
            <div class="modal-title">Establish Causal Verdict</div>
            <button class="modal-close" id="btn-modal-close">✕</button>
          </div>
          <form id="form-create-verdict" class="modal-body">
            <div class="form-group">
              <label class="form-label">Verdict Identifier</label>
              <input type="text" class="form-input" id="inp-verdict-id" placeholder="e.g. verdict-credit-facility" required />
            </div>
            <div class="form-group">
              <label class="form-label">Reasoned Inquiry</label>
              <textarea class="form-textarea" id="inp-verdict-inquiry" rows="3" placeholder="Specify the decision question to be evaluated by consensus validators..." required></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">Upstream Dependencies (Select 1 or more)</label>
              <div class="dep-selector">
                ${topologyNodes.length === 0 ? `<p style="color: var(--text-muted); font-size: 0.85rem;">No nodes registered yet. Register an Anchor first.</p>` : ""}
                ${topologyNodes.map((n) => `
                  <label class="dep-checkbox-label">
                    <input type="checkbox" name="deps" value="${n.id}" />
                    <span><strong>${n.id}</strong> (${n.kind})</span>
                  </label>
                `).join("")}
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" id="btn-modal-cancel">Cancel</button>
              <button type="submit" class="btn btn-primary">Establish Verdict On-Chain</button>
            </div>
          </form>
        </div>
      </div>
    `;
  }

  if (activeModal === "settings") {
    return `
      <div class="modal-backdrop" id="modal-backdrop">
        <div class="modal-dialog">
          <div class="modal-header">
            <div class="modal-title">Protocol Contract Settings</div>
            <button class="modal-close" id="btn-modal-close">✕</button>
          </div>
          <form id="form-settings" class="modal-body">
            <div class="form-group">
              <label class="form-label">Intelligent Contract Address</label>
              <input type="text" class="form-input" id="inp-settings-contract" value="${CONFIG.contractAddress}" required />
            </div>
            <div class="form-group">
              <label class="form-label">Network RPC</label>
              <input type="text" class="form-input" value="https://studio-dev.genlayer.com/api" disabled />
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" id="btn-modal-cancel">Cancel</button>
              <button type="submit" class="btn btn-primary">Save Settings</button>
            </div>
          </form>
        </div>
      </div>
    `;
  }

  return "";
}

// -----------------------------------------------------------------------------
// DOM Event Listeners & Interactive Handlers
// -----------------------------------------------------------------------------

function bindEvents() {
  document.getElementById("btn-wallet")?.addEventListener("click", () => {
    connectWallet().catch((err) => alert(err.message));
  });

  document.getElementById("btn-empty-wallet")?.addEventListener("click", () => {
    connectWallet().catch((err) => alert(err.message));
  });

  document.getElementById("btn-refresh-chain")?.addEventListener("click", () => {
    refreshOnChainState().catch((err) => alert(err.message));
  });

  document.getElementById("btn-config-contract")?.addEventListener("click", () => {
    activeModal = "settings";
    renderApp();
  });

  document.getElementById("btn-anchor-modal")?.addEventListener("click", () => {
    activeModal = "anchor";
    renderApp();
  });

  document.getElementById("btn-empty-anchor")?.addEventListener("click", () => {
    activeModal = "anchor";
    renderApp();
  });

  document.getElementById("btn-verdict-modal")?.addEventListener("click", () => {
    activeModal = "verdict";
    renderApp();
  });

  document.getElementById("btn-modal-close")?.addEventListener("click", () => {
    activeModal = null;
    renderApp();
  });

  document.getElementById("btn-modal-cancel")?.addEventListener("click", () => {
    activeModal = null;
    renderApp();
  });

  document.getElementById("btn-close-drawer")?.addEventListener("click", () => {
    selectedNodeId = null;
    effectiveStatusResult = null;
    renderApp();
  });

  // Node selection from canvas cards
  document.querySelectorAll(".node-card").forEach((card) => {
    card.addEventListener("click", () => {
      selectedNodeId = card.getAttribute("data-node-id");
      effectiveStatusResult = null;
      renderApp();
    });
  });

  // Create Anchor Form
  document.getElementById("form-create-anchor")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("inp-anchor-id").value.trim();
    const uri = document.getElementById("inp-anchor-uri").value.trim();
    const hypothesis = document.getElementById("inp-anchor-hypothesis").value.trim();

    try {
      activeModal = null;
      rememberNodeId(id);
      await executeWrite("register_anchor", [id, uri, hypothesis]);
    } catch (err) {
      alert(`Anchor registration failed: ${err.message}`);
    }
  });

  // Create Verdict Form
  document.getElementById("form-create-verdict")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("inp-verdict-id").value.trim();
    const inquiry = document.getElementById("inp-verdict-inquiry").value.trim();
    const checkboxes = document.querySelectorAll('input[name="deps"]:checked');
    const dependencies = Array.from(checkboxes).map((cb) => cb.value);

    if (dependencies.length === 0) {
      alert("Please select at least one upstream dependency.");
      return;
    }

    try {
      activeModal = null;
      rememberNodeId(id);
      await executeWrite("establish_verdict", [id, inquiry, dependencies]);
    } catch (err) {
      alert(`Verdict establishment failed: ${err.message}`);
    }
  });

  // Settings Form
  document.getElementById("form-settings")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const newAddress = document.getElementById("inp-settings-contract").value.trim();
    if (newAddress) {
      CONFIG.contractAddress = newAddress;
      localStorage.setItem("cascadia_contract", newAddress);
      activeModal = null;
      refreshOnChainState().catch(console.error);
    }
  });

  // Action: Audit Anchor On-Chain
  document.getElementById("btn-audit-anchor")?.addEventListener("click", async () => {
    if (!selectedNodeId) return;
    try {
      await executeWrite("audit_anchor", [selectedNodeId]);
    } catch (err) {
      alert(`Audit transaction failed: ${err.message}`);
    }
  });

  // Action: Adjudicate Verdict On-Chain
  document.getElementById("btn-adjudicate-verdict")?.addEventListener("click", async () => {
    if (!selectedNodeId) return;
    try {
      await executeWrite("adjudicate_verdict", [selectedNodeId]);
    } catch (err) {
      alert(`Adjudication transaction failed: ${err.message}`);
    }
  });

  // Action: Verify Effective Status (Zero-Gas Read)
  document.getElementById("btn-verify-effective")?.addEventListener("click", async () => {
    if (!selectedNodeId) return;
    try {
      const result = await executeRead("evaluate_effective_verdict", [selectedNodeId]);
      effectiveStatusResult = result || "Unknown";
      renderApp();
    } catch (err) {
      alert(`Verification call failed: ${err.message}`);
    }
  });
}

// Initial Bootstrapping: Auto-sync on-chain state on page load
refreshOnChainState().catch((err) => {
  console.log("Initial on-chain sync notice:", err);
  renderApp();
});
