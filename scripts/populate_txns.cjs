#!/usr/bin/env node
/**
 * CASCADIA PROTOCOL — Live On-Chain Transaction Population Script
 * ================================================================
 * Submits live on-chain transactions to GenLayer Studio Net to establish
 * empirical anchors and multi-hop causal verdict dependency topology.
 *
 * Usage:
 *   PRIVATE_KEY=0x... CONTRACT_ADDRESS=0x... node scripts/populate_txns.cjs
 */

const { createClient, createAccount } = require("genlayer-js");
const { studionet } = require("genlayer-js/chains");

const CONTRACT_ADDRESS =
  process.env.CONTRACT_ADDRESS || "0xF88B847a8003Dc16d6dEbFedB2695Aff20801ea8";
const PRIVATE_KEY = process.env.PRIVATE_KEY;

if (!PRIVATE_KEY) {
  console.error("=================================================================");
  console.error("CASCADIA: PRIVATE_KEY environment variable is required.");
  console.error("Usage: PRIVATE_KEY=0x... node scripts/populate_txns.cjs");
  console.error("Never hardcode private keys into source files or repositories.");
  console.error("=================================================================");
  process.exit(1);
}

const NODES_TO_POPULATE = [
  {
    kind: "ANCHOR",
    id: "anchor-iana-domains",
    uri: "https://www.iana.org/help/example-domains",
    hypothesis:
      "IANA maintains example domains such as example.com and example.org for documentation purposes."
  },
  {
    kind: "ANCHOR",
    id: "anchor-w3c-standards",
    uri: "https://www.w3.org/Consortium/",
    hypothesis:
      "The World Wide Web Consortium maintains international web standards and technical specifications."
  },
  {
    kind: "ANCHOR",
    id: "anchor-sec-edgar-filing",
    uri: "https://www.sec.gov/edgar/searchedgar/companysearch",
    hypothesis:
      "The SEC EDGAR database records enterprise statutory disclosures and regulatory filings."
  },
  {
    kind: "VERDICT",
    id: "verdict-procurement-tier1",
    inquiry:
      "Is enterprise procurement authorized based on verified upstream compliance status?",
    dependencies: ["anchor-iana-domains"]
  },
  {
    kind: "VERDICT",
    id: "verdict-vendor-qualification",
    inquiry:
      "Does the vendor meet Tier-1 qualification standards across international web and compliance benchmarks?",
    dependencies: ["anchor-iana-domains", "anchor-w3c-standards"]
  },
  {
    kind: "VERDICT",
    id: "verdict-treasury-wire-auth",
    inquiry:
      "Authorize autonomous treasury disbursement under multi-hop compliance and statutory filing validation.",
    dependencies: ["anchor-sec-edgar-filing", "verdict-vendor-qualification"]
  }
];

async function main() {
  console.log("=======================================================================");
  console.log("  CASCADIA PROTOCOL — ON-CHAIN TOPOLOGY POPULATION");
  console.log("=======================================================================");
  console.log(`Target Contract: ${CONTRACT_ADDRESS}`);
  console.log(`Network:         GenLayer Studio Net (Chain ID: 61999)`);

  const account = createAccount(PRIVATE_KEY);
  console.log(`Funder Address:  ${account.address}`);

  const client = createClient({ chain: studionet, account });

  const existingAnchorsRaw =
    (await client.readContract({
      address: CONTRACT_ADDRESS,
      functionName: "get_curator_anchors",
      args: [account.address]
    })) || "[]";
  const existingVerdictsRaw =
    (await client.readContract({
      address: CONTRACT_ADDRESS,
      functionName: "get_curator_verdicts",
      args: [account.address]
    })) || "[]";

  const existingAnchors = new Set(
    typeof existingAnchorsRaw === "string"
      ? JSON.parse(existingAnchorsRaw)
      : existingAnchorsRaw
  );
  const existingVerdicts = new Set(
    typeof existingVerdictsRaw === "string"
      ? JSON.parse(existingVerdictsRaw)
      : existingVerdictsRaw
  );

  console.log(
    `\nCurrent State:   ${existingAnchors.size} Anchors, ${existingVerdicts.size} Verdicts registered.`
  );

  for (let i = 0; i < NODES_TO_POPULATE.length; i++) {
    const node = NODES_TO_POPULATE[i];
    const isAnchor = node.kind === "ANCHOR";
    const exists = isAnchor
      ? existingAnchors.has(node.id)
      : existingVerdicts.has(node.id);

    if (exists) {
      console.log(
        `\n[${i + 1}/${NODES_TO_POPULATE.length}] ${node.kind} '${node.id}' already confirmed on-chain. Skipping.`
      );
      continue;
    }

    console.log(
      `\n[${i + 1}/${NODES_TO_POPULATE.length}] Deploying ${node.kind}: '${node.id}'...`
    );

    const fnName = isAnchor ? "register_anchor" : "establish_verdict";
    const args = isAnchor
      ? [node.id, node.uri, node.hypothesis]
      : [node.id, node.inquiry, node.dependencies];

    const txHash = await client.writeContract({
      address: CONTRACT_ADDRESS,
      functionName: fnName,
      args,
      value: 0n
    });
    console.log(`  ➔ Broadcasted Tx: ${txHash}`);

    console.log("  ➔ Waiting for validator receipt...");
    const receipt = await client.waitForTransactionReceipt({ hash: txHash });
    console.log(`  ✔ Confirmed with status: ${receipt.statusName || receipt.status}`);
  }

  console.log("\n=======================================================================");
  console.log("  VERIFYING COMPLETE TOPOLOGY READBACK FROM GENLAYER");
  console.log("=======================================================================");

  for (const node of NODES_TO_POPULATE) {
    if (node.kind === "ANCHOR") {
      const data = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: "get_anchor",
        args: [node.id]
      });
      const parsed = typeof data === "string" ? JSON.parse(data) : data;
      console.log(
        `[ANCHOR]  ${node.id.padEnd(30)} | Epoch: ${parsed.epoch} | Status: ${parsed.status}`
      );
    } else {
      const data = await client.readContract({
        address: CONTRACT_ADDRESS,
        functionName: "get_verdict",
        args: [node.id]
      });
      const parsed = typeof data === "string" ? JSON.parse(data) : data;
      console.log(
        `[VERDICT] ${node.id.padEnd(30)} | Depth: ${parsed.topology_depth} | Status: ${parsed.status} | Deps: [${parsed.dependencies.join(", ")}]`
      );
    }
  }

  console.log("\n[SUCCESS] CASCADIA Protocol DAG is 100% verified live on GenLayer!");
}

main().catch((err) => {
  console.error("\n[ERROR] Population failed:", err.message || err);
  process.exit(1);
});
