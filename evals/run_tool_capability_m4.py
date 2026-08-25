#!/usr/bin/env python3
"""Deterministic qualification for Modern SEF M4 tool capability resolution."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tool_capabilities import (  # noqa: E402
    ToolCapabilityError,
    resolve,
    validate_document,
    validate_resolution,
)

FIXTURE = ROOT / "tool_capabilities" / "fixtures" / "ready.json"
REPORT_PATH = ROOT / "eval-results" / "tool-capability-m4-report.json"


def _base() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _browser(document: dict) -> dict:
    return next(item for item in document["observations"] if item["capability"] == "browser")


def _browser_result(report: dict) -> dict:
    return next(item for item in report["results"] if item["capability"] == "browser")


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except ToolCapabilityError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected ToolCapabilityError")


def control_ready_fixture() -> dict:
    report = resolve(_base())
    assert report["status"] == "READY"
    assert report["ready_count"] == 2
    validate_resolution(report)
    return {"status": report["status"], "digest": report["content_sha256"]}


def control_authorization_required() -> dict:
    document = _base()
    obs = _browser(document)
    obs["authorization_required"] = "REQUIRED"
    obs["authorization_ref"] = "policy://human-approval/browser"
    result = _browser_result(resolve(document))
    assert result["status"] == "AUTHORIZATION_REQUIRED"
    return {"status": result["status"]}


def control_authorization_unknown() -> dict:
    document = _base()
    obs = _browser(document)
    obs["authorization_required"] = "UNKNOWN"
    obs["authorization_ref"] = None
    result = _browser_result(resolve(document))
    assert result["status"] == "AUTHORIZATION_UNKNOWN"
    return {"status": result["status"]}


def control_unauthenticated() -> dict:
    document = _base()
    _browser(document)["authentication"] = "UNAUTHENTICATED"
    result = _browser_result(resolve(document))
    assert result["status"] == "UNAUTHENTICATED"
    return {"status": result["status"]}


def control_unavailable() -> dict:
    document = _base()
    obs = _browser(document)
    obs.update({"availability": "UNAVAILABLE", "authentication": "UNKNOWN", "access": "NONE", "evidence_kinds": []})
    result = _browser_result(resolve(document))
    assert result["status"] == "UNAVAILABLE"
    return {"status": result["status"]}


def control_no_observation_unknown() -> dict:
    document = _base()
    document["observations"] = [item for item in document["observations"] if item["capability"] != "browser"]
    result = _browser_result(resolve(document))
    assert result["status"] == "UNKNOWN"
    assert "NO_OBSERVATION" in result["reasons"]
    return {"status": result["status"]}


def control_insufficient_access() -> dict:
    document = _base()
    document["requirements"][0]["access"] = "WRITE"
    result = _browser_result(resolve(document))
    assert result["status"] == "INSUFFICIENT_ACCESS"
    return {"status": result["status"]}


def control_insufficient_scope() -> dict:
    document = _base()
    document["requirements"][0]["sensitivity"] = "PRODUCTION_SENSITIVE"
    result = _browser_result(resolve(document))
    assert result["status"] == "INSUFFICIENT_SCOPE"
    return {"status": result["status"]}


def control_insufficient_evidence() -> dict:
    document = _base()
    document["requirements"][0]["required_evidence_kinds"].append("dom_snapshot")
    result = _browser_result(resolve(document))
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    return {"status": result["status"]}


def control_stale_observation_unknown() -> dict:
    document = _base()
    _browser(document)["observed_at"] = "2026-08-25T06:40:00Z"
    result = _browser_result(resolve(document))
    assert result["status"] == "UNKNOWN"
    assert "ONLY_STALE_OBSERVATIONS" in result["reasons"]
    assert "browser:builtin-browser" in result["stale_surfaces"]
    return {"status": result["status"]}


def control_newer_observation_supersedes_old() -> dict:
    document = _base()
    old = copy.deepcopy(_browser(document))
    old.update({
        "id": "OBS-browser-old",
        "observed_at": "2026-08-25T06:53:00Z",
        "availability": "UNAVAILABLE",
        "authentication": "UNKNOWN",
        "access": "NONE",
        "evidence_kinds": [],
        "evidence_ref": "evidence://old-unavailable/browser"
    })
    document["observations"].append(old)
    result = _browser_result(resolve(document))
    assert result["status"] == "READY"
    assert result["selected_surface_id"] == "builtin-browser"
    return {"status": result["status"]}


def control_equivalent_tied_observations_not_conflict() -> dict:
    document = _base()
    duplicate = copy.deepcopy(_browser(document))
    duplicate["id"] = "OBS-browser-equivalent"
    document["observations"].append(duplicate)
    report = resolve(document)
    result = _browser_result(report)
    assert result["status"] == "READY"
    assert not result["conflicting_surfaces"]
    return {"status": result["status"]}


def control_conflicting_latest_observations() -> dict:
    document = _base()
    conflict = copy.deepcopy(_browser(document))
    conflict.update({
        "id": "OBS-browser-conflict",
        "availability": "UNAVAILABLE",
        "authentication": "UNKNOWN",
        "access": "NONE",
        "evidence_kinds": [],
        "evidence_ref": "evidence://same-time-unavailable/browser"
    })
    document["observations"].append(conflict)
    result = _browser_result(resolve(document))
    assert result["status"] == "CONFLICT"
    assert "browser:builtin-browser" in result["conflicting_surfaces"]
    return {"status": result["status"]}


def control_conflict_does_not_block_independent_ready_surface() -> dict:
    document = _base()
    conflict = copy.deepcopy(_browser(document))
    conflict.update({
        "id": "OBS-browser-conflict",
        "availability": "UNAVAILABLE",
        "authentication": "UNKNOWN",
        "access": "NONE",
        "evidence_kinds": [],
        "evidence_ref": "evidence://same-time-unavailable/browser"
    })
    alternative = copy.deepcopy(_browser(document))
    alternative.update({
        "id": "OBS-browser-mcp",
        "surface_id": "mcp-browser",
        "source_kind": "MCP",
        "source_ref": "tool-schema://mcp/browser",
        "evidence_ref": "evidence://mcp-list/browser"
    })
    document["observations"].extend([conflict, alternative])
    result = _browser_result(resolve(document))
    assert result["status"] == "READY"
    assert result["selected_surface_id"] == "mcp-browser"
    assert "browser:builtin-browser" in result["conflicting_surfaces"]
    return {"status": result["status"], "selected": result["selected_surface_id"]}


def control_least_privilege_precedes_source_priority() -> dict:
    document = _base()
    builtin = _browser(document)
    builtin["sensitivity"] = "PRODUCTION_SENSITIVE"
    mcp = copy.deepcopy(builtin)
    mcp.update({
        "id": "OBS-browser-mcp",
        "surface_id": "mcp-browser",
        "source_kind": "MCP",
        "source_ref": "tool-schema://mcp/browser",
        "sensitivity": "SANDBOX",
        "evidence_ref": "evidence://mcp-list/browser"
    })
    document["observations"].append(mcp)
    result = _browser_result(resolve(document))
    assert result["selected_surface_id"] == "mcp-browser"
    return {"selected": result["selected_surface_id"]}


def control_source_priority_breaks_equal_fit() -> dict:
    document = _base()
    mcp = copy.deepcopy(_browser(document))
    mcp.update({
        "id": "OBS-browser-mcp",
        "surface_id": "mcp-browser",
        "source_kind": "MCP",
        "source_ref": "tool-schema://mcp/browser",
        "evidence_ref": "evidence://mcp-list/browser"
    })
    document["observations"].append(mcp)
    result = _browser_result(resolve(document))
    assert result["selected_surface_id"] == "builtin-browser"
    return {"selected": result["selected_surface_id"]}


def control_future_observation_rejected() -> dict:
    document = _base()
    _browser(document)["observed_at"] = "2026-08-25T06:55:01Z"
    message = _expect_error(lambda: validate_document(document), "must not be newer than resolved_at")
    return {"rejected": message}


def control_unavailable_requires_evidence() -> dict:
    document = _base()
    obs = _browser(document)
    obs.update({"availability": "UNAVAILABLE", "authentication": "UNKNOWN", "access": "NONE", "evidence_kinds": [], "evidence_ref": None})
    message = _expect_error(lambda: validate_document(document), "known availability requires evidence_ref")
    return {"rejected": message}


def control_positive_claim_requires_evidence() -> dict:
    document = _base()
    _browser(document)["evidence_ref"] = None
    message = _expect_error(lambda: validate_document(document), "known availability requires evidence_ref")
    return {"rejected": message}


def control_known_authorization_requires_reference() -> dict:
    document = _base()
    _browser(document)["authorization_ref"] = None
    message = _expect_error(lambda: validate_document(document), "known authorization state requires authorization_ref")
    return {"rejected": message}


def control_unknown_authorization_rejects_reference() -> dict:
    document = _base()
    obs = _browser(document)
    obs["authorization_required"] = "UNKNOWN"
    message = _expect_error(lambda: validate_document(document), "UNKNOWN authorization must not carry authorization_ref")
    return {"rejected": message}


def control_secret_guard() -> dict:
    document = _base()
    _browser(document)["source_ref"] = "api_key=" + "x" * 24
    message = _expect_error(lambda: validate_document(document), "credential-shaped secret")
    return {"rejected": message}


def control_unavailable_cannot_claim_access() -> dict:
    document = _base()
    obs = _browser(document)
    obs.update({"availability": "UNAVAILABLE", "authentication": "UNKNOWN", "access": "READ", "evidence_kinds": []})
    message = _expect_error(lambda: validate_document(document), "unavailable surface must have access NONE")
    return {"rejected": message}


def control_duplicate_requirement_rejected() -> dict:
    document = _base()
    document["requirements"].append(copy.deepcopy(document["requirements"][0]))
    message = _expect_error(lambda: validate_document(document), "requirements contain duplicate ids")
    return {"rejected": message}


def control_duplicate_observation_id_rejected() -> dict:
    document = _base()
    document["observations"].append(copy.deepcopy(document["observations"][0]))
    message = _expect_error(lambda: validate_document(document), "observations contain duplicate ids")
    return {"rejected": message}


def control_invalid_max_age_rejected() -> dict:
    document = _base()
    document["max_observation_age_seconds"] = 0
    message = _expect_error(lambda: validate_document(document), "max_observation_age_seconds")
    return {"rejected": message}


def control_timezone_required() -> dict:
    document = _base()
    document["resolved_at"] = "2026-08-25T06:55:00"
    message = _expect_error(lambda: validate_document(document), "must include a timezone offset")
    return {"rejected": message}


def control_capability_name_contract() -> dict:
    document = _base()
    document["requirements"][0]["capability"] = "Browser Tool"
    message = _expect_error(lambda: validate_document(document), "lowercase snake_case")
    return {"rejected": message}


def control_resolution_tamper_detection() -> dict:
    report = resolve(_base())
    report["ready_count"] = 999
    message = _expect_error(lambda: validate_resolution(report), "content hash mismatch")
    return {"rejected": message}


def control_production_write_requires_authorization_when_observed() -> dict:
    document = _base()
    requirement = document["requirements"][0]
    requirement.update({"capability": "hosting", "access": "WRITE", "sensitivity": "PRODUCTION_SENSITIVE", "required_evidence_kinds": ["deployment_result"]})
    obs = _browser(document)
    obs.update({
        "capability": "hosting",
        "surface_id": "mcp-hosting",
        "source_kind": "MCP",
        "source_ref": "tool-schema://mcp/hosting",
        "authentication": "AUTHENTICATED",
        "access": "WRITE",
        "sensitivity": "PRODUCTION_SENSITIVE",
        "evidence_kinds": ["deployment_result"],
        "evidence_ref": "evidence://mcp-list/hosting",
        "authorization_required": "REQUIRED",
        "authorization_ref": "policy://production/deploy-approval"
    })
    result = next(item for item in resolve(document)["results"] if item["requirement_id"] == "REQ-browser")
    assert result["status"] == "AUTHORIZATION_REQUIRED"
    return {"status": result["status"]}


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
    ("M4-01-ready-fixture", control_ready_fixture),
    ("M4-02-authorization-required", control_authorization_required),
    ("M4-03-authorization-unknown", control_authorization_unknown),
    ("M4-04-unauthenticated", control_unauthenticated),
    ("M4-05-unavailable", control_unavailable),
    ("M4-06-no-observation", control_no_observation_unknown),
    ("M4-07-insufficient-access", control_insufficient_access),
    ("M4-08-insufficient-scope", control_insufficient_scope),
    ("M4-09-insufficient-evidence", control_insufficient_evidence),
    ("M4-10-stale-observation", control_stale_observation_unknown),
    ("M4-11-newer-supersedes-old", control_newer_observation_supersedes_old),
    ("M4-12-equivalent-tie", control_equivalent_tied_observations_not_conflict),
    ("M4-13-conflicting-tie", control_conflicting_latest_observations),
    ("M4-14-conflict-alternative", control_conflict_does_not_block_independent_ready_surface),
    ("M4-15-least-privilege", control_least_privilege_precedes_source_priority),
    ("M4-16-source-priority", control_source_priority_breaks_equal_fit),
    ("M4-17-future-observation", control_future_observation_rejected),
    ("M4-18-unavailable-evidence", control_unavailable_requires_evidence),
    ("M4-19-positive-evidence", control_positive_claim_requires_evidence),
    ("M4-20-authorization-reference", control_known_authorization_requires_reference),
    ("M4-21-unknown-authorization-reference", control_unknown_authorization_rejects_reference),
    ("M4-22-secret-guard", control_secret_guard),
    ("M4-23-unavailable-access", control_unavailable_cannot_claim_access),
    ("M4-24-duplicate-requirement", control_duplicate_requirement_rejected),
    ("M4-25-duplicate-observation", control_duplicate_observation_id_rejected),
    ("M4-26-max-age", control_invalid_max_age_rejected),
    ("M4-27-timezone", control_timezone_required),
    ("M4-28-capability-name", control_capability_name_contract),
    ("M4-29-resolution-tamper", control_resolution_tamper_detection),
    ("M4-30-production-authorization", control_production_write_requires_authorization_when_observed),
    ("M4-31-runtime-integrity", control_legacy_runtime_integrity),
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
        "schema": "sef.eval.tool-capability-m4.v1",
        "stage": "M4_TOOL_CAPABILITY_RESOLUTION",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "model_calls": 0,
        "network_calls": 0,
        "provider_calls": 0,
        "credential_storage_claim": False,
        "live_harness_discovery_claim": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
