# CASCADIA PROTOCOL — Contract API & SDK Reference

Complete technical reference for public transactions, view methods, error states, and client-side interfaces of the **CASCADIA Protocol Intelligent Contract** (`contracts/cascadia.py`).

---

## 1. Storage & State Enums

### `NodeKind`
| Identifier | Description |
| :--- | :--- |
| `ANCHOR` | Empirical observation node anchored to external web or verifiable truth source. |
| `VERDICT` | Reasoned causal decision node evaluated against upstream anchor and verdict dependencies. |

### `NodeStatus`
| Status | Associated Kind | Semantics |
| :--- | :--- | :--- |
| `ANCHOR_ACTIVE` | ANCHOR | Empirical baseline verified and active. |
| `ANCHOR_MUTATED` | ANCHOR | External data source mutated, invalidating empirical hypothesis. |
| `ANCHOR_DEGRADED` | ANCHOR | External source unreachable or format unparseable. |
| `VERDICT_INITIAL_STALE`| VERDICT | Initial state upon creation prior to first consensus execution. |
| `VERDICT_VALID` | VERDICT | Active consensus reached, all upstream dependencies valid. |
| `VERDICT_INVALID` | VERDICT | Upstream dependencies valid, but LLM consensus voted NO on inquiry. |
| `VERDICT_STALE` | VERDICT | Invalidated due to upstream anchor mutation or verdict invalidation. |

---

## 2. Public State-Modifying Functions

### `create_anchor(anchor_id: str, title: str, hypothesis: str, uri: str) -> None`
Initializes a new empirical ground-truth anchor at depth 0.
- **Parameters:**
  - `anchor_id`: Alphanumeric slug (max 64 chars).
  - `title`: Short human-readable title (max 128 chars).
  - `hypothesis`: Precise factual claim being anchored (max 512 chars).
  - `uri`: Target URL for web observation (max 256 chars).
- **Constraints:**
  - Node ID must be unique across the protocol.
  - Total active nodes must not exceed `MAX_NODES` (128).
- **Initial Status:** `ANCHOR_ACTIVE` (Genesis baseline established at epoch 0).

### `create_verdict(verdict_id: str, title: str, inquiry: str, dependencies: List[str]) -> None`
Initializes a new reasoned decision node dependent on existing anchors or verdicts.
- **Parameters:**
  - `verdict_id`: Unique identifier for the verdict node.
  - `title`: Short title describing the decision.
  - `inquiry`: High-stakes question evaluated by consensus committee.
  - `dependencies`: List of parent node IDs (`1 <= len <= 8`).
- **Constraints:**
  - All dependency IDs must exist in storage.
  - Maximum DAG depth cannot exceed `MAX_DEPTH` (32).
  - DAG must remain strictly acyclic.
- **Initial Status:** `VERDICT_INITIAL_STALE`.

### `observe_anchor(anchor_id: str) -> None`
Executes non-deterministic web observation consensus via `gl.vm.run_nondet`.
- **Consensus Logic:**
  - Committee fetches live content at `anchor.uri`.
  - Computes SHA-256 digest of content.
  - Evaluates factual continuity against `anchor.hypothesis`.
  - Compares actionable boolean `mutation_detected`.
- **Effects:**
  - If `mutation_detected == False`: Anchor remains `ANCHOR_ACTIVE`.
  - If `mutation_detected == True`: Anchor transitions to `ANCHOR_MUTATED`. Triggers `_propagate_staleness_cascade(anchor_id)`, marking all downstream verdicts as `VERDICT_STALE`.

### `evaluate_verdict(verdict_id: str) -> None`
Executes non-deterministic LLM reasoning consensus over dependencies.
- **Preconditions:**
  - All upstream dependencies must be in valid active state. If any dependency is stale or mutated, the transaction reverts with `DependencyStaleError`.
- **Consensus Logic:**
  - Evaluates synthesized prompt combining upstream hypotheses and verdicts.
  - Outputs decision tuple `(outcome: bool, affected_ids: List[str])`.
- **Effects:**
  - Sets verdict status to `VERDICT_VALID` (if true) or `VERDICT_INVALID` (if false).

### `re_evaluate_verdict(verdict_id: str) -> None`
Re-evaluates a currently stale or invalid verdict once upstream dependencies have been remediated.
- **Preconditions:**
  - All upstream dependencies must currently be `ANCHOR_ACTIVE` or `VERDICT_VALID`.
- **Effects:**
  - Runs consensus re-evaluation and restores verdict to `VERDICT_VALID` upon approval.

---

## 3. Public View Methods

### `get_node(node_id: str) -> Dict[str, Any]`
Returns the full record for an anchor or verdict.
- **Returns:**
  ```python
  {
      "id": str,
      "kind": "ANCHOR" | "VERDICT",
      "title": str,
      "status": str,
      "effective_status": str,
      "depth": int,
      "epoch": int,
      "dependencies": List[str],
      "dependents": List[str],
      "definition_fingerprint": str,
      "last_updated": int
  }
  ```

### `is_verdict_valid(verdict_id: str) -> bool`
Authoritative deterministic check used by external smart contracts to authorize actions.
- **Returns:** `True` if and only if:
  - Node exists and is of kind `VERDICT`
  - Node status is `VERDICT_VALID`
  - All recursive upstream dependencies remain `ANCHOR_ACTIVE` or `VERDICT_VALID`
- **Returns:** `False` if node is stale, mutated, invalid, or uninitialized.

### `get_topology_summary() -> Dict[str, Any]`
Returns aggregated protocol statistics:
- Total nodes, active anchors, mutated anchors, valid verdicts, stale verdicts, and max depth.

---

## 4. Contract Exceptions & Invariants

| Exception | Cause |
| :--- | :--- |
| `NodeExistsError` | Attempted to register duplicate node ID. |
| `NodeNotFoundError` | Referenced node ID does not exist in protocol storage. |
| `InvalidDependencyError` | Node attempts to depend on non-existent node or itself. |
| `TopologicalCycleError` | Dependency addition would introduce a directed cycle. |
| `DepthLimitExceededError`| Resulting node depth exceeds maximum allowed bound (32). |
| `DependencyStaleError` | Attempted to evaluate verdict while upstream dependency is stale. |
| `UnauthorizedError` | Caller is not protocol administrator. |
