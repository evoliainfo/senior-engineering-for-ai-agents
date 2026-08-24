#!/usr/bin/env python3
"""Deterministic qualification for the web-experience-visual-quality Expert Pack."""
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
PACK = PACK_ROOT / "web-experience-visual-quality"
FIXTURES = PACK / "fixtures"
REPORT_PATH = ROOT / "eval-results" / "web-visual-pack-m3-report.json"

spec = importlib.util.spec_from_file_location("sef_web_visual_evaluator", PACK / "evaluators" / "evaluate.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
evaluate = module.evaluate
validate_document = module.validate_document
VisualEvidenceError = module.VisualEvidenceError


def _fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except VisualEvidenceError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected VisualEvidenceError")


def control_pack_contract_loads() -> dict:
    pack = load_pack(PACK)
    assert pack["id"] == "web-experience-visual-quality"
    assert [item["capability"] for item in pack["tool_requirements"]] == ["browser", "visual_capture"]
    assert pack["entry_points"][0]["kind"] == "EVALUATOR"
    return {"bundle_files": len(pack["files"]), "digest": pack["content_sha256"]}


def control_manifest_contains_pack() -> dict:
    manifest = build_manifest(PACK_ROOT)
    match = [item for item in manifest["packs"] if item["id"] == "web-experience-visual-quality"]
    assert len(match) == 1
    return {"pack_count": manifest["pack_count"], "manifest_digest": manifest["content_sha256"]}


def control_complete_fixture_passes() -> dict:
    report = evaluate(_fixture("pass.json"))
    assert report["status"] == "PASS"
    assert all(item["status"] == "PASS" for item in report["case_results"])
    assert report["claims"]["browser_executed_by_evaluator"] is False
    return {"status": report["status"], "cases": report["required_case_count"]}


def control_missing_required_case_is_incomplete() -> dict:
    report = evaluate(_fixture("incomplete.json"))
    assert report["status"] == "INCOMPLETE"
    missing = [item for item in report["case_results"] if item["reason"] == "MISSING_OBSERVATION"]
    assert len(missing) == 1
    return {"status": report["status"], "missing_case": missing[0]["case_id"]}


def control_material_discrepancy_fails() -> dict:
    report = evaluate(_fixture("fail-material-discrepancy.json"))
    assert report["status"] == "FAIL"
    assert "UNRESOLVED_MATERIAL_DISCREPANCY" in report["case_results"][0]["reason"]
    return {"status": report["status"]}


def control_failed_interaction_fails() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["interaction_status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "INTERACTION_FAILED" in report["case_results"][0]["reason"]
    return {"status": report["status"]}


def control_accessibility_failure_fails() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["accessibility_status"] = "FAIL"
    report = evaluate(document)
    assert report["status"] == "FAIL"
    assert "ACCESSIBILITY_FAILED" in report["case_results"][0]["reason"]
    return {"status": report["status"]}


def control_missing_accessibility_evidence_is_incomplete() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["accessibility_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "ACCESSIBILITY_EVIDENCE_MISSING" in report["case_results"][0]["reason"]
    return {"status": report["status"]}


def control_unstable_capture_is_incomplete() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["capture_stable"] = False
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "CAPTURE_NOT_COMPARABLE" in report["case_results"][0]["reason"]
    return {"status": report["status"]}


def control_missing_capture_context_is_incomplete() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["capture_context_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "CAPTURE_CONTEXT_MISSING" in report["case_results"][0]["reason"]
    return {"status": report["status"]}


def control_missing_screenshot_is_incomplete() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["screenshot_ref"] = None
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    assert "VISUAL_CAPTURE_MISSING" in report["case_results"][0]["reason"]
    return {"status": report["status"]}


def control_advisory_discrepancy_does_not_fail() -> dict:
    report = evaluate(_fixture("pass.json"))
    advisory_case = next(item for item in report["case_results"] if item["case_id"] == "home-desktop")
    assert advisory_case["status"] == "PASS"
    return {"status": advisory_case["status"]}


def control_correction_loop_uses_latest_iteration() -> dict:
    document = _fixture("fail-material-discrepancy.json")
    first = document["observations"][0]
    corrected = copy.deepcopy(first)
    corrected["id"] = "OBS-002"
    corrected["iteration"] = 2
    corrected["screenshot_ref"] = "artifact://dashboard-corrected.png"
    corrected["discrepancies"][0]["resolved"] = True
    document["observations"].append(corrected)
    report = evaluate(document)
    assert report["status"] == "PASS"
    result = report["case_results"][0]
    assert result["observation_id"] == "OBS-002"
    assert result["history_count"] == 2
    assert result["unresolved_material_discrepancies"] == []
    return {"status": report["status"], "history_count": result["history_count"]}


def control_material_discrepancy_cannot_silently_disappear() -> dict:
    document = _fixture("fail-material-discrepancy.json")
    first = document["observations"][0]
    second = copy.deepcopy(first)
    second["id"] = "OBS-002"
    second["iteration"] = 2
    second["screenshot_ref"] = "artifact://dashboard-second.png"
    second["discrepancies"] = []
    document["observations"].append(second)
    report = evaluate(document)
    assert report["status"] == "FAIL"
    result = report["case_results"][0]
    assert result["unresolved_material_discrepancies"] == ["DISC-001"]
    return {"status": report["status"], "sticky_discrepancy": "DISC-001"}


def control_duplicate_case_iteration_rejected() -> dict:
    document = _fixture("pass.json")
    duplicate = copy.deepcopy(document["observations"][0])
    duplicate["id"] = "OBS-DUP"
    document["observations"].append(duplicate)
    message = _expect_error(lambda: validate_document(document), "only one observation")
    return {"rejected": message}


def control_not_run_is_not_success() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["interaction_status"] = "NOT_RUN"
    document["observations"][0]["accessibility_status"] = "NOT_RUN"
    report = evaluate(document)
    assert report["status"] == "INCOMPLETE"
    return {"status": report["status"]}


def control_unknown_case_reference_rejected() -> dict:
    document = _fixture("pass.json")
    document["observations"][0]["case_id"] = "unknown-case"
    message = _expect_error(lambda: validate_document(document), "unknown cases")
    return {"rejected": message}


def control_duplicate_case_rejected() -> dict:
    document = _fixture("pass.json")
    document["required_cases"].append(copy.deepcopy(document["required_cases"][0]))
    message = _expect_error(lambda: validate_document(document), "duplicate ids")
    return {"rejected": message}


def control_no_wcag_or_pixel_perfect_claim() -> dict:
    report = evaluate(_fixture("pass.json"))
    assert report["claims"] == {
        "browser_executed_by_evaluator": False,
        "wcag_conformance_claim": False,
        "pixel_perfect_claim": False,
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
    ("WV-01-pack-contract", control_pack_contract_loads),
    ("WV-02-manifest", control_manifest_contains_pack),
    ("WV-03-complete-pass", control_complete_fixture_passes),
    ("WV-04-missing-case", control_missing_required_case_is_incomplete),
    ("WV-05-material-discrepancy", control_material_discrepancy_fails),
    ("WV-06-interaction-failure", control_failed_interaction_fails),
    ("WV-07-accessibility-failure", control_accessibility_failure_fails),
    ("WV-08-accessibility-evidence", control_missing_accessibility_evidence_is_incomplete),
    ("WV-09-capture-stability", control_unstable_capture_is_incomplete),
    ("WV-10-capture-context", control_missing_capture_context_is_incomplete),
    ("WV-11-screenshot-required", control_missing_screenshot_is_incomplete),
    ("WV-12-advisory-proportionality", control_advisory_discrepancy_does_not_fail),
    ("WV-13-correction-loop", control_correction_loop_uses_latest_iteration),
    ("WV-14-sticky-material-discrepancy", control_material_discrepancy_cannot_silently_disappear),
    ("WV-15-unique-case-iteration", control_duplicate_case_iteration_rejected),
    ("WV-16-not-run-truth", control_not_run_is_not_success),
    ("WV-17-unknown-case", control_unknown_case_reference_rejected),
    ("WV-18-duplicate-case", control_duplicate_case_rejected),
    ("WV-19-non-claims", control_no_wcag_or_pixel_perfect_claim),
    ("WV-20-runtime-integrity", control_legacy_runtime_integrity),
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
        "schema": "sef.eval.web-visual-pack-m3.v1",
        "stage": "M3_WEB_EXPERIENCE_VISUAL_QUALITY",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "browser_calls": 0,
        "model_calls": 0,
        "network_calls": 0,
        "outcome_superiority_claim": False,
        "live_browser_claim": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
