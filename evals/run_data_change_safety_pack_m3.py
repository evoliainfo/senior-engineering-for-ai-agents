#!/usr/bin/env python3
"""Deterministic qualification for the data-change-safety Expert Pack."""
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
PACK = PACK_ROOT / "data-change-safety"
FIXTURES = PACK / "fixtures"
REPORT_PATH = ROOT / "eval-results" / "data-change-safety-pack-m3-report.json"

spec = importlib.util.spec_from_file_location("sef_data_change_safety_evaluator", PACK / "evaluators" / "evaluate.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
evaluate = module.evaluate
validate_document = module.validate_document
DataChangeEvidenceError = module.DataChangeEvidenceError


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except DataChangeEvidenceError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected DataChangeEvidenceError")


def control_pack_contract_loads() -> dict:
    pack = load_pack(PACK)
    assert pack["id"] == "data-change-safety"
    assert [item["capability"] for item in pack["tool_requirements"]] == ["database_admin"]
    assert pack["entry_points"][0]["kind"] == "EVALUATOR"
    return {"bundle_files": len(pack["files"]), "digest": pack["content_sha256"]}


def control_manifest_contains_two_initial_packs() -> dict:
    manifest = build_manifest(PACK_ROOT)
    ids = [item["id"] for item in manifest["packs"]]
    assert ids == ["data-change-safety", "web-experience-visual-quality"]
    return {"pack_count": manifest["pack_count"], "pack_ids": ids}


def control_safe_migration_passes() -> dict:
    report = evaluate(_fixture("pass-migration.json"))
    assert report["status"] == "PASS"
    assert report["failures"] == [] and report["incomplete"] == []
    return {"status": report["status"]}


def control_safe_destructive_change_passes() -> dict:
    report = evaluate(_fixture("pass-destructive.json"))
    assert report["status"] == "PASS"
    return {"status": report["status"], "kind": report["change_kind"]}


def control_critical_invariant_failure_fails() -> dict:
    report = evaluate(_fixture("fail-invariant.json"))
    assert report["status"] == "FAIL"
    assert "CRITICAL_INVARIANT_FAILED:INV-NO-NULLS" in report["failures"]
    return {"status": report["status"]}


def control_not_run_recovery_is_incomplete() -> dict:
    report = evaluate(_fixture("incomplete-recovery.json"))
    assert report["status"] == "INCOMPLETE"
    assert "RECOVERY_NOT_PROVEN" in report["incomplete"]
    return {"status": report["status"]}


def control_scope_mismatch_fails() -> dict:
    document = _fixture("pass-migration.json")
    document["change"]["scope_status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "ACTUAL_CHANGE_SCOPE_MISMATCH" in report["failures"]
    return {"status": report["status"]}


def control_rehearsal_failure_fails() -> dict:
    document = _fixture("pass-migration.json")
    document["rehearsal"]["status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "REHEARSAL_FAILED" in report["failures"]
    return {"status": report["status"]}


def control_missing_rehearsal_evidence_is_incomplete() -> dict:
    document = _fixture("pass-migration.json")
    document["rehearsal"]["fixture_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "REHEARSAL_FIXTURE_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_rehearsal_cannot_be_production() -> dict:
    document = _fixture("pass-migration.json")
    document["rehearsal"]["environment_kind"] = "PRODUCTION"
    message = _expect_error(lambda: validate_document(document), "SANDBOX or PREVIEW")
    return {"rejected": message}


def control_all_durable_controls_must_be_accounted() -> dict:
    document = _fixture("pass-migration.json")
    document["controls"] = document["controls"][:-1]
    message = _expect_error(lambda: validate_document(document), "controls must account for exactly")
    return {"rejected": message}


def control_nonrequired_control_must_be_explicit_na() -> dict:
    document = _fixture("pass-migration.json")
    resumability = next(item for item in document["controls"] if item["id"] == "resumability")
    resumability["status"] = "PASS"
    message = _expect_error(lambda: validate_document(document), "non-required control must be N_A")
    return {"rejected": message}


def control_required_control_cannot_be_na() -> dict:
    document = _fixture("pass-migration.json")
    idem = next(item for item in document["controls"] if item["id"] == "idempotency")
    idem["status"] = "N_A"
    idem["evidence_ref"] = None
    message = _expect_error(lambda: validate_document(document), "required control cannot be N_A")
    return {"rejected": message}


def control_required_control_failure_fails() -> dict:
    document = _fixture("pass-migration.json")
    idem = next(item for item in document["controls"] if item["id"] == "idempotency")
    idem["status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "CONTROL_FAILED:idempotency" in report["failures"]
    return {"status": report["status"]}


def control_required_control_missing_evidence_is_incomplete() -> dict:
    document = _fixture("pass-migration.json")
    idem = next(item for item in document["controls"] if item["id"] == "idempotency")
    idem["evidence_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "CONTROL_EVIDENCE_MISSING:idempotency" in report["incomplete"]
    return {"status": report["status"]}


def control_no_recovery_strategy_fails() -> dict:
    document = _fixture("pass-migration.json")
    document["recovery"].update({"strategy": "NONE", "status": "N_A", "evidence_ref": None})
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "RECOVERY_STRATEGY_MISSING" in report["failures"]
    return {"status": report["status"]}


def control_none_recovery_cannot_fake_evidence() -> dict:
    document = _fixture("pass-migration.json")
    document["recovery"].update({"strategy": "NONE", "status": "PASS", "evidence_ref": "artifact://fake-recovery.json"})
    message = _expect_error(lambda: validate_document(document), "NONE requires status N_A")
    return {"rejected": message}


def control_recovery_failure_fails() -> dict:
    document = _fixture("pass-migration.json")
    document["recovery"]["status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "RECOVERY_EXERCISE_FAILED" in report["failures"]
    return {"status": report["status"]}


def control_recovery_pass_requires_evidence() -> dict:
    document = _fixture("pass-migration.json")
    document["recovery"]["evidence_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "RECOVERY_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_destructive_backup_not_run_is_incomplete() -> dict:
    document = _fixture("pass-destructive.json")
    document["recovery"]["backup_status"] = "NOT_RUN"
    document["recovery"]["backup_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "BACKUP_NOT_PROVEN" in report["incomplete"]
    return {"status": report["status"]}


def control_destructive_backup_failure_fails() -> dict:
    document = _fixture("pass-destructive.json")
    document["recovery"]["backup_status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "BACKUP_FAILED" in report["failures"]
    return {"status": report["status"]}


def control_destructive_backup_ref_required() -> dict:
    document = _fixture("pass-destructive.json")
    document["recovery"]["backup_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "BACKUP_EVIDENCE_MISSING" in report["incomplete"]
    return {"status": report["status"]}


def control_destructive_cleanup_flag_consistency() -> dict:
    document = _fixture("pass-destructive.json")
    document["change"]["destructive"] = False
    message = _expect_error(lambda: validate_document(document), "must set change.destructive=true")
    return {"rejected": message}


def control_missing_invariant_evidence_is_incomplete() -> dict:
    document = _fixture("pass-migration.json")
    document["invariants"][0]["post_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "INVARIANT_INCOMPLETE:INV-ROW-COUNT" in report["incomplete"]
    return {"status": report["status"]}


def control_no_provider_or_production_execution_claim() -> dict:
    report = evaluate(_fixture("pass-migration.json"))
    assert report["claims"] == {
        "database_executed_by_evaluator": False,
        "production_change_authorized": False,
        "provider_specific_correctness_claim": False,
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
    ("DS-01-pack-contract", control_pack_contract_loads),
    ("DS-02-manifest", control_manifest_contains_two_initial_packs),
    ("DS-03-safe-migration", control_safe_migration_passes),
    ("DS-04-safe-destructive", control_safe_destructive_change_passes),
    ("DS-05-critical-invariant", control_critical_invariant_failure_fails),
    ("DS-06-recovery-not-run", control_not_run_recovery_is_incomplete),
    ("DS-07-scope-mismatch", control_scope_mismatch_fails),
    ("DS-08-rehearsal-failure", control_rehearsal_failure_fails),
    ("DS-09-rehearsal-evidence", control_missing_rehearsal_evidence_is_incomplete),
    ("DS-10-non-production-rehearsal", control_rehearsal_cannot_be_production),
    ("DS-11-control-accounting", control_all_durable_controls_must_be_accounted),
    ("DS-12-explicit-na", control_nonrequired_control_must_be_explicit_na),
    ("DS-13-required-not-na", control_required_control_cannot_be_na),
    ("DS-14-control-failure", control_required_control_failure_fails),
    ("DS-15-control-evidence", control_required_control_missing_evidence_is_incomplete),
    ("DS-16-recovery-required", control_no_recovery_strategy_fails),
    ("DS-17-no-fake-recovery", control_none_recovery_cannot_fake_evidence),
    ("DS-18-recovery-failure", control_recovery_failure_fails),
    ("DS-19-recovery-evidence", control_recovery_pass_requires_evidence),
    ("DS-20-destructive-backup-not-run", control_destructive_backup_not_run_is_incomplete),
    ("DS-21-destructive-backup-failure", control_destructive_backup_failure_fails),
    ("DS-22-destructive-backup-ref", control_destructive_backup_ref_required),
    ("DS-23-destructive-kind-consistency", control_destructive_cleanup_flag_consistency),
    ("DS-24-invariant-evidence", control_missing_invariant_evidence_is_incomplete),
    ("DS-25-non-claims", control_no_provider_or_production_execution_claim),
    ("DS-26-runtime-integrity", control_legacy_runtime_integrity),
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
        "schema": "sef.eval.data-change-safety-pack-m3.v1",
        "stage": "M3_DATA_CHANGE_SAFETY",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "database_calls": 0,
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
