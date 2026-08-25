"""Deterministic orchestration core for the first Modern SEF Delivery Mission.

This module does not execute tools, browse documentation, deploy software, or
advance Project State. It composes the already-qualified M1-M4 contracts so the
active agent can ask a much narrower question: what is the next evidence-backed
engineering action, and what currently blocks it?
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from expert_packs import load_pack
from jit_expertise import (
    JITExpertiseError,
    evaluate_invalidation,
    validate_capsule,
)
from project_state import (
    DELIVERY_STATES,
    DOMAINS,
    ProjectStateError,
    add_entry,
    new_state,
    select_context,
    validate_state,
)
from tool_capabilities import (
    CodexInventoryError,
    adapt_inventory,
    resolve_codex_inventory,
    validate_bridge_report,
)

MISSION_SCHEMA_ID = "sef.delivery-mission.launch-production-web-product.v1"
DECISION_SCHEMA_ID = "sef.delivery-mission-decision.launch-production-web-product.v1"
MISSION_NAME = "launch-production-web-product"

ROOT = Path(__file__).resolve().parents[2]
PACK_ROOT = ROOT / "expert_packs"

ACTIONS_BY_STATE = {
    "FRAMED": "PLAN_ARCHITECTURE",
    "ARCHITECTED": "IMPLEMENT_PRODUCT",
    "IMPLEMENTED": "VERIFY_LOCAL_PRODUCT",
    "VERIFIED_LOCAL": "DEPLOY_AND_VERIFY_PREVIEW",
    "PREVIEW_VERIFIED": "PROVE_RELEASE_READINESS",
    "RELEASE_READY": "DEPLOY_PRODUCTION",
    "DEPLOYED": "VERIFY_PRODUCTION",
    "POST_DEPLOY_VERIFIED": "COMPLETE",
}

CONTEXT_BY_ACTION = {
    "PLAN_ARCHITECTURE": [
        "product",
        "requirements",
        "integrations",
        "data",
        "identity_access",
        "open_decisions",
        "known_risks",
    ],
    "IMPLEMENT_PRODUCT": [
        "product",
        "requirements",
        "architecture",
        "interfaces",
        "data",
        "identity_access",
        "integrations",
        "environments",
        "security",
    ],
    "VERIFY_LOCAL_PRODUCT": [
        "requirements",
        "architecture",
        "interfaces",
        "data",
        "identity_access",
        "integrations",
        "quality",
        "security",
    ],
    "DEPLOY_AND_VERIFY_PREVIEW": [
        "requirements",
        "architecture",
        "environments",
        "quality",
        "security",
        "release",
    ],
    "PROVE_RELEASE_READINESS": [
        "requirements",
        "data",
        "quality",
        "security",
        "release",
        "known_risks",
        "open_decisions",
    ],
    "DEPLOY_PRODUCTION": [
        "environments",
        "security",
        "release",
        "deployments",
        "known_risks",
        "open_decisions",
    ],
    "VERIFY_PRODUCTION": [
        "requirements",
        "deployments",
        "observability",
        "quality",
        "release",
        "known_risks",
    ],
    "COMPLETE": ["product", "release", "deployments", "observability", "known_risks"],
}

PACKS_BY_ACTION = {
    "PLAN_ARCHITECTURE": [],
    "IMPLEMENT_PRODUCT": [],
    "VERIFY_LOCAL_PRODUCT": ["web-experience-visual-quality"],
    "DEPLOY_AND_VERIFY_PREVIEW": ["web-experience-visual-quality"],
    "PROVE_RELEASE_READINESS": ["web-experience-visual-quality"],
    "DEPLOY_PRODUCTION": [],
    "VERIFY_PRODUCTION": ["production-evidence-operations"],
    "COMPLETE": [],
}

BASE_TOOL_REQUIREMENTS = {
    "PLAN_ARCHITECTURE": [],
    "IMPLEMENT_PRODUCT": [
        ("source_control", "WRITE", "LOCAL"),
    ],
    "VERIFY_LOCAL_PRODUCT": [
        ("browser", "READ", "SANDBOX"),
        ("visual_capture", "READ", "SANDBOX"),
    ],
    "DEPLOY_AND_VERIFY_PREVIEW": [
        ("hosting", "WRITE", "SANDBOX"),
        ("browser", "READ", "SANDBOX"),
        ("visual_capture", "READ", "SANDBOX"),
    ],
    "PROVE_RELEASE_READINESS": [
        ("ci", "READ", "SANDBOX"),
    ],
    "DEPLOY_PRODUCTION": [
        ("hosting", "WRITE", "PRODUCTION_SENSITIVE"),
    ],
    "VERIFY_PRODUCTION": [
        ("browser", "READ", "PRODUCTION_SENSITIVE"),
        ("observability", "READ", "PRODUCTION_SENSITIVE"),
    ],
    "COMPLETE": [],
}

ACCESS_RANK = {"NONE": 0, "READ": 1, "WRITE": 2}
SENSITIVITY_RANK = {"LOCAL": 0, "SANDBOX": 1, "PRODUCTION_SENSITIVE": 2}

MISSION_KEYS = {
    "schema",
    "mission_id",
    "project_id",
    "outcome",
    "acceptance",
    "surfaces",
    "expertise_needs",
    "created_at",
}
ACCEPTANCE_KEYS = {"id", "statement", "authority", "blocking"}
SURFACE_KEYS = {
    "web_ui",
    "persistent_data",
    "material_data_change",
    "identity_access",
    "billing",
    "external_integrations",
}
INTEGRATION_KEYS = {"id", "name"}
EXPERTISE_NEED_KEYS = {"id", "mission_need", "subject", "context_domains"}
SUBJECT_KEYS = {"kind", "name", "version_context"}
SUBJECT_KINDS = {"EXTERNAL_PROVIDER", "FRAMEWORK", "REPOSITORY_CONTRACT", "STANDARD"}
AUTHORITIES = {"USER", "ENGINEERING"}

ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
PROJECT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*[^\s,;]{8,}"),
)


class MissionError(ValueError):
    """Raised when the M5 mission contract or composition is invalid."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise MissionError(f"{label} must be a non-empty ISO-8601 timestamp")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MissionError(f"{label} must be valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise MissionError(f"{label} must include a timezone")
    return parsed


def _exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise MissionError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise MissionError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _text(value: Any, label: str, *, limit: int = 1200) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MissionError(f"{label} must be a non-empty string")
    if len(value) > limit:
        raise MissionError(f"{label} exceeds {limit} characters")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise MissionError(f"{label} must be a compact stable identifier")
    return value


def _scan_secrets(value: Any, path: str = "mission") -> None:
    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise MissionError(f"credential-shaped secret value detected at {path}")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _scan_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secrets(child, f"{path}[{index}]")


def validate_spec(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise MissionError("mission spec root must be an object")
    _exact(spec, MISSION_KEYS, "mission")
    if spec["schema"] != MISSION_SCHEMA_ID:
        raise MissionError(f"mission.schema must equal {MISSION_SCHEMA_ID}")
    _item_id(spec["mission_id"], "mission_id")
    if not isinstance(spec["project_id"], str) or not PROJECT_ID_RE.fullmatch(spec["project_id"]):
        raise MissionError("project_id must be lowercase kebab-case")
    _text(spec["outcome"], "outcome", limit=1200)
    _parse_time(spec["created_at"], "created_at")
    _scan_secrets(spec)

    acceptance = spec["acceptance"]
    if not isinstance(acceptance, list) or not acceptance:
        raise MissionError("acceptance must be a non-empty list")
    acceptance_ids: set[str] = set()
    for index, item in enumerate(acceptance):
        label = f"acceptance[{index}]"
        if not isinstance(item, dict):
            raise MissionError(f"{label} must be an object")
        _exact(item, ACCEPTANCE_KEYS, label)
        item_id = _item_id(item["id"], f"{label}.id")
        if item_id in acceptance_ids:
            raise MissionError("acceptance contains duplicate ids")
        acceptance_ids.add(item_id)
        _text(item["statement"], f"{label}.statement")
        if item["authority"] not in AUTHORITIES:
            raise MissionError(f"{label}.authority must be USER or ENGINEERING")
        if not isinstance(item["blocking"], bool):
            raise MissionError(f"{label}.blocking must be boolean")
    if not any(item["blocking"] for item in acceptance):
        raise MissionError("at least one acceptance criterion must be blocking")

    surfaces = spec["surfaces"]
    if not isinstance(surfaces, dict):
        raise MissionError("surfaces must be an object")
    _exact(surfaces, SURFACE_KEYS, "surfaces")
    for key in SURFACE_KEYS - {"external_integrations"}:
        if not isinstance(surfaces[key], bool):
            raise MissionError(f"surfaces.{key} must be boolean")
    if not surfaces["web_ui"]:
        raise MissionError("launch-production-web-product requires surfaces.web_ui=true")
    if surfaces["material_data_change"] and not surfaces["persistent_data"]:
        raise MissionError("material_data_change requires persistent_data=true")
    integrations = surfaces["external_integrations"]
    if not isinstance(integrations, list):
        raise MissionError("surfaces.external_integrations must be a list")
    integration_ids: set[str] = set()
    for index, item in enumerate(integrations):
        label = f"surfaces.external_integrations[{index}]"
        if not isinstance(item, dict):
            raise MissionError(f"{label} must be an object")
        _exact(item, INTEGRATION_KEYS, label)
        integration_id = _item_id(item["id"], f"{label}.id")
        if integration_id in integration_ids:
            raise MissionError("external_integrations contains duplicate ids")
        integration_ids.add(integration_id)
        _text(item["name"], f"{label}.name", limit=300)

    needs = spec["expertise_needs"]
    if not isinstance(needs, list):
        raise MissionError("expertise_needs must be a list")
    need_ids: set[str] = set()
    for index, need in enumerate(needs):
        label = f"expertise_needs[{index}]"
        if not isinstance(need, dict):
            raise MissionError(f"{label} must be an object")
        _exact(need, EXPERTISE_NEED_KEYS, label)
        need_id = _item_id(need["id"], f"{label}.id")
        if need_id in need_ids:
            raise MissionError("expertise_needs contains duplicate ids")
        need_ids.add(need_id)
        _text(need["mission_need"], f"{label}.mission_need", limit=800)
        subject = need["subject"]
        if not isinstance(subject, dict):
            raise MissionError(f"{label}.subject must be an object")
        _exact(subject, SUBJECT_KEYS, f"{label}.subject")
        if subject["kind"] not in SUBJECT_KINDS:
            raise MissionError(f"{label}.subject.kind is invalid")
        _text(subject["name"], f"{label}.subject.name", limit=300)
        if subject["version_context"] is not None:
            _text(subject["version_context"], f"{label}.subject.version_context", limit=200)
        domains = need["context_domains"]
        if not isinstance(domains, list) or not domains:
            raise MissionError(f"{label}.context_domains must be a non-empty list")
        if len(domains) != len(set(domains)):
            raise MissionError(f"{label}.context_domains must not contain duplicates")
        unknown = [domain for domain in domains if domain not in DOMAINS]
        if unknown:
            raise MissionError(f"{label}.context_domains contains unknown domains: {sorted(unknown)}")
    return spec


def initialize_project_state(
    spec: dict[str, Any],
    *,
    evidence_locator: str,
    at: str,
    evidence_sha256: str | None = None,
) -> dict[str, Any]:
    """Create a FRAMED M1 state aligned with outcome and acceptance."""
    validate_spec(spec)
    _parse_time(at, "at")
    state = new_state(
        project_id=spec["project_id"],
        product_statement=spec["outcome"],
        evidence_locator=evidence_locator,
        at=at,
        evidence_sha256=evidence_sha256,
    )
    for item in spec["acceptance"]:
        state = add_entry(
            state,
            domain="requirements",
            entry_id="ACCEPT-" + item["id"],
            kind="DECISION",
            statement=item["statement"],
            authority=item["authority"],
            evidence_refs=["EVID-FRAME-001"],
            updated_at=at,
        )
    validate_state(state)
    _validate_state_alignment(spec, state)
    return state


def _validate_state_alignment(spec: dict[str, Any], state: dict[str, Any]) -> None:
    validate_state(state)
    if state["project_id"] != spec["project_id"]:
        raise MissionError("project state project_id does not match mission")
    product_entries = [item for item in state["domains"]["product"] if item["status"] == "ACTIVE"]
    if not any(item["statement"] == spec["outcome"] for item in product_entries):
        raise MissionError("project state does not contain the mission outcome")
    requirements = {
        item["id"]: item
        for item in state["domains"]["requirements"]
        if item["status"] == "ACTIVE"
    }
    for acceptance in spec["acceptance"]:
        entry = requirements.get("ACCEPT-" + acceptance["id"])
        if entry is None:
            raise MissionError(f"project state is missing acceptance {acceptance['id']}")
        if entry["statement"] != acceptance["statement"] or entry["authority"] != acceptance["authority"]:
            raise MissionError(f"project state acceptance {acceptance['id']} diverges from mission")


def _active_pack_ids(spec: dict[str, Any], action: str) -> list[str]:
    pack_ids = list(PACKS_BY_ACTION[action])
    if spec["surfaces"]["material_data_change"] and action in {
        "VERIFY_LOCAL_PRODUCT",
        "PROVE_RELEASE_READINESS",
        "DEPLOY_PRODUCTION",
    }:
        pack_ids.append("data-change-safety")
    return sorted(set(pack_ids))


def _add_requirement(
    merged: dict[str, dict[str, Any]],
    *,
    capability: str,
    access: str,
    sensitivity: str,
    evidence_kinds: Iterable[str] = (),
) -> None:
    current = merged.get(capability)
    if current is None:
        merged[capability] = {
            "capability": capability,
            "access": access,
            "sensitivity": sensitivity,
            "required_evidence_kinds": sorted(set(evidence_kinds)),
        }
        return
    if ACCESS_RANK[access] > ACCESS_RANK[current["access"]]:
        current["access"] = access
    if SENSITIVITY_RANK[sensitivity] > SENSITIVITY_RANK[current["sensitivity"]]:
        current["sensitivity"] = sensitivity
    current["required_evidence_kinds"] = sorted(
        set(current["required_evidence_kinds"]) | set(evidence_kinds)
    )


def _tool_requirements(spec: dict[str, Any], action: str, pack_ids: list[str]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for capability, access, sensitivity in BASE_TOOL_REQUIREMENTS[action]:
        _add_requirement(
            merged,
            capability=capability,
            access=access,
            sensitivity=sensitivity,
        )

    surfaces = spec["surfaces"]
    if action in {"IMPLEMENT_PRODUCT", "VERIFY_LOCAL_PRODUCT", "PROVE_RELEASE_READINESS"}:
        if surfaces["persistent_data"]:
            _add_requirement(
                merged,
                capability="database_admin",
                access="WRITE",
                sensitivity="SANDBOX",
            )
        if surfaces["identity_access"] and action in {"IMPLEMENT_PRODUCT", "VERIFY_LOCAL_PRODUCT"}:
            _add_requirement(
                merged,
                capability="auth_admin",
                access="WRITE",
                sensitivity="SANDBOX",
            )
        if surfaces["billing"] and action in {"IMPLEMENT_PRODUCT", "VERIFY_LOCAL_PRODUCT"}:
            _add_requirement(
                merged,
                capability="billing_admin",
                access="WRITE",
                sensitivity="SANDBOX",
            )
        if surfaces["external_integrations"] and action in {"IMPLEMENT_PRODUCT", "VERIFY_LOCAL_PRODUCT"}:
            _add_requirement(
                merged,
                capability="external_provider_sandbox",
                access="WRITE",
                sensitivity="SANDBOX",
            )

    for pack_id in pack_ids:
        pack = load_pack(PACK_ROOT / pack_id)
        for requirement in pack["tool_requirements"]:
            if not requirement["required"]:
                continue
            _add_requirement(
                merged,
                capability=requirement["capability"],
                access=requirement["access"],
                sensitivity=requirement["sensitivity"],
            )

    out = []
    for capability in sorted(merged):
        item = merged[capability]
        out.append(
            {
                "id": f"REQ-{action.lower().replace('_', '-')}-{capability.replace('_', '-')}",
                "capability": capability,
                "access": item["access"],
                "sensitivity": item["sensitivity"],
                "required_evidence_kinds": item["required_evidence_kinds"],
            }
        )
    return out


def _capsule_matches_need(capsule: Mapping[str, Any], need: Mapping[str, Any]) -> bool:
    return (
        capsule.get("mission_need") == need["mission_need"]
        and capsule.get("subject") == need["subject"]
    )


def _semantic_current_tool(
    expected: Mapping[str, Any], adapter_report: Mapping[str, Any]
) -> dict[str, str]:
    capability = expected["capability"]
    observations = [
        item for item in adapter_report["observations"] if item["capability"] == capability
    ]
    authenticated = [
        item
        for item in observations
        if item["availability"] == "AVAILABLE"
        and item["authentication"] in {"AUTHENTICATED", "NOT_APPLICABLE"}
    ]
    access_fit = [
        item for item in authenticated if ACCESS_RANK[item["access"]] >= ACCESS_RANK[expected["access"]]
    ]
    if access_fit:
        selected = sorted(
            access_fit,
            key=lambda item: (ACCESS_RANK[item["access"]], item["surface_id"]),
        )[0]
        return {"capability": capability, "availability": "AVAILABLE", "access": selected["access"]}
    if any(item["availability"] == "AVAILABLE" for item in observations):
        if not authenticated:
            return {"capability": capability, "availability": "UNAUTHENTICATED", "access": "NONE"}
        best = sorted(authenticated, key=lambda item: (-ACCESS_RANK[item["access"]], item["surface_id"]))[0]
        return {"capability": capability, "availability": "AVAILABLE", "access": best["access"]}
    return {"capability": capability, "availability": "UNAVAILABLE", "access": "NONE"}


def _jit_readiness(
    spec: dict[str, Any],
    state: dict[str, Any],
    *,
    action: str,
    at: str,
    capsules: Iterable[Mapping[str, Any]],
    adapter_report: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if action in {"PLAN_ARCHITECTURE", "COMPLETE"} or not spec["expertise_needs"]:
        return [], []
    capsule_list = [copy.deepcopy(dict(item)) for item in capsules]
    results: list[dict[str, Any]] = []
    blockers: list[str] = []

    for need in spec["expertise_needs"]:
        matching = [item for item in capsule_list if _capsule_matches_need(item, need)]
        if len(matching) != 1:
            results.append({"need_id": need["id"], "status": "MISSING", "capsule_id": None, "reasons": []})
            blockers.append(f"JIT_CAPSULE_REQUIRED:{need['id']}")
            continue
        capsule = matching[0]
        try:
            validate_capsule(capsule)
        except JITExpertiseError as exc:
            results.append(
                {
                    "need_id": need["id"],
                    "status": "INVALID",
                    "capsule_id": capsule.get("capsule_id"),
                    "reasons": [str(exc)],
                }
            )
            blockers.append(f"JIT_CAPSULE_INVALID:{need['id']}")
            continue
        if capsule["project_id"] != spec["project_id"]:
            results.append(
                {
                    "need_id": need["id"],
                    "status": "INVALID",
                    "capsule_id": capsule["capsule_id"],
                    "reasons": ["PROJECT_ID_MISMATCH"],
                }
            )
            blockers.append(f"JIT_CAPSULE_INVALID:{need['id']}")
            continue
        context = select_context(state, need["context_domains"])
        reasons = evaluate_invalidation(
            capsule,
            now=at,
            project_context=context,
            # M4 owns observation freshness. Reusing capsule tool timestamps here
            # prevents a harmless re-observation timestamp from masquerading as a
            # capability change; semantic capability/access is checked below.
            tools=capsule["tools"],
        )
        if capsule["tools"]:
            if adapter_report is None:
                reasons.append("TOOL_STATE_NOT_REOBSERVED")
            else:
                for expected in capsule["tools"]:
                    current = _semantic_current_tool(expected, adapter_report)
                    expected_semantic = {
                        "capability": expected["capability"],
                        "availability": expected["availability"],
                        "access": expected["access"],
                    }
                    if current != expected_semantic:
                        reasons.append("TOOL_CAPABILITY_CHANGED")
                        break
        reasons = sorted(set(reasons))
        if capsule["status"] != "READY":
            reasons.append(f"CAPSULE_STATUS:{capsule['status']}")
        status = "READY" if not reasons else "STALE_OR_BLOCKED"
        results.append(
            {
                "need_id": need["id"],
                "status": status,
                "capsule_id": capsule["capsule_id"],
                "reasons": sorted(set(reasons)),
            }
        )
        if status != "READY":
            blockers.append(f"JIT_CAPSULE_NOT_READY:{need['id']}")
    return results, sorted(set(blockers))


def decide_next_action(
    spec: dict[str, Any],
    state: dict[str, Any],
    *,
    at: str,
    tool_inventory: dict[str, Any] | None = None,
    capsules: Iterable[Mapping[str, Any]] = (),
    max_tool_age_seconds: int = 300,
) -> dict[str, Any]:
    """Return the next mission action and current blockers without executing it."""
    validate_spec(spec)
    validate_state(state)
    _validate_state_alignment(spec, state)
    _parse_time(at, "at")
    action = ACTIONS_BY_STATE[state["delivery_state"]]
    context_domains = CONTEXT_BY_ACTION[action]
    context = select_context(state, context_domains)
    pack_ids = _active_pack_ids(spec, action)
    requirements = _tool_requirements(spec, action, pack_ids)

    blockers: list[str] = []
    tool_bridge = None
    adapter_report = None
    if tool_inventory is not None:
        try:
            adapter_report = adapt_inventory(tool_inventory)
        except CodexInventoryError as exc:
            raise MissionError(f"invalid Codex tool inventory: {exc}") from exc

    if requirements:
        if tool_inventory is None:
            blockers.append("TOOL_INVENTORY_REQUIRED")
        else:
            try:
                tool_bridge = resolve_codex_inventory(
                    tool_inventory,
                    requirements,
                    max_observation_age_seconds=max_tool_age_seconds,
                )
                validate_bridge_report(tool_bridge)
            except CodexInventoryError as exc:
                raise MissionError(f"tool capability resolution failed: {exc}") from exc
            for result in tool_bridge["resolution"]["results"]:
                if result["status"] != "READY":
                    blockers.append(f"TOOL_{result['status']}:{result['capability']}")

    jit_results, jit_blockers = _jit_readiness(
        spec,
        state,
        action=action,
        at=at,
        capsules=capsules,
        adapter_report=adapter_report,
    )
    blockers.extend(jit_blockers)
    blockers = sorted(set(blockers))

    if action == "COMPLETE":
        status = "COMPLETE"
    elif blockers:
        status = "BLOCKED"
    else:
        status = "READY_FOR_AGENT"

    payload = {
        "schema": DECISION_SCHEMA_ID,
        "mission_id": spec["mission_id"],
        "project_id": spec["project_id"],
        "project_state_sha256": state["content_sha256"],
        "delivery_state": state["delivery_state"],
        "next_action": action,
        "status": status,
        "context_domains": context_domains,
        "project_context_sha256": hashlib.sha256(_canonical_json(context).encode("utf-8")).hexdigest(),
        "active_packs": pack_ids,
        "tool_requirements": requirements,
        "tool_bridge": tool_bridge,
        "jit_readiness": jit_results,
        "blockers": blockers,
        "claims": {
            "tool_execution_performed": False,
            "state_advanced_by_decision": False,
            "deployment_performed": False,
            "production_authorization_granted": False,
            "model_assertion_used_as_evidence": False,
        },
    }
    payload["content_sha256"] = _digest(payload)
    validate_decision(payload)
    return payload


def validate_decision(decision: Any) -> dict[str, Any]:
    if not isinstance(decision, dict) or decision.get("schema") != DECISION_SCHEMA_ID:
        raise MissionError("invalid mission decision schema")
    supplied = decision.get("content_sha256")
    if not isinstance(supplied, str) or not re.fullmatch(r"[0-9a-f]{64}", supplied):
        raise MissionError("mission decision missing valid content_sha256")
    unsigned = copy.deepcopy(decision)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != supplied:
        raise MissionError("mission decision content hash mismatch")
    if decision.get("delivery_state") not in DELIVERY_STATES:
        raise MissionError("mission decision contains invalid delivery_state")
    expected_action = ACTIONS_BY_STATE[decision["delivery_state"]]
    if decision.get("next_action") != expected_action:
        raise MissionError("mission decision next_action does not match delivery_state")
    if decision.get("status") not in {"READY_FOR_AGENT", "BLOCKED", "COMPLETE"}:
        raise MissionError("mission decision status is invalid")
    expected_claims = {
        "tool_execution_performed": False,
        "state_advanced_by_decision": False,
        "deployment_performed": False,
        "production_authorization_granted": False,
        "model_assertion_used_as_evidence": False,
    }
    if decision.get("claims") != expected_claims:
        raise MissionError("mission decision contains unsupported execution claims")
    if decision["status"] == "COMPLETE" and decision["delivery_state"] != "POST_DEPLOY_VERIFIED":
        raise MissionError("only POST_DEPLOY_VERIFIED can produce COMPLETE")
    if decision["status"] == "BLOCKED" and not decision.get("blockers"):
        raise MissionError("BLOCKED decision must contain blockers")
    if decision["status"] == "READY_FOR_AGENT" and decision.get("blockers"):
        raise MissionError("READY_FOR_AGENT decision must not contain blockers")
    return decision
