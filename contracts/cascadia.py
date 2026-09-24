# { "Depends": "py-genlayer:5jycge4q8k23462jtb0b9fyey1s9qz928sz2nbrd9mg4sxqg2qng" }

"""
CASCADIA PROTOCOL: Autonomous Causal Dependency and Truth-Cascade Engine
========================================================================
A GenLayer-native intelligent contract for maintaining living decision topologies.

Traditional on-chain architectures suffer from a critical vulnerability: decisions
and attestations remain permanently recorded as "valid" even when the empirical
real-world facts or upstream conclusions underpinning them have mutated or expired.

CASCADIA establishes a living topological mesh of verifiable external anchors
(HTTPS sources) and derived verdicts (reasoned conclusions). When ground-truth
facts shift, CASCADIA reaches validator consensus over external web observations
and deterministically cascades staleness down reverse dependency edges, protecting
protocols against silent decision obsolescence.
"""

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import genlayer as gl
from genlayer.types import *


# -----------------------------------------------------------------------------
# Protocol Constants & Lifecycle States
# -----------------------------------------------------------------------------

PROTOCOL_VERSION = "cascadia.v1"

# Anchor (Ground-Truth Web Source) States
ANCHOR_GENESIS = "ANCHOR_GENESIS"       # Registered, awaiting initial empirical baseline observation
ANCHOR_ACTIVE = "ANCHOR_ACTIVE"         # Observation successful; tracked hypothesis remains valid
ANCHOR_MUTATED = "ANCHOR_MUTATED"       # Ground truth has shifted materially; upstream dependencies invalid
ANCHOR_DEGRADED = "ANCHOR_DEGRADED"     # Web endpoint unreachable, contradictory, or observation failed

# Verdict (Reasoned Decision) States
VERDICT_INITIAL_STALE = "VERDICT_INITIAL_STALE"   # Newly established; awaiting initial adjudication
VERDICT_VALID = "VERDICT_VALID"                   # Adjudicated valid; all dependency snapshots align
VERDICT_INVALIDATED = "VERDICT_INVALIDATED"       # Empirical facts or logic disproved the inquiry
VERDICT_INDETERMINATE = "VERDICT_INDETERMINATE"   # Recheck failed or upstream dependencies corrupted
VERDICT_STALE = "VERDICT_STALE"                   # Cascaded staleness due to upstream mutation

# Anchor Semantic Observation Outcomes
MUTATION_DETECTED = "MUTATION_DETECTED"
NO_MUTATION = "NO_MUTATION"
OBSERVATION_INDETERMINATE = "OBSERVATION_INDETERMINATE"

# Verdict Adjudication Outcomes
VERDICT_AFFIRMED = "VERDICT_AFFIRMED"
VERDICT_DISPROVED = "VERDICT_DISPROVED"
VERDICT_UNRESOLVED = "VERDICT_UNRESOLVED"

# Protocol Boundary Limits (Guarding against resource exhaustion & denial-of-service)
MAX_IDENTIFIER = 96
MAX_URI = 2048
MAX_HYPOTHESIS = 4000
MAX_INQUIRY = 4000
MAX_RATIONALE = 512
MAX_RENDER_PAYLOAD = 32768
MAX_DEPENDENCIES_PER_VERDICT = 8
MAX_FANOUT_LIMIT = 32
MAX_CASCADE_NODES = 128
MAX_TOPOLOGY_DEPTH = 32

ANCHOR_OBSERVATION_KEYS = {"mutation", "rationale"}
VERDICT_ADJUDICATION_KEYS = {"outcome", "rationale", "affected_dependency_ids"}


# -----------------------------------------------------------------------------
# Storage Schemas
# -----------------------------------------------------------------------------

@gl.storage.allow
@dataclass
class AnchorRecord:
    """Verifiable ground-truth external web observation point."""
    anchor_id: str
    custodian: str
    uri: str
    tracked_hypothesis: str
    epoch: u256
    content_digest: str
    semantic_snapshot: str
    status: str
    definition_fingerprint: str
    epoch_fingerprint: str


@gl.storage.allow
@dataclass
class VerdictRecord:
    """Reasoned conclusion bound to an upstream dependency topology."""
    verdict_id: str
    curator: str
    inquiry: str
    dependencies_json: str
    dependency_epoch_snapshot: str
    topology_depth: u256
    epoch: u256
    adjudication_json: str
    status: str
    definition_fingerprint: str
    epoch_fingerprint: str


# -----------------------------------------------------------------------------
# Deterministic Serialization & Cryptographic Helpers
# -----------------------------------------------------------------------------

def _canonical_json(value: Any) -> str:
    """Produces deterministically sorted, whitespace-compact JSON representations."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest_label(label: str, *components: Any) -> str:
    """Computes SHA-256 fingerprint for protocol records and transition bindings."""
    encoded = _canonical_json([label, *components]).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sanitize_string(value: Any, max_len: int, field_name: str) -> str:
    """Enforces non-empty string constraints within strict length ceilings."""
    if not isinstance(value, str) or not value.strip() or len(value) > max_len:
        raise gl.vm.UserError(f"Field '{field_name}' must be non-empty and under {max_len} characters.")
    return value.strip()


def _sanitize_identifier(value: Any, field_name: str) -> str:
    """Validates alphanumeric identifiers with standard hyphen/underscore/dot separators."""
    val = _sanitize_string(value, MAX_IDENTIFIER, field_name)
    for char in val:
        if not (char.isalnum() or char in "-_."):
            raise gl.vm.UserError(f"Identifier '{field_name}' contains illegal characters.")
    return val


def _sanitize_https_uri(value: Any) -> str:
    """Enforces valid HTTPS URI formatting, rejecting URL fragments and insecure schemes."""
    uri_str = _sanitize_string(value, MAX_URI, "uri")
    parsed = urlsplit(uri_str)
    if parsed.scheme.lower() != "https" or not parsed.netloc or parsed.fragment:
        raise gl.vm.UserError("Source URI must be a valid HTTPS location without URL fragments.")
    return uri_str


def _validate_anchor_model_output(payload: Any) -> dict[str, str]:
    """Validates schema adherence for validator LLM anchor observation outputs."""
    if not isinstance(payload, dict) or set(payload.keys()) != ANCHOR_OBSERVATION_KEYS:
        raise gl.vm.UserError("Malformed anchor observation schema from model.")
    mutation = payload.get("mutation")
    rationale = payload.get("rationale")
    if mutation not in (MUTATION_DETECTED, NO_MUTATION, OBSERVATION_INDETERMINATE):
        raise gl.vm.UserError(f"Illegal anchor mutation value: {mutation}")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > MAX_RATIONALE:
        raise gl.vm.UserError("Anchor observation rationale exceeds boundary limits.")
    return {"mutation": mutation, "rationale": rationale}


def _validate_observation_package(package: Any) -> dict[str, Any]:
    """Validates full observation tuple (raw digest + semantic verdict)."""
    if not isinstance(package, dict) or set(package.keys()) != {"content_digest", "semantic"}:
        raise gl.vm.UserError("Invalid observation package structure.")
    digest = package.get("content_digest")
    if not isinstance(digest, str) or len(digest) != 64:
        raise gl.vm.UserError("Content digest must be a 64-character SHA-256 hexadecimal string.")
    semantic = _validate_anchor_model_output(package.get("semantic"))
    return {"content_digest": digest, "semantic": semantic}


def _validate_verdict_model_output(payload: Any, valid_dependencies: list[str]) -> dict[str, Any]:
    """Validates schema adherence for validator LLM verdict adjudication outputs."""
    if not isinstance(payload, dict) or set(payload.keys()) != VERDICT_ADJUDICATION_KEYS:
        raise gl.vm.UserError("Malformed verdict adjudication schema from model.")
    outcome = payload.get("outcome")
    rationale = payload.get("rationale")
    affected = payload.get("affected_dependency_ids")

    if outcome not in (VERDICT_AFFIRMED, VERDICT_DISPROVED, VERDICT_UNRESOLVED):
        raise gl.vm.UserError(f"Illegal verdict adjudication outcome: {outcome}")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > MAX_RATIONALE:
        raise gl.vm.UserError("Verdict rationale exceeds boundary limits.")
    if not isinstance(affected, list) or len(affected) > MAX_DEPENDENCIES_PER_VERDICT:
        raise gl.vm.UserError("Affected dependency list is corrupted or too large.")

    unique_affected: list[str] = []
    for dep_id in affected:
        if not isinstance(dep_id, str) or dep_id not in valid_dependencies:
            raise gl.vm.UserError(f"Verdict references unknown affected dependency: {dep_id}")
        if dep_id in unique_affected:
            raise gl.vm.UserError(f"Duplicate affected dependency ID: {dep_id}")
        unique_affected.append(dep_id)

    return {
        "outcome": outcome,
        "rationale": rationale,
        "affected_dependency_ids": sorted(unique_affected),
    }


# -----------------------------------------------------------------------------
# Prompt Builders
# -----------------------------------------------------------------------------

def _build_anchor_audit_prompt(
    uri: str,
    hypothesis: str,
    previous_digest: str,
    previous_semantic_json: str,
    rendered_body: str,
) -> str:
    """Constructs prompt for multi-validator empirical web observation."""
    prev_str = previous_semantic_json if previous_semantic_json else "NONE (GENESIS OBSERVATION)"
    return (
        "You are an impartial GenLayer consensus validator auditing an empirical ground-truth anchor for CASCADIA.\n"
        "Analyze whether the newly observed webpage content materially alters the tracked hypothesis.\n"
        "A material mutation occurs if the newly observed facts could invalidate downstream decisions relying on the claim.\n"
        "Rely strictly on the rendered content. Do not extrapolate unsupported assumptions.\n\n"
        f"Registered URI: {uri}\n"
        f"Tracked Hypothesis: {hypothesis}\n"
        f"Prior Content SHA-256 Digest: {previous_digest}\n"
        f"Prior Semantic Record: {prev_str}\n"
        f"Current Rendered Content:\n{rendered_body}\n\n"
        "Respond with EXACTLY ONE JSON object matching this schema and no other text:\n"
        '{"mutation": "MUTATION_DETECTED|NO_MUTATION|OBSERVATION_INDETERMINATE", "rationale": "..."}\n'
        "Keep the rationale concise, empirical, and under 512 characters.\n"
        "If the webpage is inaccessible, empty, or contradictory, output OBSERVATION_INDETERMINATE."
    )


def _build_verdict_adjudication_prompt(
    inquiry: str,
    dependencies_json: str,
    snapshot_json: str,
    topology_context_json: str,
) -> str:
    """Constructs prompt for multi-validator verdict re-evaluation."""
    return (
        "You are an impartial GenLayer consensus validator adjudicating a CASCADIA verdict.\n"
        "Evaluate the inquiry against the current state of its upstream dependency topology.\n\n"
        f"Inquiry / Decision Question: {inquiry}\n"
        f"Declared Dependencies (JSON): {dependencies_json}\n"
        f"Recorded Epoch Snapshot: {snapshot_json}\n"
        f"Current Upstream Topology Context: {topology_context_json}\n\n"
        "Respond with EXACTLY ONE JSON object matching this schema and no other text:\n"
        '{"outcome": "VERDICT_AFFIRMED|VERDICT_DISPROVED|VERDICT_UNRESOLVED", '
        '"rationale": "...", "affected_dependency_ids": ["..."]}\n'
        "Every ID in affected_dependency_ids must belong to the declared dependencies list.\n"
        "Keep the rationale concise and under 512 characters."
    )


# -----------------------------------------------------------------------------
# Main Intelligent Contract Class
# -----------------------------------------------------------------------------

class Cascadia(gl.contract.Contract):
    """
    CASCADIA PROTOCOL
    Autonomous causal dependency graph, empirical truth monitoring, and staleness cascades.
    """

    anchors: gl.storage.TreeMap[str, AnchorRecord]
    verdicts: gl.storage.TreeMap[str, VerdictRecord]
    registry_kind: gl.storage.TreeMap[str, str]            # Unified namespace preventing ID collisions
    downstream_dependents: gl.storage.TreeMap[str, str]    # Canonical reverse-edge adjacency list
    curator_anchors: gl.storage.TreeMap[str, str]          # Account -> [anchor_id, ...]
    curator_verdicts: gl.storage.TreeMap[str, str]         # Account -> [verdict_id, ...]
    total_nodes: u256

    def __init__(self):
        """Initializes the empty CASCADIA topology."""
        self.total_nodes = 0

    # -------------------------------------------------------------------------
    # Public Write Operations
    # -------------------------------------------------------------------------

    @gl.public.write
    def register_anchor(self, anchor_id: str, uri: str, tracked_hypothesis: str) -> str:
        """
        Registers a new empirical truth anchor in the CASCADIA topology.
        Starts in ANCHOR_GENESIS state until first audited.
        """
        anchor_id = _sanitize_identifier(anchor_id, "anchor_id")
        uri = _sanitize_https_uri(uri)
        tracked_hypothesis = _sanitize_string(tracked_hypothesis, MAX_HYPOTHESIS, "tracked_hypothesis")

        if self.registry_kind.get(anchor_id, ""):
            raise gl.vm.UserError(f"Node identifier '{anchor_id}' already exists in topology.")
        if int(self.total_nodes) >= MAX_CASCADE_NODES:
            raise gl.vm.UserError("Topology node ceiling reached (128 nodes maximum).")

        custodian = str(gl.message.sender_address).lower()
        definition_fingerprint = _digest_label(
            "CASCADIA-ANCHOR-DEF-V1",
            anchor_id,
            custodian,
            uri,
            tracked_hypothesis,
        )
        initial_semantic = ""
        epoch_fingerprint = _digest_label(
            "CASCADIA-ANCHOR-EPOCH-V1",
            anchor_id,
            0,
            "",
            initial_semantic,
        )

        record = AnchorRecord(
            anchor_id=anchor_id,
            custodian=custodian,
            uri=uri,
            tracked_hypothesis=tracked_hypothesis,
            epoch=0,
            content_digest="",
            semantic_snapshot=initial_semantic,
            status=ANCHOR_GENESIS,
            definition_fingerprint=definition_fingerprint,
            epoch_fingerprint=epoch_fingerprint,
        )

        self.anchors[anchor_id] = record
        self.registry_kind[anchor_id] = "ANCHOR"
        self.downstream_dependents[anchor_id] = "[]"
        self._append_to_index(self.curator_anchors, custodian, anchor_id)
        self.total_nodes = self.total_nodes + 1

        return json.dumps(
            {
                "anchor_id": anchor_id,
                "status": ANCHOR_GENESIS,
                "epoch": 0,
                "definition_fingerprint": definition_fingerprint,
            },
            sort_keys=True,
        )

    @gl.public.write
    def establish_verdict(self, verdict_id: str, inquiry: str, dependencies: list[str]) -> str:
        """
        Establishes a reasoned verdict node dependent on upstream anchors or other verdicts.
        Starts in VERDICT_INITIAL_STALE until formally adjudicated.
        """
        verdict_id = _sanitize_identifier(verdict_id, "verdict_id")
        inquiry = _sanitize_string(inquiry, MAX_INQUIRY, "inquiry")

        if not isinstance(dependencies, list) or not dependencies:
            raise gl.vm.UserError("A verdict must declare at least one upstream dependency.")
        if len(dependencies) > MAX_DEPENDENCIES_PER_VERDICT:
            raise gl.vm.UserError(f"Dependency count exceeds maximum limit of {MAX_DEPENDENCIES_PER_VERDICT}.")
        if self.registry_kind.get(verdict_id, ""):
            raise gl.vm.UserError(f"Node identifier '{verdict_id}' already exists in topology.")
        if int(self.total_nodes) >= MAX_CASCADE_NODES:
            raise gl.vm.UserError("Topology node ceiling reached (128 nodes maximum).")

        canonical_deps: list[str] = []
        for dep_id in dependencies:
            dep_id = _sanitize_identifier(dep_id, "dependency_id")
            if dep_id == verdict_id:
                raise gl.vm.UserError("Self-referential dependencies are strictly prohibited.")
            if dep_id in canonical_deps:
                raise gl.vm.UserError(f"Duplicate dependency declared: {dep_id}")
            if not self.registry_kind.get(dep_id, ""):
                raise gl.vm.UserError(f"Referenced dependency '{dep_id}' does not exist in topology.")
            canonical_deps.append(dep_id)

        canonical_deps.sort()
        self._assert_acyclic(verdict_id, canonical_deps)

        computed_depth = 1
        for dep_id in canonical_deps:
            parent_depth = self._get_node_depth(dep_id) + 1
            if parent_depth > computed_depth:
                computed_depth = parent_depth

        if computed_depth > MAX_TOPOLOGY_DEPTH:
            raise gl.vm.UserError(f"Topology depth ({computed_depth}) exceeds protocol limit ({MAX_TOPOLOGY_DEPTH}).")

        epoch_snapshot: dict[str, int] = {}
        for dep_id in canonical_deps:
            epoch_snapshot[dep_id] = self._get_node_epoch(dep_id)
            existing_dependents = self._get_dependents_list(dep_id)
            if len(existing_dependents) >= MAX_FANOUT_LIMIT:
                raise gl.vm.UserError(f"Dependency '{dep_id}' has reached maximum fanout limit ({MAX_FANOUT_LIMIT}).")

        curator = str(gl.message.sender_address).lower()
        deps_json = _canonical_json(canonical_deps)
        snapshot_json = _canonical_json(epoch_snapshot)
        definition_fingerprint = _digest_label(
            "CASCADIA-VERDICT-DEF-V1",
            verdict_id,
            curator,
            inquiry,
            canonical_deps,
        )
        initial_adjudication = ""
        epoch_fingerprint = _digest_label(
            "CASCADIA-VERDICT-EPOCH-V1",
            verdict_id,
            0,
            initial_adjudication,
            epoch_snapshot,
        )

        record = VerdictRecord(
            verdict_id=verdict_id,
            curator=curator,
            inquiry=inquiry,
            dependencies_json=deps_json,
            dependency_epoch_snapshot=snapshot_json,
            topology_depth=computed_depth,
            epoch=0,
            adjudication_json=initial_adjudication,
            status=VERDICT_INITIAL_STALE,
            definition_fingerprint=definition_fingerprint,
            epoch_fingerprint=epoch_fingerprint,
        )

        self.verdicts[verdict_id] = record
        self.registry_kind[verdict_id] = "VERDICT"
        self.downstream_dependents[verdict_id] = "[]"

        # Register reverse edges for staleness cascades
        for dep_id in canonical_deps:
            self._register_dependent(dep_id, verdict_id)

        self._append_to_index(self.curator_verdicts, curator, verdict_id)
        self.total_nodes = self.total_nodes + 1

        return json.dumps(
            {
                "verdict_id": verdict_id,
                "status": VERDICT_INITIAL_STALE,
                "epoch": 0,
                "topology_depth": computed_depth,
                "dependencies": canonical_deps,
                "definition_fingerprint": definition_fingerprint,
            },
            sort_keys=True,
        )

    @gl.public.write
    def audit_anchor(self, anchor_id: str) -> str:
        """
        Executes multi-validator web rendering and semantic observation.
        If empirical mutation is detected, cascades staleness down reverse dependency edges.
        """
        anchor = self._load_anchor(anchor_id)
        prior_digest = anchor.content_digest
        prior_semantic = anchor.semantic_snapshot

        try:
            observation = self._consensus_audit_anchor(
                anchor.uri,
                anchor.tracked_hypothesis,
                prior_digest,
                prior_semantic,
            )
        except Exception:
            self._degrade_anchor(anchor)
            return self._anchor_export_json(anchor)

        content_digest = observation["content_digest"]
        semantic = observation["semantic"]

        # Deterministic Genesis Baseline:
        # The very first successful observation establishes the initial factual baseline.
        # It cannot represent a mutation from non-existent prior content.
        if not prior_digest and semantic["mutation"] != OBSERVATION_INDETERMINATE:
            semantic = {
                "mutation": NO_MUTATION,
                "rationale": "Genesis observation established empirical truth baseline.",
            }

        # Contradiction guard: cannot claim mutation if byte content digest is identical
        if semantic["mutation"] == MUTATION_DETECTED and prior_digest == content_digest:
            self._degrade_anchor(anchor)
            return self._anchor_export_json(anchor)

        anchor.content_digest = content_digest
        anchor.semantic_snapshot = _canonical_json(semantic)

        if semantic["mutation"] == MUTATION_DETECTED:
            anchor.epoch = anchor.epoch + 1
            anchor.status = ANCHOR_MUTATED
            anchor.epoch_fingerprint = _digest_label(
                "CASCADIA-ANCHOR-EPOCH-V1",
                anchor.anchor_id,
                int(anchor.epoch),
                content_digest,
                semantic,
            )
            # Cascade staleness deterministically to all downstream dependents
            self._cascade_staleness(anchor.anchor_id)
        elif semantic["mutation"] == NO_MUTATION:
            anchor.status = ANCHOR_ACTIVE
            anchor.epoch_fingerprint = _digest_label(
                "CASCADIA-ANCHOR-EPOCH-V1",
                anchor.anchor_id,
                int(anchor.epoch),
                content_digest,
                semantic,
            )
        else:
            anchor.status = ANCHOR_DEGRADED
            anchor.epoch_fingerprint = _digest_label(
                "CASCADIA-ANCHOR-EPOCH-V1",
                anchor.anchor_id,
                int(anchor.epoch),
                content_digest,
                semantic,
            )
            self._cascade_staleness(anchor.anchor_id)

        return self._anchor_export_json(anchor)

    @gl.public.write
    def adjudicate_verdict(self, verdict_id: str) -> str:
        """
        Re-evaluates a verdict against its current upstream dependency state.
        If affirmed, advances epoch and updates snapshot. If disproved, propagates staleness.
        """
        verdict = self._load_verdict(verdict_id)
        dependencies = self._get_verdict_dependencies(verdict)
        self._assert_dependencies_intact(dependencies)

        snapshot = json.loads(verdict.dependency_epoch_snapshot)
        context = self._build_dependency_context(dependencies, snapshot)
        prompt = _build_verdict_adjudication_prompt(
            verdict.inquiry,
            verdict.dependencies_json,
            verdict.dependency_epoch_snapshot,
            _canonical_json(context),
        )

        try:
            adjudication = self._consensus_adjudicate_verdict(prompt, dependencies)
        except Exception:
            adjudication = {
                "outcome": VERDICT_UNRESOLVED,
                "rationale": "Adjudication consensus failed or external model error.",
                "affected_dependency_ids": [],
            }

        # Invariant safety guard: A verdict cannot be affirmed valid if any dependency is degraded/mutated
        if adjudication["outcome"] == VERDICT_AFFIRMED and not self._are_dependencies_healthy(dependencies):
            adjudication = {
                "outcome": VERDICT_UNRESOLVED,
                "rationale": "Verdict cannot be affirmed valid while upstream dependencies are unsafe.",
                "affected_dependency_ids": [],
            }

        adjudication_json = _canonical_json(adjudication)

        if adjudication["outcome"] == VERDICT_AFFIRMED:
            verdict.epoch = verdict.epoch + 1
            verdict.status = VERDICT_VALID
            verdict.dependency_epoch_snapshot = self._export_current_snapshot_json(dependencies)
            verdict.adjudication_json = adjudication_json
            verdict.epoch_fingerprint = _digest_label(
                "CASCADIA-VERDICT-EPOCH-V1",
                verdict.verdict_id,
                int(verdict.epoch),
                adjudication,
                json.loads(verdict.dependency_epoch_snapshot),
            )
        elif adjudication["outcome"] == VERDICT_DISPROVED:
            verdict.epoch = verdict.epoch + 1
            verdict.status = VERDICT_INVALIDATED
            verdict.dependency_epoch_snapshot = self._export_current_snapshot_json(dependencies)
            verdict.adjudication_json = adjudication_json
            verdict.epoch_fingerprint = _digest_label(
                "CASCADIA-VERDICT-EPOCH-V1",
                verdict.verdict_id,
                int(verdict.epoch),
                adjudication,
                json.loads(verdict.dependency_epoch_snapshot),
            )
            # Invalidation cascades staleness downstream
            self._cascade_staleness(verdict.verdict_id)
        else:
            verdict.status = VERDICT_INDETERMINATE
            verdict.adjudication_json = adjudication_json
            verdict.epoch_fingerprint = _digest_label(
                "CASCADIA-VERDICT-EPOCH-V1",
                verdict.verdict_id,
                int(verdict.epoch),
                adjudication,
                json.loads(verdict.dependency_epoch_snapshot),
            )
            self._cascade_staleness(verdict.verdict_id)

        return self._verdict_export_json(verdict)

    # -------------------------------------------------------------------------
    # Public View & Telemetry Operations
    # -------------------------------------------------------------------------

    @gl.public.view
    def get_anchor(self, anchor_id: str) -> str:
        """Returns full telemetry and canonical state for an empirical anchor."""
        anchor = self._load_anchor(anchor_id)
        return json.dumps(
            {
                "anchor_id": anchor.anchor_id,
                "custodian": anchor.custodian,
                "uri": anchor.uri,
                "tracked_hypothesis": anchor.tracked_hypothesis,
                "epoch": int(anchor.epoch),
                "content_digest": anchor.content_digest,
                "semantic_snapshot": json.loads(anchor.semantic_snapshot) if anchor.semantic_snapshot else None,
                "status": anchor.status,
                "definition_fingerprint": anchor.definition_fingerprint,
                "epoch_fingerprint": anchor.epoch_fingerprint,
            },
            sort_keys=True,
        )

    @gl.public.view
    def get_verdict(self, verdict_id: str) -> str:
        """Returns full telemetry, snapshot, and effective health status for a verdict."""
        verdict = self._load_verdict(verdict_id)
        return json.dumps(
            {
                "verdict_id": verdict.verdict_id,
                "curator": verdict.curator,
                "inquiry": verdict.inquiry,
                "dependencies": self._get_verdict_dependencies(verdict),
                "dependency_epoch_snapshot": json.loads(verdict.dependency_epoch_snapshot),
                "topology_depth": int(verdict.topology_depth),
                "epoch": int(verdict.epoch),
                "adjudication": json.loads(verdict.adjudication_json) if verdict.adjudication_json else None,
                "status": verdict.status,
                "effective_status": self._resolve_effective_status(verdict.verdict_id, [], 0),
                "definition_fingerprint": verdict.definition_fingerprint,
                "epoch_fingerprint": verdict.epoch_fingerprint,
            },
            sort_keys=True,
        )

    @gl.public.view
    def evaluate_effective_verdict(self, verdict_id: str) -> str:
        """
        Deterministic, zero-gas recursive health verification.
        Walks upstream DAG to determine if the verdict is genuinely fresh and safe without invoking an LLM.
        """
        self._load_verdict(verdict_id)
        return self._resolve_effective_status(verdict_id, [], 0)

    @gl.public.view
    def get_dependencies(self, verdict_id: str) -> str:
        """Returns list of upstream dependency identifiers for a verdict."""
        return _canonical_json(self._get_verdict_dependencies(self._load_verdict(verdict_id)))

    @gl.public.view
    def get_downstream_dependents(self, node_id: str) -> str:
        """Returns list of downstream dependent identifiers for any topology node."""
        self._assert_node_exists(node_id)
        return _canonical_json(self._get_dependents_list(node_id))

    @gl.public.view
    def get_curator_anchors(self, curator: str) -> str:
        """Returns all anchor identifiers created by a specific curator account."""
        clean_curator = _sanitize_string(curator, 128, "curator").lower()
        return _canonical_json(self._get_index_entries(self.curator_anchors, clean_curator))

    @gl.public.view
    def get_curator_verdicts(self, curator: str) -> str:
        """Returns all verdict identifiers created by a specific curator account."""
        clean_curator = _sanitize_string(curator, 128, "curator").lower()
        return _canonical_json(self._get_index_entries(self.curator_verdicts, clean_curator))

    # -------------------------------------------------------------------------
    # Consensus Verification Engines (gl.vm.run_nondet)
    # -------------------------------------------------------------------------

    def _consensus_audit_anchor(
        self, uri: str, hypothesis: str, prior_digest: str, prior_semantic: str
    ) -> dict[str, Any]:
        """
        Reaches multi-validator consensus over nondeterministic web rendering & LLM observation.
        Validators enforce exact agreement on categorical mutation outcome while tolerating rationale text variances.
        """
        def observe() -> dict[str, Any]:
            body = gl.nondet.web.render(uri, mode="text")
            if not isinstance(body, str) or not body.strip() or len(body) > MAX_RENDER_PAYLOAD:
                raise gl.vm.UserError("Rendered web body is unavailable or exceeds payload limit.")
            raw_model = gl.nondet.exec_prompt(
                _build_anchor_audit_prompt(uri, hypothesis, prior_digest, prior_semantic, body),
                response_format="json",
            )
            validated_semantic = _validate_anchor_model_output(raw_model)
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
            return {"content_digest": digest, "semantic": validated_semantic}

        def validator_fn(leader_result: Any) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader_pkg = _validate_observation_package(leader_result.calldata)
                validator_pkg = _validate_observation_package(observe())
            except Exception:
                return False
            # Consensus assertion: exact agreement on the categorical mutation verdict
            return leader_pkg["semantic"]["mutation"] == validator_pkg["semantic"]["mutation"]

        return _validate_observation_package(gl.vm.run_nondet(observe, validator_fn))

    def _consensus_adjudicate_verdict(self, prompt: str, dependencies: list[str]) -> dict[str, Any]:
        """
        Reaches multi-validator consensus over verdict adjudication against its dependency topology.
        Validators enforce exact agreement on outcome enum and sorted affected dependency IDs.
        """
        def evaluate() -> dict[str, Any]:
            raw_model = gl.nondet.exec_prompt(prompt, response_format="json")
            return _validate_verdict_model_output(raw_model, dependencies)

        def validator_fn(leader_result: Any) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            try:
                leader_data = _validate_verdict_model_output(leader_result.calldata, dependencies)
                validator_data = _validate_verdict_model_output(evaluate(), dependencies)
            except Exception:
                return False
            # Consensus assertion: agreement on both the verdict outcome AND affected dependency IDs
            return (
                leader_data["outcome"] == validator_data["outcome"]
                and leader_data["affected_dependency_ids"] == validator_data["affected_dependency_ids"]
            )

        return _validate_verdict_model_output(
            gl.vm.run_nondet(evaluate, validator_fn), dependencies
        )

    # -------------------------------------------------------------------------
    # Internal Topological & Invariant Algorithms
    # -------------------------------------------------------------------------

    def _load_anchor(self, anchor_id: str) -> AnchorRecord:
        record = self.anchors.get(anchor_id, None)
        if record is None:
            raise gl.vm.UserError(f"Anchor '{anchor_id}' does not exist.")
        return record

    def _load_verdict(self, verdict_id: str) -> VerdictRecord:
        record = self.verdicts.get(verdict_id, None)
        if record is None:
            raise gl.vm.UserError(f"Verdict '{verdict_id}' does not exist.")
        return record

    def _assert_node_exists(self, node_id: str) -> str:
        kind = self.registry_kind.get(node_id, "")
        if not kind:
            raise gl.vm.UserError(f"Node '{node_id}' does not exist in topology.")
        return kind

    def _get_verdict_dependencies(self, verdict: VerdictRecord) -> list[str]:
        deps = json.loads(verdict.dependencies_json)
        if not isinstance(deps, list):
            raise gl.vm.UserError("Corrupted dependencies JSON in storage.")
        return deps

    def _get_dependents_list(self, node_id: str) -> list[str]:
        deps = json.loads(self.downstream_dependents.get(node_id, "[]"))
        if not isinstance(deps, list):
            raise gl.vm.UserError("Corrupted reverse edge list in storage.")
        return deps

    def _register_dependent(self, node_id: str, dependent_id: str) -> None:
        deps = self._get_dependents_list(node_id)
        if dependent_id in deps:
            raise gl.vm.UserError("Duplicate reverse dependency edge.")
        if len(deps) >= MAX_FANOUT_LIMIT:
            raise gl.vm.UserError(f"Fanout limit exceeded for node '{node_id}'.")
        deps.append(dependent_id)
        deps.sort()
        self.downstream_dependents[node_id] = _canonical_json(deps)

    def _get_index_entries(self, index: gl.storage.TreeMap[str, str], curator: str) -> list[str]:
        entries = json.loads(index.get(curator, "[]"))
        if not isinstance(entries, list):
            raise gl.vm.UserError("Corrupted curator index in storage.")
        return entries

    def _append_to_index(self, index: gl.storage.TreeMap[str, str], curator: str, node_id: str) -> None:
        entries = self._get_index_entries(index, curator)
        if node_id in entries:
            raise gl.vm.UserError("Duplicate node registration in curator index.")
        if len(entries) >= MAX_CASCADE_NODES:
            raise gl.vm.UserError("Curator index capacity exceeded.")
        entries.append(node_id)
        entries.sort()
        index[curator] = _canonical_json(entries)

    def _assert_dependencies_intact(self, dependencies: list[str]) -> None:
        for dep_id in dependencies:
            self._assert_node_exists(dep_id)

    def _assert_acyclic(self, candidate_id: str, dependencies: list[str]) -> None:
        """
        Performs depth-first cycle traversal.
        Guarantees that admitting the new verdict cannot create a directed topological cycle.
        """
        visited: list[str] = []
        pending = list(dependencies)
        nodes_traversed = 0

        while pending:
            curr = pending.pop()
            if curr == candidate_id:
                raise gl.vm.UserError("Topological cycle detected: a verdict cannot depend on its own descendants.")
            if curr in visited:
                continue
            visited.append(curr)
            nodes_traversed += 1
            if nodes_traversed > MAX_CASCADE_NODES:
                raise gl.vm.UserError("Cycle detection path length exceeded boundary ceiling.")

            if self.registry_kind.get(curr, "") == "VERDICT":
                parent_verdict = self._load_verdict(curr)
                pending.extend(self._get_verdict_dependencies(parent_verdict))

    def _get_node_epoch(self, node_id: str) -> int:
        kind = self._assert_node_exists(node_id)
        if kind == "ANCHOR":
            return int(self._load_anchor(node_id).epoch)
        return int(self._load_verdict(node_id).epoch)

    def _get_node_depth(self, node_id: str) -> int:
        kind = self._assert_node_exists(node_id)
        if kind == "ANCHOR":
            return 0
        return int(self._load_verdict(node_id).topology_depth)

    def _export_current_snapshot_json(self, dependencies: list[str]) -> str:
        snapshot: dict[str, int] = {}
        for dep_id in dependencies:
            snapshot[dep_id] = self._get_node_epoch(dep_id)
        return _canonical_json(snapshot)

    def _build_dependency_context(
        self, dependencies: list[str], snapshot: dict[str, Any]
    ) -> list[dict[str, Any]]:
        context: list[dict[str, Any]] = []
        for dep_id in dependencies:
            kind = self._assert_node_exists(dep_id)
            if kind == "ANCHOR":
                anchor = self._load_anchor(dep_id)
                context.append(
                    {
                        "id": dep_id,
                        "kind": "ANCHOR",
                        "status": anchor.status,
                        "epoch": int(anchor.epoch),
                        "snapshot_epoch": snapshot.get(dep_id),
                        "content_digest": anchor.content_digest,
                        "semantic": json.loads(anchor.semantic_snapshot) if anchor.semantic_snapshot else None,
                    }
                )
            else:
                parent_verdict = self._load_verdict(dep_id)
                context.append(
                    {
                        "id": dep_id,
                        "kind": "VERDICT",
                        "persisted_status": parent_verdict.status,
                        "effective_status": self._resolve_effective_status(dep_id, [], 0),
                        "epoch": int(parent_verdict.epoch),
                        "snapshot_epoch": snapshot.get(dep_id),
                        "adjudication": json.loads(parent_verdict.adjudication_json)
                        if parent_verdict.adjudication_json
                        else None,
                    }
                )
        return context

    def _are_dependencies_healthy(self, dependencies: list[str]) -> bool:
        """Checks if all dependencies are currently in active/valid state."""
        for dep_id in dependencies:
            kind = self._assert_node_exists(dep_id)
            if kind == "ANCHOR":
                if self._load_anchor(dep_id).status != ANCHOR_ACTIVE:
                    return False
            elif self._resolve_effective_status(dep_id, [], 0) != VERDICT_VALID:
                return False
        return True

    def _resolve_effective_status(self, verdict_id: str, visited: list[str], depth: int) -> str:
        """
        Recursively resolves effective health status without paying consensus or LLM overhead.
        Detects if an upstream dependency has mutated or diverged from the recorded epoch snapshot.
        """
        if depth > MAX_TOPOLOGY_DEPTH or verdict_id in visited:
            return VERDICT_STALE
        verdict = self._load_verdict(verdict_id)
        if verdict.status != VERDICT_VALID:
            return verdict.status

        snapshot = json.loads(verdict.dependency_epoch_snapshot)
        next_visited = visited + [verdict_id]

        for dep_id in self._get_verdict_dependencies(verdict):
            # Check epoch snapshot parity
            if self._get_node_epoch(dep_id) != int(snapshot.get(dep_id, -1)):
                return VERDICT_STALE

            kind = self._assert_node_exists(dep_id)
            if kind == "ANCHOR":
                anchor_status = self._load_anchor(dep_id).status
                if anchor_status == ANCHOR_DEGRADED:
                    return VERDICT_INDETERMINATE
                if anchor_status != ANCHOR_ACTIVE:
                    return VERDICT_STALE
            else:
                parent_status = self._resolve_effective_status(dep_id, next_visited, depth + 1)
                if parent_status == VERDICT_INDETERMINATE:
                    return VERDICT_INDETERMINATE
                if parent_status != VERDICT_VALID:
                    return VERDICT_STALE

        return VERDICT_VALID

    def _cascade_staleness(self, origin_node_id: str) -> None:
        """
        Executes bounded breadth-first staleness cascade over reverse dependency edges.
        Invalidates downstream decisions deterministically without LLM calls.
        """
        queue: list[tuple[str, int]] = [(origin_node_id, 0)]
        visited: list[str] = []
        nodes_cascaded = 0

        while queue:
            current_id, depth = queue.pop(0)
            if current_id in visited:
                continue
            visited.append(current_id)
            nodes_cascaded += 1

            if nodes_cascaded > MAX_CASCADE_NODES:
                raise gl.vm.UserError("Staleness cascade exceeded node count safety limit.")
            if depth > MAX_TOPOLOGY_DEPTH:
                raise gl.vm.UserError("Staleness cascade exceeded topology depth limit.")

            for dependent_id in self._get_dependents_list(current_id):
                dependent_verdict = self._load_verdict(dependent_id)
                dependent_verdict.status = VERDICT_STALE
                queue.append((dependent_id, depth + 1))

    def _degrade_anchor(self, anchor: AnchorRecord) -> None:
        """Marks an anchor degraded upon observation failure and propagates staleness."""
        semantic = {
            "mutation": OBSERVATION_INDETERMINATE,
            "rationale": "External empirical evidence unreachable or rendering failure.",
        }
        anchor.status = ANCHOR_DEGRADED
        anchor.semantic_snapshot = _canonical_json(semantic)
        anchor.epoch_fingerprint = _digest_label(
            "CASCADIA-ANCHOR-EPOCH-V1",
            anchor.anchor_id,
            int(anchor.epoch),
            anchor.content_digest,
            semantic,
        )
        self._cascade_staleness(anchor.anchor_id)

    def _anchor_export_json(self, anchor: AnchorRecord) -> str:
        return json.dumps(
            {
                "anchor_id": anchor.anchor_id,
                "status": anchor.status,
                "epoch": int(anchor.epoch),
                "content_digest": anchor.content_digest,
                "semantic_snapshot": json.loads(anchor.semantic_snapshot) if anchor.semantic_snapshot else None,
                "epoch_fingerprint": anchor.epoch_fingerprint,
            },
            sort_keys=True,
        )

    def _verdict_export_json(self, verdict: VerdictRecord) -> str:
        return json.dumps(
            {
                "verdict_id": verdict.verdict_id,
                "status": verdict.status,
                "effective_status": self._resolve_effective_status(verdict.verdict_id, [], 0),
                "epoch": int(verdict.epoch),
                "adjudication": json.loads(verdict.adjudication_json) if verdict.adjudication_json else None,
                "dependency_epoch_snapshot": json.loads(verdict.dependency_epoch_snapshot),
                "epoch_fingerprint": verdict.epoch_fingerprint,
            },
            sort_keys=True,
        )
