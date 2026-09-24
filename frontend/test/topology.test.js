import test from "node:test";
import assert from "node:assert/strict";
import {
  calculateNodePositions,
  generateBezierPath,
  simulateCascade,
  computeTopologyStats
} from "../src/topology.js";

test("calculateNodePositions computes deterministic 2D coordinates across DAG depths", () => {
  const nodes = [
    { id: "a1", depth: 0, kind: "ANCHOR" },
    { id: "v1", depth: 1, kind: "VERDICT" },
    { id: "v2", depth: 2, kind: "VERDICT" }
  ];

  const positions = calculateNodePositions(nodes, 1000, 400);

  assert.equal(positions.size, 3);
  assert.ok(positions.has("a1"));
  assert.ok(positions.has("v1"));
  assert.ok(positions.has("v2"));

  const posA = positions.get("a1");
  const posV1 = positions.get("v1");
  const posV2 = positions.get("v2");

  // Higher depth must be rendered further to the right (x increases)
  assert.ok(posV1.x > posA.x, "Depth 1 node x coordinate should exceed depth 0 node x coordinate");
  assert.ok(posV2.x > posV1.x, "Depth 2 node x coordinate should exceed depth 1 node x coordinate");
  assert.ok(posA.y > 0 && posA.y < 400);
});

test("generateBezierPath outputs valid SVG cubic bezier command", () => {
  const path = generateBezierPath(100, 150, 300, 250);
  assert.equal(typeof path, "string");
  assert.ok(path.startsWith("M 100 150 C"));
  assert.ok(path.endsWith("300 250"));
});

test("simulateCascade propagates mutation status to downstream dependent verdicts", () => {
  const nodes = [
    { id: "anchor-sec", kind: "ANCHOR", status: "ANCHOR_ACTIVE" },
    { id: "verdict-kyc", kind: "VERDICT", status: "VERDICT_VALID", effective_status: "VERDICT_VALID" },
    { id: "verdict-loan", kind: "VERDICT", status: "VERDICT_VALID", effective_status: "VERDICT_VALID" },
    { id: "anchor-unrelated", kind: "ANCHOR", status: "ANCHOR_ACTIVE" }
  ];

  const edges = [
    ["anchor-sec", "verdict-kyc"],
    ["verdict-kyc", "verdict-loan"]
  ];

  const cascaded = simulateCascade(nodes, edges, "anchor-sec");

  const anchorSec = cascaded.find((n) => n.id === "anchor-sec");
  const verdictKyc = cascaded.find((n) => n.id === "verdict-kyc");
  const verdictLoan = cascaded.find((n) => n.id === "verdict-loan");
  const unrelated = cascaded.find((n) => n.id === "anchor-unrelated");

  assert.equal(anchorSec.status, "ANCHOR_MUTATED");
  assert.equal(verdictKyc.effective_status, "VERDICT_STALE");
  assert.equal(verdictLoan.effective_status, "VERDICT_STALE");
  assert.equal(unrelated.status, "ANCHOR_ACTIVE");
});

test("computeTopologyStats aggregates metrics accurately", () => {
  const nodes = [
    { id: "a1", kind: "ANCHOR", depth: 0, status: "ANCHOR_ACTIVE" },
    { id: "a2", kind: "ANCHOR", depth: 0, status: "ANCHOR_MUTATED" },
    { id: "v1", kind: "VERDICT", depth: 1, status: "VERDICT_VALID", effective_status: "VERDICT_VALID" },
    { id: "v2", kind: "VERDICT", depth: 2, status: "VERDICT_STALE", effective_status: "VERDICT_STALE" }
  ];

  const stats = computeTopologyStats(nodes);
  assert.equal(stats.totalNodes, 4);
  assert.equal(stats.anchors, 2);
  assert.equal(stats.verdicts, 2);
  assert.equal(stats.activeAnchors, 1);
  assert.equal(stats.validVerdicts, 1);
  assert.equal(stats.staleCount, 2);
});
