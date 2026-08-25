"""Harness-neutral tool capability resolution for Modern SEF M4.

This module normalizes evidence-backed observations from agent-native tool
surfaces (built-ins, MCP, functions, CLI/project tooling) and resolves whether
a requested capability is actually usable. It performs no provider/model calls
and stores no credentials.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any, Mapping

SCHEMA_ID = "sef.tool-capability-observations.v1"
REPORT_SCHEMA_ID = "sef.tool-capability-resolution.v1"

SOURCE_KINDS = {"BUILTIN", "MCP", "FUNCTION", "CLI", "PROJECT"}
AVAILABILITY = {"AVAILABLE", "UNAVAILABLE", "UNKNOWN"}
AUTHENTICATION = {"AUTHENTICATED", "UNAUTHENTICATED", "NOT_APPLICABLE", "UNKNOWN"}
ACCESS = {"NONE", "READ", "WRITE"}
SENSITIVITY = {"LOCAL", "SANDBOX", "PRODUCTION_SENSITIVE"}
AUTHORIZATION = {"REQUIRED", "NOT_REQUIRED", "UNKNOWN"}
RESOLUTION_STATUSES = {
    "READY",
    "AUTHORIZATION_REQUIRED",
    "AUTHORIZATION_UNKNOWN",
    "UNAVAILABLE",
    "UNAUTHENTICATED",
    "INSUFFICIENT_ACCESS",
    "INSUFFICIENT_SCOPE",
    "INSUFFICIENT_EVIDENCE",
    "UNKNOWN",
    "CONFLICT",
}

CAPABILITY_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
EVIDENCE_KIND_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*[^\s,;]{8,}"),
)

SOURCE_PRIORITY = {"BUILTIN": 0, "MCP": 1, "FUNCTION": 2, "CLI": 3, "PROJECT": 4}
ACCESS_RANK = {"NONE": 0, "READ": 1, "WRITE": 2}
SENSITIVITY_RANK = {"LOCAL": 0, "SANDBOX": 1, "PRODUCTION_SENSITIVE": 2}

OBSERVATION_KEYS = {
    "id",
    "capability",
    "surface_id",
    "source_kind",
    "source_ref",
    "observed_at",
    "availability",
    "authentication",
    "access",
    "sensitivity",
    "evidence_kinds",
    "evidence_ref",
    "authorization_required",
    "authorization_ref",
}
REQUIREMENT_KEYS = {"id", "capability", "access", "sensitivity", "required_evidence_kinds"}
ROOT_KEYS = {"schema", "resolved_at", "max_observation_age_seconds", "requirements", "observations"}


class ToolCapabilityError(ValueError):
    """Raised when a tool-capability document violates the M4 contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise ToolCapabilityError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ToolCapabilityError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolCapabilityError(f"{label} must be a non-empty string")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise ToolCapabilityError(f"{label} must be a compact stable identifier")
    return value


def _capability(value: Any, label: str) -> str:
    if not isinstance(value, str) or not CAPABILITY_RE.fullmatch(value):
        raise ToolCapabilityError(f"{label} must be lowercase snake_case")
    return value


def _optional_ref(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _parse_time(value: Any, label: str) -> datetime:
    text = _text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ToolCapabilityError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ToolCapabilityError(f"{label} must include a timezone offset")
    return parsed


def _scan_secrets(value: Any, label: str = "root") -> None:
    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise ToolCapabilityError(f"credential-shaped secret value detected at {label}")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _scan_secrets(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secrets(child, f"{label}[{index}]")


def _evidence_kinds(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and EVIDENCE_KIND_RE.fullmatch(item) for item in value):
        raise ToolCapabilityError(f"{label} must be a list of lowercase snake_case evidence kinds")
    if len(value) != len(set(value)):
        raise ToolCapabilityError(f"{label} must not contain duplicates")
    return list(value)


def _validate_requirement(value: Any, index: int) -> dict[str, Any]:
    label = f"requirements[{index}]"
    if not isinstance(value, dict):
        raise ToolCapabilityError(f"{label} must be an object")
    _exact(value, REQUIREMENT_KEYS, label)
    _item_id(value["id"], f"{label}.id")
    _capability(value["capability"], f"{label}.capability")
    if value["access"] not in {"READ", "WRITE"}:
        raise ToolCapabilityError(f"{label}.access must be READ or WRITE")
    if value["sensitivity"] not in SENSITIVITY:
        raise ToolCapabilityError(f"{label}.sensitivity is invalid")
    _evidence_kinds(value["required_evidence_kinds"], f"{label}.required_evidence_kinds")
    return value


def _validate_observation(value: Any, index: int) -> dict[str, Any]:
    label = f"observations[{index}]"
    if not isinstance(value, dict):
        raise ToolCapabilityError(f"{label} must be an object")
    _exact(value, OBSERVATION_KEYS, label)
    _item_id(value["id"], f"{label}.id")
    _capability(value["capability"], f"{label}.capability")
    _item_id(value["surface_id"], f"{label}.surface_id")
    if value["source_kind"] not in SOURCE_KINDS:
        raise ToolCapabilityError(f"{label}.source_kind is invalid")
    _text(value["source_ref"], f"{label}.source_ref")
    _parse_time(value["observed_at"], f"{label}.observed_at")
    if value["availability"] not in AVAILABILITY:
        raise ToolCapabilityError(f"{label}.availability is invalid")
    if value["authentication"] not in AUTHENTICATION:
        raise ToolCapabilityError(f"{label}.authentication is invalid")
    if value["access"] not in ACCESS:
        raise ToolCapabilityError(f"{label}.access is invalid")
    if value["sensitivity"] not in SENSITIVITY:
        raise ToolCapabilityError(f"{label}.sensitivity is invalid")
    kinds = _evidence_kinds(value["evidence_kinds"], f"{label}.evidence_kinds")
    _optional_ref(value["evidence_ref"], f"{label}.evidence_ref")
    if value["authorization_required"] not in AUTHORIZATION:
        raise ToolCapabilityError(f"{label}.authorization_required is invalid")
    _optional_ref(value["authorization_ref"], f"{label}.authorization_ref")

    if value["availability"] != "UNKNOWN" and value["evidence_ref"] is None:
        raise ToolCapabilityError(f"{label}: known availability requires evidence_ref")
    positive = (
        value["authentication"] == "AUTHENTICATED"
        or value["access"] in {"READ", "WRITE"}
        or bool(kinds)
    )
    if positive and value["evidence_ref"] is None:
        raise ToolCapabilityError(f"{label}: positive capability claims require evidence_ref")
    if value["authorization_required"] != "UNKNOWN" and value["authorization_ref"] is None:
        raise ToolCapabilityError(f"{label}: known authorization state requires authorization_ref")
    if value["authorization_required"] == "UNKNOWN" and value["authorization_ref"] is not None:
        raise ToolCapabilityError(f"{label}: UNKNOWN authorization must not carry authorization_ref")
    if value["availability"] == "UNAVAILABLE" and value["access"] != "NONE":
        raise ToolCapabilityError(f"{label}: unavailable surface must have access NONE")
    if value["availability"] == "UNAVAILABLE" and value["authentication"] == "AUTHENTICATED":
        raise ToolCapabilityError(f"{label}: unavailable surface cannot claim authenticated")
    return value


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ToolCapabilityError("root must be an object")
    _scan_secrets(document)
    _exact(document, ROOT_KEYS, "root")
    if document["schema"] != SCHEMA_ID:
        raise ToolCapabilityError(f"schema must equal {SCHEMA_ID}")
    resolved_at = _parse_time(document["resolved_at"], "resolved_at")
    max_age = document["max_observation_age_seconds"]
    if not isinstance(max_age, int) or isinstance(max_age, bool) or not 1 <= max_age <= 86400:
        raise ToolCapabilityError("max_observation_age_seconds must be integer between 1 and 86400")
    if not isinstance(document["requirements"], list) or not document["requirements"]:
        raise ToolCapabilityError("requirements must be a non-empty list")
    requirements = [_validate_requirement(item, i) for i, item in enumerate(document["requirements"])]
    requirement_ids = [item["id"] for item in requirements]
    if len(requirement_ids) != len(set(requirement_ids)):
        raise ToolCapabilityError("requirements contain duplicate ids")
    if not isinstance(document["observations"], list):
        raise ToolCapabilityError("observations must be a list")
    observations = [_validate_observation(item, i) for i, item in enumerate(document["observations"])]
    observation_ids = [item["id"] for item in observations]
    if len(observation_ids) != len(set(observation_ids)):
        raise ToolCapabilityError("observations contain duplicate ids")
    future = [item["id"] for item in observations if _parse_time(item["observed_at"], "observed_at") > resolved_at]
    if future:
        raise ToolCapabilityError(f"observations must not be newer than resolved_at: {sorted(future)}")
    return document


def _observation_state(observation: dict[str, Any]) -> dict[str, Any]:
    """Return semantic surface state without record identity."""
    return {key: value for key, value in observation.items() if key != "id"}


def _latest_surfaces(
    observations: list[dict[str, Any]], resolved_at: datetime, max_age_seconds: int
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Collapse history per capability/surface and reject stale/tied latest state."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for obs in observations:
        grouped.setdefault((obs["capability"], obs["surface_id"]), []).append(obs)

    latest: list[dict[str, Any]] = []
    conflicts: list[str] = []
    stale: list[str] = []
    for (capability, surface_id), items in sorted(grouped.items()):
        newest_time = max(_parse_time(item["observed_at"], "observed_at") for item in items)
        surface_key = f"{capability}:{surface_id}"
        age_seconds = (resolved_at - newest_time).total_seconds()
        if age_seconds > max_age_seconds:
            stale.append(surface_key)
            continue
        newest = [item for item in items if _parse_time(item["observed_at"], "observed_at") == newest_time]
        normalized = {_canonical_json(_observation_state(item)) for item in newest}
        if len(normalized) > 1:
            conflicts.append(surface_key)
            continue
        latest.append(sorted(newest, key=lambda item: item["id"])[0])
    return latest, conflicts, stale


def _candidate_sort_key(obs: dict[str, Any], requirement: dict[str, Any]) -> tuple[int, int, int, str]:
    scope_excess = SENSITIVITY_RANK[obs["sensitivity"]] - SENSITIVITY_RANK[requirement["sensitivity"]]
    access_excess = ACCESS_RANK[obs["access"]] - ACCESS_RANK[requirement["access"]]
    return (scope_excess, access_excess, SOURCE_PRIORITY[obs["source_kind"]], obs["surface_id"])


def _technical_fit(obs: dict[str, Any], requirement: dict[str, Any]) -> bool:
    return (
        obs["availability"] == "AVAILABLE"
        and obs["authentication"] in {"AUTHENTICATED", "NOT_APPLICABLE"}
        and ACCESS_RANK[obs["access"]] >= ACCESS_RANK[requirement["access"]]
        and SENSITIVITY_RANK[obs["sensitivity"]] >= SENSITIVITY_RANK[requirement["sensitivity"]]
        and set(requirement["required_evidence_kinds"]).issubset(set(obs["evidence_kinds"]))
    )


def _blocked_status(
    observations: list[dict[str, Any]], requirement: dict[str, Any], has_conflict: bool, has_stale: bool
) -> tuple[str, list[str]]:
    if has_conflict:
        return "CONFLICT", ["LATEST_SURFACE_OBSERVATIONS_CONFLICT"]
    if not observations:
        if has_stale:
            return "UNKNOWN", ["ONLY_STALE_OBSERVATIONS"]
        return "UNKNOWN", ["NO_OBSERVATION"]
    if all(item["availability"] == "UNAVAILABLE" for item in observations):
        return "UNAVAILABLE", ["ALL_OBSERVED_SURFACES_UNAVAILABLE"]
    available = [item for item in observations if item["availability"] == "AVAILABLE"]
    if not available:
        return "UNKNOWN", ["AVAILABILITY_NOT_PROVEN"]
    authenticated = [item for item in available if item["authentication"] in {"AUTHENTICATED", "NOT_APPLICABLE"}]
    if not authenticated:
        return "UNAUTHENTICATED", ["NO_AVAILABLE_AUTHENTICATED_SURFACE"]
    access_fit = [item for item in authenticated if ACCESS_RANK[item["access"]] >= ACCESS_RANK[requirement["access"]]]
    if not access_fit:
        return "INSUFFICIENT_ACCESS", ["NO_SURFACE_MEETS_REQUIRED_ACCESS"]
    scope_fit = [item for item in access_fit if SENSITIVITY_RANK[item["sensitivity"]] >= SENSITIVITY_RANK[requirement["sensitivity"]]]
    if not scope_fit:
        return "INSUFFICIENT_SCOPE", ["NO_SURFACE_MEETS_REQUIRED_SENSITIVITY"]
    evidence_fit = [
        item for item in scope_fit
        if set(requirement["required_evidence_kinds"]).issubset(set(item["evidence_kinds"]))
    ]
    if not evidence_fit:
        return "INSUFFICIENT_EVIDENCE", ["NO_SURFACE_CAN_OBTAIN_REQUIRED_EVIDENCE"]
    return "UNKNOWN", ["NO_SELECTABLE_SURFACE"]


def resolve(document: dict[str, Any]) -> dict[str, Any]:
    validate_document(document)
    resolved_at = _parse_time(document["resolved_at"], "resolved_at")
    latest, conflicts, stale = _latest_surfaces(
        document["observations"], resolved_at, document["max_observation_age_seconds"]
    )
    results: list[dict[str, Any]] = []

    for requirement in document["requirements"]:
        capability = requirement["capability"]
        relevant = [item for item in latest if item["capability"] == capability]
        cap_conflicts = [item for item in conflicts if item.startswith(capability + ":")]
        cap_stale = [item for item in stale if item.startswith(capability + ":")]
        fitting = [item for item in relevant if _technical_fit(item, requirement)]

        # A conflict on one surface does not block an independent, fully evidenced
        # alternative surface. If no usable alternative exists, conflict wins over
        # weaker diagnoses because the disputed latest state could change the result.
        if fitting:
            selected = sorted(fitting, key=lambda item: _candidate_sort_key(item, requirement))[0]
            if selected["authorization_required"] == "REQUIRED":
                status = "AUTHORIZATION_REQUIRED"
                reasons = ["TECHNICALLY_READY_HUMAN_AUTHORIZATION_REQUIRED"]
            elif selected["authorization_required"] == "UNKNOWN":
                status = "AUTHORIZATION_UNKNOWN"
                reasons = ["TECHNICALLY_READY_AUTHORIZATION_STATE_UNKNOWN"]
            else:
                status = "READY"
                reasons = ["TECHNICALLY_AND_AUTHORIZATION_READY"]
            result = {
                "requirement_id": requirement["id"],
                "capability": capability,
                "status": status,
                "selected_surface_id": selected["surface_id"],
                "selected_source_kind": selected["source_kind"],
                "access": selected["access"],
                "sensitivity": selected["sensitivity"],
                "authentication": selected["authentication"],
                "authorization_required": selected["authorization_required"],
                "evidence_kinds": sorted(selected["evidence_kinds"]),
                "evidence_ref": selected["evidence_ref"],
                "authorization_ref": selected["authorization_ref"],
                "reasons": reasons,
                "conflicting_surfaces": sorted(cap_conflicts),
                "stale_surfaces": sorted(cap_stale),
            }
        else:
            status, reasons = _blocked_status(relevant, requirement, bool(cap_conflicts), bool(cap_stale))
            result = {
                "requirement_id": requirement["id"],
                "capability": capability,
                "status": status,
                "selected_surface_id": None,
                "selected_source_kind": None,
                "access": None,
                "sensitivity": None,
                "authentication": None,
                "authorization_required": None,
                "evidence_kinds": [],
                "evidence_ref": None,
                "authorization_ref": None,
                "reasons": reasons,
                "conflicting_surfaces": sorted(cap_conflicts),
                "stale_surfaces": sorted(cap_stale),
            }
        results.append(result)

    payload = {
        "schema": REPORT_SCHEMA_ID,
        "resolved_at": document["resolved_at"],
        "max_observation_age_seconds": document["max_observation_age_seconds"],
        "status": "READY" if all(item["status"] == "READY" for item in results) else "ATTENTION_REQUIRED",
        "requirement_count": len(document["requirements"]),
        "resolved_count": sum(item["selected_surface_id"] is not None for item in results),
        "ready_count": sum(item["status"] == "READY" for item in results),
        "authorization_required_count": sum(item["status"] == "AUTHORIZATION_REQUIRED" for item in results),
        "authorization_unknown_count": sum(item["status"] == "AUTHORIZATION_UNKNOWN" for item in results),
        "surface_conflicts": sorted(conflicts),
        "stale_surfaces": sorted(stale),
        "results": results,
    }
    payload["content_sha256"] = _digest(payload)
    return payload


def validate_resolution(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMA_ID:
        raise ToolCapabilityError("invalid resolution schema")
    supplied = report.get("content_sha256")
    if not isinstance(supplied, str):
        raise ToolCapabilityError("resolution missing content_sha256")
    unsigned = dict(report)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != supplied:
        raise ToolCapabilityError("resolution content hash mismatch")
    for item in report.get("results", []):
        if item.get("status") not in RESOLUTION_STATUSES:
            raise ToolCapabilityError("resolution contains invalid status")
    return report
