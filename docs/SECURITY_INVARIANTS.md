# CASCADIA: Security Model & Invariant Protections

## Threat Vectors & Defenses

### 1. Silent Staleness of Stored Decisions
- **Threat:** Smart contracts read static boolean flags or cached parameters that were approved months ago, unaware that external licenses, prices, credit statuses, or regulations have changed.
- **Defense:** Every verdict records an immutable snapshot of parent epochs (`dependency_epoch_snapshot`). `evaluate_effective_verdict` evaluates this snapshot recursively, guaranteeing that any upstream fact change immediately yields `VERDICT_STALE` on-chain without requiring a transaction.

### 2. Malicious Circular Dependency Induction
- **Threat:** An attacker establishes circular causal dependencies (`A -> B -> C -> A`), causing infinite loops and out-of-gas errors during staleness cascades.
- **Defense:** Strict depth-first cycle verification (`_assert_acyclic`) traverses parent dependency trees during `establish_verdict`. Any path referencing the candidate node ID immediately reverts the transaction.

### 3. Resource Exhaustion & Cascade Griefing
- **Threat:** An attacker constructs an excessively deep or wide dependency tree to force out-of-gas reverts whenever an anchor is audited.
- **Defense:**
  - Maximum topology depth is hard-capped at 32 (`MAX_TOPOLOGY_DEPTH`).
  - Maximum node fanout is hard-capped at 32 (`MAX_FANOUT_LIMIT`).
  - Maximum nodes in a cascade traversal is hard-capped at 128 (`MAX_CASCADE_NODES`).
  - Input strings, URIs, inquiries, and rationales enforce strict length bounds.

### 4. Consensus Disagreement Over Free-Form Text
- **Threat:** Using strict string equality over LLM explanations causes honest validators to disagree due to harmless phrasing variance, stalling consensus.
- **Defense:** CASCADIA's `gl.vm.run_nondet` custom validator functions require strict identity on actionable categorical enums (`mutation` for anchors, `outcome` and sorted `affected_dependency_ids` for verdicts) while allowing natural explanatory variance in validator rationales.

### 5. Authority Confusion & Malicious URIs
- **Threat:** Attackers submit credentials in URL authority components (e.g. `https://reuters.com@malicious.com`) to spoof institutional allowlists.
- **Defense:** `_sanitize_https_uri` enforces RFC 3986 compliance, requiring explicit HTTPS schemes, rejecting fragments, and validating hostname structure.
