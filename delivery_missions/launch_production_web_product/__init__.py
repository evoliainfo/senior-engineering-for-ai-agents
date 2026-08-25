"""First Modern SEF Delivery Mission: launch a production web product."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .core import (
    DECISION_SCHEMA_ID,
    MISSION_SCHEMA_ID,
    MissionError,
    decide_next_action as _decide_next_action,
    initialize_project_state,
    validate_decision,
    validate_spec,
)
from .evidence import (
    EVIDENCE_RECEIPT_SCHEMA_ID,
    EXECUTION_RESULT_SCHEMA_ID,
    MissionEvidenceError,
    advance_from_execution as _advance_from_execution,
    evaluate_execution_result as _evaluate_execution_result,
    seal_execution_result,
    validate_evidence_receipt,
    validate_execution_result,
)
from .execution_plan import (
    EXECUTION_PLAN_SCHEMA_ID,
    ExecutionPlanError,
    build_execution_plan,
    validate_execution_plan,
)


_VISUAL_TARGET_BY_ACTION = {
    "VERIFY_LOCAL_PRODUCT": "local",
    "DEPLOY_AND_VERIFY_PREVIEW": "preview",
    "PROVE_RELEASE_READINESS": "preview",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _parse_time(value: str, label: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if isinstance(value, str) and value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError) as exc:
        raise MissionError(f"{label} must be valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise MissionError(f"{label} must include a timezone")
    return parsed


def _reseal(decision: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(decision)
    value.pop("content_sha256", None)
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    value["content_sha256"] = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    validate_decision(value)
    return value


def _bind_jit_capsule_digests(
    decision: dict[str, Any],
    capsules: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind public M5 decisions to the exact JIT capsule bytes they approved.

    The M5 core historically exposed capsule ids in ``jit_readiness``.  An id is
    not version identity: a capsule can be regenerated under the same stable id.
    The public mission surface therefore also records the already-validated
    capsule ``content_sha256`` and reseals the decision.  Execution plans can now
    require the exact capsule version without duplicating M2 invalidation logic.
    """
    value = copy.deepcopy(decision)
    by_id: dict[str, str] = {}
    for capsule in capsules:
        capsule_id = capsule.get("capsule_id")
        digest = capsule.get("content_sha256")
        if not isinstance(capsule_id, str) or not capsule_id:
            continue
        if capsule_id in by_id:
            raise MissionError(f"duplicate JIT capsule id supplied to mission: {capsule_id}")
        if isinstance(digest, str) and _SHA256_RE.fullmatch(digest):
            by_id[capsule_id] = digest

    for item in value.get("jit_readiness", []):
        capsule_id = item.get("capsule_id")
        digest = by_id.get(capsule_id) if isinstance(capsule_id, str) else None
        item["capsule_sha256"] = digest
        if value.get("status") == "READY_FOR_AGENT" and capsule_id is not None and digest is None:
            raise MissionError(f"READY decision cannot bind JIT capsule without exact digest: {capsule_id}")
    return _reseal(value)


def _pack_observation_document(
    result: Mapping[str, Any],
    *,
    pack_id: str,
    artifact_root: Path,
) -> dict[str, Any]:
    refs = [
        item["artifact_ref"]
        for item in result.get("pack_observations", [])
        if item.get("pack_id") == pack_id
    ]
    if len(refs) != 1:
        raise MissionEvidenceError(f"pack {pack_id} must have exactly one observation reference")
    artifacts = [item for item in result.get("artifacts", []) if item.get("ref") == refs[0]]
    if len(artifacts) != 1:
        raise MissionEvidenceError(f"pack {pack_id} observation artifact is missing or ambiguous")
    # The underlying evidence evaluator has already verified path containment and
    # the artifact hash before this scope check runs. Resolve the same verified
    # artifact only to inspect mission-specific context that generic pack
    # evaluators intentionally do not know about.
    root = Path(artifact_root).resolve()
    path = (root / artifacts[0]["path"]).resolve()
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MissionEvidenceError(f"pack {pack_id} observation cannot be read for scope validation") from exc
    if not isinstance(document, dict):
        raise MissionEvidenceError(f"pack {pack_id} observation root must be an object")
    return document


def _validate_pack_action_scope(
    decision: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    artifact_root: Path,
) -> None:
    active = set(decision.get("active_packs", []))
    action = decision.get("next_action")

    if "web-experience-visual-quality" in active:
        expected = _VISUAL_TARGET_BY_ACTION.get(action)
        if expected is None:
            raise MissionEvidenceError(
                f"web visual-quality pack is not valid for mission action {action}"
            )
        document = _pack_observation_document(
            result,
            pack_id="web-experience-visual-quality",
            artifact_root=artifact_root,
        )
        target = document.get("target")
        observed = target.get("kind") if isinstance(target, dict) else None
        if observed != expected:
            raise MissionEvidenceError(
                "pack web-experience-visual-quality target.kind must be "
                f"{expected} for {action}; observed {observed!r}"
            )

    if "production-evidence-operations" in active:
        if action != "VERIFY_PRODUCTION":
            raise MissionEvidenceError(
                f"production-evidence-operations pack is not valid for mission action {action}"
            )
        document = _pack_observation_document(
            result,
            pack_id="production-evidence-operations",
            artifact_root=artifact_root,
        )
        release = document.get("release")
        environment = release.get("environment_kind") if isinstance(release, dict) else None
        if environment != "PRODUCTION":
            raise MissionEvidenceError(
                "pack production-evidence-operations release.environment_kind must be "
                f"PRODUCTION for VERIFY_PRODUCTION; observed {environment!r}"
            )


def decide_next_action(
    spec: dict[str, Any],
    state: dict[str, Any],
    *,
    at: str,
    tool_inventory: dict[str, Any] | None = None,
    capsules: Iterable[Mapping[str, Any]] = (),
    max_tool_age_seconds: int = 300,
) -> dict[str, Any]:
    """Public mission decision with current-tool and exact-JIT-version guards."""
    if not isinstance(max_tool_age_seconds, int) or isinstance(max_tool_age_seconds, bool) or not 1 <= max_tool_age_seconds <= 86400:
        raise MissionError("max_tool_age_seconds must be integer between 1 and 86400")

    capsule_list = [copy.deepcopy(dict(item)) for item in capsules]

    if tool_inventory is None:
        decision = _decide_next_action(
            spec,
            state,
            at=at,
            tool_inventory=None,
            capsules=capsule_list,
            max_tool_age_seconds=max_tool_age_seconds,
        )
        return _bind_jit_capsule_digests(decision, capsule_list)

    current = _parse_time(at, "at")
    captured = _parse_time(tool_inventory.get("captured_at"), "tool_inventory.captured_at")
    if captured > current:
        raise MissionError("tool inventory cannot be captured after mission decision time")
    age_seconds = (current - captured).total_seconds()
    if age_seconds <= max_tool_age_seconds:
        decision = _decide_next_action(
            spec,
            state,
            at=at,
            tool_inventory=tool_inventory,
            capsules=capsule_list,
            max_tool_age_seconds=max_tool_age_seconds,
        )
        return _bind_jit_capsule_digests(decision, capsule_list)

    # Evaluate without the stale snapshot so the core can reveal whether the
    # current action actually needs tool/JIT observations. Do not block a purely
    # planning action merely because the caller happened to supply an old cache.
    decision = _decide_next_action(
        spec,
        state,
        at=at,
        tool_inventory=None,
        capsules=capsule_list,
        max_tool_age_seconds=max_tool_age_seconds,
    )
    needs_inventory = bool(decision["tool_requirements"]) or any(
        "TOOL_STATE_NOT_REOBSERVED" in item.get("reasons", []) for item in decision["jit_readiness"]
    )
    if needs_inventory:
        blockers = [item for item in decision["blockers"] if item != "TOOL_INVENTORY_REQUIRED"]
        blockers.append("TOOL_INVENTORY_STALE")
        decision["blockers"] = sorted(set(blockers))
        decision["status"] = "BLOCKED"
        decision["tool_bridge"] = None
        decision = _reseal(decision)
    return _bind_jit_capsule_digests(decision, capsule_list)


def evaluate_execution_result(
    spec: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, Any],
    result: dict[str, Any],
    *,
    artifact_root: Path,
) -> dict[str, Any]:
    """Evaluate evidence and enforce mission-specific pack scope."""
    receipt = _evaluate_execution_result(
        spec,
        state,
        decision,
        result,
        artifact_root=Path(artifact_root),
    )
    _validate_pack_action_scope(
        decision,
        result,
        artifact_root=Path(artifact_root),
    )
    return receipt


def advance_from_execution(
    spec: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, Any],
    result: dict[str, Any],
    *,
    artifact_root: Path,
    receipt_path: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Enforce pack scope before allowing the internal evidence layer to advance M1."""
    evaluate_execution_result(
        spec,
        state,
        decision,
        result,
        artifact_root=Path(artifact_root),
    )
    return _advance_from_execution(
        spec,
        state,
        decision,
        result,
        artifact_root=Path(artifact_root),
        receipt_path=receipt_path,
    )


__all__ = [
    "DECISION_SCHEMA_ID",
    "EVIDENCE_RECEIPT_SCHEMA_ID",
    "EXECUTION_PLAN_SCHEMA_ID",
    "EXECUTION_RESULT_SCHEMA_ID",
    "MISSION_SCHEMA_ID",
    "ExecutionPlanError",
    "MissionError",
    "MissionEvidenceError",
    "advance_from_execution",
    "build_execution_plan",
    "decide_next_action",
    "evaluate_execution_result",
    "initialize_project_state",
    "seal_execution_result",
    "validate_decision",
    "validate_evidence_receipt",
    "validate_execution_plan",
    "validate_execution_result",
    "validate_spec",
]
