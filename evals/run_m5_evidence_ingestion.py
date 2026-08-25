#!/usr/bin/env python3
"""Deterministic qualification for M5 evidence ingestion/state advancement."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from delivery_missions import (  # noqa: E402
    EVIDENCE_RECEIPT_SCHEMA_ID,
    EXECUTION_RESULT_SCHEMA_ID,
    MissionEvidenceError,
    advance_from_execution,
    decide_next_action,
    evaluate_execution_result,
    initialize_project_state,
    seal_execution_result,
    validate_evidence_receipt,
    validate_execution_result,
)
from project_state import (  # noqa: E402
    DELIVERY_STATES,
    EVIDENCE_KIND_FOR_STATE,
    add_evidence,
    advance_delivery_state,
    validate_state,
)

SPEC_PATH = ROOT / "delivery_missions" / "launch_production_web_product" / "fixtures" / "basic-web-product.json"
INVENTORY_PATH = ROOT / "tool_capabilities" / "fixtures" / "codex-inventory.json"
RESULT_SCHEMA_PATH = ROOT / "delivery_missions" / "launch_production_web_product" / "execution-result.schema.json"
RECEIPT_SCHEMA_PATH = ROOT / "delivery_missions" / "launch_production_web_product" / "evidence-receipt.schema.json"
REPORT_PATH = ROOT / "eval-results" / "m5-evidence-ingestion-report.json"

VISUAL_PASS = ROOT / "expert_packs" / "web-experience-visual-quality" / "fixtures" / "pass.json"
VISUAL_FAIL = ROOT / "expert_packs" / "web-experience-visual-quality" / "fixtures" / "fail-material-discrepancy.json"
DATA_PASS = ROOT / "expert_packs" / "data-change-safety" / "fixtures" / "pass-migration.json"
DATA_FAIL = ROOT / "expert_packs" / "data-change-safety" / "fixtures" / "fail-invariant.json"
PROD_PASS = ROOT / "expert_packs" / "production-evidence-operations" / "fixtures" / "pass-production.json"
PROD_FAIL = ROOT / "expert_packs" / "production-evidence-operations" / "fixtures" / "fail-smoke.json"

TIMES = [f"2026-08-25T08:{minute:02d}:00Z" for minute in range(0, 30)]

PRIMARY_CAPABILITY = {
    "PLAN_ARCHITECTURE": None,
    "IMPLEMENT_PRODUCT": "source_control",
    "VERIFY_LOCAL_PRODUCT": "browser",
    "DEPLOY_AND_VERIFY_PREVIEW": "hosting",
    "PROVE_RELEASE_READINESS": "ci",
    "DEPLOY_PRODUCTION": "hosting",
    "VERIFY_PRODUCTION": "browser",
}


def _spec() -> dict[str, Any]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def _state_at(spec: dict[str, Any], target: str) -> dict[str, Any]:
    state = initialize_project_state(
        spec,
        evidence_locator="conversation://qualification/outcome",
        at=TIMES[0],
    )
    target_index = DELIVERY_STATES.index(target)
    for index in range(1, target_index + 1):
        to_state = DELIVERY_STATES[index]
        evidence_id = f"EVID-PRE-{to_state}"
        state = add_evidence(
            state,
            evidence_id=evidence_id,
            kind=EVIDENCE_KIND_FOR_STATE[to_state],
            locator=f"artifact://prequalification/{to_state.lower()}.json",
            observed_at=TIMES[index],
            sha256=hashlib.sha256(to_state.encode("utf-8")).hexdigest(),
        )
        state = advance_delivery_state(
            state,
            to_state=to_state,
            evidence_refs=[evidence_id],
            at=TIMES[index],
            reason=f"Qualification pre-state evidence for {to_state}.",
        )
    return state


def _inventory(*, captured_at: str) -> dict[str, Any]:
    value = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    value["captured_at"] = captured_at
    return value


def _replace_tool(
    inventory: dict[str, Any],
    capability: str,
    *,
    access: str,
    sensitivity: str,
    authorization: str = "NOT_REQUIRED",
) -> dict[str, Any]:
    value = copy.deepcopy(inventory)
    bound_surface_ids = {
        item["surface_id"] for item in value["bindings"] if item["capability"] == capability
    }
    value["bindings"] = [
        item for item in value["bindings"] if item["capability"] != capability
    ]
    value["surfaces"] = [
        item for item in value["surfaces"] if item["id"] not in bound_surface_ids
    ]
    surface_id = f"mcp-{capability.replace('_', '-')}-{sensitivity.lower().replace('_', '-')}"
    value["surfaces"].append(
        {
            "id": surface_id,
            "source_kind": "MCP",
            "tool_name": capability.replace("_", "."),
            "source_ref": f"tool-schema://qualification/{capability}",
            "availability": "AVAILABLE",
            "authentication": "AUTHENTICATED",
            "access": access,
            "sensitivity": sensitivity,
            "evidence_kinds": ["structured_evidence"],
            "evidence_ref": f"inventory-evidence://qualification/{capability}",
            "authorization_required": authorization,
            "authorization_ref": f"policy://qualification/{capability}/{authorization.lower()}",
        }
    )
    value["bindings"].append(
        {
            "id": f"BIND-{capability.replace('_', '-')}-{sensitivity.lower().replace('_', '-')}",
            "surface_id": surface_id,
            "capability": capability,
            "binding_kind": "SEF_ADAPTER",
            "binding_ref": f"sef-binding://qualification/{capability}/v1",
        }
    )
    return value


def _ready_inventory(spec: dict[str, Any], action: str, *, captured_at: str) -> dict[str, Any]:
    value = _inventory(captured_at=captured_at)
    if action == "IMPLEMENT_PRODUCT":
        value = _replace_tool(value, "source_control", access="WRITE", sensitivity="LOCAL")
        if spec["surfaces"]["persistent_data"]:
            value = _replace_tool(value, "database_admin", access="WRITE", sensitivity="SANDBOX")
        if spec["surfaces"]["identity_access"]:
            value = _replace_tool(value, "auth_admin", access="WRITE", sensitivity="SANDBOX")
        if spec["surfaces"]["billing"]:
            value = _replace_tool(value, "billing_admin", access="WRITE", sensitivity="SANDBOX")
        if spec["surfaces"]["external_integrations"]:
            value = _replace_tool(value, "external_provider_sandbox", access="WRITE", sensitivity="SANDBOX")
    elif action == "VERIFY_LOCAL_PRODUCT":
        if spec["surfaces"]["persistent_data"]:
            value = _replace_tool(value, "database_admin", access="WRITE", sensitivity="SANDBOX")
        if spec["surfaces"]["identity_access"]:
            value = _replace_tool(value, "auth_admin", access="WRITE", sensitivity="SANDBOX")
        if spec["surfaces"]["billing"]:
            value = _replace_tool(value, "billing_admin", access="WRITE", sensitivity="SANDBOX")
        if spec["surfaces"]["external_integrations"]:
            value = _replace_tool(value, "external_provider_sandbox", access="WRITE", sensitivity="SANDBOX")
        if spec["surfaces"]["material_data_change"]:
            value = _replace_tool(value, "database_admin", access="WRITE", sensitivity="SANDBOX")
    elif action == "DEPLOY_AND_VERIFY_PREVIEW":
        value = _replace_tool(value, "hosting", access="WRITE", sensitivity="SANDBOX")
    elif action == "PROVE_RELEASE_READINESS":
        value = _replace_tool(value, "ci", access="READ", sensitivity="SANDBOX")
        if spec["surfaces"]["material_data_change"]:
            value = _replace_tool(value, "database_admin", access="WRITE", sensitivity="SANDBOX")
    elif action == "DEPLOY_PRODUCTION":
        value = _replace_tool(
            value,
            "hosting",
            access="WRITE",
            sensitivity="PRODUCTION_SENSITIVE",
            authorization="NOT_REQUIRED",
        )
        if spec["surfaces"]["material_data_change"]:
            value = _replace_tool(value, "database_admin", access="WRITE", sensitivity="SANDBOX")
    elif action == "VERIFY_PRODUCTION":
        value = _replace_tool(value, "browser", access="READ", sensitivity="PRODUCTION_SENSITIVE")
        value = _replace_tool(value, "observability", access="READ", sensitivity="PRODUCTION_SENSITIVE")
        value = _replace_tool(
            value,
            "hosting",
            access="WRITE",
            sensitivity="PRODUCTION_SENSITIVE",
            authorization="NOT_REQUIRED",
        )
    return value


def _decision(spec: dict[str, Any], state: dict[str, Any], *, at: str = TIMES[20]) -> dict[str, Any]:
    action = {
        "FRAMED": "PLAN_ARCHITECTURE",
        "ARCHITECTED": "IMPLEMENT_PRODUCT",
        "IMPLEMENTED": "VERIFY_LOCAL_PRODUCT",
        "VERIFIED_LOCAL": "DEPLOY_AND_VERIFY_PREVIEW",
        "PREVIEW_VERIFIED": "PROVE_RELEASE_READINESS",
        "RELEASE_READY": "DEPLOY_PRODUCTION",
        "DEPLOYED": "VERIFY_PRODUCTION",
        "POST_DEPLOY_VERIFIED": "COMPLETE",
    }[state["delivery_state"]]
    inventory = None if action in {"PLAN_ARCHITECTURE", "COMPLETE"} else _ready_inventory(spec, action, captured_at=at)
    decision = decide_next_action(spec, state, at=at, tool_inventory=inventory)
    assert decision["status"] in {"READY_FOR_AGENT", "COMPLETE"}, decision
    return decision


class ArtifactBuilder:
    def __init__(self, root: Path, decision: dict[str, Any]):
        self.root = root
        self.decision = decision
        self.artifacts: list[dict[str, Any]] = []
        self.by_ref: dict[str, dict[str, Any]] = {}
        self.counter = 0
        self.selected = {
            item["capability"]: item["selected_surface_id"]
            for item in (decision.get("tool_bridge") or {}).get("resolution", {}).get("results", [])
            if item["status"] == "READY" and item["selected_surface_id"] is not None
        }

    def add(
        self,
        ref: str,
        *,
        kind: str,
        producer: str,
        capability: str | None = None,
        payload: bytes | str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if ref in self.by_ref:
            return self.by_ref[ref]
        self.counter += 1
        relative = ref.removeprefix("artifact://")
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, dict):
            data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        elif isinstance(payload, str):
            data = payload.encode("utf-8")
        elif isinstance(payload, bytes):
            data = payload
        else:
            data = (f"qualification evidence for {ref}\n").encode("utf-8")
        path.write_bytes(data)
        artifact = {
            "id": f"ART-{self.counter:03d}",
            "ref": ref,
            "kind": kind,
            "path": relative,
            "sha256": hashlib.sha256(data).hexdigest(),
            "producer": producer,
            "capability": capability if producer == "TOOL" else None,
            "surface_id": self.selected.get(capability) if producer == "TOOL" else None,
        }
        if producer == "TOOL":
            assert artifact["surface_id"], (capability, self.selected)
        self.artifacts.append(artifact)
        self.by_ref[ref] = artifact
        return artifact


def _artifact_refs(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            found |= _artifact_refs(child)
    elif isinstance(value, list):
        for child in value:
            found |= _artifact_refs(child)
    elif isinstance(value, str) and value.startswith("artifact://"):
        found.add(value)
    return found


def _pack_capability(pack_id: str, ref: str) -> str:
    if pack_id == "web-experience-visual-quality":
        return "visual_capture" if ref.endswith(".png") else "browser"
    if pack_id == "data-change-safety":
        return "database_admin"
    if pack_id == "production-evidence-operations":
        if "deployment" in ref or "runtime-version" in ref:
            return "hosting"
        if "logs" in ref or "error-signal" in ref:
            return "observability"
        return "browser"
    raise AssertionError(pack_id)


def _add_pack_observation(
    builder: ArtifactBuilder,
    pack_id: str,
    fixture_path: Path,
    *,
    action: str,
) -> dict[str, str]:
    document = json.loads(fixture_path.read_text(encoding="utf-8"))
    if pack_id == "web-experience-visual-quality":
        if action == "VERIFY_LOCAL_PRODUCT":
            document["target"]["kind"] = "local"
            document["target"]["locator"] = "local://qualification"
        else:
            document["target"]["kind"] = "preview"
            document["target"]["locator"] = "preview://qualification"
    for ref in sorted(_artifact_refs(document)):
        builder.add(
            ref,
            kind="pack-evidence",
            producer="TOOL",
            capability=_pack_capability(pack_id, ref),
        )
    observation_ref = f"artifact://pack-observations/{pack_id}.json"
    builder.add(
        observation_ref,
        kind="pack-observation",
        producer="SYSTEM",
        payload=document,
    )
    return {"pack_id": pack_id, "artifact_ref": observation_ref}


def _successful_result(
    spec: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, Any],
    root: Path,
    *,
    observed_at: str = TIMES[21],
    fixture_overrides: dict[str, Path] | None = None,
) -> dict[str, Any]:
    builder = ArtifactBuilder(root, decision)
    target_index = DELIVERY_STATES.index(state["delivery_state"]) + 1
    target = DELIVERY_STATES[target_index]
    required_kind = EVIDENCE_KIND_FOR_STATE[target]
    primary_capability = PRIMARY_CAPABILITY[decision["next_action"]]

    if primary_capability is None:
        builder.add(
            f"artifact://primary/{required_kind}.json",
            kind=required_kind,
            producer="AGENT",
            payload={"kind": required_kind, "action": decision["next_action"]},
        )

    for requirement in decision["tool_requirements"]:
        capability = requirement["capability"]
        kind = required_kind if capability == primary_capability else "tool-output"
        builder.add(
            f"artifact://tool/{capability}.json",
            kind=kind,
            producer="TOOL",
            capability=capability,
            payload={"capability": capability, "action": decision["next_action"]},
        )

    defaults = {
        "web-experience-visual-quality": VISUAL_PASS,
        "data-change-safety": DATA_PASS,
        "production-evidence-operations": PROD_PASS,
    }
    overrides = fixture_overrides or {}
    pack_observations = [
        _add_pack_observation(
            builder,
            pack_id,
            overrides.get(pack_id, defaults[pack_id]),
            action=decision["next_action"],
        )
        for pack_id in decision["active_packs"]
    ]

    return seal_execution_result(
        {
            "schema": EXECUTION_RESULT_SCHEMA_ID,
            "mission_id": spec["mission_id"],
            "project_id": spec["project_id"],
            "decision_sha256": decision["content_sha256"],
            "project_state_sha256": state["content_sha256"],
            "action": decision["next_action"],
            "observed_at": observed_at,
            "status": "SUCCEEDED",
            "artifacts": builder.artifacts,
            "pack_observations": pack_observations,
        }
    )


def _expect_error(fn, contains: str) -> str:
    try:
        fn()
    except MissionEvidenceError as exc:
        message = str(exc)
        assert contains in message, (contains, message)
        return message
    raise AssertionError("expected MissionEvidenceError")


def control_schema_contracts() -> dict[str, Any]:
    result_schema = json.loads(RESULT_SCHEMA_PATH.read_text(encoding="utf-8"))
    receipt_schema = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert result_schema["properties"]["schema"]["const"] == EXECUTION_RESULT_SCHEMA_ID
    assert receipt_schema["properties"]["schema"]["const"] == EVIDENCE_RECEIPT_SCHEMA_ID
    return {"result": EXECUTION_RESULT_SCHEMA_ID, "receipt": EVIDENCE_RECEIPT_SCHEMA_ID}


def control_architecture_evidence_advances_one_state() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        validate_execution_result(result)
        updated, receipt = advance_from_execution(
            spec,
            state,
            decision,
            result,
            artifact_root=root,
            receipt_path="receipts/architecture.json",
        )
        assert receipt["status"] == "PASS"
        assert updated["delivery_state"] == "ARCHITECTED"
        assert state["delivery_state"] == "FRAMED"
        validate_state(updated)
        latest = updated["evidence"][-1]
        assert latest["kind"] == "architecture-decision"
        receipt_bytes = (root / "receipts/architecture.json").read_bytes()
        assert latest["sha256"] == hashlib.sha256(receipt_bytes).hexdigest()
        return {"from": state["delivery_state"], "to": updated["delivery_state"], "kind": latest["kind"]}


def control_result_exact_decision_binding() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["decision_sha256"] = "a" * 64
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "exact mission decision",
        )
        return {"rejected": message}


def control_result_exact_state_binding() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["project_state_sha256"] = "b" * 64
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "current Project State",
        )
        return {"rejected": message}


def control_action_binding() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["action"] = "DEPLOY_PRODUCTION"
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "action does not match decision",
        )
        return {"rejected": message}


def control_result_tamper_detection() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["status"] = "FAILED"
        message = _expect_error(lambda: validate_execution_result(result), "content hash mismatch")
        return {"rejected": message}


def control_path_traversal_rejected() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["artifacts"][0]["path"] = "../escape.json"
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "unsafe artifact path",
        )
        return {"rejected": message}


def control_missing_file_rejected() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        (root / result["artifacts"][0]["path"]).unlink()
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "does not exist",
        )
        return {"rejected": message}


def control_artifact_hash_mismatch_rejected() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["artifacts"][0]["sha256"] = "c" * 64
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "SHA-256 mismatch",
        )
        return {"rejected": message}


def control_failed_execution_never_advances() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    original = state["content_sha256"]
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["status"] = "FAILED"
        result = seal_execution_result(result)
        updated, receipt = advance_from_execution(
            spec,
            state,
            decision,
            result,
            artifact_root=root,
            receipt_path="receipts/failure.json",
        )
        assert receipt["status"] == "FAIL"
        assert "EXECUTION_STATUS:FAILED" in receipt["blockers"]
        assert updated["content_sha256"] == original
        assert (root / "receipts/failure.json").is_file()
        return {"state_unchanged": True, "blockers": receipt["blockers"]}


def control_missing_primary_evidence_blocks() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "ARCHITECTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        for artifact in result["artifacts"]:
            if artifact["kind"] == "implementation-change":
                artifact["kind"] = "tool-output"
        result = seal_execution_result(result)
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        assert receipt["status"] == "FAIL"
        assert "PRIMARY_EVIDENCE_MISSING:implementation-change" in receipt["blockers"]
        return {"blockers": receipt["blockers"]}


def control_tool_evidence_required_per_capability() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "ARCHITECTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        source_ref = next(
            item["ref"] for item in result["artifacts"] if item["capability"] == "source_control"
        )
        artifact = next(item for item in result["artifacts"] if item["ref"] == source_ref)
        (root / artifact["path"]).unlink()
        result["artifacts"] = [item for item in result["artifacts"] if item["ref"] != source_ref]
        result = seal_execution_result(result)
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        assert "TOOL_EVIDENCE_MISSING:source_control" in receipt["blockers"]
        return {"blockers": receipt["blockers"]}


def control_wrong_tool_surface_rejected() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "ARCHITECTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        artifact = next(item for item in result["artifacts"] if item["capability"] == "source_control")
        artifact["surface_id"] = "mcp-unselected-surface"
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "surface does not match selected",
        )
        return {"rejected": message}


def control_implementation_evidence_advances() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "ARCHITECTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        updated, receipt = advance_from_execution(
            spec, state, decision, result, artifact_root=root, receipt_path="receipts/implementation.json"
        )
        assert receipt["status"] == "PASS"
        assert updated["delivery_state"] == "IMPLEMENTED"
        assert updated["evidence"][-1]["kind"] == "implementation-change"
        return {"to": updated["delivery_state"]}


def control_visual_pack_is_recomputed_and_passes() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "IMPLEMENTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        assert receipt["status"] == "PASS"
        assert receipt["pack_reports"][0]["pack_id"] == "web-experience-visual-quality"
        assert receipt["pack_reports"][0]["status"] == "PASS"
        assert receipt["claims"]["pack_reports_computed_by_sef"] is True
        return {"pack": receipt["pack_reports"][0]["pack_id"], "status": "PASS"}


def control_visual_pack_failure_blocks() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "IMPLEMENTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(
            spec,
            state,
            decision,
            root,
            fixture_overrides={"web-experience-visual-quality": VISUAL_FAIL},
        )
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        assert receipt["status"] == "FAIL"
        assert any(item.startswith("PACK_NOT_PASS:web-experience-visual-quality:FAIL") for item in receipt["blockers"])
        return {"blockers": receipt["blockers"]}


def control_pack_dangling_evidence_rejected() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "IMPLEMENTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        observation_artifact = next(item for item in result["artifacts"] if item["kind"] == "pack-observation")
        observation_path = root / observation_artifact["path"]
        document = json.loads(observation_path.read_text(encoding="utf-8"))
        document["observations"][0]["screenshot_ref"] = "artifact://undeclared.png"
        data = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
        observation_path.write_bytes(data)
        observation_artifact["sha256"] = hashlib.sha256(data).hexdigest()
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "undeclared artifact",
        )
        return {"rejected": message}


def control_pack_evidence_must_be_tool_produced() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "IMPLEMENTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        evidence = next(
            item
            for item in result["artifacts"]
            if item["kind"] == "pack-evidence" and item["producer"] == "TOOL"
        )
        evidence["producer"] = "SYSTEM"
        evidence["capability"] = None
        evidence["surface_id"] = None
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "must be backed by TOOL-produced evidence",
        )
        return {"rejected": message}


def control_local_verification_advances() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "IMPLEMENTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        updated, receipt = advance_from_execution(
            spec, state, decision, result, artifact_root=root, receipt_path="receipts/local.json"
        )
        assert receipt["status"] == "PASS"
        assert updated["delivery_state"] == "VERIFIED_LOCAL"
        return {"to": updated["delivery_state"]}


def control_preview_verification_advances() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "VERIFIED_LOCAL")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        updated, receipt = advance_from_execution(
            spec, state, decision, result, artifact_root=root, receipt_path="receipts/preview.json"
        )
        assert receipt["status"] == "PASS"
        assert updated["delivery_state"] == "PREVIEW_VERIFIED"
        return {"to": updated["delivery_state"]}


def control_release_readiness_advances() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "PREVIEW_VERIFIED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        updated, receipt = advance_from_execution(
            spec, state, decision, result, artifact_root=root, receipt_path="receipts/release-ready.json"
        )
        assert receipt["status"] == "PASS"
        assert updated["delivery_state"] == "RELEASE_READY"
        return {"to": updated["delivery_state"]}


def control_material_data_pack_pass_required() -> dict[str, Any]:
    spec = _spec()
    spec["surfaces"]["persistent_data"] = True
    spec["surfaces"]["material_data_change"] = True
    state = _state_at(spec, "PREVIEW_VERIFIED")
    decision = _decision(spec, state)
    assert set(decision["active_packs"]) == {"data-change-safety", "web-experience-visual-quality"}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        assert receipt["status"] == "PASS"
        assert {item["pack_id"] for item in receipt["pack_reports"]} == set(decision["active_packs"])
        return {"packs": sorted(decision["active_packs"])}


def control_material_data_pack_failure_blocks() -> dict[str, Any]:
    spec = _spec()
    spec["surfaces"]["persistent_data"] = True
    spec["surfaces"]["material_data_change"] = True
    state = _state_at(spec, "PREVIEW_VERIFIED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(
            spec,
            state,
            decision,
            root,
            fixture_overrides={"data-change-safety": DATA_FAIL},
        )
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        assert receipt["status"] == "FAIL"
        assert any(item.startswith("PACK_NOT_PASS:data-change-safety:FAIL") for item in receipt["blockers"])
        return {"blockers": receipt["blockers"]}


def control_production_deployment_advances_when_authorized() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "RELEASE_READY")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        updated, receipt = advance_from_execution(
            spec, state, decision, result, artifact_root=root, receipt_path="receipts/deploy.json"
        )
        assert receipt["status"] == "PASS"
        assert updated["delivery_state"] == "DEPLOYED"
        return {"to": updated["delivery_state"]}


def control_blocked_production_decision_cannot_accept_result() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "RELEASE_READY")
    inventory = _inventory(captured_at=TIMES[20])
    decision = decide_next_action(spec, state, at=TIMES[20], tool_inventory=inventory)
    assert decision["status"] == "BLOCKED"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # A structurally valid empty result is enough: the blocked-decision guard
        # must fire before any claim can be promoted into evidence.
        result = seal_execution_result(
            {
                "schema": EXECUTION_RESULT_SCHEMA_ID,
                "mission_id": spec["mission_id"],
                "project_id": spec["project_id"],
                "decision_sha256": decision["content_sha256"],
                "project_state_sha256": state["content_sha256"],
                "action": decision["next_action"],
                "observed_at": TIMES[21],
                "status": "SUCCEEDED",
                "artifacts": [],
                "pack_observations": [],
            }
        )
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "READY_FOR_AGENT",
        )
        return {"rejected": message}


def control_production_pack_pass_advances_postdeploy() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "DEPLOYED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        updated, receipt = advance_from_execution(
            spec, state, decision, result, artifact_root=root, receipt_path="receipts/postdeploy.json"
        )
        assert receipt["status"] == "PASS"
        assert updated["delivery_state"] == "POST_DEPLOY_VERIFIED"
        assert receipt["pack_reports"][0]["pack_id"] == "production-evidence-operations"
        return {"to": updated["delivery_state"]}


def control_production_pack_failure_blocks() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "DEPLOYED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(
            spec,
            state,
            decision,
            root,
            fixture_overrides={"production-evidence-operations": PROD_FAIL},
        )
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        assert receipt["status"] == "FAIL"
        assert any(item.startswith("PACK_NOT_PASS:production-evidence-operations:FAIL") for item in receipt["blockers"])
        return {"blockers": receipt["blockers"]}


def control_pack_set_must_match_decision() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "IMPLEMENTED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        result["pack_observations"] = []
        result = seal_execution_result(result)
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "pack observation set must match active packs",
        )
        return {"rejected": message}


def control_receipt_tamper_detection() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        validate_evidence_receipt(receipt)
        receipt["target_delivery_state"] = "DEPLOYED"
        message = _expect_error(lambda: validate_evidence_receipt(receipt), "content hash mismatch")
        return {"rejected": message}


def control_receipt_is_immutable() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        advance_from_execution(
            spec, state, decision, result, artifact_root=root, receipt_path="receipts/immutable.json"
        )
        message = _expect_error(
            lambda: advance_from_execution(
                spec,
                state,
                decision,
                result,
                artifact_root=root,
                receipt_path="receipts/immutable.json",
            ),
            "refusing to overwrite",
        )
        return {"rejected": message}


def control_receipt_nonclaims_are_explicit() -> dict[str, Any]:
    spec = _spec()
    state = _state_at(spec, "FRAMED")
    decision = _decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = _successful_result(spec, state, decision, root)
        receipt = evaluate_execution_result(spec, state, decision, result, artifact_root=root)
        claims = receipt["claims"]
        assert claims["artifact_bytes_verified"] is True
        assert claims["pack_reports_computed_by_sef"] is True
        assert claims["state_advanced_by_evaluation"] is False
        assert claims["external_truth_cryptographically_proven"] is False
        assert claims["model_assertion_sufficient"] is False
        return claims


def control_all_seven_transitions_are_single_step() -> dict[str, Any]:
    spec = _spec()
    observed = {}
    for index, start_state in enumerate(DELIVERY_STATES[:-1]):
        state = _state_at(spec, start_state)
        decision = _decision(spec, state)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = _successful_result(spec, state, decision, root, observed_at=TIMES[22])
            updated, receipt = advance_from_execution(
                spec,
                state,
                decision,
                result,
                artifact_root=root,
                receipt_path=f"receipts/{index}.json",
            )
            expected = DELIVERY_STATES[index + 1]
            assert receipt["status"] == "PASS"
            assert updated["delivery_state"] == expected
            assert updated["evidence"][-1]["kind"] == EVIDENCE_KIND_FOR_STATE[expected]
            observed[start_state] = expected
    return observed


def control_legacy_runtime_integrity() -> dict[str, Any]:
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
    ("M5E-01-schema-contracts", control_schema_contracts),
    ("M5E-02-architecture-single-step", control_architecture_evidence_advances_one_state),
    ("M5E-03-decision-binding", control_result_exact_decision_binding),
    ("M5E-04-state-binding", control_result_exact_state_binding),
    ("M5E-05-action-binding", control_action_binding),
    ("M5E-06-result-tamper", control_result_tamper_detection),
    ("M5E-07-path-traversal", control_path_traversal_rejected),
    ("M5E-08-missing-file", control_missing_file_rejected),
    ("M5E-09-artifact-hash", control_artifact_hash_mismatch_rejected),
    ("M5E-10-failed-no-advance", control_failed_execution_never_advances),
    ("M5E-11-primary-evidence", control_missing_primary_evidence_blocks),
    ("M5E-12-tool-evidence-coverage", control_tool_evidence_required_per_capability),
    ("M5E-13-tool-surface-binding", control_wrong_tool_surface_rejected),
    ("M5E-14-implementation-advance", control_implementation_evidence_advances),
    ("M5E-15-visual-pack-recomputed", control_visual_pack_is_recomputed_and_passes),
    ("M5E-16-visual-pack-fail", control_visual_pack_failure_blocks),
    ("M5E-17-dangling-pack-evidence", control_pack_dangling_evidence_rejected),
    ("M5E-18-pack-evidence-tool-only", control_pack_evidence_must_be_tool_produced),
    ("M5E-19-local-verification-advance", control_local_verification_advances),
    ("M5E-20-preview-verification-advance", control_preview_verification_advances),
    ("M5E-21-release-readiness-advance", control_release_readiness_advances),
    ("M5E-22-data-pack-pass", control_material_data_pack_pass_required),
    ("M5E-23-data-pack-fail", control_material_data_pack_failure_blocks),
    ("M5E-24-production-deploy-advance", control_production_deployment_advances_when_authorized),
    ("M5E-25-blocked-production-reject", control_blocked_production_decision_cannot_accept_result),
    ("M5E-26-production-pack-pass", control_production_pack_pass_advances_postdeploy),
    ("M5E-27-production-pack-fail", control_production_pack_failure_blocks),
    ("M5E-28-pack-set-exact", control_pack_set_must_match_decision),
    ("M5E-29-receipt-tamper", control_receipt_tamper_detection),
    ("M5E-30-receipt-immutable", control_receipt_is_immutable),
    ("M5E-31-explicit-nonclaims", control_receipt_nonclaims_are_explicit),
    ("M5E-32-all-transitions", control_all_seven_transitions_are_single_step),
    ("M5E-33-runtime-integrity", control_legacy_runtime_integrity),
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
        "schema": "sef.eval.m5-evidence-ingestion.v1",
        "stage": "M5_EVIDENCE_INGESTION_STATE_ADVANCEMENT",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "status": "PASS" if passed == len(results) else "FAIL",
        "model_calls": 0,
        "network_calls": 0,
        "provider_calls": 0,
        "tool_execution_calls": 0,
        "external_truth_cryptographic_claim": False,
        "m5_end_to_end_claim": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
