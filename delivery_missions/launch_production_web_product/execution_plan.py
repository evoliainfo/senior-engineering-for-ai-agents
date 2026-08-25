"""Deterministic Codex execution hand-off for the first Modern SEF mission.

A mission decision already answers *what should happen next* and M4 already
selects the tool surfaces that are allowed to satisfy the action.  This module
turns that READY decision into a compact machine-readable execution/evidence
plan for the active Codex harness.  It does not execute tools and cannot grant
new authorization.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from expert_packs import load_pack
from project_state import DELIVERY_STATES, EVIDENCE_KIND_FOR_STATE, validate_state

from .core import PACK_ROOT, MissionError, validate_decision, validate_spec
from .evidence import EXECUTION_RESULT_SCHEMA_ID, PRIMARY_CAPABILITY_BY_ACTION

EXECUTION_PLAN_SCHEMA_ID = "sef.codex-execution-plan.launch-production-web-product.v1"

PLAN_STATUSES = {"READY"}
SLOT_ROLES = {"PRIMARY", "TOOL_SUPPORT", "PACK_OBSERVATION"}
PRODUCERS = {"AGENT", "SYSTEM", "TOOL"}
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
PROJECT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CAPABILITY_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_NAMESPACE_RE = re.compile(r"^artifact://[A-Za-z0-9._/-]+/$")

EXPECTED_VISUAL_SCOPE = {
    "VERIFY_LOCAL_PRODUCT": {"target.kind": "local"},
    "DEPLOY_AND_VERIFY_PREVIEW": {"target.kind": "preview"},
    "PROVE_RELEASE_READINESS": {"target.kind": "preview"},
}

PLAN_KEYS = {
    "schema",
    "mission_id",
    "project_id",
    "decision_sha256",
    "project_state_sha256",
    "delivery_state",
    "action",
    "generated_at",
    "status",
    "evidence_namespace",
    "selected_tools",
    "artifact_slots",
    "pack_tasks",
    "result_contract",
    "sequence",
    "claims",
    "content_sha256",
}
SELECTED_TOOL_KEYS = {
    "capability",
    "surface_id",
    "source_kind",
    "access",
    "sensitivity",
    "evidence_kinds",
    "evidence_ref",
    "authorization_ref",
}
SLOT_KEYS = {
    "id",
    "role",
    "kind",
    "required",
    "allowed_producers",
    "capability",
    "surface_id",
    "artifact_ref_hint",
}
PACK_TASK_KEYS = {
    "pack_id",
    "skill_ref",
    "evaluator_ref",
    "observation_schema",
    "expected_scope",
    "required_tool_bindings",
    "evidence_requires",
    "evidence_produces",
    "observation_artifact_ref_hint",
}
RESULT_CONTRACT_KEYS = {
    "schema",
    "mission_id",
    "project_id",
    "decision_sha256",
    "project_state_sha256",
    "action",
}
CLAIMS = {
    "tool_execution_performed": False,
    "evidence_collected": False,
    "state_advanced": False,
    "authorization_granted": False,
    "agent_may_change_selected_surface": False,
}
SEQUENCE = [
    "EXECUTE_ACTION",
    "COLLECT_SELECTED_TOOL_ARTIFACTS",
    "BUILD_ACTIVE_PACK_OBSERVATIONS",
    "SEAL_EXECUTION_RESULT",
    "SUBMIT_RESULT_TO_SEF_EVIDENCE_API",
]


class ExecutionPlanError(MissionError):
    """Raised when a Codex execution hand-off is unsafe or inconsistent."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionPlanError(f"{label} must be a non-empty ISO-8601 timestamp")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ExecutionPlanError(f"{label} must be valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ExecutionPlanError(f"{label} must include a timezone")
    return parsed


def _exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise ExecutionPlanError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ExecutionPlanError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise ExecutionPlanError(f"{label} must be a compact stable identifier")
    return value


def _target_state(delivery_state: str) -> str:
    index = DELIVERY_STATES.index(delivery_state)
    if index >= len(DELIVERY_STATES) - 1:
        raise ExecutionPlanError("POST_DEPLOY_VERIFIED has no executable next state")
    return DELIVERY_STATES[index + 1]


def _selected_tools(decision: Mapping[str, Any]) -> list[dict[str, Any]]:
    bridge = decision.get("tool_bridge")
    requirements = decision.get("tool_requirements", [])
    if not requirements:
        if bridge is not None:
            raise ExecutionPlanError("decision without tool requirements must not carry tool bridge")
        return []
    if bridge is None:
        raise ExecutionPlanError("READY decision with tool requirements must carry M4 tool bridge")

    resolution = bridge.get("resolution", {})
    results = resolution.get("results", [])
    by_capability = {item.get("capability"): item for item in results}
    selected: list[dict[str, Any]] = []
    for requirement in requirements:
        capability = requirement["capability"]
        item = by_capability.get(capability)
        if not isinstance(item, dict) or item.get("status") != "READY":
            raise ExecutionPlanError(f"capability {capability} is not READY in exact M4 decision")
        if item.get("selected_surface_id") is None:
            raise ExecutionPlanError(f"capability {capability} has no selected M4 surface")
        selected.append(
            {
                "capability": capability,
                "surface_id": item["selected_surface_id"],
                "source_kind": item["selected_source_kind"],
                "access": item["access"],
                "sensitivity": item["sensitivity"],
                "evidence_kinds": sorted(item["evidence_kinds"]),
                "evidence_ref": item["evidence_ref"],
                "authorization_ref": item["authorization_ref"],
            }
        )
    return sorted(selected, key=lambda item: item["capability"])


def _load_pack_observation_schema(pack_id: str) -> tuple[dict[str, Any], str, str, str]:
    pack_dir = PACK_ROOT / pack_id
    pack = load_pack(pack_dir)
    evaluators = [entry for entry in pack["entry_points"] if entry["kind"] == "EVALUATOR"]
    if len(evaluators) != 1:
        raise ExecutionPlanError(f"pack {pack_id} must expose exactly one evaluator")
    evaluator_rel = evaluators[0]["path"]
    evaluator_path = (pack_dir / evaluator_rel).resolve()
    root = pack_dir.resolve()
    if os.path.commonpath([str(root), str(evaluator_path)]) != str(root):
        raise ExecutionPlanError(f"pack {pack_id} evaluator escapes pack directory")
    module_name = "_sef_m5_plan_pack_" + re.sub(r"[^A-Za-z0-9_]", "_", pack_id)
    spec = importlib.util.spec_from_file_location(module_name, evaluator_path)
    if spec is None or spec.loader is None:
        raise ExecutionPlanError(f"cannot inspect evaluator for pack {pack_id}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    observation_schema = getattr(module, "SCHEMA", None)
    if not isinstance(observation_schema, str) or not observation_schema:
        raise ExecutionPlanError(f"pack {pack_id} evaluator does not declare observation SCHEMA")
    return pack, observation_schema, f"expert_packs/{pack_id}/SKILL.md", f"expert_packs/{pack_id}/{evaluator_rel}"


def _expected_pack_scope(pack_id: str, action: str) -> dict[str, str]:
    if pack_id == "web-experience-visual-quality":
        scope = EXPECTED_VISUAL_SCOPE.get(action)
        if scope is None:
            raise ExecutionPlanError(f"visual-quality pack has no valid scope for action {action}")
        return dict(scope)
    if pack_id == "production-evidence-operations":
        if action != "VERIFY_PRODUCTION":
            raise ExecutionPlanError(f"production operations pack has no valid scope for action {action}")
        return {"release.environment_kind": "PRODUCTION"}
    return {}


def _pack_tasks(
    decision: Mapping[str, Any],
    selected_tools: list[dict[str, Any]],
    namespace: str,
) -> list[dict[str, Any]]:
    by_capability = {item["capability"]: item for item in selected_tools}
    tasks: list[dict[str, Any]] = []
    for pack_id in decision.get("active_packs", []):
        pack, observation_schema, skill_ref, evaluator_ref = _load_pack_observation_schema(pack_id)
        bindings = []
        for requirement in pack["tool_requirements"]:
            if not requirement["required"]:
                continue
            selected = by_capability.get(requirement["capability"])
            if selected is None:
                raise ExecutionPlanError(
                    f"active pack {pack_id} requires unselected capability {requirement['capability']}"
                )
            bindings.append(
                {
                    "capability": selected["capability"],
                    "surface_id": selected["surface_id"],
                    "access": selected["access"],
                    "sensitivity": selected["sensitivity"],
                }
            )
        tasks.append(
            {
                "pack_id": pack_id,
                "skill_ref": skill_ref,
                "evaluator_ref": evaluator_ref,
                "observation_schema": observation_schema,
                "expected_scope": _expected_pack_scope(pack_id, decision["next_action"]),
                "required_tool_bindings": sorted(bindings, key=lambda item: item["capability"]),
                "evidence_requires": list(pack["evidence_contract"]["requires"]),
                "evidence_produces": list(pack["evidence_contract"]["produces"]),
                "observation_artifact_ref_hint": f"{namespace}pack-observations/{pack_id}.json",
            }
        )
    return tasks


def _artifact_slots(
    decision: Mapping[str, Any],
    selected_tools: list[dict[str, Any]],
    namespace: str,
) -> list[dict[str, Any]]:
    action = decision["next_action"]
    target_state = _target_state(decision["delivery_state"])
    primary_kind = EVIDENCE_KIND_FOR_STATE[target_state]
    primary_capability = PRIMARY_CAPABILITY_BY_ACTION[action]
    by_capability = {item["capability"]: item for item in selected_tools}

    slots: list[dict[str, Any]] = []
    if primary_capability is None:
        slots.append(
            {
                "id": "SLOT-PRIMARY",
                "role": "PRIMARY",
                "kind": primary_kind,
                "required": True,
                "allowed_producers": ["AGENT", "SYSTEM"],
                "capability": None,
                "surface_id": None,
                "artifact_ref_hint": f"{namespace}primary/{primary_kind}.json",
            }
        )
    else:
        selected = by_capability.get(primary_capability)
        if selected is None:
            raise ExecutionPlanError(
                f"primary evidence capability {primary_capability} is not selected by M4"
            )
        slots.append(
            {
                "id": "SLOT-PRIMARY",
                "role": "PRIMARY",
                "kind": primary_kind,
                "required": True,
                "allowed_producers": ["TOOL"],
                "capability": primary_capability,
                "surface_id": selected["surface_id"],
                "artifact_ref_hint": f"{namespace}primary/{primary_kind}.json",
            }
        )

    for tool in selected_tools:
        if tool["capability"] == primary_capability:
            continue
        slots.append(
            {
                "id": f"SLOT-TOOL-{tool['capability'].replace('_', '-').upper()}",
                "role": "TOOL_SUPPORT",
                "kind": "tool-output",
                "required": True,
                "allowed_producers": ["TOOL"],
                "capability": tool["capability"],
                "surface_id": tool["surface_id"],
                "artifact_ref_hint": f"{namespace}tool/{tool['capability']}.json",
            }
        )

    for pack_id in decision.get("active_packs", []):
        slots.append(
            {
                "id": f"SLOT-PACK-{pack_id.upper()}",
                "role": "PACK_OBSERVATION",
                "kind": "pack-observation",
                "required": True,
                "allowed_producers": ["SYSTEM"],
                "capability": None,
                "surface_id": None,
                "artifact_ref_hint": f"{namespace}pack-observations/{pack_id}.json",
            }
        )
    return slots


def build_execution_plan(
    spec: dict[str, Any],
    state: dict[str, Any],
    decision: dict[str, Any],
    *,
    generated_at: str,
    evidence_namespace: str | None = None,
) -> dict[str, Any]:
    """Compile a READY mission decision into a deterministic Codex hand-off."""
    validate_spec(spec)
    validate_state(state)
    validate_decision(decision)
    _parse_time(generated_at, "generated_at")

    if decision["status"] != "READY_FOR_AGENT":
        raise ExecutionPlanError("only READY_FOR_AGENT decisions can produce execution plans")
    if decision["mission_id"] != spec["mission_id"] or decision["project_id"] != spec["project_id"]:
        raise ExecutionPlanError("decision does not belong to mission spec")
    if decision["project_state_sha256"] != state["content_sha256"]:
        raise ExecutionPlanError("decision is stale for current Project State")
    if decision["delivery_state"] != state["delivery_state"]:
        raise ExecutionPlanError("decision delivery state does not match Project State")

    namespace = evidence_namespace or (
        f"artifact://m5/{spec['mission_id']}/{decision['content_sha256'][:16]}/"
    )
    if not isinstance(namespace, str) or not ARTIFACT_NAMESPACE_RE.fullmatch(namespace) or ".." in namespace:
        raise ExecutionPlanError("evidence_namespace must be a safe artifact:// namespace ending in /")

    selected_tools = _selected_tools(decision)
    slots = _artifact_slots(decision, selected_tools, namespace)
    pack_tasks = _pack_tasks(decision, selected_tools, namespace)
    payload = {
        "schema": EXECUTION_PLAN_SCHEMA_ID,
        "mission_id": spec["mission_id"],
        "project_id": spec["project_id"],
        "decision_sha256": decision["content_sha256"],
        "project_state_sha256": state["content_sha256"],
        "delivery_state": state["delivery_state"],
        "action": decision["next_action"],
        "generated_at": generated_at,
        "status": "READY",
        "evidence_namespace": namespace,
        "selected_tools": selected_tools,
        "artifact_slots": slots,
        "pack_tasks": pack_tasks,
        "result_contract": {
            "schema": EXECUTION_RESULT_SCHEMA_ID,
            "mission_id": spec["mission_id"],
            "project_id": spec["project_id"],
            "decision_sha256": decision["content_sha256"],
            "project_state_sha256": state["content_sha256"],
            "action": decision["next_action"],
        },
        "sequence": list(SEQUENCE),
        "claims": dict(CLAIMS),
        "content_sha256": "0" * 64,
    }
    unsigned = copy.deepcopy(payload)
    unsigned.pop("content_sha256", None)
    payload["content_sha256"] = _digest(unsigned)
    validate_execution_plan(payload, decision=decision, state=state)
    return payload


def validate_execution_plan(
    plan: Any,
    *,
    decision: Mapping[str, Any] | None = None,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise ExecutionPlanError("execution plan root must be an object")
    _exact(plan, PLAN_KEYS, "execution_plan")
    if plan["schema"] != EXECUTION_PLAN_SCHEMA_ID:
        raise ExecutionPlanError(f"execution_plan.schema must equal {EXECUTION_PLAN_SCHEMA_ID}")
    _item_id(plan["mission_id"], "mission_id")
    if not isinstance(plan["project_id"], str) or not PROJECT_ID_RE.fullmatch(plan["project_id"]):
        raise ExecutionPlanError("project_id must be lowercase kebab-case")
    for field in ("decision_sha256", "project_state_sha256", "content_sha256"):
        if not isinstance(plan[field], str) or not SHA256_RE.fullmatch(plan[field]):
            raise ExecutionPlanError(f"{field} must be lowercase SHA-256")
    if plan["delivery_state"] not in DELIVERY_STATES[:-1]:
        raise ExecutionPlanError("execution plan delivery_state must be executable")
    if not isinstance(plan["action"], str) or not plan["action"]:
        raise ExecutionPlanError("execution plan action must be non-empty")
    _parse_time(plan["generated_at"], "generated_at")
    if plan["status"] not in PLAN_STATUSES:
        raise ExecutionPlanError("execution plan status is invalid")
    if not isinstance(plan["evidence_namespace"], str) or not ARTIFACT_NAMESPACE_RE.fullmatch(plan["evidence_namespace"]) or ".." in plan["evidence_namespace"]:
        raise ExecutionPlanError("execution plan evidence_namespace is invalid")

    tools = plan["selected_tools"]
    if not isinstance(tools, list):
        raise ExecutionPlanError("selected_tools must be a list")
    capabilities: set[str] = set()
    for index, tool in enumerate(tools):
        label = f"selected_tools[{index}]"
        if not isinstance(tool, dict):
            raise ExecutionPlanError(f"{label} must be an object")
        _exact(tool, SELECTED_TOOL_KEYS, label)
        capability = tool["capability"]
        if not isinstance(capability, str) or not CAPABILITY_RE.fullmatch(capability):
            raise ExecutionPlanError(f"{label}.capability is invalid")
        if capability in capabilities:
            raise ExecutionPlanError("selected_tools contains duplicate capabilities")
        capabilities.add(capability)
        _item_id(tool["surface_id"], f"{label}.surface_id")
        if tool["access"] not in {"READ", "WRITE"}:
            raise ExecutionPlanError(f"{label}.access is invalid")
        if tool["sensitivity"] not in {"LOCAL", "SANDBOX", "PRODUCTION_SENSITIVE"}:
            raise ExecutionPlanError(f"{label}.sensitivity is invalid")
        if not isinstance(tool["evidence_kinds"], list):
            raise ExecutionPlanError(f"{label}.evidence_kinds must be a list")

    slots = plan["artifact_slots"]
    if not isinstance(slots, list) or not slots:
        raise ExecutionPlanError("artifact_slots must be a non-empty list")
    slot_ids: set[str] = set()
    primary_count = 0
    for index, slot in enumerate(slots):
        label = f"artifact_slots[{index}]"
        if not isinstance(slot, dict):
            raise ExecutionPlanError(f"{label} must be an object")
        _exact(slot, SLOT_KEYS, label)
        slot_id = _item_id(slot["id"], f"{label}.id")
        if slot_id in slot_ids:
            raise ExecutionPlanError("artifact_slots contains duplicate ids")
        slot_ids.add(slot_id)
        if slot["role"] not in SLOT_ROLES:
            raise ExecutionPlanError(f"{label}.role is invalid")
        if slot["role"] == "PRIMARY":
            primary_count += 1
        if not isinstance(slot["required"], bool):
            raise ExecutionPlanError(f"{label}.required must be boolean")
        if not isinstance(slot["allowed_producers"], list) or not slot["allowed_producers"] or not set(slot["allowed_producers"]) <= PRODUCERS:
            raise ExecutionPlanError(f"{label}.allowed_producers is invalid")
        if not isinstance(slot["artifact_ref_hint"], str) or not slot["artifact_ref_hint"].startswith(plan["evidence_namespace"]):
            raise ExecutionPlanError(f"{label}.artifact_ref_hint must stay in evidence namespace")
        if slot["capability"] is None:
            if slot["surface_id"] is not None:
                raise ExecutionPlanError(f"{label}: null capability requires null surface_id")
        else:
            if slot["capability"] not in capabilities:
                raise ExecutionPlanError(f"{label} references unselected capability")
            _item_id(slot["surface_id"], f"{label}.surface_id")
    if primary_count != 1:
        raise ExecutionPlanError("execution plan must contain exactly one PRIMARY artifact slot")

    tasks = plan["pack_tasks"]
    if not isinstance(tasks, list):
        raise ExecutionPlanError("pack_tasks must be a list")
    task_ids: set[str] = set()
    for index, task in enumerate(tasks):
        label = f"pack_tasks[{index}]"
        if not isinstance(task, dict):
            raise ExecutionPlanError(f"{label} must be an object")
        _exact(task, PACK_TASK_KEYS, label)
        pack_id = _item_id(task["pack_id"], f"{label}.pack_id")
        if pack_id in task_ids:
            raise ExecutionPlanError("pack_tasks contains duplicate pack ids")
        task_ids.add(pack_id)
        for field in ("skill_ref", "evaluator_ref", "observation_schema", "observation_artifact_ref_hint"):
            if not isinstance(task[field], str) or not task[field]:
                raise ExecutionPlanError(f"{label}.{field} must be non-empty")
        if not task["observation_artifact_ref_hint"].startswith(plan["evidence_namespace"]):
            raise ExecutionPlanError(f"{label}.observation artifact must stay in evidence namespace")
        if not isinstance(task["expected_scope"], dict):
            raise ExecutionPlanError(f"{label}.expected_scope must be an object")
        if not isinstance(task["required_tool_bindings"], list):
            raise ExecutionPlanError(f"{label}.required_tool_bindings must be a list")
        for binding in task["required_tool_bindings"]:
            if binding.get("capability") not in capabilities:
                raise ExecutionPlanError(f"{label} references unselected tool binding")

    if not isinstance(plan["result_contract"], dict):
        raise ExecutionPlanError("result_contract must be an object")
    _exact(plan["result_contract"], RESULT_CONTRACT_KEYS, "result_contract")
    expected_contract = {
        "schema": EXECUTION_RESULT_SCHEMA_ID,
        "mission_id": plan["mission_id"],
        "project_id": plan["project_id"],
        "decision_sha256": plan["decision_sha256"],
        "project_state_sha256": plan["project_state_sha256"],
        "action": plan["action"],
    }
    if plan["result_contract"] != expected_contract:
        raise ExecutionPlanError("result_contract does not match execution plan binding")
    if plan["sequence"] != SEQUENCE:
        raise ExecutionPlanError("execution plan sequence is not canonical")
    if plan["claims"] != CLAIMS:
        raise ExecutionPlanError("execution plan contains unsupported claims")

    unsigned = copy.deepcopy(plan)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != plan["content_sha256"]:
        raise ExecutionPlanError("execution plan content hash mismatch")

    if decision is not None:
        validate_decision(dict(decision))
        if decision["status"] != "READY_FOR_AGENT":
            raise ExecutionPlanError("bound decision is not READY_FOR_AGENT")
        if plan["decision_sha256"] != decision["content_sha256"]:
            raise ExecutionPlanError("execution plan is not bound to exact decision")
        if plan["action"] != decision["next_action"] or plan["delivery_state"] != decision["delivery_state"]:
            raise ExecutionPlanError("execution plan action/state diverges from decision")
        expected_caps = sorted(item["capability"] for item in decision["tool_requirements"])
        if sorted(capabilities) != expected_caps:
            raise ExecutionPlanError("execution plan selected tools diverge from decision requirements")
        if sorted(task_ids) != sorted(decision["active_packs"]):
            raise ExecutionPlanError("execution plan pack tasks diverge from active packs")

    if state is not None:
        validate_state(dict(state))
        if plan["project_state_sha256"] != state["content_sha256"]:
            raise ExecutionPlanError("execution plan is stale for current Project State")
        if plan["delivery_state"] != state["delivery_state"]:
            raise ExecutionPlanError("execution plan delivery state diverges from Project State")
    return plan
