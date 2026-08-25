"""Explicit Codex-harness inventory adapter for Modern SEF M4.

SEF cannot inspect a Codex UI or hidden tool registry from repository code.
Instead the harness supplies a credential-free inventory snapshot. This module
validates that snapshot and converts only explicitly bound surfaces into the
observation contract consumed by :mod:`tool_capabilities.core`.

No model, provider, network, or tool-registry calls are performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from .core import (
    ACCESS,
    AUTHENTICATION,
    AUTHORIZATION,
    AVAILABILITY,
    CAPABILITY_RE,
    EVIDENCE_KIND_RE,
    ITEM_ID_RE,
    SENSITIVITY,
    SOURCE_KINDS,
    ToolCapabilityError,
    validate_document,
)

INVENTORY_SCHEMA_ID = "sef.codex-tool-inventory.v1"
ADAPTER_REPORT_SCHEMA_ID = "sef.codex-tool-inventory-adapter-report.v1"
HARNESS_KIND = "CODEX"
BINDING_KINDS = {"SEF_ADAPTER", "REPOSITORY_CONTRACT", "HARNESS_METADATA"}

ROOT_KEYS = {"schema", "harness", "session_ref", "captured_at", "surfaces", "bindings"}
SURFACE_KEYS = {
    "id",
    "source_kind",
    "tool_name",
    "source_ref",
    "availability",
    "authentication",
    "access",
    "sensitivity",
    "evidence_kinds",
    "evidence_ref",
    "authorization_required",
    "authorization_ref",
}
BINDING_KEYS = {"id", "surface_id", "capability", "binding_kind", "binding_ref"}

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*[^\s,;]{8,}"),
)
TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")


class CodexInventoryError(ToolCapabilityError):
    """Raised when a Codex inventory/binding violates the adapter contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _exact(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise CodexInventoryError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise CodexInventoryError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CodexInventoryError(f"{label} must be a non-empty string")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise CodexInventoryError(f"{label} must be a compact stable identifier")
    return value


def _optional_ref(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _scan_secrets(value: Any, label: str = "root") -> None:
    if isinstance(value, str):
        for pattern in SECRET_PATTERNS:
            if pattern.search(value):
                raise CodexInventoryError(f"credential-shaped secret value detected at {label}")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _scan_secrets(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secrets(child, f"{label}[{index}]")


def _validate_timestamp(value: Any, label: str) -> str:
    # Reuse the strict resolver timestamp contract without exporting internals:
    # a minimal one-requirement/no-observation document validates the timestamp.
    probe = {
        "schema": "sef.tool-capability-observations.v1",
        "resolved_at": value,
        "max_observation_age_seconds": 1,
        "requirements": [
            {
                "id": "REQ-timestamp-probe",
                "capability": "timestamp_probe",
                "access": "READ",
                "sensitivity": "LOCAL",
                "required_evidence_kinds": [],
            }
        ],
        "observations": [],
    }
    try:
        validate_document(probe)
    except ToolCapabilityError as exc:
        raise CodexInventoryError(f"{label}: {exc}") from exc
    return str(value)


def _evidence_kinds(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and EVIDENCE_KIND_RE.fullmatch(item) for item in value
    ):
        raise CodexInventoryError(
            f"{label} must be a list of lowercase snake_case evidence kinds"
        )
    if len(value) != len(set(value)):
        raise CodexInventoryError(f"{label} must not contain duplicates")
    return list(value)


def _validate_surface(value: Any, index: int) -> dict[str, Any]:
    label = f"surfaces[{index}]"
    if not isinstance(value, dict):
        raise CodexInventoryError(f"{label} must be an object")
    _exact(value, SURFACE_KEYS, label)
    _item_id(value["id"], f"{label}.id")
    if value["source_kind"] not in SOURCE_KINDS:
        raise CodexInventoryError(f"{label}.source_kind is invalid")
    if not isinstance(value["tool_name"], str) or not TOOL_NAME_RE.fullmatch(value["tool_name"]):
        raise CodexInventoryError(f"{label}.tool_name must be a compact tool identifier")
    _text(value["source_ref"], f"{label}.source_ref")
    if value["availability"] not in AVAILABILITY:
        raise CodexInventoryError(f"{label}.availability is invalid")
    if value["authentication"] not in AUTHENTICATION:
        raise CodexInventoryError(f"{label}.authentication is invalid")
    if value["access"] not in ACCESS:
        raise CodexInventoryError(f"{label}.access is invalid")
    if value["sensitivity"] not in SENSITIVITY:
        raise CodexInventoryError(f"{label}.sensitivity is invalid")
    _evidence_kinds(value["evidence_kinds"], f"{label}.evidence_kinds")
    _optional_ref(value["evidence_ref"], f"{label}.evidence_ref")
    if value["authorization_required"] not in AUTHORIZATION:
        raise CodexInventoryError(f"{label}.authorization_required is invalid")
    _optional_ref(value["authorization_ref"], f"{label}.authorization_ref")

    if value["availability"] != "UNKNOWN" and value["evidence_ref"] is None:
        raise CodexInventoryError(f"{label}: known availability requires evidence_ref")
    if value["availability"] == "UNAVAILABLE" and value["access"] != "NONE":
        raise CodexInventoryError(f"{label}: unavailable surface must have access NONE")
    if value["availability"] == "UNAVAILABLE" and value["authentication"] == "AUTHENTICATED":
        raise CodexInventoryError(f"{label}: unavailable surface cannot claim authenticated")
    if value["authorization_required"] != "UNKNOWN" and value["authorization_ref"] is None:
        raise CodexInventoryError(f"{label}: known authorization state requires authorization_ref")
    if value["authorization_required"] == "UNKNOWN" and value["authorization_ref"] is not None:
        raise CodexInventoryError(f"{label}: UNKNOWN authorization must not carry authorization_ref")
    return value


def _validate_binding(value: Any, index: int) -> dict[str, Any]:
    label = f"bindings[{index}]"
    if not isinstance(value, dict):
        raise CodexInventoryError(f"{label} must be an object")
    _exact(value, BINDING_KEYS, label)
    _item_id(value["id"], f"{label}.id")
    _item_id(value["surface_id"], f"{label}.surface_id")
    if not isinstance(value["capability"], str) or not CAPABILITY_RE.fullmatch(value["capability"]):
        raise CodexInventoryError(f"{label}.capability must be lowercase snake_case")
    if value["binding_kind"] not in BINDING_KINDS:
        raise CodexInventoryError(
            f"{label}.binding_kind must be one of {sorted(BINDING_KINDS)}; inferred/model-only bindings are not accepted"
        )
    _text(value["binding_ref"], f"{label}.binding_ref")
    return value


def validate_inventory(inventory: Any) -> dict[str, Any]:
    if not isinstance(inventory, dict):
        raise CodexInventoryError("root must be an object")
    _scan_secrets(inventory)
    _exact(inventory, ROOT_KEYS, "root")
    if inventory["schema"] != INVENTORY_SCHEMA_ID:
        raise CodexInventoryError(f"schema must equal {INVENTORY_SCHEMA_ID}")
    if inventory["harness"] != HARNESS_KIND:
        raise CodexInventoryError(f"harness must equal {HARNESS_KIND}")
    _text(inventory["session_ref"], "session_ref")
    _validate_timestamp(inventory["captured_at"], "captured_at")

    if not isinstance(inventory["surfaces"], list):
        raise CodexInventoryError("surfaces must be a list")
    surfaces = [_validate_surface(item, i) for i, item in enumerate(inventory["surfaces"])]
    surface_ids = [item["id"] for item in surfaces]
    if len(surface_ids) != len(set(surface_ids)):
        raise CodexInventoryError("surfaces contain duplicate ids")

    if not isinstance(inventory["bindings"], list):
        raise CodexInventoryError("bindings must be a list")
    bindings = [_validate_binding(item, i) for i, item in enumerate(inventory["bindings"])]
    binding_ids = [item["id"] for item in bindings]
    if len(binding_ids) != len(set(binding_ids)):
        raise CodexInventoryError("bindings contain duplicate ids")

    surface_set = set(surface_ids)
    unknown = sorted({item["surface_id"] for item in bindings} - surface_set)
    if unknown:
        raise CodexInventoryError(f"bindings reference unknown surfaces: {unknown}")

    semantic_bindings = [(item["surface_id"], item["capability"]) for item in bindings]
    if len(semantic_bindings) != len(set(semantic_bindings)):
        raise CodexInventoryError(
            "a surface may bind to a capability only once; duplicate semantic bindings are ambiguous"
        )
    return inventory


def _observation_id(surface_id: str, capability: str, binding_ref: str, captured_at: str) -> str:
    seed = f"{surface_id}\n{capability}\n{binding_ref}\n{captured_at}".encode("utf-8")
    return "OBS-" + hashlib.sha256(seed).hexdigest()[:24]


def adapt_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    """Convert an explicit Codex snapshot into M4 observations.

    Only surfaces with an accepted explicit binding are emitted. Unmapped
    surfaces remain visible in the adapter report, but do not receive guessed
    SEF capabilities.
    """
    validate_inventory(inventory)
    by_surface = {item["id"]: item for item in inventory["surfaces"]}
    observations: list[dict[str, Any]] = []
    binding_records: list[dict[str, Any]] = []

    for binding in sorted(inventory["bindings"], key=lambda item: (item["surface_id"], item["capability"], item["id"])):
        surface = by_surface[binding["surface_id"]]
        observations.append(
            {
                "id": _observation_id(
                    surface["id"], binding["capability"], binding["binding_ref"], inventory["captured_at"]
                ),
                "capability": binding["capability"],
                "surface_id": surface["id"],
                "source_kind": surface["source_kind"],
                "source_ref": surface["source_ref"],
                "observed_at": inventory["captured_at"],
                "availability": surface["availability"],
                "authentication": surface["authentication"],
                "access": surface["access"],
                "sensitivity": surface["sensitivity"],
                "evidence_kinds": sorted(surface["evidence_kinds"]),
                "evidence_ref": surface["evidence_ref"],
                "authorization_required": surface["authorization_required"],
                "authorization_ref": surface["authorization_ref"],
            }
        )
        binding_records.append(
            {
                "binding_id": binding["id"],
                "surface_id": surface["id"],
                "tool_name": surface["tool_name"],
                "capability": binding["capability"],
                "binding_kind": binding["binding_kind"],
                "binding_ref": binding["binding_ref"],
            }
        )

    bound_surface_ids = {item["surface_id"] for item in inventory["bindings"]}
    unmapped = sorted(item["id"] for item in inventory["surfaces"] if item["id"] not in bound_surface_ids)

    # Prove the generated observations satisfy the already-merged M4 contract.
    if observations:
        probe_requirements = []
        seen_caps: set[str] = set()
        for obs in observations:
            if obs["capability"] in seen_caps:
                continue
            seen_caps.add(obs["capability"])
            probe_requirements.append(
                {
                    "id": "REQ-adapter-" + obs["capability"],
                    "capability": obs["capability"],
                    "access": "READ",
                    "sensitivity": "LOCAL",
                    "required_evidence_kinds": [],
                }
            )
        validate_document(
            {
                "schema": "sef.tool-capability-observations.v1",
                "resolved_at": inventory["captured_at"],
                "max_observation_age_seconds": 1,
                "requirements": probe_requirements,
                "observations": observations,
            }
        )

    inventory_hash = _digest(inventory)
    payload = {
        "schema": ADAPTER_REPORT_SCHEMA_ID,
        "harness": HARNESS_KIND,
        "session_ref": inventory["session_ref"],
        "captured_at": inventory["captured_at"],
        "inventory_sha256": inventory_hash,
        "surface_count": len(inventory["surfaces"]),
        "binding_count": len(inventory["bindings"]),
        "observation_count": len(observations),
        "unmapped_surfaces": unmapped,
        "bindings": binding_records,
        "observations": observations,
        "claims": {
            "live_registry_read_by_adapter": False,
            "model_inferred_bindings": False,
            "credential_storage": False,
        },
    }
    payload["content_sha256"] = _digest(payload)
    return payload


def validate_adapter_report(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("schema") != ADAPTER_REPORT_SCHEMA_ID:
        raise CodexInventoryError("invalid adapter report schema")
    supplied = report.get("content_sha256")
    if not isinstance(supplied, str):
        raise CodexInventoryError("adapter report missing content_sha256")
    unsigned = dict(report)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != supplied:
        raise CodexInventoryError("adapter report content hash mismatch")
    if report.get("claims") != {
        "live_registry_read_by_adapter": False,
        "model_inferred_bindings": False,
        "credential_storage": False,
    }:
        raise CodexInventoryError("adapter report contains unsupported claims")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Adapt an explicit Codex tool inventory into SEF M4 observations")
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        report = adapt_inventory(inventory)
    except (OSError, json.JSONDecodeError, CodexInventoryError, ToolCapabilityError) as exc:
        print(
            json.dumps({"schema": ADAPTER_REPORT_SCHEMA_ID, "status": "HARNESS_ERROR", "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
