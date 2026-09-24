# CASCADIA: State Machine & Transition Invariants

## Anchor State Machine

```text
register_anchor
       │
       ▼
ANCHOR_GENESIS
       │
       ├── Initial Audit (Success) ──▶ ANCHOR_ACTIVE (Epoch 0 Baseline)
       │
       ├── Subsequent Audit (NO_MUTATION) ──▶ ANCHOR_ACTIVE (Epoch Unchanged)
       │
       ├── Audit (MUTATION_DETECTED) ──▶ ANCHOR_MUTATED (Epoch + 1) ──┐
       │                                                              │
       └── Audit Failure / Indeterminate ──▶ ANCHOR_DEGRADED ─────────┴──▶ Reverse Invalidation Cascade
```

### Invariants:
1. **Genesis Pinning:** The initial successful audit of an `ANCHOR_GENESIS` node sets `status = ANCHOR_ACTIVE` and stores `content_digest` without incrementing `epoch`. A source cannot represent a mutation from non-existent prior content.
2. **Byte Parity Contradiction Guard:** If `prior_digest == content_digest`, a model claiming `MUTATION_DETECTED` is rejected and marked `ANCHOR_DEGRADED`.
3. **Fail-Closed Degradation:** Transient network failures or model errors transition the node to `ANCHOR_DEGRADED` and cascade staleness to protect downstream decision makers.

---

## Verdict State Machine

```text
establish_verdict
       │
       ▼
VERDICT_INITIAL_STALE
       │
       ├── Adjudicate (VERDICT_AFFIRMED + Dependencies Safe) ──▶ VERDICT_VALID (Epoch + 1, Snapshot Refreshed)
       │
       ├── Upstream Dependency Mutated or Snapshot Mismatch ──▶ Effective VERDICT_STALE (via evaluate_effective_verdict)
       │
       ├── Adjudicate (VERDICT_DISPROVED) ──▶ VERDICT_INVALIDATED (Epoch + 1) ──┐
       │                                                                          │
       └── Adjudication Failure / Unresolved ──▶ VERDICT_INDETERMINATE ───────────┴──▶ Downstream Cascade
```

### Invariants:
1. **Optimism Barrier:** A verdict cannot be affirmed valid (`VERDICT_AFFIRMED`) if any upstream dependency is currently mutated, degraded, or invalidated.
2. **Dual-State Separation:** A verdict's persisted status may be `VERDICT_VALID`, but `evaluate_effective_verdict` deterministically reports `VERDICT_STALE` the instant any upstream dependency's epoch diverges from the stored snapshot.
3. **Terminal Invalidation:** `VERDICT_INVALIDATED` permanently records that the inquiry was disproved for that epoch, cascading staleness to any composite decisions depending on it.
