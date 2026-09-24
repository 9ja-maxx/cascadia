# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import hashlib
import json
from dataclasses import dataclass
from typing import Any

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

# Verdict Adjudication Categorical Outcomes
VERDICT_AFFIRMED = "VERDICT_AFFIRMED"
VERDICT_DISPROVED = "VERDICT_DISPROVED"
VERDICT_UNRESOLVED = "VERDICT_UNRESOLVED"

# Protocol Bounds & Limits
MAX_IDENTIFIER = 64
MAX_URI = 1024
MAX_HYPOTHESIS = 2048
MAX_INQUIRY = 2048
MAX_RATIONALE = 512
MAX_RENDER_PAYLOAD = 32768
MAX_DEPENDENCIES_PER_VERDICT = 8
MAX_FANOUT_LIMIT = 32
MAX_CASCADE_NODES = 128
MAX_TOPOLOGY_DEPTH = 32

ANCHOR_OBSERVATION_KEYS = {"mutation", "rationale"}
VERDICT_ADJUDICATION_KEYS = {"outcome", "rationale", "affected_dependency_ids"}


# -----------------------------------------------------------------------------
# Record Schemas & Serialization
# -----------------------------------------------------------------------------

@dataclass
class AnchorRecord:
    """Verifiable ground-truth external web observation point."""
    anchor_id: str
    custodian: str
    uri: str
    tracked_hypothesis: str
    epoch: int
    content_digest: str
    semantic_snapshot: str
    status: str
    definition_fingerprint: str
    epoch_fingerprint: str

    def to_json(self) -> str:
        return json.dumps({
            "anchor_id": self.anchor_id,
            "custodian": self.custodian,
            "uri": self.uri,
            "tracked_hypothesis": self.tracked_hypothesis,
            "epoch": int(self.epoch),
            "content_digest": self.content_digest,
            "semantic_snapshot": self.semantic_snapshot,
            "status": self.status,
            "definition_fingerprint": self.definition_fingerprint,
            "epoch_fingerprint": self.epoch_fingerprint,
        }, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "AnchorRecord":
        d = json.loads(raw)
        return cls(
            anchor_id=d["anchor_id"],
            custodian=d["custodian"],
            uri=d["uri"],
            tracked_hypothesis=d["tracked_hypothesis"],
            epoch=int(d["epoch"]),
            content_digest=d["content_digest"],
            semantic_snapshot=d["semantic_snapshot"],
            status=d["status"],
            definition_fingerprint=d["definition_fingerprint"],
            epoch_fingerprint=d["epoch_fingerprint"],
        )


@dataclass
class VerdictRecord:
    """Reasoned conclusion bound to an upstream dependency topology."""
    verdict_id: str
    curator: str
    inquiry: str
    dependencies_json: str
    dependency_epoch_snapshot: str
    topology_depth: int
    epoch: int
    adjudication_json: str
    status: str
    definition_fingerprint: str
    epoch_fingerprint: str

    def to_json(self) -> str:
        return json.dumps({
            "verdict_id": self.verdict_id,
            "curator": self.curator,
            "inquiry": self.inquiry,
            "dependencies_json": self.dependencies_json,
            "dependency_epoch_snapshot": self.dependency_epoch_snapshot,
            "topology_depth": int(self.topology_depth),
            "epoch": int(self.epoch),
            "adjudication_json": self.adjudication_json,
            "status": self.status,
            "definition_fingerprint": self.definition_fingerprint,
            "epoch_fingerprint": self.epoch_fingerprint,
        }, sort_keys=True)

    @classmethod
    def from_json(cls, raw: str) -> "VerdictRecord":
        d = json.loads(raw)
        return cls(
            verdict_id=d["verdict_id"],
            curator=d["curator"],
            inquiry=d["inquiry"],
            dependencies_json=d["dependencies_json"],
            dependency_epoch_snapshot=d["dependency_epoch_snapshot"],
            topology_depth=int(d["topology_depth"]),
            epoch=int(d["epoch"]),
            adjudication_json=d["adjudication_json"],
            status=d["status"],
            definition_fingerprint=d["definition_fingerprint"],
            epoch_fingerprint=d["epoch_fingerprint"],
        )


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
    if not uri_str.startswith("https://") or len(uri_str) <= 8:
        raise gl.vm.UserError("Source URI must be a valid HTTPS location (starting with https://).")
    if "#" in uri_str:
        raise gl.vm.UserError("Source URI must not contain URL fragments (#).")
    return uri_str


def _validate_anchor_model_output(payload: Any) -> dict[str, str]:
    """Validates the categorical output schema returned by the observation LLM."""
    if not isinstance(payload, dict) or set(payload.keys()) != ANCHOR_OBSERVATION_KEYS:
        raise gl.vm.UserError("Anchor model output does not conform to required observation schema.")
    mutation = payload.get("mutation")
    rationale = payload.get("rationale")
    if mutation not in (MUTATION_DETECTED, NO_MUTATION, OBSERVATION_INDETERMINATE):
        raise gl.vm.UserError(f"Illegal mutation state '{mutation}' in anchor model response.")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > MAX_RATIONALE:
        raise gl.vm.UserError("Anchor model rationale is invalid, empty, or exceeds length ceiling.")
    return {"mutation": mutation, "rationale": rationale.strip()}


def _validate_observation_package(package: Any) -> dict[str, Any]:
    """Validates structure of raw non-deterministic observation payload."""
    if not isinstance(package, dict) or "content_digest" not in package or "semantic" not in package:
        raise gl.vm.UserError("Observation package missing required digest or semantic components.")
    if not isinstance(package["content_digest"], str) or len(package["content_digest"]) != 64:
        raise gl.vm.UserError("Observation package carries an invalid SHA-256 content digest.")
    semantic = _validate_anchor_model_output(package["semantic"])
    return {"content_digest": package["content_digest"], "semantic": semantic}


def _validate_verdict_model_output(payload: Any, valid_dependencies: list[str]) -> dict[str, Any]:
    """Validates the categorical adjudication schema returned by the decision LLM."""
    if not isinstance(payload, dict) or set(payload.keys()) != VERDICT_ADJUDICATION_KEYS:
        raise gl.vm.UserError("Verdict model output does not conform to required adjudication schema.")
    outcome = payload.get("outcome")
    rationale = payload.get("rationale")
    affected = payload.get("affected_dependency_ids")

    if outcome not in (VERDICT_AFFIRMED, VERDICT_DISPROVED, VERDICT_UNRESOLVED):
        raise gl.vm.UserError(f"Illegal adjudication outcome '{outcome}' in verdict model response.")
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale) > MAX_RATIONALE:
        raise gl.vm.UserError("Verdict model rationale is invalid, empty, or exceeds length ceiling.")
    if not isinstance(affected, list):
        raise gl.vm.UserError("Affected dependencies must be returned as a JSON list.")

    valid_set = set(valid_dependencies)
    clean_affected: list[str] = []
    for dep_id in affected:
        if not isinstance(dep_id, str) or dep_id not in valid_set:
            raise gl.vm.UserError(f"Affected dependency '{dep_id}' is not in the declared dependency set.")
        if dep_id not in clean_affected:
            clean_affected.append(dep_id)
    clean_affected.sort()

    return {
        "outcome": outcome,
        "rationale": rationale.strip(),
        "affected_dependency_ids": clean_affected,
    }


# -----------------------------------------------------------------------------
# Consensus Prompt Engineering
# -----------------------------------------------------------------------------

def _build_anchor_audit_prompt(
    uri: str,
    hypothesis: str,
    prior_digest: str,
    prior_semantic_json: str,
    rendered_body: str,
) -> str:
    """Constructs prompt for multi-validator empirical truth evaluation."""
    prior_info = prior_semantic_json if prior_semantic_json else "None (Initial Baseline)"
    return (
        "You are an empirical fact-checking validator in the CASCADIA Protocol.\n"
        "Your task is to observe rendered web content and evaluate a specific factual hypothesis.\n\n"
        f"TARGET URI: {uri}\n"
        f"TRACKED HYPOTHESIS: {hypothesis}\n"
        f"PRIOR CONTENT HASH: {prior_digest if prior_digest else 'GENESIS'}\n"
        f"PRIOR SEMANTIC STATE: {prior_info}\n\n"
        "--- LIVE OBSERVED EVIDENCE BEGIN ---\n"
        f"{rendered_body[:MAX_RENDER_PAYLOAD]}\n"
        "--- LIVE OBSERVED EVIDENCE END ---\n\n"
        "Analyze whether the live content affirms or mutates the hypothesis:\n"
        "1. If the hypothesis remains fully supported and true: 'NO_MUTATION'\n"
        "2. If the ground truth has shifted, expired, revoked, or changed: 'MUTATION_DETECTED'\n"
        "3. If evidence is ambiguous, missing, or contradictory: 'OBSERVATION_INDETERMINATE'\n\n"
        "Return ONLY a JSON object with this exact schema:\n"
        '{"mutation": "NO_MUTATION|MUTATION_DETECTED|OBSERVATION_INDETERMINATE", "rationale": "..."}\n'
        "Keep the rationale concise and under 512 characters."
    )


def _build_verdict_adjudication_prompt(
    inquiry: str,
    context_json: str,
    valid_dependencies: list[str],
) -> str:
    """Constructs prompt for multi-validator causal verdict adjudication."""
    dep_list_str = ", ".join(valid_dependencies)
    return (
        "You are a causal adjudication validator in the CASCADIA Protocol.\n"
        "Evaluate the following inquiry strictly based on the current state of its dependencies.\n\n"
        f"PRIMARY INQUIRY: {inquiry}\n"
        f"VALID DEPENDENCIES: [{dep_list_str}]\n\n"
        "--- CURRENT DEPENDENCY CONTEXT BEGIN ---\n"
        f"{context_json}\n"
        "--- CURRENT DEPENDENCY CONTEXT END ---\n\n"
        "Determine the status of the inquiry:\n"
        "1. If dependency facts support affirmative resolution: 'VERDICT_AFFIRMED'\n"
        "2. If facts invalidate or contradict the inquiry: 'VERDICT_DISPROVED'\n"
        "3. If evidence is incomplete or indeterminable: 'VERDICT_UNRESOLVED'\n\n"
        "List all dependency IDs whose status specifically affected this determination.\n"
        "Return ONLY a JSON object with this exact schema:\n"
        '{"outcome": "VERDICT_AFFIRMED|VERDICT_DISPROVED|VERDICT_UNRESOLVED", '
        '"rationale": "...", "affected_dependency_ids": ["..."]}\n'
        "Every ID in affected_dependency_ids must belong to the declared dependencies list.\n"
        "Keep the rationale concise and under 512 characters."
    )


# -----------------------------------------------------------------------------
# Main Intelligent Contract Class
# -----------------------------------------------------------------------------

class Cascadia(gl.Contract):
    """
    CASCADIA PROTOCOL
    Autonomous causal dependency graph, empirical truth monitoring, and staleness cascades.
    """

    anchors: TreeMap[str, str]
    verdicts: TreeMap[str, str]
    registry_kind: TreeMap[str, str]            # Unified namespace preventing ID collisions
    downstream_dependents: TreeMap[str, str]    # Canonical reverse-edge adjacency list
    curator_anchors: TreeMap[str, str]          # Account -> [anchor_id, ...]
    curator_verdicts: TreeMap[str, str]         # Account -> [verdict_id, ...]
    total_nodes: u256

    def __init__(self):
        """Initializes the empty CASCADIA topology."""
        self.total_nodes = u256(0)
        self.anchors = TreeMap()
        self.verdicts = TreeMap()
        self.registry_kind = TreeMap()
        self.downstream_dependents = TreeMap()
        self.curator_anchors = TreeMap()
        self.curator_verdicts = TreeMap()

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

        self._save_anchor(record)
        self.registry_kind[anchor_id] = "ANCHOR"
        self.downstream_dependents[anchor_id] = "[]"
        self._append_to_index(self.curator_anchors, custodian, anchor_id)
        self.total_nodes = self.total_nodes + u256(1)

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

        clean_dependencies: list[str] = []
        for dep_id in dependencies:
            clean_dep = _sanitize_identifier(dep_id, "dependency_id")
            if clean_dep == verdict_id:
                raise gl.vm.UserError("Self-referential dependencies are forbidden.")
            if clean_dep not in clean_dependencies:
                clean_dependencies.append(clean_dep)
        clean_dependencies.sort()

        self._assert_dependencies_intact(clean_dependencies)
        self._assert_acyclic(verdict_id, clean_dependencies)

        depth = 0
        for dep_id in clean_dependencies:
            dep_depth = self._get_node_depth(dep_id)
            if dep_depth + 1 > depth:
                depth = dep_depth + 1

        if depth > MAX_TOPOLOGY_DEPTH:
            raise gl.vm.UserError(f"Graph depth {depth} exceeds protocol safety ceiling of {MAX_TOPOLOGY_DEPTH}.")

        curator = str(gl.message.sender_address).lower()
        dependencies_json = _canonical_json(clean_dependencies)
        definition_fingerprint = _digest_label(
            "CASCADIA-VERDICT-DEF-V1",
            verdict_id,
            curator,
            inquiry,
            dependencies_json,
        )

        initial_snapshot = self._export_current_snapshot_json(clean_dependencies)
        epoch_fingerprint = _digest_label(
            "CASCADIA-VERDICT-EPOCH-V1",
            verdict_id,
            0,
            initial_snapshot,
            "",
        )

        record = VerdictRecord(
            verdict_id=verdict_id,
            curator=curator,
            inquiry=inquiry,
            dependencies_json=dependencies_json,
            dependency_epoch_snapshot=initial_snapshot,
            topology_depth=depth,
            epoch=0,
            adjudication_json="",
            status=VERDICT_INITIAL_STALE,
            definition_fingerprint=definition_fingerprint,
            epoch_fingerprint=epoch_fingerprint,
        )

        self._save_verdict(record)
        self.registry_kind[verdict_id] = "VERDICT"
        self.downstream_dependents[verdict_id] = "[]"
        self._append_to_index(self.curator_verdicts, curator, verdict_id)
        self.total_nodes = self.total_nodes + u256(1)

        # Register reverse dependency edges
        for dep_id in clean_dependencies:
            self._register_dependent(dep_id, verdict_id)

        return json.dumps(
            {
                "verdict_id": verdict_id,
                "status": VERDICT_INITIAL_STALE,
                "topology_depth": depth,
                "dependencies": clean_dependencies,
                "definition_fingerprint": definition_fingerprint,
            },
            sort_keys=True,
        )

    @gl.public.write
    def audit_anchor(self, anchor_id: str) -> str:
        """
        Executes multi-validator consensus to observe empirical web state and check for mutations.
        Triggers reverse-edge staleness cascade if a material mutation is affirmed by consensus.
        """
        anchor_id = _sanitize_identifier(anchor_id, "anchor_id")
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
        mutation = semantic["mutation"]

        is_first_audit = anchor.status == ANCHOR_GENESIS
        anchor.content_digest = content_digest
        anchor.semantic_snapshot = _canonical_json(semantic)
        anchor.epoch = anchor.epoch + 1

        if is_first_audit:
            # Genesis observation establishes initial empirical baseline
            if mutation == MUTATION_DETECTED:
                anchor.status = ANCHOR_MUTATED
            else:
                anchor.status = ANCHOR_ACTIVE
        elif mutation == MUTATION_DETECTED:
            anchor.status = ANCHOR_MUTATED
            self._cascade_staleness(anchor_id)
        elif mutation == OBSERVATION_INDETERMINATE:
            anchor.status = ANCHOR_DEGRADED
            self._cascade_staleness(anchor_id)
        else:
            if anchor.status != ANCHOR_ACTIVE:
                anchor.status = ANCHOR_ACTIVE

        anchor.epoch_fingerprint = _digest_label(
            "CASCADIA-ANCHOR-EPOCH-V1",
            anchor.anchor_id,
            int(anchor.epoch),
            anchor.content_digest,
            anchor.semantic_snapshot,
        )

        self._save_anchor(anchor)
        return self._anchor_export_json(anchor)

    @gl.public.write
    def adjudicate_verdict(self, verdict_id: str) -> str:
        """
        Executes multi-validator consensus to adjudicate a verdict against its declared dependencies.
        Enforces strict prerequisite that all upstream dependencies must be fresh and healthy.
        """
        verdict_id = _sanitize_identifier(verdict_id, "verdict_id")
        verdict = self._load_verdict(verdict_id)
        dependencies = self._get_verdict_dependencies(verdict)

        if not self._are_dependencies_healthy(dependencies):
            raise gl.vm.UserError("Cannot adjudicate verdict: one or more upstream dependencies are stale, mutated, or degraded.")

        current_snapshot = self._export_current_snapshot_json(dependencies)
        context_json = self._build_dependency_context(dependencies)
        prompt = _build_verdict_adjudication_prompt(verdict.inquiry, context_json, dependencies)

        adjudication = self._consensus_adjudicate_verdict(prompt, dependencies)
        outcome = adjudication["outcome"]

        verdict.epoch = verdict.epoch + 1
        verdict.dependency_epoch_snapshot = current_snapshot
        verdict.adjudication_json = _canonical_json(adjudication)

        if outcome == VERDICT_AFFIRMED:
            verdict.status = VERDICT_VALID
        elif outcome == VERDICT_DISPROVED:
            verdict.status = VERDICT_INVALIDATED
            self._cascade_staleness(verdict_id)
        else:
            verdict.status = VERDICT_INDETERMINATE
            self._cascade_staleness(verdict_id)

        verdict.epoch_fingerprint = _digest_label(
            "CASCADIA-VERDICT-EPOCH-V1",
            verdict.verdict_id,
            int(verdict.epoch),
            verdict.dependency_epoch_snapshot,
            verdict.adjudication_json,
        )

        self._save_verdict(verdict)
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
            validated = _validate_observation_package(leader_result)
            candidate = observe()
            # Consensus criteria: exact agreement on categorical mutation outcome
            return candidate["semantic"]["mutation"] == validated["semantic"]["mutation"]

        return gl.vm.run_nondet(
            observe,
            validator_fn,
        )

    def _consensus_adjudicate_verdict(self, prompt: str, dependencies: list[str]) -> dict[str, Any]:
        """
        Reaches multi-validator consensus over LLM causal reasoning.
        Enforces agreement on categorical outcome and affected dependency sets while tolerating rationale variances.
        """
        def evaluate() -> dict[str, Any]:
            raw_model = gl.nondet.exec_prompt(prompt, response_format="json")
            return _validate_verdict_model_output(raw_model, dependencies)

        def validator_fn(leader_result: Any) -> bool:
            validated = _validate_verdict_model_output(leader_result, dependencies)
            candidate = evaluate()
            return (
                candidate["outcome"] == validated["outcome"]
                and candidate["affected_dependency_ids"] == validated["affected_dependency_ids"]
            )

        return gl.vm.run_nondet(
            evaluate,
            validator_fn,
        )

    # -------------------------------------------------------------------------
    # Internal Storage & Record Persistence
    # -------------------------------------------------------------------------

    def _save_anchor(self, anchor: AnchorRecord) -> None:
        self.anchors[anchor.anchor_id] = anchor.to_json()

    def _save_verdict(self, verdict: VerdictRecord) -> None:
        self.verdicts[verdict.verdict_id] = verdict.to_json()

    def _load_anchor(self, anchor_id: str) -> AnchorRecord:
        if self.registry_kind.get(anchor_id, "") != "ANCHOR":
            raise gl.vm.UserError(f"Anchor '{anchor_id}' does not exist.")
        raw = self.anchors.get(anchor_id, "")
        if not raw:
            raise gl.vm.UserError(f"Anchor record for '{anchor_id}' is empty.")
        return AnchorRecord.from_json(raw)

    def _load_verdict(self, verdict_id: str) -> VerdictRecord:
        if self.registry_kind.get(verdict_id, "") != "VERDICT":
            raise gl.vm.UserError(f"Verdict '{verdict_id}' does not exist.")
        raw = self.verdicts.get(verdict_id, "")
        if not raw:
            raise gl.vm.UserError(f"Verdict record for '{verdict_id}' is empty.")
        return VerdictRecord.from_json(raw)

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

    def _get_index_entries(self, index: TreeMap[str, str], curator: str) -> list[str]:
        entries = json.loads(index.get(curator, "[]"))
        if not isinstance(entries, list):
            raise gl.vm.UserError("Corrupted curator index in storage.")
        return entries

    def _append_to_index(self, index: TreeMap[str, str], curator: str, node_id: str) -> None:
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
        Enforces strict DAG acyclicity invariants prior to admitting new edges.
        Walks upstream paths from dependencies using breadth-first traversal.
        """
        queue: list[str] = list(dependencies)
        visited: list[str] = []

        while queue:
            curr = queue.pop(0)
            if curr == candidate_id:
                raise gl.vm.UserError(f"Topological cycle detected: dependency path references '{candidate_id}'.")
            if curr in visited:
                continue
            visited.append(curr)

            if len(visited) > MAX_CASCADE_NODES:
                raise gl.vm.UserError("Cycle verification exceeded node safety limit.")

            if self.registry_kind.get(curr, "") == "VERDICT":
                parent_verdict = self._load_verdict(curr)
                queue.extend(self._get_verdict_dependencies(parent_verdict))

    def _get_node_epoch(self, node_id: str) -> int:
        if self.registry_kind.get(node_id, "") == "ANCHOR":
            return int(self._load_anchor(node_id).epoch)
        return int(self._load_verdict(node_id).epoch)

    def _get_node_depth(self, node_id: str) -> int:
        if self.registry_kind.get(node_id, "") == "ANCHOR":
            return 0
        return int(self._load_verdict(node_id).topology_depth)

    def _export_current_snapshot_json(self, dependencies: list[str]) -> str:
        snapshot = {dep_id: self._get_node_epoch(dep_id) for dep_id in dependencies}
        return _canonical_json(snapshot)

    def _build_dependency_context(
        self, dependencies: list[str]
    ) -> str:
        """Builds structured JSON payload documenting the current state of all dependencies."""
        context: dict[str, Any] = {}
        for dep_id in dependencies:
            kind = self._assert_node_exists(dep_id)
            if kind == "ANCHOR":
                anchor = self._load_anchor(dep_id)
                context[dep_id] = {
                    "kind": "ANCHOR",
                    "status": anchor.status,
                    "hypothesis": anchor.tracked_hypothesis,
                    "epoch": int(anchor.epoch),
                    "semantic": json.loads(anchor.semantic_snapshot) if anchor.semantic_snapshot else None,
                }
            else:
                parent_verdict = self._load_verdict(dep_id)
                context[dep_id] = {
                    "kind": "VERDICT",
                    "status": parent_verdict.status,
                    "inquiry": parent_verdict.inquiry,
                    "epoch": int(parent_verdict.epoch),
                    "adjudication": json.loads(parent_verdict.adjudication_json) if parent_verdict.adjudication_json else None,
                }
        return _canonical_json(context)

    def _are_dependencies_healthy(self, dependencies: list[str]) -> bool:
        """Returns True if all upstream direct dependencies are currently in a valid state."""
        for dep_id in dependencies:
            kind = self.registry_kind.get(dep_id, "")
            if kind == "ANCHOR":
                if self._load_anchor(dep_id).status != ANCHOR_ACTIVE:
                    return False
            elif kind == "VERDICT":
                if self._load_verdict(dep_id).status != VERDICT_VALID:
                    return False
            else:
                return False
        return True

    def _resolve_effective_status(self, verdict_id: str, visited: list[str], depth: int) -> str:
        """
        Recursively walks upstream DAG paths to compute the effective health of a decision.
        Returns VERDICT_VALID only if all ancestor paths terminate in active anchors without mutations.
        """
        if verdict_id in visited:
            return VERDICT_INDETERMINATE
        if depth > MAX_TOPOLOGY_DEPTH:
            return VERDICT_INDETERMINATE

        verdict = self._load_verdict(verdict_id)
        if verdict.status != VERDICT_VALID:
            return verdict.status

        dependencies = self._get_verdict_dependencies(verdict)
        next_visited = list(visited)
        next_visited.append(verdict_id)

        for dep_id in dependencies:
            kind = self.registry_kind.get(dep_id, "")
            if not kind:
                return VERDICT_INDETERMINATE

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
                if self.registry_kind.get(dependent_id, "") == "VERDICT":
                    dependent_verdict = self._load_verdict(dependent_id)
                    if dependent_verdict.status != VERDICT_STALE:
                        dependent_verdict.status = VERDICT_STALE
                        self._save_verdict(dependent_verdict)
                    queue.append((dependent_id, depth + 1))

    def _degrade_anchor(self, anchor: AnchorRecord) -> None:
        """Marks an anchor degraded upon observation failure and propagates staleness."""
        semantic = {
            "mutation": OBSERVATION_INDETERMINATE,
            "rationale": "External empirical evidence unreachable or rendering failure.",
        }
        anchor.status = ANCHOR_DEGRADED
        anchor.semantic_snapshot = _canonical_json(semantic)
        anchor.epoch = anchor.epoch + 1
        anchor.epoch_fingerprint = _digest_label(
            "CASCADIA-ANCHOR-EPOCH-V1",
            anchor.anchor_id,
            int(anchor.epoch),
            anchor.content_digest,
            anchor.semantic_snapshot,
        )
        self._save_anchor(anchor)
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
