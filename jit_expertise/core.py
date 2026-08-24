"""Deterministic Just-In-Time Expertise capsule contract.

JIT Expertise does not fetch documentation or call a model. The surrounding
agent/harness already has browser, search, plugins, MCP and repository tools.
This module turns observations from those surfaces into a compact, auditable,
project-bound capsule and can later decide whether that capsule is stale.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping

SCHEMA_ID = "sef.jit-expertise.v1"

SOURCE_TIERS = {
    "REPOSITORY": 0,
    "OFFICIAL": 1,
    "TOOL_SCHEMA": 2,
    "STANDARD": 3,
    "SECONDARY": 4,
}
SUBJECT_KINDS = {"EXTERNAL_PROVIDER", "FRAMEWORK", "REPOSITORY_CONTRACT", "STANDARD"}
SOURCE_STATUSES = {"OBSERVED", "UNAVAILABLE"}
TOOL_AVAILABILITY = {"AVAILABLE", "UNAVAILABLE", "UNAUTHENTICATED"}
TOOL_ACCESS = {"NONE", "READ", "WRITE"}
MATERIALITY = {"MATERIAL", "ADVISORY"}
CAPSULE_STATUSES = {"READY", "REVIEW_REQUIRED", "BLOCKED_SOURCE_GAP", "BLOCKED_TOOL_GAP", "STALE"}

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
PROJECT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CAPABILITY_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

CAPSULE_KEYS = {
    "schema",
    "capsule_id",
    "project_id",
    "mission_need",
    "subject",
    "generated_at",
    "project_context_sha256",
    "tool_snapshot_sha256",
    "sources",
    "constraints",
    "tools",
    "verification_paths",
    "uncertainties",
    "status",
    "content_sha256",
}
SUBJECT_KEYS = {"kind", "name", "version_context"}
SOURCE_KEYS = {
    "id",
    "tier",
    "uri",
    "observed_at",
    "max_age_seconds",
    "content_sha256",
    "subject_version",
    "status",
}
SUPPORT_KEYS = {"source_ref", "anchor"}
CONSTRAINT_KEYS = {"id", "statement", "materiality", "supports"}
TOOL_KEYS = {"capability", "availability", "access", "observed_at"}
VERIFICATION_KEYS = {"id", "description", "required_tools", "supports"}
UNCERTAINTY_KEYS = {"id", "statement", "blocking", "source_refs"}

MAX_SOURCES = 16
MAX_CONSTRAINTS = 64
MAX_TOOLS = 32
MAX_VERIFICATION_PATHS = 32
MAX_UNCERTAINTIES = 32
MAX_STATEMENT_CHARS = 1200
MAX_ANCHOR_CHARS = 320

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\b(?:password|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*[^\s,;]{8,}"),
)


class JITExpertiseError(ValueError):
    pass


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _parse_time(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise JITExpertiseError(f"{label} must be a non-empty ISO-8601 timestamp")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise JITExpertiseError(f"{label} must be valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise JITExpertiseError(f"{label} must include a timezone")
    return parsed


def _require_exact(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise JITExpertiseError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise JITExpertiseError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _text(value: Any, label: str, *, limit: int = MAX_STATEMENT_CHARS) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JITExpertiseError(f"{label} must be a non-empty string")
    if len(value) > limit:
        raise JITExpertiseError(f"{label} exceeds compactness limit {limit}")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise JITExpertiseError(f"{label} must be a compact stable identifier")
    return value


def _unique_strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise JITExpertiseError(f"{label} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise JITExpertiseError(f"{label} must not contain duplicates")
    return value


def _scan_secrets(value: Any, path: str = "capsule") -> None:
    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise JITExpertiseError(f"credential-shaped secret value detected at {path}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _scan_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secrets(child, f"{path}[{index}]")


def project_context_digest(project_context: Mapping[str, Any]) -> str:
    """Fingerprint only the selected context content, not global state revision.

    M1 project-context slices include global state revision/digest. Excluding those
    fields prevents an unrelated project-state update from invalidating a capsule
    whose selected domains and delivery state did not change.
    """
    if not isinstance(project_context, Mapping):
        raise JITExpertiseError("project_context must be an object")
    required = {"schema", "project_id", "delivery_state", "domains", "evidence"}
    missing = required - set(project_context)
    if missing:
        raise JITExpertiseError(f"project_context missing keys: {sorted(missing)}")
    payload = {key: copy.deepcopy(project_context[key]) for key in sorted(required)}
    return _digest(payload)


def tool_snapshot_digest(tools: Iterable[Mapping[str, Any]]) -> str:
    normalized = [dict(item) for item in tools]
    normalized.sort(key=lambda item: str(item.get("capability", "")))
    return _digest(normalized)


def _source_is_fresh(source: Mapping[str, Any], at: str) -> bool:
    if source["status"] != "OBSERVED":
        return False
    observed = _parse_time(source["observed_at"], "source.observed_at")
    current = _parse_time(at, "freshness.at")
    if observed > current:
        raise JITExpertiseError("source observation cannot be in the future")
    ttl = source["max_age_seconds"]
    if ttl is None:
        return True
    return current <= observed + timedelta(seconds=ttl)


def rank_sources(sources: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rank sources by authority first and recency second."""
    items = [dict(item) for item in sources]
    for item in items:
        if item.get("tier") not in SOURCE_TIERS:
            raise JITExpertiseError(f"unknown source tier: {item.get('tier')}")
        _parse_time(item.get("observed_at"), "source.observed_at")
    return sorted(
        items,
        key=lambda item: (
            SOURCE_TIERS[item["tier"]],
            -_parse_time(item["observed_at"], "source.observed_at").timestamp(),
            item.get("id", ""),
        ),
    )


def _validate_sources(sources: Any, generated_at: str) -> dict[str, dict[str, Any]]:
    if not isinstance(sources, list) or not sources:
        raise JITExpertiseError("sources must be a non-empty list")
    if len(sources) > MAX_SOURCES:
        raise JITExpertiseError(f"sources exceed compactness limit {MAX_SOURCES}")
    by_id: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources):
        label = f"sources[{index}]"
        if not isinstance(source, dict):
            raise JITExpertiseError(f"{label} must be an object")
        _require_exact(source, SOURCE_KEYS, label)
        source_id = _item_id(source["id"], f"{label}.id")
        if source_id in by_id:
            raise JITExpertiseError(f"duplicate source id: {source_id}")
        if source["tier"] not in SOURCE_TIERS:
            raise JITExpertiseError(f"{label}.tier is invalid")
        _text(source["uri"], f"{label}.uri", limit=1200)
        observed = _parse_time(source["observed_at"], f"{label}.observed_at")
        generated = _parse_time(generated_at, "generated_at")
        if observed > generated:
            raise JITExpertiseError(f"{label} observation cannot be later than capsule generation")
        ttl = source["max_age_seconds"]
        if ttl is not None and (not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 0):
            raise JITExpertiseError(f"{label}.max_age_seconds must be null or integer >= 0")
        digest = source["content_sha256"]
        if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
            raise JITExpertiseError(f"{label}.content_sha256 must be null or lowercase SHA-256")
        if source["subject_version"] is not None:
            _text(source["subject_version"], f"{label}.subject_version", limit=200)
        if source["status"] not in SOURCE_STATUSES:
            raise JITExpertiseError(f"{label}.status is invalid")
        by_id[source_id] = source
    return by_id


def _validate_supports(
    supports: Any,
    label: str,
    source_by_id: Mapping[str, Mapping[str, Any]],
    *,
    allow_empty: bool = False,
) -> list[dict[str, str]]:
    if not isinstance(supports, list):
        raise JITExpertiseError(f"{label} must be a list")
    if not supports and not allow_empty:
        raise JITExpertiseError(f"{label} must cite at least one source")
    normalized: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for index, support in enumerate(supports):
        item_label = f"{label}[{index}]"
        if not isinstance(support, dict):
            raise JITExpertiseError(f"{item_label} must be an object")
        _require_exact(support, SUPPORT_KEYS, item_label)
        source_ref = _item_id(support["source_ref"], f"{item_label}.source_ref")
        if source_ref not in source_by_id:
            raise JITExpertiseError(f"{item_label} references unknown source: {source_ref}")
        if source_by_id[source_ref]["status"] != "OBSERVED":
            raise JITExpertiseError(f"{item_label} references unavailable source: {source_ref}")
        anchor = _text(support["anchor"], f"{item_label}.anchor", limit=MAX_ANCHOR_CHARS)
        key = (source_ref, anchor)
        if key in seen:
            raise JITExpertiseError(f"{label} contains duplicate support")
        seen.add(key)
        normalized.append({"source_ref": source_ref, "anchor": anchor})
    return normalized


def _validate_tools(tools: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(tools, list):
        raise JITExpertiseError("tools must be a list")
    if len(tools) > MAX_TOOLS:
        raise JITExpertiseError(f"tools exceed compactness limit {MAX_TOOLS}")
    by_capability: dict[str, dict[str, Any]] = {}
    for index, tool in enumerate(tools):
        label = f"tools[{index}]"
        if not isinstance(tool, dict):
            raise JITExpertiseError(f"{label} must be an object")
        _require_exact(tool, TOOL_KEYS, label)
        capability = tool["capability"]
        if not isinstance(capability, str) or not CAPABILITY_RE.fullmatch(capability):
            raise JITExpertiseError(f"{label}.capability must be lowercase snake_case")
        if capability in by_capability:
            raise JITExpertiseError(f"duplicate tool capability: {capability}")
        if tool["availability"] not in TOOL_AVAILABILITY:
            raise JITExpertiseError(f"{label}.availability is invalid")
        if tool["access"] not in TOOL_ACCESS:
            raise JITExpertiseError(f"{label}.access is invalid")
        if tool["availability"] != "AVAILABLE" and tool["access"] != "NONE":
            raise JITExpertiseError(f"{label} unavailable/unauthenticated tool must have NONE access")
        if tool["availability"] == "AVAILABLE" and tool["access"] == "NONE":
            raise JITExpertiseError(f"{label} available tool must expose READ or WRITE access")
        _parse_time(tool["observed_at"], f"{label}.observed_at")
        by_capability[capability] = tool
    return by_capability


def _subject_source_requirement(kind: str) -> set[str]:
    if kind in {"EXTERNAL_PROVIDER", "FRAMEWORK"}:
        return {"OFFICIAL", "TOOL_SCHEMA"}
    if kind == "REPOSITORY_CONTRACT":
        return {"REPOSITORY"}
    if kind == "STANDARD":
        return {"STANDARD", "OFFICIAL"}
    raise JITExpertiseError(f"unknown subject kind: {kind}")


def _derive_status(capsule: Mapping[str, Any]) -> str:
    generated_at = capsule["generated_at"]
    fresh_observed = [source for source in capsule["sources"] if _source_is_fresh(source, generated_at)]
    required_tiers = _subject_source_requirement(capsule["subject"]["kind"])
    if not any(source["tier"] in required_tiers for source in fresh_observed):
        return "BLOCKED_SOURCE_GAP"

    source_by_id = {source["id"]: source for source in capsule["sources"]}
    used_source_ids: set[str] = set()
    for constraint in capsule["constraints"]:
        used_source_ids.update(support["source_ref"] for support in constraint["supports"])
    for path in capsule["verification_paths"]:
        used_source_ids.update(support["source_ref"] for support in path["supports"])
    for uncertainty in capsule["uncertainties"]:
        used_source_ids.update(uncertainty["source_refs"])
    if any(not _source_is_fresh(source_by_id[source_id], generated_at) for source_id in used_source_ids):
        return "STALE"

    tool_by_cap = {tool["capability"]: tool for tool in capsule["tools"]}
    for path in capsule["verification_paths"]:
        for capability in path["required_tools"]:
            tool = tool_by_cap.get(capability)
            if tool is None or tool["availability"] != "AVAILABLE" or tool["access"] == "NONE":
                return "BLOCKED_TOOL_GAP"

    if any(item["blocking"] for item in capsule["uncertainties"]):
        return "REVIEW_REQUIRED"
    return "READY"


def _capsule_digest(capsule: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(capsule))
    payload.pop("content_sha256", None)
    return _digest(payload)


def validate_capsule(capsule: dict[str, Any], *, verify_digest: bool = True) -> dict[str, Any]:
    if not isinstance(capsule, dict):
        raise JITExpertiseError("capsule root must be an object")
    _require_exact(capsule, CAPSULE_KEYS, "capsule")
    if capsule["schema"] != SCHEMA_ID:
        raise JITExpertiseError(f"capsule.schema must equal {SCHEMA_ID}")
    _item_id(capsule["capsule_id"], "capsule_id")
    if not isinstance(capsule["project_id"], str) or not PROJECT_ID_RE.fullmatch(capsule["project_id"]):
        raise JITExpertiseError("project_id must be lowercase kebab-case")
    _text(capsule["mission_need"], "mission_need", limit=800)
    _parse_time(capsule["generated_at"], "generated_at")
    for digest_field in ("project_context_sha256", "tool_snapshot_sha256", "content_sha256"):
        value = capsule[digest_field]
        if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
            raise JITExpertiseError(f"{digest_field} must be lowercase SHA-256")

    subject = capsule["subject"]
    if not isinstance(subject, dict):
        raise JITExpertiseError("subject must be an object")
    _require_exact(subject, SUBJECT_KEYS, "subject")
    if subject["kind"] not in SUBJECT_KINDS:
        raise JITExpertiseError("subject.kind is invalid")
    _text(subject["name"], "subject.name", limit=300)
    if subject["version_context"] is not None:
        _text(subject["version_context"], "subject.version_context", limit=200)

    _scan_secrets(capsule)
    source_by_id = _validate_sources(capsule["sources"], capsule["generated_at"])
    tool_by_cap = _validate_tools(capsule["tools"])

    constraints = capsule["constraints"]
    if not isinstance(constraints, list) or not constraints:
        raise JITExpertiseError("constraints must be a non-empty list")
    if len(constraints) > MAX_CONSTRAINTS:
        raise JITExpertiseError(f"constraints exceed compactness limit {MAX_CONSTRAINTS}")
    constraint_ids: set[str] = set()
    for index, constraint in enumerate(constraints):
        label = f"constraints[{index}]"
        if not isinstance(constraint, dict):
            raise JITExpertiseError(f"{label} must be an object")
        _require_exact(constraint, CONSTRAINT_KEYS, label)
        constraint_id = _item_id(constraint["id"], f"{label}.id")
        if constraint_id in constraint_ids:
            raise JITExpertiseError(f"duplicate constraint id: {constraint_id}")
        constraint_ids.add(constraint_id)
        _text(constraint["statement"], f"{label}.statement")
        if constraint["materiality"] not in MATERIALITY:
            raise JITExpertiseError(f"{label}.materiality is invalid")
        supports = _validate_supports(constraint["supports"], f"{label}.supports", source_by_id)
        if constraint["materiality"] == "MATERIAL":
            tiers = {source_by_id[support["source_ref"]]["tier"] for support in supports}
            if tiers <= {"SECONDARY"}:
                raise JITExpertiseError(f"{label} MATERIAL constraint cannot rely only on secondary sources")

    verification_paths = capsule["verification_paths"]
    if not isinstance(verification_paths, list):
        raise JITExpertiseError("verification_paths must be a list")
    if len(verification_paths) > MAX_VERIFICATION_PATHS:
        raise JITExpertiseError(f"verification_paths exceed compactness limit {MAX_VERIFICATION_PATHS}")
    verification_ids: set[str] = set()
    for index, path in enumerate(verification_paths):
        label = f"verification_paths[{index}]"
        if not isinstance(path, dict):
            raise JITExpertiseError(f"{label} must be an object")
        _require_exact(path, VERIFICATION_KEYS, label)
        path_id = _item_id(path["id"], f"{label}.id")
        if path_id in verification_ids:
            raise JITExpertiseError(f"duplicate verification path id: {path_id}")
        verification_ids.add(path_id)
        _text(path["description"], f"{label}.description")
        required_tools = _unique_strings(path["required_tools"], f"{label}.required_tools")
        for capability in required_tools:
            if not CAPABILITY_RE.fullmatch(capability):
                raise JITExpertiseError(f"{label} invalid tool capability: {capability}")
        _validate_supports(path["supports"], f"{label}.supports", source_by_id, allow_empty=True)

    uncertainties = capsule["uncertainties"]
    if not isinstance(uncertainties, list):
        raise JITExpertiseError("uncertainties must be a list")
    if len(uncertainties) > MAX_UNCERTAINTIES:
        raise JITExpertiseError(f"uncertainties exceed compactness limit {MAX_UNCERTAINTIES}")
    uncertainty_ids: set[str] = set()
    for index, uncertainty in enumerate(uncertainties):
        label = f"uncertainties[{index}]"
        if not isinstance(uncertainty, dict):
            raise JITExpertiseError(f"{label} must be an object")
        _require_exact(uncertainty, UNCERTAINTY_KEYS, label)
        uncertainty_id = _item_id(uncertainty["id"], f"{label}.id")
        if uncertainty_id in uncertainty_ids:
            raise JITExpertiseError(f"duplicate uncertainty id: {uncertainty_id}")
        uncertainty_ids.add(uncertainty_id)
        _text(uncertainty["statement"], f"{label}.statement")
        if not isinstance(uncertainty["blocking"], bool):
            raise JITExpertiseError(f"{label}.blocking must be boolean")
        refs = _unique_strings(uncertainty["source_refs"], f"{label}.source_refs")
        missing = [ref for ref in refs if ref not in source_by_id]
        if missing:
            raise JITExpertiseError(f"{label} references unknown sources: {missing}")

    if tool_snapshot_digest(capsule["tools"]) != capsule["tool_snapshot_sha256"]:
        raise JITExpertiseError("tool_snapshot_sha256 does not match tools")

    derived = _derive_status(capsule)
    if capsule["status"] != derived:
        raise JITExpertiseError(f"capsule.status must be derived status {derived}")

    if verify_digest:
        observed = _capsule_digest(capsule)
        if observed != capsule["content_sha256"]:
            raise JITExpertiseError(
                f"capsule digest mismatch: expected {capsule['content_sha256']} observed {observed}"
            )
    return capsule


def compile_capsule(
    *,
    capsule_id: str,
    project_id: str,
    mission_need: str,
    subject: Mapping[str, Any],
    generated_at: str,
    project_context: Mapping[str, Any],
    sources: Iterable[Mapping[str, Any]],
    constraints: Iterable[Mapping[str, Any]],
    tools: Iterable[Mapping[str, Any]],
    verification_paths: Iterable[Mapping[str, Any]],
    uncertainties: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Compile observations into a sealed capsule; no fetching/synthesis occurs here."""
    source_list = [copy.deepcopy(dict(item)) for item in sources]
    constraint_list = [copy.deepcopy(dict(item)) for item in constraints]
    tool_list = [copy.deepcopy(dict(item)) for item in tools]
    verification_list = [copy.deepcopy(dict(item)) for item in verification_paths]
    uncertainty_list = [copy.deepcopy(dict(item)) for item in uncertainties]

    if project_context.get("project_id") != project_id:
        raise JITExpertiseError("project_context project_id does not match capsule project_id")

    capsule = {
        "schema": SCHEMA_ID,
        "capsule_id": capsule_id,
        "project_id": project_id,
        "mission_need": mission_need,
        "subject": copy.deepcopy(dict(subject)),
        "generated_at": generated_at,
        "project_context_sha256": project_context_digest(project_context),
        "tool_snapshot_sha256": tool_snapshot_digest(tool_list),
        "sources": source_list,
        "constraints": constraint_list,
        "tools": tool_list,
        "verification_paths": verification_list,
        "uncertainties": uncertainty_list,
        "status": "READY",
        "content_sha256": "0" * 64,
    }

    # Validate structure before deriving status. We temporarily derive using the
    # same deterministic logic, then seal and validate the final capsule.
    capsule["status"] = _derive_status(capsule)
    capsule["content_sha256"] = _capsule_digest(capsule)
    validate_capsule(capsule)
    return capsule


def evaluate_invalidation(
    capsule: Mapping[str, Any],
    *,
    now: str,
    project_context: Mapping[str, Any],
    tools: Iterable[Mapping[str, Any]],
    current_source_digests: Mapping[str, str | None] | None = None,
) -> list[str]:
    """Return deterministic reasons a previously valid capsule must be rebuilt."""
    value = copy.deepcopy(dict(capsule))
    validate_capsule(value)
    reasons: list[str] = []

    if project_context_digest(project_context) != value["project_context_sha256"]:
        reasons.append("PROJECT_CONTEXT_CHANGED")
    if tool_snapshot_digest(tools) != value["tool_snapshot_sha256"]:
        reasons.append("TOOL_CAPABILITY_CHANGED")

    for source in value["sources"]:
        if source["status"] == "OBSERVED" and not _source_is_fresh(source, now):
            reasons.append(f"SOURCE_EXPIRED:{source['id']}")

    if current_source_digests is not None:
        for source in value["sources"]:
            expected = source["content_sha256"]
            if expected is None or source["id"] not in current_source_digests:
                continue
            observed = current_source_digests[source["id"]]
            if observed != expected:
                reasons.append(f"SOURCE_CHANGED:{source['id']}")

    return sorted(set(reasons))
