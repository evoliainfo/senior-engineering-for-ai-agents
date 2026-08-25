#!/usr/bin/env python3
"""Deterministic qualification for the explicit Codex tool-inventory adapter."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tool_capabilities.codex_adapter import (  # noqa: E402
    CodexInventoryError,
    adapt_inventory,
    validate_adapter_report,
    validate_inventory,
)
from tool_capabilities.codex_bridge import (  # noqa: E402
    resolve_codex_inventory,
    validate_bridge_report,
)
from tool_capabilities.core import ToolCapabilityError, resolve, validate_document  # noqa: E402

INVENTORY_PATH = ROOT / "tool_capabilities" / "fixtures" / "codex-inventory.json"
REQUIREMENTS_PATH = ROOT / "tool_capabilities" / "fixtures" / "codex-requirements.json"
REPORT_PATH = ROOT / "eval-results" / "codex-inventory-adapter-m4-report.json"


def _inventory() -> dict:
    return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))


def _requirements() -> dict:
    return json.loads(REQUIREMENTS_PATH.read_text(encoding="utf-8"))


def _surface(document: dict, surface_id: str) -> dict:
    return next(item for item in document["surfaces"] if item["id"] == surface_id)


def _result(report: dict, capability: str) -> dict:
    return next(item for item in report["resolution"]["results"] if item["capability"] == capability)


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except (CodexInventoryError, ToolCapabilityError) as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected adapter error")


def control_valid_inventory_adapts() -> dict:
    report = adapt_inventory(_inventory())
    validate_adapter_report(report)
    assert report["surface_count"] == 4
    assert report["binding_count"] == 3
    assert report["observation_count"] == 3
    assert report["unmapped_surfaces"] == ["builtin-web-search"]
    return {"observations": report["observation_count"], "unmapped": report["unmapped_surfaces"]}


def control_bridge_end_to_end() -> dict:
    report = resolve_codex_inventory(_inventory(), _requirements())
    validate_bridge_report(report)
    assert _result(report, "browser")["status"] == "READY"
    assert _result(report, "visual_capture")["status"] == "READY"
    assert _result(report, "hosting")["status"] == "AUTHORIZATION_REQUIRED"
    assert report["resolution"]["status"] == "ATTENTION_REQUIRED"
    return {
        "browser": _result(report, "browser")["status"],
        "visual": _result(report, "visual_capture")["status"],
        "hosting": _result(report, "hosting")["status"],
    }


def control_unmapped_surface_never_becomes_observation() -> dict:
    report = adapt_inventory(_inventory())
    assert all(item["surface_id"] != "builtin-web-search" for item in report["observations"])
    assert "builtin-web-search" in report["unmapped_surfaces"]
    return {"unmapped": report["unmapped_surfaces"]}


def control_binding_provenance_preserved() -> dict:
    report = adapt_inventory(_inventory())
    hosting = next(item for item in report["bindings"] if item["capability"] == "hosting")
    assert hosting["binding_kind"] == "REPOSITORY_CONTRACT"
    assert hosting["binding_ref"] == "repo-contract://tools/hosting-deploy"
    return {"kind": hosting["binding_kind"], "ref": hosting["binding_ref"]}


def control_surface_state_preserved() -> dict:
    report = adapt_inventory(_inventory())
    hosting = next(item for item in report["observations"] if item["capability"] == "hosting")
    assert hosting["authentication"] == "AUTHENTICATED"
    assert hosting["access"] == "WRITE"
    assert hosting["sensitivity"] == "PRODUCTION_SENSITIVE"
    assert hosting["authorization_required"] == "REQUIRED"
    return {"access": hosting["access"], "authorization": hosting["authorization_required"]}


def control_source_and_evidence_refs_preserved() -> dict:
    report = adapt_inventory(_inventory())
    browser = next(item for item in report["observations"] if item["capability"] == "browser")
    assert browser["source_ref"] == "tool-schema://codex/builtin/browser"
    assert browser["evidence_ref"] == "inventory-evidence://codex/builtin/browser"
    return {"source_ref": browser["source_ref"], "evidence_ref": browser["evidence_ref"]}


def control_capture_time_becomes_observed_time() -> dict:
    inventory = _inventory()
    report = adapt_inventory(inventory)
    assert all(item["observed_at"] == inventory["captured_at"] for item in report["observations"])
    return {"observed_at": inventory["captured_at"]}


def control_one_surface_can_bind_multiple_capabilities() -> dict:
    inventory = _inventory()
    inventory["bindings"].append(
        {
            "id": "BIND-browser-visual",
            "surface_id": "builtin-browser",
            "capability": "visual_capture",
            "binding_kind": "SEF_ADAPTER",
            "binding_ref": "sef-binding://codex/browser-to-visual/v1",
        }
    )
    report = adapt_inventory(inventory)
    mapped = [item["capability"] for item in report["observations"] if item["surface_id"] == "builtin-browser"]
    assert mapped == ["browser", "visual_capture"]
    return {"mapped": mapped}


def control_duplicate_semantic_binding_rejected() -> dict:
    inventory = _inventory()
    duplicate = copy.deepcopy(inventory["bindings"][0])
    duplicate["id"] = "BIND-browser-duplicate"
    duplicate["binding_ref"] = "repo-contract://duplicate/browser"
    inventory["bindings"].append(duplicate)
    message = _expect_error(lambda: validate_inventory(inventory), "duplicate semantic bindings")
    return {"rejected": message}


def control_binding_unknown_surface_rejected() -> dict:
    inventory = _inventory()
    inventory["bindings"][0]["surface_id"] = "missing-surface"
    message = _expect_error(lambda: validate_inventory(inventory), "unknown surfaces")
    return {"rejected": message}


def control_duplicate_surface_id_rejected() -> dict:
    inventory = _inventory()
    inventory["surfaces"].append(copy.deepcopy(inventory["surfaces"][0]))
    message = _expect_error(lambda: validate_inventory(inventory), "surfaces contain duplicate ids")
    return {"rejected": message}


def control_duplicate_binding_id_rejected() -> dict:
    inventory = _inventory()
    extra = copy.deepcopy(inventory["bindings"][0])
    extra["surface_id"] = "mcp-visual-capture"
    extra["capability"] = "browser"
    inventory["bindings"].append(extra)
    message = _expect_error(lambda: validate_inventory(inventory), "bindings contain duplicate ids")
    return {"rejected": message}


def control_model_inferred_binding_rejected() -> dict:
    inventory = _inventory()
    inventory["bindings"][0]["binding_kind"] = "MODEL_INFERRED"
    message = _expect_error(lambda: validate_inventory(inventory), "inferred/model-only bindings are not accepted")
    return {"rejected": message}


def control_binding_reference_required() -> dict:
    inventory = _inventory()
    inventory["bindings"][0]["binding_ref"] = ""
    message = _expect_error(lambda: validate_inventory(inventory), "binding_ref must be a non-empty string")
    return {"rejected": message}


def control_harness_must_be_codex() -> dict:
    inventory = _inventory()
    inventory["harness"] = "OTHER"
    message = _expect_error(lambda: validate_inventory(inventory), "harness must equal CODEX")
    return {"rejected": message}


def control_schema_must_match() -> dict:
    inventory = _inventory()
    inventory["schema"] = "sef.codex-tool-inventory.v2"
    message = _expect_error(lambda: validate_inventory(inventory), "schema must equal")
    return {"rejected": message}


def control_capture_timestamp_requires_timezone() -> dict:
    inventory = _inventory()
    inventory["captured_at"] = "2026-08-25T07:10:00"
    message = _expect_error(lambda: validate_inventory(inventory), "timezone offset")
    return {"rejected": message}


def control_invalid_source_kind_rejected() -> dict:
    inventory = _inventory()
    inventory["surfaces"][0]["source_kind"] = "PLUGIN"
    message = _expect_error(lambda: validate_inventory(inventory), "source_kind is invalid")
    return {"rejected": message}


def control_invalid_tool_name_rejected() -> dict:
    inventory = _inventory()
    inventory["surfaces"][0]["tool_name"] = "tool with spaces"
    message = _expect_error(lambda: validate_inventory(inventory), "compact tool identifier")
    return {"rejected": message}


def control_invalid_capability_rejected() -> dict:
    inventory = _inventory()
    inventory["bindings"][0]["capability"] = "Browser Tool"
    message = _expect_error(lambda: validate_inventory(inventory), "lowercase snake_case")
    return {"rejected": message}


def control_secret_guard() -> dict:
    inventory = _inventory()
    inventory["session_ref"] = "api_" + "key=" + "x" * 24
    message = _expect_error(lambda: validate_inventory(inventory), "credential-shaped secret")
    return {"rejected": message}


def control_unavailable_requires_evidence() -> dict:
    inventory = _inventory()
    surface = _surface(inventory, "builtin-browser")
    surface.update(
        {
            "availability": "UNAVAILABLE",
            "authentication": "UNKNOWN",
            "access": "NONE",
            "evidence_kinds": [],
            "evidence_ref": None,
        }
    )
    message = _expect_error(lambda: validate_inventory(inventory), "known availability requires evidence_ref")
    return {"rejected": message}


def control_unavailable_cannot_claim_access() -> dict:
    inventory = _inventory()
    surface = _surface(inventory, "builtin-browser")
    surface.update({"availability": "UNAVAILABLE", "authentication": "UNKNOWN", "access": "READ"})
    message = _expect_error(lambda: validate_inventory(inventory), "unavailable surface must have access NONE")
    return {"rejected": message}


def control_known_authorization_requires_reference() -> dict:
    inventory = _inventory()
    _surface(inventory, "builtin-browser")["authorization_ref"] = None
    message = _expect_error(lambda: validate_inventory(inventory), "known authorization state requires authorization_ref")
    return {"rejected": message}


def control_unknown_authorization_rejects_reference() -> dict:
    inventory = _inventory()
    surface = _surface(inventory, "builtin-browser")
    surface["authorization_required"] = "UNKNOWN"
    message = _expect_error(lambda: validate_inventory(inventory), "UNKNOWN authorization must not carry authorization_ref")
    return {"rejected": message}


def control_empty_inventory_is_truthful() -> dict:
    inventory = _inventory()
    inventory["surfaces"] = []
    inventory["bindings"] = []
    adapter = adapt_inventory(inventory)
    assert adapter["observation_count"] == 0
    bridge = resolve_codex_inventory(inventory, _requirements())
    statuses = {item["status"] for item in bridge["resolution"]["results"]}
    assert statuses == {"UNKNOWN"}
    return {"observations": 0, "resolution_statuses": sorted(statuses)}


def control_report_determinism() -> dict:
    first = adapt_inventory(_inventory())
    second = adapt_inventory(_inventory())
    assert first == second
    return {"digest": first["content_sha256"]}


def control_observation_id_changes_with_binding_provenance() -> dict:
    first_inventory = _inventory()
    second_inventory = _inventory()
    second_inventory["bindings"][0]["binding_ref"] = "sef-binding://codex/builtin-browser-to-browser/v2"
    first = next(item for item in adapt_inventory(first_inventory)["observations"] if item["capability"] == "browser")
    second = next(item for item in adapt_inventory(second_inventory)["observations"] if item["capability"] == "browser")
    assert first["id"] != second["id"]
    return {"changed": True}


def control_adapter_report_tamper_detected() -> dict:
    report = adapt_inventory(_inventory())
    report["observation_count"] = 999
    message = _expect_error(lambda: validate_adapter_report(report), "content hash mismatch")
    return {"rejected": message}


def control_bridge_report_tamper_detected() -> dict:
    report = resolve_codex_inventory(_inventory(), _requirements())
    report["resolution"]["ready_count"] = 999
    message = _expect_error(lambda: validate_bridge_report(report), "content hash mismatch")
    return {"rejected": message}


def control_bridge_rejects_empty_requirements() -> dict:
    message = _expect_error(lambda: resolve_codex_inventory(_inventory(), {"requirements": []}), "non-empty list")
    return {"rejected": message}


def control_generated_observations_match_m4_contract() -> dict:
    inventory = _inventory()
    adapter = adapt_inventory(inventory)
    document = {
        "schema": "sef.tool-capability-observations.v1",
        "resolved_at": inventory["captured_at"],
        "max_observation_age_seconds": 300,
        "requirements": _requirements()["requirements"],
        "observations": adapter["observations"],
    }
    validate_document(document)
    resolution = resolve(document)
    assert resolution["resolved_count"] == 3
    return {"resolved_count": resolution["resolved_count"]}


def control_no_hidden_discovery_or_model_binding_claim() -> dict:
    report = resolve_codex_inventory(_inventory(), _requirements())
    assert report["claims"] == {
        "inventory_supplied_by_harness": True,
        "hidden_registry_introspection": False,
        "model_inferred_bindings": False,
        "credential_storage": False,
    }
    assert report["adapter_report"]["claims"] == {
        "live_registry_read_by_adapter": False,
        "model_inferred_bindings": False,
        "credential_storage": False,
    }
    return report["claims"]


def control_legacy_runtime_integrity() -> dict:
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
    ("CA-01-valid-adapter", control_valid_inventory_adapts),
    ("CA-02-end-to-end-bridge", control_bridge_end_to_end),
    ("CA-03-unmapped-surface", control_unmapped_surface_never_becomes_observation),
    ("CA-04-binding-provenance", control_binding_provenance_preserved),
    ("CA-05-surface-state", control_surface_state_preserved),
    ("CA-06-source-evidence", control_source_and_evidence_refs_preserved),
    ("CA-07-capture-time", control_capture_time_becomes_observed_time),
    ("CA-08-multi-capability-binding", control_one_surface_can_bind_multiple_capabilities),
    ("CA-09-duplicate-semantic-binding", control_duplicate_semantic_binding_rejected),
    ("CA-10-unknown-surface", control_binding_unknown_surface_rejected),
    ("CA-11-duplicate-surface", control_duplicate_surface_id_rejected),
    ("CA-12-duplicate-binding-id", control_duplicate_binding_id_rejected),
    ("CA-13-no-model-inferred-binding", control_model_inferred_binding_rejected),
    ("CA-14-binding-reference", control_binding_reference_required),
    ("CA-15-harness-contract", control_harness_must_be_codex),
    ("CA-16-schema-contract", control_schema_must_match),
    ("CA-17-capture-timezone", control_capture_timestamp_requires_timezone),
    ("CA-18-source-kind", control_invalid_source_kind_rejected),
    ("CA-19-tool-name", control_invalid_tool_name_rejected),
    ("CA-20-capability-name", control_invalid_capability_rejected),
    ("CA-21-secret-guard", control_secret_guard),
    ("CA-22-unavailable-evidence", control_unavailable_requires_evidence),
    ("CA-23-unavailable-access", control_unavailable_cannot_claim_access),
    ("CA-24-authorization-reference", control_known_authorization_requires_reference),
    ("CA-25-unknown-authorization-reference", control_unknown_authorization_rejects_reference),
    ("CA-26-empty-inventory", control_empty_inventory_is_truthful),
    ("CA-27-determinism", control_report_determinism),
    ("CA-28-observation-provenance-id", control_observation_id_changes_with_binding_provenance),
    ("CA-29-adapter-tamper", control_adapter_report_tamper_detected),
    ("CA-30-bridge-tamper", control_bridge_report_tamper_detected),
    ("CA-31-requirements-required", control_bridge_rejects_empty_requirements),
    ("CA-32-m4-contract-composition", control_generated_observations_match_m4_contract),
    ("CA-33-non-claims", control_no_hidden_discovery_or_model_binding_claim),
    ("CA-34-runtime-integrity", control_legacy_runtime_integrity),
]


def main() -> int:
    results = []
    for control_id, fn in CONTROLS:
        try:
            results.append({"id": control_id, "status": "PASS", "detail": fn()})
        except Exception as exc:
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})
    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.codex-inventory-adapter-m4.v1",
        "stage": "M4_CODEX_TOOL_INVENTORY_ADAPTER",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "model_calls": 0,
        "network_calls": 0,
        "provider_calls": 0,
        "hidden_registry_calls": 0,
        "credential_storage_claim": False,
        "live_registry_introspection_claim": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
