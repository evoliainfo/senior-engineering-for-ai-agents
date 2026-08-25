"""Compose the Codex inventory adapter with the M4 capability resolver.

The harness owns discovery of its actual exposed tools. This bridge accepts that
explicit snapshot plus mission/pack requirements and returns both the adapter
provenance report and the M4 resolution. It performs no hidden discovery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from .codex_adapter import CodexInventoryError, adapt_inventory, validate_adapter_report
from .core import ToolCapabilityError, resolve, validate_resolution

BRIDGE_SCHEMA_ID = "sef.codex-tool-capability-bridge.v1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _requirements(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, dict) and set(value) == {"requirements"}:
        items = value["requirements"]
    else:
        raise CodexInventoryError("requirements input must be a list or an object containing only requirements")
    if not isinstance(items, list) or not items:
        raise CodexInventoryError("requirements must be a non-empty list")
    if not all(isinstance(item, dict) for item in items):
        raise CodexInventoryError("each requirement must be an object")
    return items


def resolve_codex_inventory(
    inventory: dict[str, Any],
    requirements: Any,
    *,
    max_observation_age_seconds: int = 300,
) -> dict[str, Any]:
    """Adapt a harness snapshot and resolve mission requirements in one call."""
    adapter_report = adapt_inventory(inventory)
    validate_adapter_report(adapter_report)
    requirement_items = _requirements(requirements)
    resolution_document = {
        "schema": "sef.tool-capability-observations.v1",
        "resolved_at": inventory["captured_at"],
        "max_observation_age_seconds": max_observation_age_seconds,
        "requirements": requirement_items,
        "observations": adapter_report["observations"],
    }
    resolution = resolve(resolution_document)
    validate_resolution(resolution)
    payload = {
        "schema": BRIDGE_SCHEMA_ID,
        "harness": "CODEX",
        "session_ref": inventory["session_ref"],
        "adapter_report": adapter_report,
        "resolution": resolution,
        "claims": {
            "inventory_supplied_by_harness": True,
            "hidden_registry_introspection": False,
            "model_inferred_bindings": False,
            "credential_storage": False,
        },
    }
    payload["content_sha256"] = _digest(payload)
    return payload


def validate_bridge_report(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict) or report.get("schema") != BRIDGE_SCHEMA_ID:
        raise CodexInventoryError("invalid bridge report schema")
    supplied = report.get("content_sha256")
    if not isinstance(supplied, str):
        raise CodexInventoryError("bridge report missing content_sha256")
    unsigned = dict(report)
    unsigned.pop("content_sha256", None)
    if _digest(unsigned) != supplied:
        raise CodexInventoryError("bridge report content hash mismatch")
    validate_adapter_report(report.get("adapter_report"))
    validate_resolution(report.get("resolution"))
    expected_claims = {
        "inventory_supplied_by_harness": True,
        "hidden_registry_introspection": False,
        "model_inferred_bindings": False,
        "credential_storage": False,
    }
    if report.get("claims") != expected_claims:
        raise CodexInventoryError("bridge report contains unsupported claims")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Resolve SEF tool requirements from an explicit Codex harness inventory"
    )
    parser.add_argument("inventory", type=Path)
    parser.add_argument("requirements", type=Path)
    parser.add_argument("--max-age", type=int, default=300)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        requirements = json.loads(args.requirements.read_text(encoding="utf-8"))
        report = resolve_codex_inventory(
            inventory,
            requirements,
            max_observation_age_seconds=args.max_age,
        )
    except (OSError, json.JSONDecodeError, CodexInventoryError, ToolCapabilityError) as exc:
        print(
            json.dumps({"schema": BRIDGE_SCHEMA_ID, "status": "HARNESS_ERROR", "error": str(exc)}, indent=2),
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
