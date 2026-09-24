/**
 * CASCADIA PROTOCOL — Topological Layout & Cascade Simulation Engine
 */

export function calculateNodePositions(nodes, canvasWidth = 1000, canvasHeight = 440) {
  // Group nodes by depth
  const layers = new Map();
  nodes.forEach((node) => {
    const depth = node.depth ?? (node.kind === "ANCHOR" ? 0 : 1);
    if (!layers.has(depth)) layers.set(depth, []);
    layers.get(depth).push(node);
  });

  const sortedDepths = Array.from(layers.keys()).sort((a, b) => a - b);
  const totalLayers = sortedDepths.length;
  const colSpacing = totalLayers > 1 ? (canvasWidth - 360) / (totalLayers - 1) : 0;

  const positions = new Map();

  sortedDepths.forEach((depth, colIndex) => {
    const layerNodes = layers.get(depth);
    const rowSpacing = canvasHeight / (layerNodes.length + 1);

    layerNodes.forEach((node, rowIndex) => {
      const x = 180 + colIndex * colSpacing;
      const y = (rowIndex + 1) * rowSpacing;
      positions.set(node.id, { x, y });
    });
  });

  return positions;
}

export function generateBezierPath(startX, startY, endX, endY) {
  const dx = endX - startX;
  const cp1x = startX + dx * 0.5;
  const cp1y = startY;
  const cp2x = startX + dx * 0.5;
  const cp2y = endY;

  return `M ${startX} ${startY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${endX} ${endY}`;
}

export function simulateCascade(nodes, edges, targetAnchorId) {
  // Clone nodes
  const updatedNodes = nodes.map((n) => ({ ...n }));
  const nodeMap = new Map(updatedNodes.map((n) => [n.id, n]));

  const target = nodeMap.get(targetAnchorId);
  if (!target) return updatedNodes;

  target.status = "ANCHOR_MUTATED";

  // Build reverse adjacency list: parent -> [children]
  const reverseAdj = new Map();
  edges.forEach(([parent, child]) => {
    if (!reverseAdj.has(parent)) reverseAdj.set(parent, []);
    reverseAdj.get(parent).push(child);
  });

  // Breadth-first staleness cascade
  const queue = [targetAnchorId];
  const visited = new Set();

  while (queue.length > 0) {
    const curr = queue.shift();
    if (visited.has(curr)) continue;
    visited.add(curr);

    const dependents = reverseAdj.get(curr) || [];
    dependents.forEach((depId) => {
      const depNode = nodeMap.get(depId);
      if (depNode && depNode.kind === "VERDICT") {
        depNode.status = "VERDICT_STALE";
        depNode.effective_status = "VERDICT_STALE";
      }
      queue.push(depId);
    });
  }

  return updatedNodes;
}

export function computeTopologyStats(nodes) {
  let anchors = 0;
  let activeAnchors = 0;
  let verdicts = 0;
  let validVerdicts = 0;
  let staleCount = 0;

  nodes.forEach((n) => {
    if (n.kind === "ANCHOR") {
      anchors++;
      if (n.status === "ANCHOR_ACTIVE") activeAnchors++;
      if (n.status === "ANCHOR_MUTATED" || n.status === "ANCHOR_DEGRADED") staleCount++;
    } else {
      verdicts++;
      if (n.status === "VERDICT_VALID") validVerdicts++;
      if (n.status === "VERDICT_STALE" || n.status === "VERDICT_INITIAL_STALE") staleCount++;
    }
  });

  return {
    totalNodes: nodes.length,
    anchors,
    activeAnchors,
    verdicts,
    validVerdicts,
    staleCount
  };
}
