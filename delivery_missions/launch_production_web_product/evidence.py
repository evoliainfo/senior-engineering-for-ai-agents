"""Evidence acceptance for the first Modern SEF Delivery Mission.

This module sits after ``decide_next_action``.  It does not execute Codex tools
or trust an agent-authored ``PASS`` flag.  Instead it binds an execution result
to the exact mission decision and Project State digest, verifies artifact bytes
and SHA-256 values under a caller-supplied evidence root, re-runs any active M3
Expert Pack evaluator from its observation document, and only then permits a
single M1 delivery-state transition.

The boundary is intentionally explicit: file/hash verification and evaluator
results are system-observed here, while the authenticity of an external tool's
returned bytes ultimately depends on the active Codex/plugin/MCP harness.  The
receipt therefore never claims cryptographic proof of external truth.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping

from expert_packs import load_pack
from project_state import (
    DELIVERY_STATES,
    EVIDENCE_KIND_FOR_STATE,
    add_evidence,
    advance_delivery_state,
    validate_state,
)

from .core import (
    PACK_ROOT,
    MissionError,
    _scan_secrets,
    _validate_state_alignment,
    validate_decision,
    validate_spec,
)

EXECUTION_RESULT_SCHEMA_ID = "sef.delivery-mission-execution-result.launch-production-web-product.v1"
EVIDENCE_RECEIPT_SCHEMA_ID = "sef.delivery-mission-evidence-receipt.launch-production-web-product.v1"

RESULT_STATUSES = {"SUCCEEDED", "FAILED", "INCOMPLETE"}
RECEIPT_STATUSES = {"PASS", "FAIL"}
ARTIFACT_PRODUCERS = {"AGENT", "TOOL", "SYSTEM"}

RESULT_KEYS = {
    "schema",
    "mission_id",
    "project_id",
    "decision_sha256",
    "project_state_sha256",
    "action",
    "observed_at",
    "status",
    "artifacts",
    "pack_observations",
    "content_sha256",
}
ARTIFACT_KEYS = {
    "id",
    "ref",
    "kind",
    "path",
    "sha256",
    "producer",
    "capability",
    "surface_id",
}
PACK_OBSERVATION_KEYS = {"pack_id", "artifact_ref"}

ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
CAPABILITY_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
KIND_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_REF_RE = re.compile(r"^artifact://[^\s]+$")

# Evidence-bearing fields used by the three initial Stable Expert Packs.  When
# these fields are non-null in an observation document, M5 requires a verified
# artifact:// reference instead of accepting an arbitrary prose/string claim.
EVIDENCE_REF_KEYS = {
    "screenshot_ref",
    "capture_context_ref",
    "accessibility_ref",
    "fixture_ref",
    "execution_ref",
    "verification_ref",
    "evidence_ref",
    "pre_ref",
    "post_ref",
    "backup_ref",
    "deployment_ref",
    "runtime_identity_ref",
    "window_ref",
}

PRIMARY_CAPABILITY_BY_ACTION = {
    "PLAN_ARCHITECTURE": None,
    "IMPLEMENT_PRODUCT": "source_control",
    "VERIFY_LOCAL_PRODUCT": "browser",
    "DEPLOY_AND_VERIFY_PREVIEW": "hosting",
    "PROVE_RELEASE_READINESS": "ci",
    "DEPLOY_PRODUCTION": "hosting",
    "VERIFY_PRODUCTION": "browser",
}

MAX_ARTIFACTS = 128
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024


class MissionEvidenceError(MissionError):
    """Raised when execution evidence cannot safely support a mission gate."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_time(value: Any, label: str):
    # Reuse the mission validator indirectly without importing another private
    # helper: ISO validation is already required for mission/state timestamps;
    # this compact local parser keeps the evidence module independently clear.
    from datetime import datetime

    if not isinstance(value, str) or not value.strip():
        raise MissionEvidenceError(f"{label} must be a non-empty ISO-8601 timestamp")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MissionEvidenceError(f"{label} must be valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise MissionEvidenceError(f"{label} must include a timezone")
    return parsed


def _exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise MissionEvidenceError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise MissionEvidenceError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise MissionEvidenceError(f"{label} must be a compact stable identifier")
    return value


def _sha256_file(path: Path) -> tuple[str, int]:
    size = path.stat().st_size
    if size <= 0:
        raise MissionEvidenceError(f"evidence artifact is empty: {path.name}")
    if size > MAX_ARTIFACT_BYTES:
        raise MissionEvidenceError(
            f"evidence artifact exceeds {MAX_ARTIFACT_BYTES} byte verification limit: {path.name}"
        )
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest(), size


def _safe_existing_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise MissionEvidenceError("artifact.path must be a non-empty relative path <= 512 characters")
    if "\\" in relative:
        raise MissionEvidenceError("artifact.path must use portable forward slashes")
    rel = Path(relative)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise MissionEvidenceError(f"unsafe artifact path: {relative}")
    resolved_root = Path(root).resolve()
    candidate = (resolved_root / rel).resolve()
    try:
        common = os.path.commonpath([str(resolved_root), str(candidate)])
    except ValueError as exc:
        raise MissionEvidenceError(f"unsafe artifact path: {relative}") from exc
    if common != str(resolved_root):
        raise MissionEvidenceError(f"artifact escapes evidence root: {relative}")
    if not candidate.is_file():
        raise MissionEvidenceError(f"artifact file does not exist: {relative}")
    return candidate


def _safe_output_path(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or len(relative) > 512:
        raise MissionEvidenceError("receipt path must be a non-empty relative path <= 512 characters")
    if "\\" in relative:
        raise MissionEvidenceError("receipt path must use portable forward slashes")
    rel = Path(relative)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise MissionEvidenceError(f"unsafe receipt path: {relative}")
    resolved_root = Path(root).resolve()
    candidate = (resolved_root / rel).resolve()
    common = os.path.commonpath([str(resolved_root), str(candidate)])
    if common != str(resolved_root):
        raise MissionEvidenceError(f"receipt path escapes evidence root: {relative}")
    return candidate


def validate_execution_result(result: Any) -> dict[str, Any]:
    """Validate and integrity-check an agent/harness execution-result envelope."""
    if not isinstance(result, dict):
        raise MissionEvidenceError("execution result root must be an object")
    _exact(result, RESULT_KEYS, "execution_result")
    if result["schema"] != EXECUTION_RESULT_SCHEMA_ID:
        raise MissionEvidenceError(
            f"execution_result.schema must equal {EXECUTION_RESULT_SCHEMA_ID}"
        )
    _item_id(result["mission_id"], "mission_id")
    if not isinstance(result["project_id"], str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", result["project_id"]
    ):
        raise MissionEvidenceError("project_id must be lowercase kebab-case")
    for field in ("decision_sha256", "project_state_sha256", "content_sha256"):
        if not isinstance(result[field], str) or not SHA256_RE.fullmatch(result[field]):
            raise MissionEvidenceError(f"{field} must be a lowercase SHA-256")
    if not isinstance(result["action"], str) or not result["action"]:
        raise MissionEvidenceError("action must be a non-empty string")
    _parse_time(result["observed_at"], "observed_at")
    if result["status"] not in RESULT_STATUSES:
        raise MissionEvidenceError("execution result status is invalid")
    _scan_secrets(result)

    artifacts = result["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > MAX_ARTIFACTS:
        raise MissionEvidenceError(f"artifacts must be a list with at most {MAX_ARTIFACTS} entries")
    ids: set[str] = set()
    refs: set[str] = set()
    paths: set[str] = set()
    for index, artifact in enumerate(artifacts):
        label = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            raise MissionEvidenceError(f"{label} must be an object")
        _exact(artifact, ARTIFACT_KEYS, label)
        artifact_id = _item_id(artifact["id"], f"{label}.id")
        if artifact_id in ids:
            raise MissionEvidenceError("artifacts contain duplicate ids")
        ids.add(artifact_id)
        if not isinstance(artifact["ref"], str) or not ARTIFACT_REF_RE.fullmatch(artifact["ref"]):
            raise MissionEvidenceError(f"{label}.ref must be an artifact:// reference")
        if artifact["ref"] in refs:
            raise MissionEvidenceError("artifacts contain duplicate refs")
        refs.add(artifact["ref"])
        if not isinstance(artifact["kind"], str) or not KIND_RE.fullmatch(artifact["kind"]):
            raise MissionEvidenceError(f"{label}.kind must be lowercase kebab-case")
        if not isinstance(artifact["path"], str) or not artifact["path"]:
            raise MissionEvidenceError(f"{label}.path must be a non-empty string")
        if artifact["path"] in paths:
            raise MissionEvidenceError("artifacts contain duplicate paths")
        paths.add(artifact["path"])
        if not isinstance(artifact["sha256"], str) or not SHA256_RE.fullmatch(artifact["sha256"]):
            raise MissionEvidenceError(f"{label}.sha256 must be a lowercase SHA-256")
        if artifact["producer"] not in ARTIFACT_PRODUCERS:
            raise MissionEvidenceError(f"{label}.producer is invalid")
        if artifact["producer"] == "TOOL":
            if not isinstance(artifact["capability"], str) or not CAPABILITY_RE.fullmatch(
                artifact["capability"]
            ):
                raise MissionEvidenceError(f"{label}.capability is required for TOOL artifacts")
            _item_id(artifact["surface_id"], f"{label}.surface_id")
        elif artifact["capability"] is not None or artifact["surface_id"] is not None:
            raise MissionEvidenceError(
                f"{label}: non-TOOL artifact must use null capability and surface_id"
            )

    pack_observations = result["pack_observations"]
    if not isinstance(pack_observations, list):
        raise MissionEvidenceError("pack_observations must be a list")
    pack_ids: set[str] = set()
    for index, item in enumerate(pack_observations):
        label = f"pack_observations[{index}]"
        if not isinstance(item, dict):
            raise MissionEvidenceError(f"{label} must be an object")
        _exact(item, PACK_OBSERVATION_KEYS, label)
        pack_id = _item_id(item["pack_id"], f"{label}.pack_id")
        if pack_id in pack_ids:
            raise MissionEvidenceError("pack_observations contain duplicate pack ids")
        pack_ids.add(pack_id)
        if not isinstance(item["artifact_ref"], str) or not ARTIFACT_REF_RE.fullmatch(
            item["artifact_ref"]
        ):
            raise MissionEvidenceError(f"{label}.artifact_ref must be an artifact:// reference")

    unsigned = copy.deepcopy(result)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != result["content_sha256"]:
        raise MissionEvidenceError("execution result content hash mismatch")
    return result


def seal_execution_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Seal a structurally complete result document for harness/test producers."""
    value = copy.deepcopy(dict(result))
    value["content_sha256"] = "0" * 64
    unsigned = copy.deepcopy(value)
    unsigned.pop("content_sha256", None)
    value["content_sha256"] = _digest(unsigned)
    validate_execution_result(value)
    return value


def _verify_artifacts(result: Mapping[str, Any], artifact_root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    by_ref: dict[str, dict[str, Any]] = {}
    verified: list[dict[str, Any]] = []
    for artifact in result["artifacts"]:
        path = _safe_existing_path(Path(artifact_root), artifact["path"])
        observed_sha, size = _sha256_file(path)
        if observed_sha != artifact["sha256"]:
            raise MissionEvidenceError(
                f"artifact SHA-256 mismatch for {artifact['ref']}: expected {artifact['sha256']} observed {observed_sha}"
            )
        item = copy.deepcopy(artifact)
        item["verified_size"] = size
        by_ref[artifact["ref"]] = item
        verified.append(
            {
                "id": artifact["id"],
                "ref": artifact["ref"],
                "kind": artifact["kind"],
                "producer": artifact["producer"],
                "capability": artifact["capability"],
                "surface_id": artifact["surface_id"],
                "sha256": observed_sha,
                "size": size,
                "status": "VERIFIED",
            }
        )
    return by_ref, verified


def _selected_tool_surfaces(decision: Mapping[str, Any]) -> dict[str, str]:
    bridge = decision.get("tool_bridge")
    selected: dict[str, str] = {}
    if bridge is None:
        return selected
    for item in bridge["resolution"]["results"]:
        if item["status"] == "READY" and item["selected_surface_id"] is not None:
            selected[item["capability"]] = item["selected_surface_id"]
    return selected


def _validate_tool_artifact_bindings(
    decision: Mapping[str, Any],
    artifacts_by_ref: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    selected = _selected_tool_surfaces(decision)
    blockers: list[str] = []
    coverage: list[dict[str, Any]] = []

    # Every claimed TOOL artifact must be bound to a capability/surface that the
    # exact pre-execution decision selected.  Evidence from an unselected or
    # unrelated surface cannot be smuggled into the transition.
    for artifact in artifacts_by_ref.values():
        if artifact["producer"] != "TOOL":
            continue
        capability = artifact["capability"]
        expected_surface = selected.get(capability)
        if expected_surface is None:
            raise MissionEvidenceError(
                f"TOOL artifact {artifact['ref']} uses capability not selected by decision: {capability}"
            )
        if artifact["surface_id"] != expected_surface:
            raise MissionEvidenceError(
                f"TOOL artifact {artifact['ref']} surface does not match selected {capability} surface"
            )

    for requirement in decision.get("tool_requirements", []):
        capability = requirement["capability"]
        surface_id = selected.get(capability)
        matches = [
            artifact
            for artifact in artifacts_by_ref.values()
            if artifact["producer"] == "TOOL"
            and artifact["capability"] == capability
            and artifact["surface_id"] == surface_id
        ]
        if surface_id is None or not matches:
            blockers.append(f"TOOL_EVIDENCE_MISSING:{capability}")
            coverage.append(
                {
                    "capability": capability,
                    "surface_id": surface_id,
                    "status": "MISSING",
                    "artifact_refs": [],
                }
            )
        else:
            coverage.append(
                {
                    "capability": capability,
                    "surface_id": surface_id,
                    "status": "VERIFIED",
                    "artifact_refs": sorted(item["ref"] for item in matches),
                }
            )
    return coverage, blockers


def _walk_evidence_refs(value: Any, artifacts_by_ref: Mapping[str, Mapping[str, Any]], path: str = "observation") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in EVIDENCE_REF_KEYS and child is not None:
                if not isinstance(child, str) or not ARTIFACT_REF_RE.fullmatch(child):
                    raise MissionEvidenceError(
                        f"{child_path} must reference verified artifact:// evidence"
                    )
                artifact = artifacts_by_ref.get(child)
                if artifact is None:
                    raise MissionEvidenceError(f"{child_path} references undeclared artifact {child}")
                if artifact["producer"] != "TOOL":
                    raise MissionEvidenceError(
                        f"{child_path} must be backed by TOOL-produced evidence, not {artifact['producer']}"
                    )
            _walk_evidence_refs(child, artifacts_by_ref, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_evidence_refs(child, artifacts_by_ref, f"{path}[{index}]")
    elif isinstance(value, str) and value.startswith("artifact://"):
        if value not in artifacts_by_ref:
            raise MissionEvidenceError(f"{path} references undeclared artifact {value}")


def _run_pack_evaluator(
    pack_id: str,
    observation: Mapping[str, Any],
) -> dict[str, Any]:
    pack_dir = PACK_ROOT / pack_id
    pack = load_pack(pack_dir)
    evaluators = [entry for entry in pack["entry_points"] if entry["kind"] == "EVALUATOR"]
    if len(evaluators) != 1:
        raise MissionEvidenceError(f"pack {pack_id} must expose exactly one evaluator for M5")
    evaluator_path = (pack_dir / evaluators[0]["path"]).resolve()
    expected_root = pack_dir.resolve()
    if os.path.commonpath([str(expected_root), str(evaluator_path)]) != str(expected_root):
        raise MissionEvidenceError(f"pack {pack_id} evaluator escapes pack directory")
    module_name = "_sef_m5_pack_" + re.sub(r"[^A-Za-z0-9_]", "_", pack_id)
    spec = importlib.util.spec_from_file_location(module_name, evaluator_path)
    if spec is None or spec.loader is None:
        raise MissionEvidenceError(f"cannot load evaluator for pack {pack_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evaluate = getattr(module, "evaluate", None)
    if not callable(evaluate):
        raise MissionEvidenceError(f"pack {pack_id} evaluator has no callable evaluate(document)")
    try:
        report = evaluate(copy.deepcopy(dict(observation)))
    except Exception as exc:  # pack-specific validation exceptions are evidence failures
        raise MissionEvidenceError(f"pack {pack_id} evaluator rejected observation: {exc}") from exc
    if not isinstance(report, dict) or not isinstance(report.get("status"), str):
        raise MissionEvidenceError(f"pack {pack_id} evaluator returned invalid report")
    return report


def _evaluate_active_packs(
    decision: Mapping[str, Any],
    result: Mapping[str, Any],
    artifacts_by_ref: Mapping[str, Mapping[str, Any]],
    artifact_root: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    active = list(decision.get("active_packs", []))
    supplied = {item["pack_id"]: item["artifact_ref"] for item in result["pack_observations"]}
    if set(supplied) != set(active):
        missing = sorted(set(active) - set(supplied))
        extra = sorted(set(supplied) - set(active))
        raise MissionEvidenceError(
            f"pack observation set must match active packs; missing={missing} extra={extra}"
        )

    reports: list[dict[str, Any]] = []
    blockers: list[str] = []
    for pack_id in active:
        observation_ref = supplied[pack_id]
        artifact = artifacts_by_ref.get(observation_ref)
        if artifact is None:
            raise MissionEvidenceError(
                f"pack {pack_id} observation references undeclared artifact {observation_ref}"
            )
        if artifact["kind"] != "pack-observation":
            raise MissionEvidenceError(
                f"pack {pack_id} observation artifact kind must be pack-observation"
            )
        path = _safe_existing_path(Path(artifact_root), artifact["path"])
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MissionEvidenceError(f"pack {pack_id} observation is not valid UTF-8 JSON") from exc
        if not isinstance(document, dict):
            raise MissionEvidenceError(f"pack {pack_id} observation root must be an object")
        _walk_evidence_refs(document, artifacts_by_ref, path=f"pack[{pack_id}]")
        report = _run_pack_evaluator(pack_id, document)
        status = report["status"]
        reports.append(
            {
                "pack_id": pack_id,
                "observation_ref": observation_ref,
                "status": status,
                "report_schema": report.get("schema"),
                "report_sha256": _digest(report),
                "report": report,
            }
        )
        if status != "PASS":
            blockers.append(f"PACK_NOT_PASS:{pack_id}:{status}")
    return reports, blockers


def _target_state(state: Mapping[str, Any]) -> str:
    current = state["delivery_state"]
    index = DELIVERY_STATES.index(current)
    if index >= len(DELIVERY_STATES) - 1:
        raise MissionEvidenceError("POST_DEPLOY_VERIFIED has no execution transition")
    return DELIVERY_STATES[index + 1]


def evaluate_execution_result(
    spec: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, Any],
    result: dict[str, Any],
    *,
    artifact_root: Path,
) -> dict[str, Any]:
    """Evaluate a completed action without mutating Project State.

    A PASS receipt authorizes exactly the next M1 transition.  It does not itself
    perform that transition; ``advance_from_execution`` is the only mutating
    helper in this module.
    """
    validate_spec(spec)
    validate_state(state)
    _validate_state_alignment(spec, state)
    validate_decision(decision)
    validate_execution_result(result)

    if decision["status"] != "READY_FOR_AGENT":
        raise MissionEvidenceError("only a READY_FOR_AGENT decision can accept execution evidence")
    if decision["mission_id"] != spec["mission_id"] or decision["project_id"] != spec["project_id"]:
        raise MissionEvidenceError("decision does not belong to mission spec")
    if decision["project_state_sha256"] != state["content_sha256"]:
        raise MissionEvidenceError("decision is stale for current Project State")
    if result["mission_id"] != spec["mission_id"] or result["project_id"] != spec["project_id"]:
        raise MissionEvidenceError("execution result does not belong to mission spec")
    if result["decision_sha256"] != decision["content_sha256"]:
        raise MissionEvidenceError("execution result is not bound to exact mission decision")
    if result["project_state_sha256"] != state["content_sha256"]:
        raise MissionEvidenceError("execution result is not bound to current Project State")
    if result["action"] != decision["next_action"]:
        raise MissionEvidenceError("execution result action does not match decision")
    if _parse_time(result["observed_at"], "observed_at") < _parse_time(state["updated_at"], "state.updated_at"):
        raise MissionEvidenceError("execution result cannot predate current Project State")

    target_state = _target_state(state)
    required_kind = EVIDENCE_KIND_FOR_STATE[target_state]
    artifacts_by_ref, artifact_verification = _verify_artifacts(result, Path(artifact_root))
    tool_coverage, tool_blockers = _validate_tool_artifact_bindings(decision, artifacts_by_ref)
    pack_reports, pack_blockers = _evaluate_active_packs(
        decision, result, artifacts_by_ref, Path(artifact_root)
    )

    blockers: list[str] = []
    if result["status"] != "SUCCEEDED":
        blockers.append(f"EXECUTION_STATUS:{result['status']}")
    blockers.extend(tool_blockers)
    blockers.extend(pack_blockers)

    primary = [artifact for artifact in artifacts_by_ref.values() if artifact["kind"] == required_kind]
    if not primary:
        blockers.append(f"PRIMARY_EVIDENCE_MISSING:{required_kind}")
    else:
        expected_capability = PRIMARY_CAPABILITY_BY_ACTION.get(result["action"])
        if expected_capability is None:
            if not any(item["producer"] in {"AGENT", "SYSTEM"} for item in primary):
                blockers.append(f"PRIMARY_EVIDENCE_PROVENANCE_INVALID:{required_kind}")
        elif not any(
            item["producer"] == "TOOL" and item["capability"] == expected_capability
            for item in primary
        ):
            blockers.append(
                f"PRIMARY_EVIDENCE_PROVENANCE_INVALID:{required_kind}:{expected_capability}"
            )

    blockers = sorted(set(blockers))
    status = "PASS" if not blockers else "FAIL"
    receipt = {
        "schema": EVIDENCE_RECEIPT_SCHEMA_ID,
        "mission_id": spec["mission_id"],
        "project_id": spec["project_id"],
        "decision_sha256": decision["content_sha256"],
        "input_state_sha256": state["content_sha256"],
        "input_delivery_state": state["delivery_state"],
        "action": decision["next_action"],
        "target_delivery_state": target_state,
        "required_evidence_kind": required_kind,
        "observed_at": result["observed_at"],
        "execution_result_sha256": result["content_sha256"],
        "status": status,
        "artifact_verification": artifact_verification,
        "tool_evidence": tool_coverage,
        "pack_reports": pack_reports,
        "blockers": blockers,
        "claims": {
            "artifact_bytes_verified": True,
            "pack_reports_computed_by_sef": True,
            "state_advanced_by_evaluation": False,
            "external_truth_cryptographically_proven": False,
            "model_assertion_sufficient": False,
        },
        "content_sha256": "0" * 64,
    }
    receipt["content_sha256"] = _digest(
        {key: value for key, value in receipt.items() if key != "content_sha256"}
    )
    validate_evidence_receipt(receipt)
    return receipt


def validate_evidence_receipt(receipt: Any) -> dict[str, Any]:
    if not isinstance(receipt, dict) or receipt.get("schema") != EVIDENCE_RECEIPT_SCHEMA_ID:
        raise MissionEvidenceError("invalid mission evidence receipt schema")
    supplied = receipt.get("content_sha256")
    if not isinstance(supplied, str) or not SHA256_RE.fullmatch(supplied):
        raise MissionEvidenceError("evidence receipt missing valid content_sha256")
    unsigned = copy.deepcopy(receipt)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != supplied:
        raise MissionEvidenceError("evidence receipt content hash mismatch")
    if receipt.get("status") not in RECEIPT_STATUSES:
        raise MissionEvidenceError("evidence receipt status is invalid")
    if receipt.get("input_delivery_state") not in DELIVERY_STATES:
        raise MissionEvidenceError("evidence receipt input state is invalid")
    if receipt.get("target_delivery_state") not in DELIVERY_STATES:
        raise MissionEvidenceError("evidence receipt target state is invalid")
    current_index = DELIVERY_STATES.index(receipt["input_delivery_state"])
    if current_index + 1 >= len(DELIVERY_STATES) or DELIVERY_STATES[current_index + 1] != receipt["target_delivery_state"]:
        raise MissionEvidenceError("evidence receipt must authorize exactly one delivery-state step")
    if receipt.get("required_evidence_kind") != EVIDENCE_KIND_FOR_STATE[receipt["target_delivery_state"]]:
        raise MissionEvidenceError("evidence receipt required kind does not match target state")
    expected_claims = {
        "artifact_bytes_verified": True,
        "pack_reports_computed_by_sef": True,
        "state_advanced_by_evaluation": False,
        "external_truth_cryptographically_proven": False,
        "model_assertion_sufficient": False,
    }
    if receipt.get("claims") != expected_claims:
        raise MissionEvidenceError("evidence receipt contains unsupported claims")
    if receipt["status"] == "PASS" and receipt.get("blockers"):
        raise MissionEvidenceError("PASS evidence receipt must not contain blockers")
    if receipt["status"] == "FAIL" and not receipt.get("blockers"):
        raise MissionEvidenceError("FAIL evidence receipt must contain blockers")
    return receipt


def _write_receipt(path: Path, receipt: Mapping[str, Any]) -> str:
    validate_evidence_receipt(dict(receipt))
    if path.exists():
        raise MissionEvidenceError(f"refusing to overwrite existing evidence receipt: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    digest, _ = _sha256_file(path)
    return digest


def advance_from_execution(
    spec: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, Any],
    result: dict[str, Any],
    *,
    artifact_root: Path,
    receipt_path: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Persist a receipt and advance M1 exactly once when the receipt is PASS.

    Failed/incomplete execution is still persisted as a receipt for diagnosis,
    but Project State remains byte-for-byte unchanged.
    """
    receipt = evaluate_execution_result(
        spec,
        state,
        decision,
        result,
        artifact_root=Path(artifact_root),
    )
    output = _safe_output_path(Path(artifact_root), receipt_path)
    receipt_file_sha = _write_receipt(output, receipt)

    if receipt["status"] != "PASS":
        return state, receipt

    target_state = receipt["target_delivery_state"]
    evidence_id = f"EVID-M5-{len(state['evidence']) + 1:03d}"
    locator = "artifact://" + Path(receipt_path).as_posix()
    updated = add_evidence(
        state,
        evidence_id=evidence_id,
        kind=receipt["required_evidence_kind"],
        locator=locator,
        observed_at=result["observed_at"],
        sha256=receipt_file_sha,
    )
    updated = advance_delivery_state(
        updated,
        to_state=target_state,
        evidence_refs=[evidence_id],
        at=result["observed_at"],
        reason=(
            f"M5 accepted verified execution evidence for {decision['next_action']} "
            f"under receipt {locator}."
        ),
    )
    validate_state(updated)
    return updated, receipt
