# CASCADIA: Causal Topology Specification

## Conceptual Model

The CASCADIA Protocol coordinates empirical ground-truth observations and reasoned conclusions within a unified directed acyclic graph (DAG):

```text
ANCHOR (External Ground Truth)
   │
   ▼
VERDICT (Reasoned Adjudication)
   │
   ▼
VERDICT (Downstream Composite Decision)
```

### Node Specialization

| Dimension | `ANCHOR` Node | `VERDICT` Node |
| :--- | :--- | :--- |
| **Role** | Empirical observation point | Reasoned decision / conclusion |
| **Grounding** | Immutable HTTPS URI & tracked hypothesis | Inquiry question & upstream dependency set |
| **Consensus Driver** | Nondeterministic web rendering + LLM semantic observation | Nondeterministic LLM multi-dependency adjudication |
| **State Evolution** | `ANCHOR_GENESIS` → `ANCHOR_ACTIVE` / `ANCHOR_MUTATED` / `ANCHOR_DEGRADED` | `VERDICT_INITIAL_STALE` → `VERDICT_VALID` / `VERDICT_INVALIDATED` / `VERDICT_INDETERMINATE` |
| **Advancement** | Epoch increments only on verified `MUTATION_DETECTED` | Epoch increments only on formal affirmation or invalidation |

## Directionality & Cascade Traversal

1. **Forward Dependency Edges:**
   A verdict explicitly stores its canonical sorted list of parent node IDs (`dependencies_json`) and snapshots their exact epochs at creation and re-adjudication time (`dependency_epoch_snapshot`).
2. **Reverse Invalidation Edges:**
   Every parent node maintains a canonical sorted array of its downstream dependents (`downstream_dependents`).
3. **Deterministic Breadth-First Invalidation:**
   When an anchor detects empirical mutation, or when an upstream verdict is disproved, `_cascade_staleness` initiates a deterministic BFS walk over the reverse adjacency list. Descendants are transitioned to `VERDICT_STALE` without executing LLM calls or evaluating qualitative prompts during the cascade.

## Boundary Enforcement & Anti-DoS Protections

- **Cycle Rejection:** Depth-first path exploration (`_assert_acyclic`) runs during verdict establishment to prevent circular causal dependencies.
- **Node Count Limit:** 128 nodes maximum per topology namespace.
- **Depth Ceiling:** 32 levels maximum to bound recursive traversal costs.
- **Fanout Ceiling:** 32 dependents maximum per node to prevent gas exhaustion during cascades.
- **Payload Bounds:** 32,768 characters maximum on rendered webpage bodies; 512 characters maximum on explanatory rationale outputs.
