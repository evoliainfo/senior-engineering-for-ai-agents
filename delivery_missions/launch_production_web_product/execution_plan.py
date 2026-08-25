"""Deterministic Codex execution hand-off for the first Modern SEF mission.

A mission decision already answers *what should happen next* and M4 already
selects the tool surfaces that are allowed to satisfy the action. This module
turns that READY decision into a compact machine-readable execution/evidence
plan for the active Codex harness.

The plan is deliberately not an authorization source. Its safety property is
recomputability: when a decision is supplied, selected tools, project-context
scope, JIT capsule identities, artifact slots and M3 pack tasks must exactly
match deterministic projections of that decision. Rehashing a modified plan is
therefore insufficient to make a substituted surface/scope/capsule acceptable.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

from expert_packs import load_pack
from project_state import DELIVERY_STATES, EVIDENCE_KIND_FOR_STATE, validate_state
from tool_capabilities import validate_bridge_report

from .core import PACK_ROOT, MissionError, _scan_secrets, validate_decision, validate_spec
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
    "project_context_sha256",
    "delivery_state",
    "action",
    "generated_at",
    "status",
    "evidence_namespace",
    "context_domains",
    "expertise_bindings",
    "selected_tools",
    "artifact_slots",
    "pack_tasks",
    "result_contract",
    "sequence",
    "claims",
    "content_sha256",
}
SELECTED_TOOL_KEYS = {
    "requirement_id",
    "capability",
    "surface_id",
    "source_kind",
    "access",
    "sensitivity",
    "authentication",
    "authorization_required",
    "evidence_kinds",
    "evidence_ref",
    "authorization_ref",
}
EXPERTISE_BINDING_KEYS = {
    "need_id",
    "capsule_id",
    "capsule_sha256",
    "mission_need",
    "subject",
}
SUBJECT_KEYS = {"kind", "name", "version_context"}
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
TOOL_BINDING_KEYS = {"capability", "surface_id", "access", "sensitivity"}
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
    "agent_may_substitute_capsule": False,
    "plan_is_authorization_source": False,
}
SEQUENCE = [
    "LOAD_BOUND_PROJECT_CONTEXT",
    "LOAD_BOUND_JIT_EXPERTISE",
    "LOAD_ACTIVE_EXPERT_PACKS",
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


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ExecutionPlanError(f"{label} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ExecutionPlanError(f"{label} must not contain duplicates")
    return value


def _validate_namespace(value: Any, label: str = "evidence_namespace") -> str:
    if not isinstance(value, str) or not ARTIFACT_NAMESPACE_RE.fullmatch(value):
        raise ExecutionPlanError(f"{label} must be a safe artifact:// namespace ending in /")
    body = value[len("artifact://") : -1]
    parts = body.split("/")
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ExecutionPlanError(f"{label} contains unsafe path segments")
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
    try:
        validate_bridge_report(dict(bridge))
    except Exception as exc:
        raise ExecutionPlanError(f"decision M4 bridge is invalid: {exc}") from exc

    resolution = bridge["resolution"]
    results = resolution["results"]
    by_capability: dict[str, dict[str, Any]] = {}
    for item in results:
        capability = item.get("capability")
        if capability in by_capability:
            raise ExecutionPlanError(f"M4 resolution contains duplicate capability: {capability}")
        by_capability[capability] = item

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
                "requirement_id": item["requirement_id"],
                "capability": capability,
                "surface_id": item["selected_surface_id"],
                "source_kind": item["selected_source_kind"],
                "access": item["access"],
                "sensitivity": item["sensitivity"],
                "authentication": item["authentication"],
                "authorization_required": item["authorization_required"],
                "evidence_kinds": sorted(item["evidence_kinds"]),
                "evidence_ref": item["evidence_ref"],
                "authorization_ref": item["authorization_ref"],
            }
        )
    return sorted(selected, key=lambda item: item["capability"])


def _validate_tool_snapshot_freshness(decision: Mapping[str, Any], generated_at: str) -> None:
    if not decision.get("tool_requirements"):
        return
    bridge = decision.get("tool_bridge")
    if not isinstance(bridge, Mapping):
        raise ExecutionPlanError("tool-bound execution plan requires exact M4 bridge")
    resolution = bridge.get("resolution")
    if not isinstance(resolution, Mapping):
        raise ExecutionPlanError("tool-bound execution plan requires M4 resolution")
    resolved_at = _parse_time(resolution.get("resolved_at"), "decision.tool_bridge.resolution.resolved_at")
    current = _parse_time(generated_at, "generated_at")
    if resolved_at > current:
        raise ExecutionPlanError("execution plan cannot predate M4 tool resolution")
    ttl = resolution.get("max_observation_age_seconds")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 1:
        raise ExecutionPlanError("M4 resolution max_observation_age_seconds is invalid")
    if current > resolved_at + timedelta(seconds=ttl):
        raise ExecutionPlanError("M4 tool snapshot is stale at execution-plan generation time")


def _expertise_bindings(spec: Mapping[str, Any], decision: Mapping[str, Any]) -> list[dict[str, Any]]:
    needs = {item["id"]: item for item in spec["expertise_needs"]}
    readiness = decision.get("jit_readiness", [])
    bindings: list[dict[str, Any]] = []
    for item in readiness:
        if item.get("status") != "READY":
            raise ExecutionPlanError(f"READY decision contains non-ready JIT need: {item.get('need_id')}")
        need_id = item.get("need_id")
        need = needs.get(need_id)
        if need is None:
            raise ExecutionPlanError(f"decision references unknown JIT need: {need_id}")
        capsule_id = item.get("capsule_id")
        capsule_sha256 = item.get("capsule_sha256")
        if not isinstance(capsule_id, str) or not capsule_id:
            raise ExecutionPlanError(f"JIT need {need_id} has no bound capsule id")
        if not isinstance(capsule_sha256, str) or not SHA256_RE.fullmatch(capsule_sha256):
            raise ExecutionPlanError(f"JIT need {need_id} has no exact capsule SHA-256 binding")
        bindings.append(
            {
                "need_id": need_id,
                "capsule_id": capsule_id,
                "capsule_sha256": capsule_sha256,
                "mission_need": need["mission_need"],
                "subject": copy.deepcopy(need["subject"]),
            }
        )

    if decision["next_action"] not in {"PLAN_ARCHITECTURE", "COMPLETE"}:
        expected_ids = sorted(needs)
        if sorted(item["need_id"] for item in bindings) != expected_ids:
            raise ExecutionPlanError("READY decision does not bind every declared JIT expertise need")
    return sorted(bindings, key=lambda item: item["need_id"])


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
    module_spec = importlib.util.spec_from_file_location(module_name, evaluator_path)
    if module_spec is None or module_spec.loader is None:
        raise ExecutionPlanError(f"cannot inspect evaluator for pack {pack_id}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    observation_schema = getattr(module, "SCHEMA", None)
    if not isinstance(observation_schema, str) or not observation_schema:
        raise ExecutionPlanError(f"pack {pack_id} evaluator does not declare observation SCHEMA")
    return (
        pack,
        observation_schema,
        f"expert_packs/{pack_id}/SKILL.md",
        f"expert_packs/{pack_id}/{evaluator_rel}",
    )


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
                # The observation JSON may be assembled by Codex or a deterministic
                # harness. Its evidence-bearing references are still required by
                # the downstream M5 evidence layer to point to TOOL artifacts.
                "allowed_producers": ["AGENT", "SYSTEM"],
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
    generated = _parse_time(generated_at, "generated_at")

    if decision["status"] != "READY_FOR_AGENT":
        raise ExecutionPlanError("only READY_FOR_AGENT decisions can produce execution plans")
    if decision["mission_id"] != spec["mission_id"] or decision["project_id"] != spec["project_id"]:
        raise ExecutionPlanError("decision does not belong to mission spec")
    if decision["project_state_sha256"] != state["content_sha256"]:
        raise ExecutionPlanError("decision is stale for current Project State")
    if decision["delivery_state"] != state["delivery_state"]:
        raise ExecutionPlanError("decision delivery state does not match Project State")
    if generated < _parse_time(state["updated_at"], "state.updated_at"):
        raise ExecutionPlanError("execution plan cannot predate current Project State")
    _validate_tool_snapshot_freshness(decision, generated_at)

    namespace = evidence_namespace or (
        f"artifact://m5/{spec['mission_id']}/{decision['content_sha256'][:16]}/"
    )
    _validate_namespace(namespace)

    selected_tools = _selected_tools(decision)
    slots = _artifact_slots(decision, selected_tools, namespace)
    pack_tasks = _pack_tasks(decision, selected_tools, namespace)
    expertise_bindings = _expertise_bindings(spec, decision)
    payload = {
        "schema": EXECUTION_PLAN_SCHEMA_ID,
        "mission_id": spec["mission_id"],
        "project_id": spec["project_id"],
        "decision_sha256": decision["content_sha256"],
        "project_state_sha256": state["content_sha256"],
        "project_context_sha256": decision["project_context_sha256"],
        "delivery_state": state["delivery_state"],
        "action": decision["next_action"],
        "generated_at": generated_at,
        "status": "READY",
        "evidence_namespace": namespace,
        "context_domains": list(decision["context_domains"]),
        "expertise_bindings": expertise_bindings,
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
    validate_execution_plan(payload, spec=spec, decision=decision, state=state)
    return payload


def validate_execution_plan(
    plan: Any,
    *,
    spec: Mapping[str, Any] | None = None,
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
    for field in (
        "decision_sha256",
        "project_state_sha256",
        "project_context_sha256",
        "content_sha256",
    ):
        if not isinstance(plan[field], str) or not SHA256_RE.fullmatch(plan[field]):
            raise ExecutionPlanError(f"{field} must be lowercase SHA-256")
    if plan["delivery_state"] not in DELIVERY_STATES[:-1]:
        raise ExecutionPlanError("execution plan delivery_state must be executable")
    if not isinstance(plan["action"], str) or not plan["action"]:
        raise ExecutionPlanError("execution plan action must be non-empty")
    _parse_time(plan["generated_at"], "generated_at")
    if plan["status"] not in PLAN_STATUSES:
        raise ExecutionPlanError("execution plan status is invalid")
    _validate_namespace(plan["evidence_namespace"])
    _scan_secrets(plan, path="execution_plan")

    context_domains = _unique_strings(plan["context_domains"], "context_domains")
    if not context_domains:
        raise ExecutionPlanError("context_domains must not be empty")

    expertise = plan["expertise_bindings"]
    if not isinstance(expertise, list):
        raise ExecutionPlanError("expertise_bindings must be a list")
    need_ids: set[str] = set()
    for index, binding in enumerate(expertise):
        label = f"expertise_bindings[{index}]"
        if not isinstance(binding, dict):
            raise ExecutionPlanError(f"{label} must be an object")
        _exact(binding, EXPERTISE_BINDING_KEYS, label)
        need_id = _item_id(binding["need_id"], f"{label}.need_id")
        if need_id in need_ids:
            raise ExecutionPlanError("expertise_bindings contains duplicate need ids")
        need_ids.add(need_id)
        _item_id(binding["capsule_id"], f"{label}.capsule_id")
        if not isinstance(binding["capsule_sha256"], str) or not SHA256_RE.fullmatch(binding["capsule_sha256"]):
            raise ExecutionPlanError(f"{label}.capsule_sha256 must be lowercase SHA-256")
        if not isinstance(binding["mission_need"], str) or not binding["mission_need"].strip():
            raise ExecutionPlanError(f"{label}.mission_need must be non-empty")
        subject = binding["subject"]
        if not isinstance(subject, dict):
            raise ExecutionPlanError(f"{label}.subject must be an object")
        _exact(subject, SUBJECT_KEYS, f"{label}.subject")
        if not isinstance(subject["kind"], str) or not subject["kind"]:
            raise ExecutionPlanError(f"{label}.subject.kind must be non-empty")
        if not isinstance(subject["name"], str) or not subject["name"].strip():
            raise ExecutionPlanError(f"{label}.subject.name must be non-empty")
        if subject["version_context"] is not None and not isinstance(subject["version_context"], str):
            raise ExecutionPlanError(f"{label}.subject.version_context must be string or null")

    tools = plan["selected_tools"]
    if not isinstance(tools, list):
        raise ExecutionPlanError("selected_tools must be a list")
    capabilities: set[str] = set()
    tool_by_capability: dict[str, dict[str, Any]] = {}
    for index, tool in enumerate(tools):
        label = f"selected_tools[{index}]"
        if not isinstance(tool, dict):
            raise ExecutionPlanError(f"{label} must be an object")
        _exact(tool, SELECTED_TOOL_KEYS, label)
        _item_id(tool["requirement_id"], f"{label}.requirement_id")
        capability = tool["capability"]
        if not isinstance(capability, str) or not CAPABILITY_RE.fullmatch(capability):
            raise ExecutionPlanError(f"{label}.capability is invalid")
        if capability in capabilities:
            raise ExecutionPlanError("selected_tools contains duplicate capabilities")
        capabilities.add(capability)
        tool_by_capability[capability] = tool
        _item_id(tool["surface_id"], f"{label}.surface_id")
        if not isinstance(tool["source_kind"], str) or not tool["source_kind"]:
            raise ExecutionPlanError(f"{label}.source_kind must be non-empty")
        if tool["access"] not in {"READ", "WRITE"}:
            raise ExecutionPlanError(f"{label}.access is invalid")
        if tool["sensitivity"] not in {"LOCAL", "SANDBOX", "PRODUCTION_SENSITIVE"}:
            raise ExecutionPlanError(f"{label}.sensitivity is invalid")
        if tool["authentication"] not in {"AUTHENTICATED", "NOT_APPLICABLE"}:
            raise ExecutionPlanError(f"{label}.authentication must be execution-ready")
        if tool["authorization_required"] != "NOT_REQUIRED":
            raise ExecutionPlanError(f"{label}.authorization_required must be NOT_REQUIRED in READY plan")
        _unique_strings(tool["evidence_kinds"], f"{label}.evidence_kinds")
        for field in ("evidence_ref", "authorization_ref"):
            if tool[field] is not None and (not isinstance(tool[field], str) or not tool[field].strip()):
                raise ExecutionPlanError(f"{label}.{field} must be non-empty string or null")

    slots = plan["artifact_slots"]
    if not isinstance(slots, list) or not slots:
        raise ExecutionPlanError("artifact_slots must be a non-empty list")
    slot_ids: set[str] = set()
    slot_refs: set[str] = set()
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
        if slot["required"] is not True:
            raise ExecutionPlanError(f"{label}.required must be true in canonical execution plan")
        producers = _unique_strings(slot["allowed_producers"], f"{label}.allowed_producers")
        if not set(producers) <= PRODUCERS:
            raise ExecutionPlanError(f"{label}.allowed_producers is invalid")
        ref_hint = slot["artifact_ref_hint"]
        if not isinstance(ref_hint, str) or not ref_hint.startswith(plan["evidence_namespace"]):
            raise ExecutionPlanError(f"{label}.artifact_ref_hint must stay in evidence namespace")
        if ref_hint in slot_refs:
            raise ExecutionPlanError("artifact_slots contains duplicate artifact_ref_hint values")
        slot_refs.add(ref_hint)
        if slot["capability"] is None:
            if slot["surface_id"] is not None:
                raise ExecutionPlanError(f"{label}: null capability requires null surface_id")
        else:
            capability = slot["capability"]
            selected = tool_by_capability.get(capability)
            if selected is None:
                raise ExecutionPlanError(f"{label} references unselected capability")
            if slot["surface_id"] != selected["surface_id"]:
                raise ExecutionPlanError(f"{label} surface does not match selected capability surface")
    if primary_count != 1:
        raise ExecutionPlanError("execution plan must contain exactly one PRIMARY artifact slot")

    tasks = plan["pack_tasks"]
    if not isinstance(tasks, list):
        raise ExecutionPlanError("pack_tasks must be a list")
    task_ids: set[str] = set()
    observation_hints: set[str] = set()
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
        hint = task["observation_artifact_ref_hint"]
        if not hint.startswith(plan["evidence_namespace"]):
            raise ExecutionPlanError(f"{label}.observation artifact must stay in evidence namespace")
        if hint in observation_hints:
            raise ExecutionPlanError("pack_tasks contains duplicate observation artifact hints")
        observation_hints.add(hint)
        if not isinstance(task["expected_scope"], dict) or not all(
            isinstance(key, str) and key and isinstance(value, str)
            for key, value in task["expected_scope"].items()
        ):
            raise ExecutionPlanError(f"{label}.expected_scope must be string-to-string object")
        bindings = task["required_tool_bindings"]
        if not isinstance(bindings, list):
            raise ExecutionPlanError(f"{label}.required_tool_bindings must be a list")
        seen_bindings: set[str] = set()
        for binding_index, binding in enumerate(bindings):
            binding_label = f"{label}.required_tool_bindings[{binding_index}]"
            if not isinstance(binding, dict):
                raise ExecutionPlanError(f"{binding_label} must be an object")
            _exact(binding, TOOL_BINDING_KEYS, binding_label)
            capability = binding["capability"]
            if capability in seen_bindings:
                raise ExecutionPlanError(f"{label} contains duplicate required tool bindings")
            seen_bindings.add(capability)
            selected = tool_by_capability.get(capability)
            if selected is None:
                raise ExecutionPlanError(f"{label} references unselected tool binding")
            expected_binding = {
                "capability": capability,
                "surface_id": selected["surface_id"],
                "access": selected["access"],
                "sensitivity": selected["sensitivity"],
            }
            if binding != expected_binding:
                raise ExecutionPlanError(f"{binding_label} diverges from selected tool")
        _unique_strings(task["evidence_requires"], f"{label}.evidence_requires")
        _unique_strings(task["evidence_produces"], f"{label}.evidence_produces")

    pack_slot_hints = {
        item["artifact_ref_hint"]
        for item in slots
        if item["role"] == "PACK_OBSERVATION"
    }
    if pack_slot_hints != observation_hints:
        raise ExecutionPlanError("pack observation slots must exactly match pack task outputs")

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

    if spec is not None:
        validate_spec(dict(spec))
        if plan["mission_id"] != spec["mission_id"] or plan["project_id"] != spec["project_id"]:
            raise ExecutionPlanError("execution plan does not belong to mission spec")

    if decision is not None:
        validate_decision(dict(decision))
        if decision["status"] != "READY_FOR_AGENT":
            raise ExecutionPlanError("bound decision is not READY_FOR_AGENT")
        if plan["decision_sha256"] != decision["content_sha256"]:
            raise ExecutionPlanError("execution plan is not bound to exact decision")
        if plan["action"] != decision["next_action"] or plan["delivery_state"] != decision["delivery_state"]:
            raise ExecutionPlanError("execution plan action/state diverges from decision")
        if plan["project_context_sha256"] != decision["project_context_sha256"]:
            raise ExecutionPlanError("execution plan project context digest diverges from decision")
        if plan["context_domains"] != decision["context_domains"]:
            raise ExecutionPlanError("execution plan context domains diverge from decision")
        _validate_tool_snapshot_freshness(decision, plan["generated_at"])

        expected_tools = _selected_tools(decision)
        if plan["selected_tools"] != expected_tools:
            raise ExecutionPlanError("execution plan selected tools are not exact M4 projection")
        expected_slots = _artifact_slots(decision, expected_tools, plan["evidence_namespace"])
        if plan["artifact_slots"] != expected_slots:
            raise ExecutionPlanError("execution plan artifact slots are not canonical for decision")
        expected_tasks = _pack_tasks(decision, expected_tools, plan["evidence_namespace"])
        if plan["pack_tasks"] != expected_tasks:
            raise ExecutionPlanError("execution plan pack tasks are not canonical for decision")

        decision_jit = {
            item["need_id"]: (item.get("capsule_id"), item.get("capsule_sha256"))
            for item in decision.get("jit_readiness", [])
            if item.get("status") == "READY"
        }
        plan_jit = {
            item["need_id"]: (item["capsule_id"], item["capsule_sha256"])
            for item in expertise
        }
        if plan_jit != decision_jit:
            raise ExecutionPlanError("execution plan JIT bindings diverge from exact decision")

    if spec is not None and decision is not None:
        expected_expertise = _expertise_bindings(spec, decision)
        if plan["expertise_bindings"] != expected_expertise:
            raise ExecutionPlanError("execution plan expertise bindings are not canonical")

    if state is not None:
        validate_state(dict(state))
        if plan["project_state_sha256"] != state["content_sha256"]:
            raise ExecutionPlanError("execution plan is stale for current Project State")
        if plan["delivery_state"] != state["delivery_state"]:
            raise ExecutionPlanError("execution plan delivery state diverges from Project State")
        if _parse_time(plan["generated_at"], "generated_at") < _parse_time(state["updated_at"], "state.updated_at"):
            raise ExecutionPlanError("execution plan cannot predate current Project State")
    return plan
