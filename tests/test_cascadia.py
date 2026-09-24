"""Comprehensive test suite for CASCADIA Protocol."""

import hashlib
import json
from pathlib import Path
import pytest


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "contracts" / "cascadia.py"
SOURCE_URI = "https://registry.example.org/compliance-charter"
GENESIS_BODY = "Acme Corp maintains SOC 2 Type II compliance. Certification is fully active."
MUTATED_BODY = "Acme Corp SOC 2 compliance has been REVOKED and is no longer active."


def make_anchor_payload(mutation: str, rationale: str = "Verified empirical evidence.") -> str:
    return json.dumps({"mutation": mutation, "rationale": rationale})


def make_verdict_payload(
    outcome: str,
    rationale: str = "Dependency facts support the conclusion.",
    affected: list[str] | None = None,
) -> str:
    return json.dumps(
        {
            "outcome": outcome,
            "rationale": rationale,
            "affected_dependency_ids": affected or [],
        }
    )


def deploy_contract(direct_deploy):
    return direct_deploy(CONTRACT_PATH)


def register_default_anchor(contract, direct_vm, sender, anchor_id="anchor-alpha") -> None:
    direct_vm.sender = sender
    contract.register_anchor(
        anchor_id,
        SOURCE_URI,
        "Acme Corp maintains active SOC 2 compliance.",
    )


def establish_default_verdict(contract, direct_vm, sender, verdict_id="verdict-beta", deps=None):
    direct_vm.sender = sender
    return contract.establish_verdict(
        verdict_id,
        "Acme Corp is certified for enterprise vendor procurement.",
        deps or ["anchor-alpha"],
    )


def read_anchor_state(contract, anchor_id="anchor-alpha"):
    return json.loads(contract.get_anchor(anchor_id))


def read_verdict_state(contract, verdict_id="verdict-beta"):
    return json.loads(contract.get_verdict(verdict_id))


def audit_with_active_baseline(
    contract,
    direct_vm,
    sender,
    anchor_id="anchor-alpha",
    uri_pattern=r"https://registry[.]example[.]org/compliance-charter",
    body=GENESIS_BODY,
):
    direct_vm.clear_mocks()
    direct_vm.mock_web(uri_pattern, {"body": body})
    direct_vm.mock_llm(r".*", make_anchor_payload("NO_MUTATION"))
    direct_vm.sender = sender
    return json.loads(contract.audit_anchor(anchor_id))


# -----------------------------------------------------------------------------
# 1. Registration & Duplicate Protection Tests
# -----------------------------------------------------------------------------

def test_register_anchor_and_duplicate_rejected(direct_vm, direct_deploy, direct_alice):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    anchor = read_anchor_state(contract)

    assert anchor["status"] == "ANCHOR_GENESIS"
    assert anchor["content_digest"] == ""
    assert anchor["semantic_snapshot"] is None
    assert anchor["epoch"] == 0
    assert anchor["definition_fingerprint"] == hashlib.sha256(
        json.dumps(
            [
                "CASCADIA-ANCHOR-DEF-V1",
                "anchor-alpha",
                "0x" + direct_alice.hex(),
                SOURCE_URI,
                "Acme Corp maintains active SOC 2 compliance.",
            ],
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    with direct_vm.expect_revert("already exists"):
        register_default_anchor(contract, direct_vm, direct_alice)


def test_establish_verdict_rejects_unknown_self_and_duplicate_dependencies(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    establish_default_verdict(contract, direct_vm, direct_alice)

    with direct_vm.expect_revert("does not exist"):
        establish_default_verdict(contract, direct_vm, direct_alice, "v-bad", ["missing-node"])

    with direct_vm.expect_revert("Self-referential"):
        establish_default_verdict(contract, direct_vm, direct_alice, "v-self", ["v-self"])

    with direct_vm.expect_revert("Duplicate dependency"):
        establish_default_verdict(contract, direct_vm, direct_alice, "v-dup", ["anchor-alpha", "anchor-alpha"])


def test_verdict_initial_status_and_deterministic_reverse_edges(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    establish_default_verdict(contract, direct_vm, direct_alice)

    verdict = read_verdict_state(contract)
    assert verdict["status"] == "VERDICT_INITIAL_STALE"
    assert verdict["epoch"] == 0
    assert verdict["topology_depth"] == 1
    assert verdict["dependencies"] == ["anchor-alpha"]
    assert verdict["dependency_epoch_snapshot"] == {"anchor-alpha": 0}

    dependents = json.loads(contract.get_downstream_dependents("anchor-alpha"))
    assert dependents == ["verdict-beta"]


# -----------------------------------------------------------------------------
# 2. Topological Cycle Prevention
# -----------------------------------------------------------------------------

def test_topological_cycle_guard_rejects_circular_paths(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-b", ["anchor-alpha"])
    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-c", ["verdict-b"])

    with direct_vm.expect_revert("Topological cycle detected"):
        # Attempt to make a circular dependency: verdict-b cannot depend on verdict-c
        direct_vm.sender = direct_alice
        contract.establish_verdict("verdict-cycle", "Loop test", ["verdict-c"])
        # Now create edge pointing back to B
        contract.establish_verdict("verdict-b-back", "Backwards edge", ["verdict-cycle"])


# -----------------------------------------------------------------------------
# 3. Genesis Baseline & Consensus Alignment
# -----------------------------------------------------------------------------

def test_genesis_observation_pins_baseline_without_epoch_increment(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    audit = audit_with_active_baseline(contract, direct_vm, direct_alice)

    assert audit["status"] == "ANCHOR_ACTIVE"
    assert audit["epoch"] == 0
    assert audit["semantic_snapshot"]["mutation"] == "NO_MUTATION"
    assert audit["semantic_snapshot"]["rationale"] == "Genesis observation established empirical truth baseline."
    assert len(audit["content_digest"]) == 64


def test_anchor_audit_consensus_tolerates_rationale_text_variances(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    audit_with_active_baseline(contract, direct_vm, direct_alice)

    # Leader outputs one rationale, validator outputs another, but both agree on NO_MUTATION
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://registry[.]example[.]org/compliance-charter", {"body": GENESIS_BODY})
    direct_vm.mock_llm(r".*", make_anchor_payload("NO_MUTATION", "Leader says: ISO charter confirms active status."))

    direct_vm.sender = direct_alice
    contract.audit_anchor("anchor-alpha")

    # Validator executes with distinct rationale
    direct_vm.mock_llm(r".*", make_anchor_payload("NO_MUTATION", "Validator says: Active status validated."))
    assert direct_vm.run_validator() is True


def test_anchor_mutation_disagreement_rejected_by_validator(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    audit_with_active_baseline(contract, direct_vm, direct_alice)

    # Leader claims MUTATION_DETECTED, validator claims NO_MUTATION
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://registry[.]example[.]org/compliance-charter", {"body": MUTATED_BODY})
    direct_vm.mock_llm(r".*", make_anchor_payload("MUTATION_DETECTED", "Charter revoked."))

    direct_vm.sender = direct_alice
    contract.audit_anchor("anchor-alpha")

    direct_vm.mock_llm(r".*", make_anchor_payload("NO_MUTATION", "Disagreement by validator."))
    assert direct_vm.run_validator() is False


def test_verdict_outcome_disagreement_rejected_by_validator(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    audit_with_active_baseline(contract, direct_vm, direct_alice)
    establish_default_verdict(contract, direct_vm, direct_alice)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_AFFIRMED", "Affirmed by leader."))
    direct_vm.sender = direct_alice
    contract.adjudicate_verdict("verdict-beta")

    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_DISPROVED", "Disproved by validator."))
    assert direct_vm.run_validator() is False


# -----------------------------------------------------------------------------
# 4. Multi-Tier Staleness Cascades
# -----------------------------------------------------------------------------

def test_mutation_advances_epoch_and_cascades_staleness_to_descendants(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    audit_with_active_baseline(contract, direct_vm, direct_alice)

    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-b", ["anchor-alpha"])
    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-c", ["verdict-b"])

    # First adjudicate B and C to valid
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_AFFIRMED", "B is valid."))
    contract.adjudicate_verdict("verdict-b")

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_AFFIRMED", "C is valid."))
    contract.adjudicate_verdict("verdict-c")

    assert read_verdict_state(contract, "verdict-b")["status"] == "VERDICT_VALID"
    assert read_verdict_state(contract, "verdict-c")["status"] == "VERDICT_VALID"

    # Now simulate empirical mutation on anchor-alpha
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://registry[.]example[.]org/compliance-charter", {"body": MUTATED_BODY})
    direct_vm.mock_llm(r".*", make_anchor_payload("MUTATION_DETECTED", "Charter revoked."))
    contract.audit_anchor("anchor-alpha")

    anchor = read_anchor_state(contract, "anchor-alpha")
    assert anchor["status"] == "ANCHOR_MUTATED"
    assert anchor["epoch"] == 1

    # Both descendants must be transitioned to VERDICT_STALE via BFS cascade
    assert read_verdict_state(contract, "verdict-b")["status"] == "VERDICT_STALE"
    assert read_verdict_state(contract, "verdict-c")["status"] == "VERDICT_STALE"


def test_effective_verdict_detects_snapshot_mismatch_without_llm(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    audit_with_active_baseline(contract, direct_vm, direct_alice)

    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-b", ["anchor-alpha"])

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_AFFIRMED"))
    contract.adjudicate_verdict("verdict-b")

    assert contract.evaluate_effective_verdict("verdict-b") == "VERDICT_VALID"

    # Mutate anchor
    direct_vm.clear_mocks()
    direct_vm.mock_web(r"https://registry[.]example[.]org/compliance-charter", {"body": MUTATED_BODY})
    direct_vm.mock_llm(r".*", make_anchor_payload("MUTATION_DETECTED", "Changed."))
    contract.audit_anchor("anchor-alpha")

    # evaluate_effective_verdict reports VERDICT_STALE deterministically
    assert contract.evaluate_effective_verdict("verdict-b") == "VERDICT_STALE"


def test_invalidated_verdict_cascades_staleness_to_downstream_verdicts(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    audit_with_active_baseline(contract, direct_vm, direct_alice)

    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-b", ["anchor-alpha"])
    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-c", ["verdict-b"])

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_AFFIRMED"))
    contract.adjudicate_verdict("verdict-b")
    contract.adjudicate_verdict("verdict-c")

    # Invalidate B
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_DISPROVED", "Disproved due to audit findings."))
    contract.adjudicate_verdict("verdict-b")

    assert read_verdict_state(contract, "verdict-b")["status"] == "VERDICT_INVALIDATED"
    # C cascades to VERDICT_STALE
    assert read_verdict_state(contract, "verdict-c")["status"] == "VERDICT_STALE"


# -----------------------------------------------------------------------------
# 5. Fail-Closed Error Handling & Boundary Limits
# -----------------------------------------------------------------------------

def test_fail_closed_degradation_on_external_network_or_model_error(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)

    # Empty web mock simulates network failure
    direct_vm.clear_mocks()
    contract.audit_anchor("anchor-alpha")

    anchor = read_anchor_state(contract, "anchor-alpha")
    assert anchor["status"] == "ANCHOR_DEGRADED"


def test_curator_indices_accurately_expose_created_nodes(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice, "anchor-1")
    register_default_anchor(contract, direct_vm, direct_alice, "anchor-2")
    establish_default_verdict(contract, direct_vm, direct_alice, "verdict-1", ["anchor-1"])

    alice_addr = "0x" + direct_alice.hex()
    anchors = json.loads(contract.get_curator_anchors(alice_addr))
    verdicts = json.loads(contract.get_curator_verdicts(alice_addr))

    assert anchors == ["anchor-1", "anchor-2"]
    assert verdicts == ["verdict-1"]


def test_genesis_anchor_cannot_support_valid_verdict(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy_contract(direct_deploy)
    register_default_anchor(contract, direct_vm, direct_alice)
    establish_default_verdict(contract, direct_vm, direct_alice)

    # Attempt to adjudicate verdict while anchor is still in ANCHOR_GENESIS
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r".*", make_verdict_payload("VERDICT_AFFIRMED"))
    contract.adjudicate_verdict("verdict-beta")

    # Invariant safety check forces VERDICT_INDETERMINATE because dependency is not ANCHOR_ACTIVE
    verdict = read_verdict_state(contract, "verdict-beta")
    assert verdict["status"] == "VERDICT_INDETERMINATE"
