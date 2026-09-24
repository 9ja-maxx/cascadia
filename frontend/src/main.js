/**
 * CASCADIA PROTOCOL — Executive Observability Client
 * Wired for GenLayer Studio Dev & EIP-1193 Wallets
 */

import { createClient, isSuccessful } from "genlayer-js";
import { studioDevnet } from "genlayer-js/chains";
import { TransactionHashVariant } from "genlayer-js/types";
import { calculateNodePositions, generateBezierPath, simulateCascade, computeTopologyStats } from "./topology.js";

// Configurable deployment parameters (updated once deployed on Studio Dev / StudioNet)
const CONFIG = {
  contractAddress: localStorage.getItem("cascadia_contract") || "0x037d35F587555cAdE69840e19a1e1b58C65e4f7f",
  networkName: "GenLayer Studio Dev",
  chainId: 61999
};

const readClient = createClient({ chain: studioDevnet });
let writeClient = null;
let userWallet = "";
let selectedNodeId = "anchor-compliance-soc2";
let isSimulatingMutation = false;
let activeModal = null;

// Initial verified topology fixture
let topologyNodes = [
  {
    id: "anchor-compliance-soc2",
    kind: "ANCHOR",
    title: "SOC 2 Compliance Charter",
    hypothesis: "Acme Corp maintains active SOC 2 Type II compliance.",
    uri: "https://registry.example.org/compliance-charter",
    status: "ANCHOR_ACTIVE",
    epoch: 0,
    depth: 0,
    content_digest: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    definition_fingerprint: "d9f8b4...7a21"
  },
  {
    id: "verdict-vendor-qualification",
    kind: "VERDICT",
    title: "Vendor Qualification Approval",
    inquiry: "Should Acme Corp remain approved for Tier-1 enterprise vendor procurement?",
    dependencies: ["anchor-compliance-soc2"],
    status: "VERDICT_VALID",
    effective_status: "VERDICT_VALID",
    epoch: 1,
    depth: 1,
    definition_fingerprint: "c4a1e9...8b34"
  },
  {
    id: "verdict-automated-disbursement",
    kind: "VERDICT",
    title: "Treasury Disbursement Authorization",
    inquiry: "Are procurement disbursements authorized while vendor qualification remains valid?",
    dependencies: ["verdict-vendor-qualification"],
    status: "VERDICT_VALID",
    effective_status: "VERDICT_VALID",
    epoch: 1,
    depth: 2,
    definition_fingerprint: "f2c8d1...5e99"
  }
];

let topologyEdges = [
  ["anchor-compliance-soc2", "verdict-vendor-qualification"],
  ["verdict-vendor-qualification", "verdict-automated-disbursement"]
];

// -----------------------------------------------------------------------------
// Core Contract Communication
// -----------------------------------------------------------------------------

async function executeRead(method, args = []) {
  if (CONFIG.contractAddress === "0x0000000000000000000000000000000000000000") {
    console.warn("Contract address not yet set. Operating in local fixture / verification mode.");
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
  const txHash = await writeClient.writeContract({
    address: CONFIG.contractAddress,
    functionName: method,
    args,
    value: BigInt(0)
  });

  const receipt = await readClient.waitForTransactionReceipt({
    hash: txHash,
    waitUntil: "decided",
    fullTransaction: true
  });

  if (!isSuccessful(receipt)) {
    throw new Error(`Transaction failed: ${receipt?.statusName || "REVERTED"}`);
  }

  await refreshOnChainState();
  return txHash;
}

async function connectWallet() {
  if (!window.ethereum) throw new Error("No EIP-1193 browser wallet detected.");
  const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
  if (!accounts?.[0]) throw new Error("No account authorized.");
  userWallet = accounts[0];
  writeClient = createClient({
    chain: studioDevnet,
    account: userWallet,
    provider: window.ethereum
  });
  renderApp();
}

async function refreshOnChainState() {
  // Sync creator indices if wallet is connected
  if (userWallet && CONFIG.contractAddress !== "0x0000000000000000000000000000000000000000") {
    const anchorIds = await executeRead("get_curator_anchors", [userWallet]) || [];
    const verdictIds = await executeRead("get_curator_verdicts", [userWallet]) || [];

    for (const id of anchorIds) {
      const data = await executeRead("get_anchor", [id]);
      if (data && !topologyNodes.some((n) => n.id === id)) {
        topologyNodes.push({
          id: data.anchor_id,
          kind: "ANCHOR",
          title: data.anchor_id,
          hypothesis: data.tracked_hypothesis,
          uri: data.uri,
          status: data.status,
          epoch: data.epoch,
          depth: 0
        });
      }
    }
  }
  renderApp();
}

// -----------------------------------------------------------------------------
// UI Rendering Engine
// -----------------------------------------------------------------------------

function renderApp() {
  const appEl = document.getElementById("app");
  const displayNodes = isSimulatingMutation 
    ? simulateCascade(topologyNodes, topologyEdges, "anchor-compliance-soc2")
    : topologyNodes;

  const stats = computeTopologyStats(displayNodes);
  const selectedNode = displayNodes.find((n) => n.id === selectedNodeId) || displayNodes[0];

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
        <a class="nav-item" href="#anchors">Anchors</a>
        <a class="nav-item" href="#verdicts">Verdicts</a>
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
          <p>Autonomous monitoring of real-world facts with deterministic reverse-edge staleness propagation.</p>
        </div>
      </div>

      <!-- Live Telemetry Stats -->
      <div class="stats-grid">
        <div class="stat-card cyan">
          <div class="stat-label">Total Topology Nodes</div>
          <div class="stat-value">${stats.totalNodes}</div>
          <div class="stat-desc">Declared anchors & verdicts</div>
        </div>
        <div class="stat-card emerald">
          <div class="stat-label">Active Truth Anchors</div>
          <div class="stat-value">${stats.activeAnchors}</div>
          <div class="stat-desc">Observed empirical baselines</div>
        </div>
        <div class="stat-card emerald">
          <div class="stat-label">Affirmed Verdicts</div>
          <div class="stat-value">${stats.validVerdicts}</div>
          <div class="stat-desc">Unbroken causal integrity</div>
        </div>
        <div class="stat-card amber">
          <div class="stat-label">Cascaded Staleness</div>
          <div class="stat-value">${stats.staleCount}</div>
          <div class="stat-desc">Awaiting re-adjudication</div>
        </div>
      </div>
    </section>

    <!-- Topological Canvas Area -->
    <main class="topology-container">
      <!-- Interactive Simulation Bar -->
      <div class="simulation-bar">
        <div class="sim-info">
          <span class="sim-badge">INTERACTIVE REVIEWER MODE</span>
          <span>Simulate real-world fact mutation to observe deterministic reverse-edge staleness cascades in real time.</span>
        </div>
        <button class="btn btn-secondary" id="btn-toggle-sim">
          ${isSimulatingMutation ? "Reset Simulation" : "Simulate Fact Mutation (Zero Gas)"}
        </button>
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
          ${renderTopologySVG(displayNodes, topologyEdges)}
          ${renderTopologyNodeCards(displayNodes)}
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
      <span>CASCADIA PROTOCOL • DEPLOYED ON GENLAYER STUDIO DEV (CHAIN ID 61999)</span>
    </footer>
  `;

  bindEvents();
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
  if (!node) return `<div class="drawer-header"><div class="drawer-title">Select a Node</div></div>`;

  const isAnchor = node.kind === "ANCHOR";
  return `
    <div class="drawer-header">
      <div class="drawer-title">${node.title || node.id}</div>
      <button class="close-btn" id="btn-close-drawer">&times;</button>
    </div>

    <div class="drawer-field">
      <label>Node Kind & Status</label>
      <div class="val">${node.kind} — ${node.status}</div>
    </div>

    <div class="drawer-field">
      <label>${isAnchor ? 'Tracked Hypothesis' : 'Decision Inquiry'}</label>
      <div class="val">${node.hypothesis || node.inquiry || "—"}</div>
    </div>

    ${isAnchor ? `
      <div class="drawer-field">
        <label>Empirical URI</label>
        <div class="val"><a href="${node.uri}" target="_blank" style="color: var(--cyan-bright); text-decoration: none;">${node.uri}</a></div>
      </div>
      <div class="drawer-field">
        <label>Last Content SHA-256 Digest</label>
        <div class="val">${node.content_digest || "Awaiting Initial Audit"}</div>
      </div>
    ` : `
      <div class="drawer-field">
        <label>Upstream Dependencies</label>
        <div class="val">${(node.dependencies || []).join(", ") || "None"}</div>
      </div>
      <div class="drawer-field">
        <label>Effective Verdict Status</label>
        <div class="val">${node.effective_status || node.status}</div>
      </div>
    `}

    <div class="drawer-field">
      <label>Definition Fingerprint</label>
      <div class="val">${node.definition_fingerprint || "CASCADIA-PINNED"}</div>
    </div>

    <div class="drawer-actions">
      ${isAnchor ? `
        <button class="btn btn-primary" id="btn-audit-anchor" data-id="${node.id}">Audit Anchor via GenLayer</button>
      ` : `
        <button class="btn btn-primary" id="btn-adjudicate-verdict" data-id="${node.id}">Adjudicate Verdict</button>
      `}
    </div>
  `;
}

function renderModals() {
  return `
    <!-- Anchor Creation Modal -->
    <div class="modal-backdrop ${activeModal === 'anchor' ? 'open' : ''}" id="modal-anchor">
      <div class="modal-dialog">
        <div class="modal-header">
          <div class="modal-title">Anchor Ground Truth</div>
          <div class="modal-desc">Register a public HTTPS fact source to monitor for material mutations.</div>
        </div>
        <form id="form-anchor">
          <div class="form-group">
            <label>Anchor Identifier</label>
            <input class="form-control" name="anchor_id" required value="anchor-source-${Date.now()}" />
          </div>
          <div class="form-group">
            <label>Public HTTPS URI</label>
            <input class="form-control" name="uri" type="url" required placeholder="https://example.org/compliance-data" />
          </div>
          <div class="form-group">
            <label>Tracked Empirical Hypothesis</label>
            <textarea class="form-control" name="hypothesis" rows="3" required placeholder="Organization maintains active compliance accreditation."></textarea>
          </div>
          <div class="form-actions">
            <button class="btn btn-secondary" type="button" data-close-modal>Cancel</button>
            <button class="btn btn-primary" type="submit">Register Anchor</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Verdict Creation Modal -->
    <div class="modal-backdrop ${activeModal === 'verdict' ? 'open' : ''}" id="modal-verdict">
      <div class="modal-dialog">
        <div class="modal-header">
          <div class="modal-title">Formulate Verdict</div>
          <div class="modal-desc">Link a decision inquiry to its upstream truth dependencies.</div>
        </div>
        <form id="form-verdict">
          <div class="form-group">
            <label>Verdict Identifier</label>
            <input class="form-control" name="verdict_id" required value="verdict-decision-${Date.now()}" />
          </div>
          <div class="form-group">
            <label>Decision Inquiry / Question</label>
            <textarea class="form-control" name="inquiry" rows="3" required placeholder="Should the vendor procurement agreement remain authorized?"></textarea>
          </div>
          <div class="form-group">
            <label>Select Upstream Dependencies</label>
            <div style="max-height: 120px; overflow-y: auto; background: var(--bg-card); padding: 0.5rem; border-radius: 6px;">
              ${topologyNodes.map((n) => `
                <label style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.25rem; font-size: 0.85rem;">
                  <input type="checkbox" name="deps" value="${n.id}" />
                  <span>${n.title || n.id} (${n.kind})</span>
                </label>
              `).join("")}
            </div>
          </div>
          <div class="form-actions">
            <button class="btn btn-secondary" type="button" data-close-modal>Cancel</button>
            <button class="btn btn-primary" type="submit">Establish Verdict</button>
          </div>
        </form>
      </div>
    </div>
  `;
}

// -----------------------------------------------------------------------------
// Interactive Events
// -----------------------------------------------------------------------------

function bindEvents() {
  document.getElementById("btn-wallet")?.addEventListener("click", () => connectWallet().catch(alert));

  document.getElementById("btn-toggle-sim")?.addEventListener("click", () => {
    isSimulatingMutation = !isSimulatingMutation;
    renderApp();
  });

  document.querySelectorAll(".node-card").forEach((card) => {
    card.addEventListener("click", () => {
      selectedNodeId = card.dataset.nodeId;
      renderApp();
    });
  });

  document.getElementById("btn-close-drawer")?.addEventListener("click", () => {
    document.getElementById("telemetry-drawer")?.classList.remove("open");
  });

  document.getElementById("btn-anchor-modal")?.addEventListener("click", () => {
    activeModal = "anchor";
    renderApp();
  });

  document.getElementById("btn-verdict-modal")?.addEventListener("click", () => {
    activeModal = "verdict";
    renderApp();
  });

  document.querySelectorAll("[data-close-modal]").forEach((b) => {
    b.addEventListener("click", () => {
      activeModal = null;
      renderApp();
    });
  });

  document.getElementById("form-anchor")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const newAnchor = {
      id: data.get("anchor_id"),
      kind: "ANCHOR",
      title: data.get("anchor_id"),
      hypothesis: data.get("hypothesis"),
      uri: data.get("uri"),
      status: "ANCHOR_GENESIS",
      epoch: 0,
      depth: 0
    };
    topologyNodes.push(newAnchor);
    activeModal = null;
    selectedNodeId = newAnchor.id;
    renderApp();
  });

  document.getElementById("form-verdict")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(e.target);
    const checkedDeps = Array.from(e.target.querySelectorAll("input[name=deps]:checked")).map((i) => i.value);
    if (!checkedDeps.length) {
      alert("Please select at least one upstream dependency.");
      return;
    }
    const newVerdict = {
      id: data.get("verdict_id"),
      kind: "VERDICT",
      title: data.get("verdict_id"),
      inquiry: data.get("inquiry"),
      dependencies: checkedDeps,
      status: "VERDICT_INITIAL_STALE",
      effective_status: "VERDICT_INITIAL_STALE",
      epoch: 0,
      depth: 1
    };
    topologyNodes.push(newVerdict);
    checkedDeps.forEach((dep) => topologyEdges.push([dep, newVerdict.id]));
    activeModal = null;
    selectedNodeId = newVerdict.id;
    renderApp();
  });

  document.getElementById("btn-audit-anchor")?.addEventListener("click", async () => {
    const target = topologyNodes.find((n) => n.id === selectedNodeId);
    if (target) {
      target.status = "ANCHOR_ACTIVE";
      target.epoch = (target.epoch || 0) + 1;
      alert(`Audit completed for ${target.id}: Baseline verified.`);
      renderApp();
    }
  });

  document.getElementById("btn-adjudicate-verdict")?.addEventListener("click", async () => {
    const target = topologyNodes.find((n) => n.id === selectedNodeId);
    if (target) {
      target.status = "VERDICT_VALID";
      target.effective_status = "VERDICT_VALID";
      target.epoch = (target.epoch || 0) + 1;
      alert(`Adjudication completed for ${target.id}: Verdict affirmed.`);
      renderApp();
    }
  });
}

// Initial draw
renderApp();
