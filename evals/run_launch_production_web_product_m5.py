#!/usr/bin/env python3
"""Deterministic qualification for the first M5 Delivery Mission slice."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from delivery_missions import (  # noqa: E402
    MissionError,
    decide_next_action,
    initialize_project_state,
    validate_decision,
    validate_spec,
)
from jit_expertise import compile_capsule  # noqa: E402
from project_state import (  # noqa: E402
    DELIVERY_STATES,
    EVIDENCE_KIND_FOR_STATE,
    add_entry,
    add_evidence,
    advance_delivery_state,
    select_context,
    validate_state,
)

SPEC_PATH = ROOT / "delivery_missions" / "launch_production_web_product" / "fixtures" / "basic-web-product.json"
INVENTORY_PATH = ROOT / "tool_capabilities" / "fixtures" / "codex-inventory.json"
REPORT_PATH = ROOT / "eval-results" / "launch-production-web-product-m5-report.json"
SCHEMA_PATH = ROOT / "delivery_missions" / "launch_production_web_product" / "mission.schema.json"

TIMES = [
    "2026-08-25T07:30:00Z",
    "2026-08-25T07:31:00Z",
    "2026-08-25T07:32:00Z",
    "2026-08-25T07:33:00Z",
    "2026-08-25T07:34:00Z",
    "2026-08-25T07:35:00Z",
    "2026-08-25T07:36:00Z",
    "2026-08-25T07:37:00Z",
    "2026-08-25T07:38:00Z",
]
SOURCE_DIGEST = hashlib.sha256(b"official-provider-contract").hexdigest()


def _spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _inventory(*, captured_at: str = TIMES[4]) -> dict:
    value = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    value["captured_at"] = captured_at
    return value


def _add_tool(
    inventory: dict,
    capability: str,
    *,
    access: str = "WRITE",
    sensitivity: str = "SANDBOX",
    authorization: str = "NOT_REQUIRED",
) -> dict:
    value = copy.deepcopy(inventory)
    surface_id = "mcp-" + capability.replace("_", "-")
    # Replacing a synthetic capability must also remove any pre-existing
    # concrete surfaces explicitly bound to that capability. Otherwise a base
    # fixture such as BIND-hosting plus a synthetic BIND-hosting would make the
    # inventory invalid for reasons unrelated to the M5 scenario under test.
    replaced_surface_ids = {
        item["surface_id"]
        for item in value["bindings"]
        if item["capability"] == capability
    }
    value["bindings"] = [
        item for item in value["bindings"] if item["capability"] != capability
    ]
    value["surfaces"] = [
        item
        for item in value["surfaces"]
        if item["id"] not in replaced_surface_ids and item["id"] != surface_id
    ]
    value["surfaces"].append(
        {
            "id": surface_id,
            "source_kind": "MCP",
            "tool_name": capability.replace("_", "."),
            "source_ref": f"tool-schema://codex/mcp/{capability}",
            "availability": "AVAILABLE",
            "authentication": "AUTHENTICATED",
            "access": access,
            "sensitivity": sensitivity,
            "evidence_kinds": ["structured_evidence"],
            "evidence_ref": f"inventory-evidence://codex/mcp/{capability}",
            "authorization_required": authorization,
            "authorization_ref": f"policy://session/{capability}",
        }
    )
    value["bindings"].append(
        {
            "id": "BIND-" + capability.replace("_", "-"),
            "surface_id": surface_id,
            "capability": capability,
            "binding_kind": "SEF_ADAPTER",
            "binding_ref": f"sef-binding://codex/{capability}/v1",
        }
    )
    return value


def _full_sandbox_inventory(*, captured_at: str = TIMES[4]) -> dict:
    value = _inventory(captured_at=captured_at)
    for capability, access in [
        ("source_control", "WRITE"),
        ("ci", "READ"),
        ("database_admin", "WRITE"),
        ("auth_admin", "WRITE"),
        ("billing_admin", "WRITE"),
        ("external_provider_sandbox", "WRITE"),
        ("observability", "READ"),
    ]:
        value = _add_tool(value, capability, access=access)
    # Add a least-privilege preview hosting surface so preview does not require
    # the production authorization carried by the fixture's production tool.
    value = _add_tool(value, "hosting", access="WRITE", sensitivity="SANDBOX")
    return value


def _state_at(spec: dict, target: str) -> dict:
    state = initialize_project_state(
        spec,
        evidence_locator="conversation://mission-outcome",
        at=TIMES[0],
    )
    target_index = DELIVERY_STATES.index(target)
    for index in range(1, target_index + 1):
        to_state = DELIVERY_STATES[index]
        evidence_id = f"EVID-{to_state}"
        state = add_evidence(
            state,
            evidence_id=evidence_id,
            kind=EVIDENCE_KIND_FOR_STATE[to_state],
            locator=f"artifact://qualification/{to_state.lower()}",
            observed_at=TIMES[index],
        )
        state = advance_delivery_state(
            state,
            to_state=to_state,
            evidence_refs=[evidence_id],
            at=TIMES[index],
            reason=f"Qualification fixture has observed evidence for {to_state}.",
        )
    return state


def _provider_spec() -> dict:
    spec = _spec()
    spec["surfaces"]["external_integrations"] = [{"id": "provider", "name": "Example Provider"}]
    spec["expertise_needs"] = [
        {
            "id": "provider-contract",
            "mission_need": "Integrate Example Provider using its current supported contract.",
            "subject": {
                "kind": "EXTERNAL_PROVIDER",
                "name": "Example Provider",
                "version_context": "current observed contract",
            },
            "context_domains": ["requirements"],
        }
    ]
    return spec


def _provider_capsule(spec: dict, state: dict, *, generated_at: str, max_age: int = 3600, with_tool: bool = False) -> dict:
    need = spec["expertise_needs"][0]
    context = select_context(state, need["context_domains"])
    tools = []
    verification_paths = []
    if with_tool:
        tools = [
            {
                "capability": "external_provider_sandbox",
                "availability": "AVAILABLE",
                "access": "WRITE",
                "observed_at": TIMES[1],
            }
        ]
        verification_paths = [
            {
                "id": "VERIFY-PROVIDER",
                "description": "Exercise the integration in an authorized sandbox.",
                "required_tools": ["external_provider_sandbox"],
                "supports": [{"source_ref": "SRC-OFFICIAL", "anchor": "Sandbox verification"}],
            }
        ]
    return compile_capsule(
        capsule_id="CAPSULE-PROVIDER-001",
        project_id=spec["project_id"],
        mission_need=need["mission_need"],
        subject=need["subject"],
        generated_at=generated_at,
        project_context=context,
        sources=[
            {
                "id": "SRC-OFFICIAL",
                "tier": "OFFICIAL",
                "uri": "https://docs.example.test/provider",
                "observed_at": generated_at,
                "max_age_seconds": max_age,
                "content_sha256": SOURCE_DIGEST,
                "subject_version": "current",
                "status": "OBSERVED",
            }
        ],
        constraints=[
            {
                "id": "CONSTRAINT-PROVIDER",
                "statement": "Use the observed supported provider contract for this integration.",
                "materiality": "MATERIAL",
                "supports": [{"source_ref": "SRC-OFFICIAL", "anchor": "Supported contract"}],
            }
        ],
        tools=tools,
        verification_paths=verification_paths,
        uncertainties=[],
    )


def _expect_error(fn, contains: str) -> str:
    try:
        fn()
    except MissionError as exc:
        message = str(exc)
        assert contains in message, (contains, message)
        return message
    raise AssertionError("expected MissionError")


def control_schema_and_basic_spec() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    spec = _spec()
    validate_spec(spec)
    assert schema["properties"]["schema"]["const"] == spec["schema"]
    return {"schema": spec["schema"], "acceptance": len(spec["acceptance"])}


def control_initialization_uses_m1_state() -> dict:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    validate_state(state)
    assert state["delivery_state"] == "FRAMED"
    assert {item["id"] for item in state["domains"]["requirements"]} == {"ACCEPT-primary-journey", "ACCEPT-responsive-quality"}
    return {"state": state["delivery_state"], "revision": state["revision"]}


def control_state_action_mapping() -> dict:
    spec = _spec()
    inventory = _full_sandbox_inventory()
    expected = {
        "FRAMED": "PLAN_ARCHITECTURE",
        "ARCHITECTED": "IMPLEMENT_PRODUCT",
        "IMPLEMENTED": "VERIFY_LOCAL_PRODUCT",
        "VERIFIED_LOCAL": "DEPLOY_AND_VERIFY_PREVIEW",
        "PREVIEW_VERIFIED": "PROVE_RELEASE_READINESS",
        "RELEASE_READY": "DEPLOY_PRODUCTION",
        "DEPLOYED": "VERIFY_PRODUCTION",
        "POST_DEPLOY_VERIFIED": "COMPLETE",
    }
    observed = {}
    for state_name, action in expected.items():
        state = _state_at(spec, state_name)
        decision = decide_next_action(spec, state, at=TIMES[8], tool_inventory=inventory)
        observed[state_name] = decision["next_action"]
        assert decision["next_action"] == action
    return observed


def control_framed_needs_no_tool_inventory() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "FRAMED"), at=TIMES[1])
    assert decision["status"] == "READY_FOR_AGENT"
    assert decision["tool_requirements"] == []
    return {"status": decision["status"], "action": decision["next_action"]}


def control_implementation_requires_source_control() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "ARCHITECTED"), at=TIMES[2], tool_inventory=_inventory(captured_at=TIMES[2]))
    assert "TOOL_UNKNOWN:source_control" in decision["blockers"]
    return {"status": decision["status"], "blockers": decision["blockers"]}


def control_implementation_ready_with_source_control() -> dict:
    spec = _spec()
    inventory = _add_tool(_inventory(captured_at=TIMES[2]), "source_control")
    decision = decide_next_action(spec, _state_at(spec, "ARCHITECTED"), at=TIMES[2], tool_inventory=inventory)
    assert decision["status"] == "READY_FOR_AGENT"
    return {"status": decision["status"]}


def control_local_verification_activates_visual_pack() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "IMPLEMENTED"), at=TIMES[3], tool_inventory=_inventory(captured_at=TIMES[3]))
    assert decision["active_packs"] == ["web-experience-visual-quality"]
    assert decision["status"] == "READY_FOR_AGENT"
    capabilities = {item["capability"] for item in decision["tool_requirements"]}
    assert {"browser", "visual_capture"}.issubset(capabilities)
    return {"packs": decision["active_packs"], "capabilities": sorted(capabilities)}


def control_material_data_change_activates_data_pack() -> dict:
    spec = _spec()
    spec["surfaces"]["persistent_data"] = True
    spec["surfaces"]["material_data_change"] = True
    inventory = _add_tool(_inventory(captured_at=TIMES[3]), "database_admin")
    decision = decide_next_action(spec, _state_at(spec, "IMPLEMENTED"), at=TIMES[3], tool_inventory=inventory)
    assert decision["active_packs"] == ["data-change-safety", "web-experience-visual-quality"]
    return {"packs": decision["active_packs"]}


def control_data_pack_not_loaded_without_material_change() -> dict:
    spec = _spec()
    spec["surfaces"]["persistent_data"] = True
    inventory = _add_tool(_inventory(captured_at=TIMES[3]), "database_admin")
    decision = decide_next_action(spec, _state_at(spec, "IMPLEMENTED"), at=TIMES[3], tool_inventory=inventory)
    assert "data-change-safety" not in decision["active_packs"]
    return {"packs": decision["active_packs"]}


def control_preview_requires_hosting_browser_visual() -> dict:
    spec = _spec()
    inventory = _full_sandbox_inventory(captured_at=TIMES[4])
    decision = decide_next_action(spec, _state_at(spec, "VERIFIED_LOCAL"), at=TIMES[4], tool_inventory=inventory)
    capabilities = {item["capability"] for item in decision["tool_requirements"]}
    assert {"hosting", "browser", "visual_capture"}.issubset(capabilities)
    assert decision["status"] == "READY_FOR_AGENT"
    return {"capabilities": sorted(capabilities)}


def control_release_readiness_requires_ci() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "PREVIEW_VERIFIED"), at=TIMES[5], tool_inventory=_full_sandbox_inventory(captured_at=TIMES[5]))
    capabilities = {item["capability"] for item in decision["tool_requirements"]}
    assert "ci" in capabilities
    return {"capabilities": sorted(capabilities)}


def control_production_deploy_requires_authorization() -> dict:
    spec = _spec()
    # Use the original fixture production hosting surface, which is technically
    # capable but explicitly requires production authorization.
    inventory = _inventory(captured_at=TIMES[6])
    decision = decide_next_action(spec, _state_at(spec, "RELEASE_READY"), at=TIMES[6], tool_inventory=inventory)
    assert "TOOL_AUTHORIZATION_REQUIRED:hosting" in decision["blockers"]
    assert decision["claims"]["production_authorization_granted"] is False
    return {"status": decision["status"], "blockers": decision["blockers"]}


def control_authorized_production_hosting_can_be_ready() -> dict:
    spec = _spec()
    inventory = _add_tool(
        _inventory(captured_at=TIMES[6]),
        "hosting",
        access="WRITE",
        sensitivity="PRODUCTION_SENSITIVE",
        authorization="NOT_REQUIRED",
    )
    decision = decide_next_action(spec, _state_at(spec, "RELEASE_READY"), at=TIMES[6], tool_inventory=inventory)
    assert decision["status"] == "READY_FOR_AGENT"
    return {"status": decision["status"]}


def control_deployed_activates_operations_pack() -> dict:
    spec = _spec()
    inventory = _full_sandbox_inventory(captured_at=TIMES[7])
    inventory = _add_tool(inventory, "browser", access="READ", sensitivity="PRODUCTION_SENSITIVE")
    inventory = _add_tool(inventory, "observability", access="READ", sensitivity="PRODUCTION_SENSITIVE")
    inventory = _add_tool(inventory, "hosting", access="WRITE", sensitivity="PRODUCTION_SENSITIVE")
    decision = decide_next_action(spec, _state_at(spec, "DEPLOYED"), at=TIMES[7], tool_inventory=inventory)
    assert decision["active_packs"] == ["production-evidence-operations"]
    return {"packs": decision["active_packs"]}


def control_complete_requires_no_execution_claim() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "POST_DEPLOY_VERIFIED"), at=TIMES[8])
    assert decision["status"] == "COMPLETE"
    assert not any(decision["claims"].values())
    return {"status": decision["status"], "claims": decision["claims"]}


def control_missing_tool_inventory_blocks_material_action() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "IMPLEMENTED"), at=TIMES[3])
    assert decision["blockers"] == ["TOOL_INVENTORY_REQUIRED"]
    return {"blockers": decision["blockers"]}


def control_stale_tool_inventory_is_not_current() -> dict:
    spec = _spec()
    inventory = _inventory(captured_at=TIMES[1])
    decision = decide_next_action(
        spec,
        _state_at(spec, "IMPLEMENTED"),
        at=TIMES[8],
        tool_inventory=inventory,
        max_tool_age_seconds=300,
    )
    assert "TOOL_INVENTORY_STALE" in decision["blockers"]
    return {"blockers": decision["blockers"]}


def control_identity_billing_data_integration_capabilities() -> dict:
    spec = _provider_spec()
    spec["surfaces"]["persistent_data"] = True
    spec["surfaces"]["identity_access"] = True
    spec["surfaces"]["billing"] = True
    state = _state_at(spec, "ARCHITECTED")
    capsule = _provider_capsule(spec, state, generated_at=TIMES[2])
    inventory = _full_sandbox_inventory(captured_at=TIMES[2])
    decision = decide_next_action(spec, state, at=TIMES[2], tool_inventory=inventory, capsules=[capsule])
    capabilities = {item["capability"] for item in decision["tool_requirements"]}
    assert {"source_control", "database_admin", "auth_admin", "billing_admin", "external_provider_sandbox"}.issubset(capabilities)
    return {"capabilities": sorted(capabilities)}


def control_missing_jit_capsule_blocks_after_architecture() -> dict:
    spec = _provider_spec()
    inventory = _add_tool(_inventory(captured_at=TIMES[2]), "source_control")
    inventory = _add_tool(inventory, "external_provider_sandbox")
    decision = decide_next_action(spec, _state_at(spec, "ARCHITECTED"), at=TIMES[2], tool_inventory=inventory)
    assert "JIT_CAPSULE_REQUIRED:provider-contract" in decision["blockers"]
    return {"blockers": decision["blockers"]}


def control_ready_jit_capsule_allows_progress() -> dict:
    spec = _provider_spec()
    state = _state_at(spec, "ARCHITECTED")
    capsule = _provider_capsule(spec, state, generated_at=TIMES[2])
    inventory = _add_tool(_inventory(captured_at=TIMES[2]), "source_control")
    inventory = _add_tool(inventory, "external_provider_sandbox")
    decision = decide_next_action(spec, state, at=TIMES[2], tool_inventory=inventory, capsules=[capsule])
    assert decision["jit_readiness"][0]["status"] == "READY"
    assert decision["status"] == "READY_FOR_AGENT"
    return {"jit": decision["jit_readiness"]}


def control_expired_jit_source_blocks() -> dict:
    spec = _provider_spec()
    state = _state_at(spec, "ARCHITECTED")
    capsule = _provider_capsule(spec, state, generated_at=TIMES[1], max_age=60)
    inventory = _add_tool(_inventory(captured_at=TIMES[4]), "source_control")
    inventory = _add_tool(inventory, "external_provider_sandbox")
    decision = decide_next_action(spec, state, at=TIMES[4], tool_inventory=inventory, capsules=[capsule])
    assert "JIT_CAPSULE_NOT_READY:provider-contract" in decision["blockers"]
    assert any(reason.startswith("SOURCE_EXPIRED:") for reason in decision["jit_readiness"][0]["reasons"])
    return {"reasons": decision["jit_readiness"][0]["reasons"]}


def control_jit_context_change_blocks() -> dict:
    spec = _provider_spec()
    state = _state_at(spec, "ARCHITECTED")
    capsule = _provider_capsule(spec, state, generated_at=TIMES[2])
    changed = add_entry(
        state,
        domain="requirements",
        entry_id="ASSUMPTION-NEW",
        kind="ASSUMPTION",
        statement="A newly discovered material requirement changes the provider context.",
        authority="ENGINEERING",
        evidence_refs=[],
        updated_at=TIMES[3],
    )
    inventory = _add_tool(_inventory(captured_at=TIMES[3]), "source_control")
    inventory = _add_tool(inventory, "external_provider_sandbox")
    decision = decide_next_action(spec, changed, at=TIMES[3], tool_inventory=inventory, capsules=[capsule])
    assert "PROJECT_CONTEXT_CHANGED" in decision["jit_readiness"][0]["reasons"]
    return {"reasons": decision["jit_readiness"][0]["reasons"]}


def control_jit_tool_reobservation_timestamp_is_not_semantic_change() -> dict:
    spec = _provider_spec()
    state = _state_at(spec, "ARCHITECTED")
    capsule = _provider_capsule(spec, state, generated_at=TIMES[2], with_tool=True)
    inventory = _add_tool(_inventory(captured_at=TIMES[3]), "source_control")
    inventory = _add_tool(inventory, "external_provider_sandbox", access="WRITE")
    decision = decide_next_action(spec, state, at=TIMES[3], tool_inventory=inventory, capsules=[capsule])
    assert "TOOL_CAPABILITY_CHANGED" not in decision["jit_readiness"][0]["reasons"]
    assert decision["jit_readiness"][0]["status"] == "READY"
    return {"jit": decision["jit_readiness"][0]}


def control_jit_tool_access_change_is_semantic_change() -> dict:
    spec = _provider_spec()
    state = _state_at(spec, "ARCHITECTED")
    capsule = _provider_capsule(spec, state, generated_at=TIMES[2], with_tool=True)
    inventory = _add_tool(_inventory(captured_at=TIMES[3]), "source_control")
    inventory = _add_tool(inventory, "external_provider_sandbox", access="READ")
    decision = decide_next_action(spec, state, at=TIMES[3], tool_inventory=inventory, capsules=[capsule])
    assert "TOOL_CAPABILITY_CHANGED" in decision["jit_readiness"][0]["reasons"]
    return {"reasons": decision["jit_readiness"][0]["reasons"]}


def control_state_outcome_divergence_rejected() -> dict:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    changed = copy.deepcopy(spec)
    changed["outcome"] = "A different outcome that is not represented in Project State."
    message = _expect_error(lambda: decide_next_action(changed, state, at=TIMES[1]), "does not contain the mission outcome")
    return {"rejected": message}


def control_acceptance_divergence_rejected() -> dict:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    changed = copy.deepcopy(spec)
    changed["acceptance"][0]["statement"] = "A materially different acceptance claim."
    message = _expect_error(lambda: decide_next_action(changed, state, at=TIMES[1]), "diverges from mission")
    return {"rejected": message}


def control_material_data_requires_persistent_data() -> dict:
    spec = _spec()
    spec["surfaces"]["material_data_change"] = True
    message = _expect_error(lambda: validate_spec(spec), "requires persistent_data=true")
    return {"rejected": message}


def control_non_web_mission_rejected() -> dict:
    spec = _spec()
    spec["surfaces"]["web_ui"] = False
    message = _expect_error(lambda: validate_spec(spec), "requires surfaces.web_ui=true")
    return {"rejected": message}


def control_acceptance_cannot_be_empty_or_nonblocking() -> dict:
    empty = _spec()
    empty["acceptance"] = []
    message1 = _expect_error(lambda: validate_spec(empty), "acceptance must be a non-empty list")
    nonblocking = _spec()
    for item in nonblocking["acceptance"]:
        item["blocking"] = False
    message2 = _expect_error(lambda: validate_spec(nonblocking), "at least one acceptance criterion")
    return {"empty": message1, "nonblocking": message2}


def control_secret_shaped_value_rejected() -> dict:
    spec = _spec()
    spec["outcome"] += " api_key=sk-exampleSecretValue123456789"
    message = _expect_error(lambda: validate_spec(spec), "credential-shaped secret value")
    return {"rejected": message}


def control_decision_is_sealed_and_tamper_detected() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "FRAMED"), at=TIMES[1])
    validate_decision(decision)
    tampered = copy.deepcopy(decision)
    tampered["next_action"] = "DEPLOY_PRODUCTION"
    message = _expect_error(lambda: validate_decision(tampered), "content hash mismatch")
    return {"digest": decision["content_sha256"], "tamper": message}


def control_decision_never_advances_state() -> dict:
    spec = _spec()
    state = _state_at(spec, "IMPLEMENTED")
    original = state["content_sha256"]
    decision = decide_next_action(spec, state, at=TIMES[3], tool_inventory=_inventory(captured_at=TIMES[3]))
    assert state["content_sha256"] == original
    assert decision["project_state_sha256"] == original
    assert decision["claims"]["state_advanced_by_decision"] is False
    return {"state_sha256": original}


def control_progressive_context_is_smaller_than_full_state() -> dict:
    spec = _spec()
    decision = decide_next_action(spec, _state_at(spec, "FRAMED"), at=TIMES[1])
    assert set(decision["context_domains"]) < set([
        "product", "requirements", "architecture", "interfaces", "data", "identity_access", "integrations",
        "environments", "quality", "security", "release", "deployments", "observability", "open_decisions", "known_risks"
    ])
    return {"domains": decision["context_domains"]}


def control_legacy_runtime_integrity() -> dict:
    expected = None
    for raw in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        parts = raw.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == "sef.py":
            expected = parts[0]
            break
    assert expected
    observed = hashlib.sha256((ROOT / "sef.py").read_bytes()).hexdigest()
    assert observed == expected
    return {"sef_sha256": observed}


CONTROLS = [
    ("M5-01-schema-basic-spec", control_schema_and_basic_spec),
    ("M5-02-initialize-m1-state", control_initialization_uses_m1_state),
    ("M5-03-state-action-mapping", control_state_action_mapping),
    ("M5-04-framed-no-tool-block", control_framed_needs_no_tool_inventory),
    ("M5-05-implementation-source-control", control_implementation_requires_source_control),
    ("M5-06-implementation-ready", control_implementation_ready_with_source_control),
    ("M5-07-visual-pack-local", control_local_verification_activates_visual_pack),
    ("M5-08-data-pack-material-only", control_material_data_change_activates_data_pack),
    ("M5-09-no-data-pack-without-material-change", control_data_pack_not_loaded_without_material_change),
    ("M5-10-preview-tool-surface", control_preview_requires_hosting_browser_visual),
    ("M5-11-release-readiness-ci", control_release_readiness_requires_ci),
    ("M5-12-production-authorization", control_production_deploy_requires_authorization),
    ("M5-13-authorized-production-ready", control_authorized_production_hosting_can_be_ready),
    ("M5-14-production-operations-pack", control_deployed_activates_operations_pack),
    ("M5-15-complete-nonclaim", control_complete_requires_no_execution_claim),
    ("M5-16-missing-inventory", control_missing_tool_inventory_blocks_material_action),
    ("M5-17-stale-inventory", control_stale_tool_inventory_is_not_current),
    ("M5-18-dynamic-capabilities", control_identity_billing_data_integration_capabilities),
    ("M5-19-missing-jit", control_missing_jit_capsule_blocks_after_architecture),
    ("M5-20-ready-jit", control_ready_jit_capsule_allows_progress),
    ("M5-21-expired-jit-source", control_expired_jit_source_blocks),
    ("M5-22-jit-context-change", control_jit_context_change_blocks),
    ("M5-23-jit-reobservation-stable", control_jit_tool_reobservation_timestamp_is_not_semantic_change),
    ("M5-24-jit-tool-access-change", control_jit_tool_access_change_is_semantic_change),
    ("M5-25-outcome-state-alignment", control_state_outcome_divergence_rejected),
    ("M5-26-acceptance-state-alignment", control_acceptance_divergence_rejected),
    ("M5-27-material-data-consistency", control_material_data_requires_persistent_data),
    ("M5-28-web-scope-contract", control_non_web_mission_rejected),
    ("M5-29-acceptance-gate", control_acceptance_cannot_be_empty_or_nonblocking),
    ("M5-30-secret-guard", control_secret_shaped_value_rejected),
    ("M5-31-decision-integrity", control_decision_is_sealed_and_tamper_detected),
    ("M5-32-no-state-auto-advance", control_decision_never_advances_state),
    ("M5-33-progressive-context", control_progressive_context_is_smaller_than_full_state),
    ("M5-34-runtime-integrity", control_legacy_runtime_integrity),
]


def main() -> int:
    results = []
    for control_id, fn in CONTROLS:
        try:
            detail = fn()
            results.append({"id": control_id, "status": "PASS", "detail": detail})
        except Exception as exc:
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})
    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.launch-production-web-product-m5.v1",
        "stage": "M5_LAUNCH_PRODUCTION_WEB_PRODUCT_ORCHESTRATION",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "status": "PASS" if passed == len(results) else "FAIL",
        "tool_execution_calls": 0,
        "model_calls": 0,
        "provider_calls": 0,
        "network_calls": 0,
        "deployment_claim": False,
        "m5_end_to_end_claim": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
