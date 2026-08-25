#!/usr/bin/env python3
"""Adversarial qualification for M5 mission-specific evidence scope."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evals"))

import run_m5_evidence_ingestion as base  # noqa: E402
from delivery_missions import (  # noqa: E402
    MissionEvidenceError,
    evaluate_execution_result,
    seal_execution_result,
)

REPORT_PATH = ROOT / "eval-results" / "m5-evidence-scope-report.json"


def _mutate_pack_observation(result: dict, root: Path, pack_id: str, mutate) -> dict:
    observation_ref = next(
        item["artifact_ref"] for item in result["pack_observations"] if item["pack_id"] == pack_id
    )
    artifact = next(item for item in result["artifacts"] if item["ref"] == observation_ref)
    path = root / artifact["path"]
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    data = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
    path.write_bytes(data)
    artifact["sha256"] = hashlib.sha256(data).hexdigest()
    return seal_execution_result(result)


def _expect_error(fn, contains: str) -> str:
    try:
        fn()
    except MissionEvidenceError as exc:
        message = str(exc)
        assert contains in message, (contains, message)
        return message
    raise AssertionError("expected MissionEvidenceError")


def control_local_rejects_preview_visual_scope() -> dict:
    spec = base._spec()
    state = base._state_at(spec, "IMPLEMENTED")
    decision = base._decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = base._successful_result(spec, state, decision, root)
        result = _mutate_pack_observation(
            result,
            root,
            "web-experience-visual-quality",
            lambda document: document["target"].update({"kind": "preview"}),
        )
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "target.kind must be local",
        )
        return {"rejected": message}


def control_preview_rejects_local_visual_scope() -> dict:
    spec = base._spec()
    state = base._state_at(spec, "VERIFIED_LOCAL")
    decision = base._decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = base._successful_result(spec, state, decision, root)
        result = _mutate_pack_observation(
            result,
            root,
            "web-experience-visual-quality",
            lambda document: document["target"].update({"kind": "local"}),
        )
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "target.kind must be preview",
        )
        return {"rejected": message}


def control_release_readiness_rejects_local_visual_scope() -> dict:
    spec = base._spec()
    state = base._state_at(spec, "PREVIEW_VERIFIED")
    decision = base._decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = base._successful_result(spec, state, decision, root)
        result = _mutate_pack_observation(
            result,
            root,
            "web-experience-visual-quality",
            lambda document: document["target"].update({"kind": "local"}),
        )
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "target.kind must be preview",
        )
        return {"rejected": message}


def control_production_verification_rejects_staging_operations_scope() -> dict:
    spec = base._spec()
    state = base._state_at(spec, "DEPLOYED")
    decision = base._decision(spec, state)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        result = base._successful_result(spec, state, decision, root)
        result = _mutate_pack_observation(
            result,
            root,
            "production-evidence-operations",
            lambda document: document["release"].update({"environment_kind": "STAGING"}),
        )
        message = _expect_error(
            lambda: evaluate_execution_result(spec, state, decision, result, artifact_root=root),
            "release.environment_kind must be PRODUCTION",
        )
        return {"rejected": message}


CONTROLS = [
    ("M5S-01-local-rejects-preview", control_local_rejects_preview_visual_scope),
    ("M5S-02-preview-rejects-local", control_preview_rejects_local_visual_scope),
    ("M5S-03-release-rejects-local", control_release_readiness_rejects_local_visual_scope),
    ("M5S-04-production-rejects-staging", control_production_verification_rejects_staging_operations_scope),
]


def main() -> int:
    results = []
    for control_id, fn in CONTROLS:
        try:
            detail = fn()
            results.append({"id": control_id, "status": "PASS", "detail": detail})
        except Exception as exc:
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})
    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.m5-evidence-scope.v1",
        "stage": "M5_EVIDENCE_SCOPE_ALIGNMENT",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "status": "PASS" if passed == len(results) else "FAIL",
        "model_calls": 0,
        "network_calls": 0,
        "provider_calls": 0,
        "tool_execution_calls": 0,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
