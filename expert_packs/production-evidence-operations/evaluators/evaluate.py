#!/usr/bin/env python3
"""Evaluate structured deployment/post-deploy evidence for release operations."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "sef.production-evidence-operations.v1"
REPORT_SCHEMA = "sef.production-evidence-operations-report.v1"
STATUSES = {"PASS", "FAIL", "NOT_RUN", "INCONCLUSIVE", "N_A"}
ENVIRONMENT_KINDS = {"PREVIEW", "STAGING", "PRODUCTION"}
RECOVERY_STRATEGIES = {"ROLLBACK", "REDEPLOY_PREVIOUS", "ROLL_FORWARD", "NONE"}
RECOVERY_EVIDENCE_KINDS = {"REHEARSAL", "OBSERVED_RECOVERY", "CURRENT_RECOVERY", "NONE"}
OBSERVABILITY_IDS = {"logs", "error_visibility", "metrics", "alerting"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


class ProductionEvidenceError(ValueError):
    pass


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductionEvidenceError(f"{label} must be a non-empty string")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ProductionEvidenceError(f"{label} must be a compact stable identifier")
    return value


def _nullable_ref(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _status(value: Any, label: str, *, allow_na: bool = True) -> str:
    if value not in STATUSES:
        raise ProductionEvidenceError(f"{label} is invalid")
    if not allow_na and value == "N_A":
        raise ProductionEvidenceError(f"{label} cannot be N_A")
    return value


def _validate_release(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionEvidenceError("release must be an object")
    expected = {
        "id", "environment_kind", "target_ref", "planned_release_ref", "deployed_release_ref",
        "deployment_status", "deployment_ref", "runtime_identity_status", "runtime_identity_ref"
    }
    if set(value) != expected:
        raise ProductionEvidenceError(f"release keys must equal {sorted(expected)}")
    _item_id(value["id"], "release.id")
    if value["environment_kind"] not in ENVIRONMENT_KINDS:
        raise ProductionEvidenceError("release.environment_kind is invalid")
    for key in ("target_ref", "planned_release_ref", "deployed_release_ref"):
        _text(value[key], f"release.{key}")
    _status(value["deployment_status"], "release.deployment_status", allow_na=False)
    _nullable_ref(value["deployment_ref"], "release.deployment_ref")
    _status(value["runtime_identity_status"], "release.runtime_identity_status", allow_na=False)
    _nullable_ref(value["runtime_identity_ref"], "release.runtime_identity_ref")
    return value


def _validate_health(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"status", "evidence_ref"}:
        raise ProductionEvidenceError("health must contain exactly status and evidence_ref")
    _status(value["status"], "health.status", allow_na=False)
    _nullable_ref(value["evidence_ref"], "health.evidence_ref")
    return value


def _validate_smoke(value: Any, index: int) -> dict[str, Any]:
    label = f"smoke_checks[{index}]"
    if not isinstance(value, dict):
        raise ProductionEvidenceError(f"{label} must be an object")
    expected = {"id", "blocking", "status", "evidence_ref"}
    if set(value) != expected:
        raise ProductionEvidenceError(f"{label} keys must equal {sorted(expected)}")
    _item_id(value["id"], f"{label}.id")
    if not isinstance(value["blocking"], bool):
        raise ProductionEvidenceError(f"{label}.blocking must be boolean")
    _status(value["status"], f"{label}.status", allow_na=False)
    _nullable_ref(value["evidence_ref"], f"{label}.evidence_ref")
    return value


def _validate_observability(value: Any, index: int) -> dict[str, Any]:
    label = f"observability[{index}]"
    if not isinstance(value, dict):
        raise ProductionEvidenceError(f"{label} must be an object")
    expected = {"id", "required", "status", "evidence_ref"}
    if set(value) != expected:
        raise ProductionEvidenceError(f"{label} keys must equal {sorted(expected)}")
    if value["id"] not in OBSERVABILITY_IDS:
        raise ProductionEvidenceError(f"{label}.id is invalid")
    if not isinstance(value["required"], bool):
        raise ProductionEvidenceError(f"{label}.required must be boolean")
    status = _status(value["status"], f"{label}.status")
    _nullable_ref(value["evidence_ref"], f"{label}.evidence_ref")
    if value["required"] and status == "N_A":
        raise ProductionEvidenceError(f"{label}: required observability control cannot be N_A")
    if not value["required"] and status != "N_A":
        raise ProductionEvidenceError(f"{label}: non-required observability control must be N_A")
    if not value["required"] and value["evidence_ref"] is not None:
        raise ProductionEvidenceError(f"{label}: N_A observability control must not carry evidence")
    return value


def _validate_recovery(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionEvidenceError("recovery must be an object")
    expected = {"strategy", "status", "evidence_kind", "environment_kind", "evidence_ref"}
    if set(value) != expected:
        raise ProductionEvidenceError(f"recovery keys must equal {sorted(expected)}")
    if value["strategy"] not in RECOVERY_STRATEGIES:
        raise ProductionEvidenceError("recovery.strategy is invalid")
    status = _status(value["status"], "recovery.status")
    if value["evidence_kind"] not in RECOVERY_EVIDENCE_KINDS:
        raise ProductionEvidenceError("recovery.evidence_kind is invalid")
    if value["environment_kind"] not in ENVIRONMENT_KINDS:
        raise ProductionEvidenceError("recovery.environment_kind is invalid")
    _nullable_ref(value["evidence_ref"], "recovery.evidence_ref")
    if value["strategy"] == "NONE":
        if status != "N_A" or value["evidence_kind"] != "NONE" or value["evidence_ref"] is not None:
            raise ProductionEvidenceError("recovery strategy NONE requires status N_A, evidence_kind NONE and no evidence_ref")
    else:
        if status == "N_A":
            raise ProductionEvidenceError("configured recovery strategy cannot have status N_A")
        if value["evidence_kind"] == "NONE":
            raise ProductionEvidenceError("configured recovery strategy requires a recovery evidence kind")
    if value["evidence_kind"] == "REHEARSAL" and value["environment_kind"] == "PRODUCTION":
        raise ProductionEvidenceError("recovery rehearsal must not use PRODUCTION environment_kind")
    return value


def _validate_post_deploy(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionEvidenceError("post_deploy must be an object")
    expected = {"status", "window_ref", "evidence_ref"}
    if set(value) != expected:
        raise ProductionEvidenceError(f"post_deploy keys must equal {sorted(expected)}")
    _status(value["status"], "post_deploy.status", allow_na=False)
    _nullable_ref(value["window_ref"], "post_deploy.window_ref")
    _nullable_ref(value["evidence_ref"], "post_deploy.evidence_ref")
    return value


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise ProductionEvidenceError("root must be an object")
    expected = {"schema", "release", "health", "smoke_checks", "observability", "recovery", "post_deploy"}
    if set(document) != expected:
        raise ProductionEvidenceError(f"root keys must equal {sorted(expected)}")
    if document["schema"] != SCHEMA:
        raise ProductionEvidenceError(f"schema must equal {SCHEMA}")
    _validate_release(document["release"])
    _validate_health(document["health"])
    if not isinstance(document["smoke_checks"], list) or not document["smoke_checks"]:
        raise ProductionEvidenceError("smoke_checks must be a non-empty list")
    smoke = [_validate_smoke(item, i) for i, item in enumerate(document["smoke_checks"])]
    smoke_ids = [item["id"] for item in smoke]
    if len(smoke_ids) != len(set(smoke_ids)):
        raise ProductionEvidenceError("smoke_checks contain duplicate ids")
    if not any(item["blocking"] for item in smoke):
        raise ProductionEvidenceError("at least one smoke check must be blocking")
    if not isinstance(document["observability"], list):
        raise ProductionEvidenceError("observability must be a list")
    observability = [_validate_observability(item, i) for i, item in enumerate(document["observability"])]
    obs_ids = [item["id"] for item in observability]
    if len(obs_ids) != len(set(obs_ids)):
        raise ProductionEvidenceError("observability contains duplicate ids")
    if set(obs_ids) != OBSERVABILITY_IDS:
        raise ProductionEvidenceError(f"observability must account for exactly {sorted(OBSERVABILITY_IDS)}")
    if not any(item["required"] for item in observability):
        raise ProductionEvidenceError("at least one observability control must be required")
    _validate_recovery(document["recovery"])
    _validate_post_deploy(document["post_deploy"])
    return document


def evaluate(document: dict[str, Any]) -> dict[str, Any]:
    validate_document(document)
    failures: list[str] = []
    incomplete: list[str] = []
    warnings: list[str] = []

    release = document["release"]
    if release["deployment_status"] == "FAIL":
        failures.append("DEPLOYMENT_FAILED")
    elif release["deployment_status"] != "PASS":
        incomplete.append("DEPLOYMENT_NOT_PROVEN")
    elif release["deployment_ref"] is None:
        incomplete.append("DEPLOYMENT_EVIDENCE_MISSING")

    if release["runtime_identity_status"] == "FAIL":
        failures.append("RUNTIME_IDENTITY_MISMATCH")
    elif release["runtime_identity_status"] != "PASS":
        incomplete.append("RUNTIME_IDENTITY_NOT_PROVEN")
    elif release["runtime_identity_ref"] is None:
        incomplete.append("RUNTIME_IDENTITY_EVIDENCE_MISSING")

    health = document["health"]
    if health["status"] == "FAIL":
        failures.append("HEALTH_CHECK_FAILED")
    elif health["status"] != "PASS":
        incomplete.append("HEALTH_CHECK_NOT_PROVEN")
    elif health["evidence_ref"] is None:
        incomplete.append("HEALTH_EVIDENCE_MISSING")

    smoke_results = []
    for item in document["smoke_checks"]:
        reasons: list[str] = []
        if item["status"] == "FAIL":
            if item["blocking"]:
                failures.append("BLOCKING_SMOKE_FAILED:" + item["id"])
                status = "FAIL"
            else:
                warnings.append("NONBLOCKING_SMOKE_FAILED:" + item["id"])
                status = "WARN"
            reasons.append("SMOKE_FAILED")
        elif item["status"] != "PASS":
            if item["blocking"]:
                incomplete.append("BLOCKING_SMOKE_NOT_PROVEN:" + item["id"])
                status = "INCOMPLETE"
            else:
                warnings.append("NONBLOCKING_SMOKE_NOT_PROVEN:" + item["id"])
                status = "WARN"
            reasons.append("SMOKE_NOT_PROVEN")
        elif item["evidence_ref"] is None:
            if item["blocking"]:
                incomplete.append("BLOCKING_SMOKE_EVIDENCE_MISSING:" + item["id"])
                status = "INCOMPLETE"
            else:
                warnings.append("NONBLOCKING_SMOKE_EVIDENCE_MISSING:" + item["id"])
                status = "WARN"
            reasons.append("SMOKE_EVIDENCE_MISSING")
        else:
            status = "PASS"
        smoke_results.append({"id": item["id"], "blocking": item["blocking"], "status": status, "reasons": reasons})

    observability_results = []
    for item in document["observability"]:
        if not item["required"]:
            observability_results.append({"id": item["id"], "status": "N_A"})
            continue
        if item["status"] == "FAIL":
            failures.append("OBSERVABILITY_FAILED:" + item["id"])
            status = "FAIL"
        elif item["status"] != "PASS":
            incomplete.append("OBSERVABILITY_NOT_PROVEN:" + item["id"])
            status = "INCOMPLETE"
        elif item["evidence_ref"] is None:
            incomplete.append("OBSERVABILITY_EVIDENCE_MISSING:" + item["id"])
            status = "INCOMPLETE"
        else:
            status = "PASS"
        observability_results.append({"id": item["id"], "status": status})

    recovery = document["recovery"]
    if recovery["strategy"] == "NONE":
        failures.append("RECOVERY_STRATEGY_MISSING")
    elif recovery["status"] == "FAIL":
        failures.append("RECOVERY_VERIFICATION_FAILED")
    elif recovery["status"] != "PASS":
        incomplete.append("RECOVERY_NOT_PROVEN")
    elif recovery["evidence_ref"] is None:
        incomplete.append("RECOVERY_EVIDENCE_MISSING")

    post = document["post_deploy"]
    if post["status"] == "FAIL":
        failures.append("POST_DEPLOY_OBSERVATION_FAILED")
    elif post["status"] != "PASS":
        incomplete.append("POST_DEPLOY_OBSERVATION_NOT_PROVEN")
    else:
        if post["window_ref"] is None:
            incomplete.append("POST_DEPLOY_WINDOW_MISSING")
        if post["evidence_ref"] is None:
            incomplete.append("POST_DEPLOY_EVIDENCE_MISSING")

    if failures:
        overall = "FAIL"
    elif incomplete:
        overall = "INCOMPLETE"
    else:
        overall = "PASS"

    return {
        "schema": REPORT_SCHEMA,
        "status": overall,
        "release_id": release["id"],
        "environment_kind": release["environment_kind"],
        "failures": sorted(set(failures)),
        "incomplete": sorted(set(incomplete)),
        "warnings": sorted(set(warnings)),
        "smoke_results": smoke_results,
        "observability_results": observability_results,
        "claims": {
            "deployment_executed_by_evaluator": False,
            "production_write_authorized": False,
            "provider_specific_operations_claim": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.input.read_text(encoding="utf-8"))
        report = evaluate(document)
    except (OSError, json.JSONDecodeError, ProductionEvidenceError) as exc:
        print(json.dumps({"schema": REPORT_SCHEMA, "status": "HARNESS_ERROR", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
