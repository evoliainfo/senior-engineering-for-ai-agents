#!/usr/bin/env python3
"""Deterministic qualification for the production-evidence-operations Expert Pack."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from expert_packs import build_manifest, load_pack  # noqa: E402

PACK_ROOT = ROOT / "expert_packs"
PACK = PACK_ROOT / "production-evidence-operations"
FIXTURES = PACK / "fixtures"
REPORT_PATH = ROOT / "eval-results" / "production-evidence-operations-pack-m3-report.json"

spec = importlib.util.spec_from_file_location("sef_production_evidence_evaluator", PACK / "evaluators" / "evaluate.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
evaluate = module.evaluate
validate_document = module.validate_document
ProductionEvidenceError = module.ProductionEvidenceError


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except ProductionEvidenceError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected ProductionEvidenceError")


def control_pack_contract_loads() -> dict:
    pack = load_pack(PACK)
    assert pack["id"] == "production-evidence-operations"
    assert [item["capability"] for item in pack["tool_requirements"]] == ["hosting", "observability"]
    assert pack["entry_points"][0]["kind"] == "EVALUATOR"
    return {"bundle_files": len(pack["files"]), "digest": pack["content_sha256"]}


def control_manifest_contains_three_initial_packs() -> dict:
    manifest = build_manifest(PACK_ROOT)
    ids = [item["id"] for item in manifest["packs"]]
    assert ids == ["data-change-safety", "production-evidence-operations", "web-experience-visual-quality"]
    return {"pack_count": manifest["pack_count"], "pack_ids": ids}


def control_passing_production_release() -> dict:
    report = evaluate(_fixture("pass-production.json"))
    assert report["status"] == "PASS"
    assert report["failures"] == [] and report["incomplete"] == []
    return {"status": report["status"], "environment": report["environment_kind"]}


def control_runtime_identity_mismatch_fails() -> dict:
    report = evaluate(_fixture("fail-runtime-identity.json"))
    assert report["status"] == "FAIL"
    assert "RUNTIME_IDENTITY_MISMATCH" in report["failures"]
    return {"status": report["status"]}


def control_blocking_smoke_failure_fails() -> dict:
    report = evaluate(_fixture("fail-smoke.json"))
    assert report["status"] == "FAIL"
    assert "BLOCKING_SMOKE_FAILED:critical-submit" in report["failures"]
    return {"status": report["status"]}


def control_required_observability_not_run_incomplete() -> dict:
    report = evaluate(_fixture("incomplete-observability.json"))
    assert report["status"] == "INCOMPLETE"
    assert "OBSERVABILITY_NOT_PROVEN:logs" in report["incomplete"]
    return {"status": report["status"]}


def control_deployment_failure_fails() -> dict:
    document = _fixture("pass-production.json")
    document["release"]["deployment_status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "DEPLOYMENT_FAILED" in report["failures"]
    return {"status": report["status"]}


def control_deployment_pass_requires_evidence() -> dict:
    document = _fixture("pass-production.json")
    document["release"]["deployment_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "DEPLOYMENT_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_runtime_identity_pass_requires_evidence() -> dict:
    document = _fixture("pass-production.json")
    document["release"]["runtime_identity_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "RUNTIME_IDENTITY_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_health_failure_fails() -> dict:
    document = _fixture("pass-production.json")
    document["health"]["status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "HEALTH_CHECK_FAILED" in report["failures"]
    return {"status": report["status"]}


def control_health_pass_requires_evidence() -> dict:
    document = _fixture("pass-production.json")
    document["health"]["evidence_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "HEALTH_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_nonblocking_smoke_failure_is_warning() -> dict:
    document = _fixture("pass-production.json")
    document["smoke_checks"].append({"id": "secondary-analytics", "blocking": False, "status": "FAIL", "evidence_ref": "artifact://secondary-failure.json"})
    report = evaluate(document)
    assert report["status"] == "PASS"
    assert "NONBLOCKING_SMOKE_FAILED:secondary-analytics" in report["warnings"]
    return {"status": report["status"], "warning_count": len(report["warnings"])}


def control_blocking_smoke_missing_evidence_incomplete() -> dict:
    document = _fixture("pass-production.json")
    document["smoke_checks"][0]["evidence_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "BLOCKING_SMOKE_EVIDENCE_MISSING:home-loads" in report["incomplete"]
    return {"status": report["status"]}


def control_duplicate_smoke_rejected() -> dict:
    document = _fixture("pass-production.json")
    document["smoke_checks"].append(copy.deepcopy(document["smoke_checks"][0]))
    message = _expect_error(lambda: validate_document(document), "duplicate ids")
    return {"rejected": message}


def control_at_least_one_blocking_smoke_required() -> dict:
    document = _fixture("pass-production.json")
    for item in document["smoke_checks"]:
        item["blocking"] = False
    message = _expect_error(lambda: validate_document(document), "at least one smoke check must be blocking")
    return {"rejected": message}


def control_observability_accounting_exact() -> dict:
    document = _fixture("pass-production.json")
    document["observability"] = document["observability"][:-1]
    message = _expect_error(lambda: validate_document(document), "observability must account for exactly")
    return {"rejected": message}


def control_at_least_one_observability_required() -> dict:
    document = _fixture("pass-production.json")
    for item in document["observability"]:
        item["required"] = False
        item["status"] = "N_A"
        item["evidence_ref"] = None
    message = _expect_error(lambda: validate_document(document), "at least one observability control must be required")
    return {"rejected": message}


def control_required_observability_failure_fails() -> dict:
    document = _fixture("pass-production.json")
    logs = next(item for item in document["observability"] if item["id"] == "logs")
    logs["status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "OBSERVABILITY_FAILED:logs" in report["failures"]
    return {"status": report["status"]}


def control_required_observability_missing_evidence_incomplete() -> dict:
    document = _fixture("pass-production.json")
    logs = next(item for item in document["observability"] if item["id"] == "logs")
    logs["evidence_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "OBSERVABILITY_EVIDENCE_MISSING:logs" in report["incomplete"]
    return {"status": report["status"]}


def control_nonrequired_observability_must_be_na() -> dict:
    document = _fixture("pass-production.json")
    metrics = next(item for item in document["observability"] if item["id"] == "metrics")
    metrics["status"] = "PASS"
    message = _expect_error(lambda: validate_document(document), "non-required observability control must be N_A")
    return {"rejected": message}


def control_required_observability_cannot_be_na() -> dict:
    document = _fixture("pass-production.json")
    logs = next(item for item in document["observability"] if item["id"] == "logs")
    logs["status"] = "N_A"
    logs["evidence_ref"] = None
    message = _expect_error(lambda: validate_document(document), "required observability control cannot be N_A")
    return {"rejected": message}


def control_no_recovery_strategy_fails() -> dict:
    document = _fixture("pass-production.json")
    document["recovery"].update({"strategy": "NONE", "status": "N_A", "evidence_kind": "NONE", "evidence_ref": None})
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "RECOVERY_STRATEGY_MISSING" in report["failures"]
    return {"status": report["status"]}


def control_none_recovery_cannot_fake_evidence() -> dict:
    document = _fixture("pass-production.json")
    document["recovery"].update({"strategy": "NONE", "status": "PASS", "evidence_kind": "OBSERVED_RECOVERY", "evidence_ref": "artifact://fake-recovery.json"})
    message = _expect_error(lambda: validate_document(document), "strategy NONE requires")
    return {"rejected": message}


def control_recovery_failure_fails() -> dict:
    document = _fixture("pass-production.json")
    document["recovery"]["status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "RECOVERY_VERIFICATION_FAILED" in report["failures"]
    return {"status": report["status"]}


def control_recovery_pass_requires_evidence() -> dict:
    document = _fixture("pass-production.json")
    document["recovery"]["evidence_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "RECOVERY_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_recovery_rehearsal_cannot_be_production() -> dict:
    document = _fixture("pass-production.json")
    document["recovery"]["environment_kind"] = "PRODUCTION"
    message = _expect_error(lambda: validate_document(document), "rehearsal must not use PRODUCTION")
    return {"rejected": message}


def control_post_deploy_failure_fails() -> dict:
    document = _fixture("pass-production.json")
    document["post_deploy"]["status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "POST_DEPLOY_OBSERVATION_FAILED" in report["failures"]
    return {"status": report["status"]}


def control_post_deploy_window_required() -> dict:
    document = _fixture("pass-production.json")
    document["post_deploy"]["window_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "POST_DEPLOY_WINDOW_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_post_deploy_evidence_required() -> dict:
    document = _fixture("pass-production.json")
    document["post_deploy"]["evidence_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "POST_DEPLOY_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_not_run_post_deploy_not_success() -> dict:
    document = _fixture("pass-production.json")
    document["post_deploy"]["status"] = "NOT_RUN"
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "POST_DEPLOY_OBSERVATION_NOT_PROVEN" in report["incomplete"]
    return {"status": report["status"]}


def control_no_live_provider_claims() -> dict:
    report = evaluate(_fixture("pass-production.json"))
    assert report["claims"] == {
        "deployment_executed_by_evaluator": False,
        "production_write_authorized": False,
        "provider_specific_operations_claim": False,
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
    ("PO-01-pack-contract", control_pack_contract_loads),
    ("PO-02-manifest", control_manifest_contains_three_initial_packs),
    ("PO-03-production-pass", control_passing_production_release),
    ("PO-04-runtime-identity-mismatch", control_runtime_identity_mismatch_fails),
    ("PO-05-blocking-smoke-failure", control_blocking_smoke_failure_fails),
    ("PO-06-observability-not-run", control_required_observability_not_run_incomplete),
    ("PO-07-deployment-failure", control_deployment_failure_fails),
    ("PO-08-deployment-evidence", control_deployment_pass_requires_evidence),
    ("PO-09-runtime-identity-evidence", control_runtime_identity_pass_requires_evidence),
    ("PO-10-health-failure", control_health_failure_fails),
    ("PO-11-health-evidence", control_health_pass_requires_evidence),
    ("PO-12-nonblocking-smoke-warning", control_nonblocking_smoke_failure_is_warning),
    ("PO-13-blocking-smoke-evidence", control_blocking_smoke_missing_evidence_incomplete),
    ("PO-14-duplicate-smoke", control_duplicate_smoke_rejected),
    ("PO-15-blocking-smoke-required", control_at_least_one_blocking_smoke_required),
    ("PO-16-observability-accounting", control_observability_accounting_exact),
    ("PO-17-observability-minimum", control_at_least_one_observability_required),
    ("PO-18-observability-failure", control_required_observability_failure_fails),
    ("PO-19-observability-evidence", control_required_observability_missing_evidence_incomplete),
    ("PO-20-observability-explicit-na", control_nonrequired_observability_must_be_na),
    ("PO-21-observability-required-not-na", control_required_observability_cannot_be_na),
    ("PO-22-recovery-required", control_no_recovery_strategy_fails),
    ("PO-23-no-fake-recovery", control_none_recovery_cannot_fake_evidence),
    ("PO-24-recovery-failure", control_recovery_failure_fails),
    ("PO-25-recovery-evidence", control_recovery_pass_requires_evidence),
    ("PO-26-rehearsal-non-production", control_recovery_rehearsal_cannot_be_production),
    ("PO-27-post-deploy-failure", control_post_deploy_failure_fails),
    ("PO-28-post-deploy-window", control_post_deploy_window_required),
    ("PO-29-post-deploy-evidence", control_post_deploy_evidence_required),
    ("PO-30-post-deploy-not-run", control_not_run_post_deploy_not_success),
    ("PO-31-non-claims", control_no_live_provider_claims),
    ("PO-32-runtime-integrity", control_legacy_runtime_integrity),
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
        "schema": "sef.eval.production-evidence-operations-pack-m3.v1",
        "stage": "M3_PRODUCTION_EVIDENCE_OPERATIONS",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "hosting_calls": 0,
        "observability_calls": 0,
        "model_calls": 0,
        "network_calls": 0,
        "production_execution_claim": False,
        "provider_specific_claim": False,
        "outcome_superiority_claim": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
