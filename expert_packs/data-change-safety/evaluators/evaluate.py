#!/usr/bin/env python3
"""Evaluate structured rehearsal/recovery evidence for data changes.

The evaluator never performs database work itself. It grades evidence collected
through the active harness and distinguishes observed unsafe conditions from
missing or inconclusive evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "sef.data-change-safety-observations.v1"
REPORT_SCHEMA = "sef.data-change-safety-report.v1"
STATUSES = {"PASS", "FAIL", "NOT_RUN", "INCONCLUSIVE", "N_A"}
CHANGE_KINDS = {"MIGRATION", "BACKFILL", "DATA_TRANSFORM", "DESTRUCTIVE_CLEANUP"}
REHEARSAL_ENVIRONMENTS = {"SANDBOX", "PREVIEW"}
RECOVERY_STRATEGIES = {"ROLLBACK", "RESTORE", "FORWARD_FIX", "NONE"}
CONTROL_IDS = {"idempotency", "resumability", "chunking", "compatibility"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


class DataChangeEvidenceError(ValueError):
    pass


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataChangeEvidenceError(f"{label} must be a non-empty string")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise DataChangeEvidenceError(f"{label} must be a compact stable identifier")
    return value


def _nullable_ref(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _status(value: Any, label: str) -> str:
    if value not in STATUSES:
        raise DataChangeEvidenceError(f"{label} is invalid")
    return value


def _validate_change(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DataChangeEvidenceError("change must be an object")
    expected = {"id", "kind", "target_environment", "destructive", "planned_change_ref", "actual_change_ref", "scope_status"}
    if set(value) != expected:
        raise DataChangeEvidenceError(f"change keys must equal {sorted(expected)}")
    _item_id(value["id"], "change.id")
    if value["kind"] not in CHANGE_KINDS:
        raise DataChangeEvidenceError("change.kind is invalid")
    _text(value["target_environment"], "change.target_environment")
    if not isinstance(value["destructive"], bool):
        raise DataChangeEvidenceError("change.destructive must be boolean")
    if value["kind"] == "DESTRUCTIVE_CLEANUP" and not value["destructive"]:
        raise DataChangeEvidenceError("DESTRUCTIVE_CLEANUP must set change.destructive=true")
    _text(value["planned_change_ref"], "change.planned_change_ref")
    _text(value["actual_change_ref"], "change.actual_change_ref")
    _status(value["scope_status"], "change.scope_status")
    if value["scope_status"] == "N_A":
        raise DataChangeEvidenceError("change.scope_status cannot be N_A")
    return value


def _validate_rehearsal(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DataChangeEvidenceError("rehearsal must be an object")
    expected = {"status", "environment_kind", "environment_ref", "fixture_ref", "execution_ref", "verification_ref"}
    if set(value) != expected:
        raise DataChangeEvidenceError(f"rehearsal keys must equal {sorted(expected)}")
    status = _status(value["status"], "rehearsal.status")
    if status == "N_A":
        raise DataChangeEvidenceError("rehearsal.status cannot be N_A")
    if value["environment_kind"] not in REHEARSAL_ENVIRONMENTS:
        raise DataChangeEvidenceError("rehearsal.environment_kind must be SANDBOX or PREVIEW")
    for key in ("environment_ref", "fixture_ref", "execution_ref", "verification_ref"):
        _nullable_ref(value[key], f"rehearsal.{key}")
    return value


def _validate_recovery(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DataChangeEvidenceError("recovery must be an object")
    expected = {"strategy", "status", "evidence_ref", "backup_status", "backup_ref"}
    if set(value) != expected:
        raise DataChangeEvidenceError(f"recovery keys must equal {sorted(expected)}")
    if value["strategy"] not in RECOVERY_STRATEGIES:
        raise DataChangeEvidenceError("recovery.strategy is invalid")
    status = _status(value["status"], "recovery.status")
    evidence_ref = _nullable_ref(value["evidence_ref"], "recovery.evidence_ref")
    _status(value["backup_status"], "recovery.backup_status")
    _nullable_ref(value["backup_ref"], "recovery.backup_ref")
    if value["strategy"] == "NONE":
        if status != "N_A" or evidence_ref is not None:
            raise DataChangeEvidenceError("recovery strategy NONE requires status N_A and no evidence_ref")
    elif status == "N_A":
        raise DataChangeEvidenceError("non-NONE recovery strategy cannot use status N_A")
    return value


def _validate_invariant(value: Any, index: int) -> dict[str, Any]:
    label = f"invariants[{index}]"
    if not isinstance(value, dict):
        raise DataChangeEvidenceError(f"{label} must be an object")
    expected = {"id", "statement", "critical", "pre_status", "pre_ref", "post_status", "post_ref"}
    if set(value) != expected:
        raise DataChangeEvidenceError(f"{label} keys must equal {sorted(expected)}")
    _item_id(value["id"], f"{label}.id")
    _text(value["statement"], f"{label}.statement")
    if not isinstance(value["critical"], bool):
        raise DataChangeEvidenceError(f"{label}.critical must be boolean")
    for key in ("pre_status", "post_status"):
        status = _status(value[key], f"{label}.{key}")
        if status == "N_A":
            raise DataChangeEvidenceError(f"{label}.{key} cannot be N_A")
    _nullable_ref(value["pre_ref"], f"{label}.pre_ref")
    _nullable_ref(value["post_ref"], f"{label}.post_ref")
    return value


def _validate_control(value: Any, index: int) -> dict[str, Any]:
    label = f"controls[{index}]"
    if not isinstance(value, dict):
        raise DataChangeEvidenceError(f"{label} must be an object")
    expected = {"id", "required", "status", "evidence_ref"}
    if set(value) != expected:
        raise DataChangeEvidenceError(f"{label} keys must equal {sorted(expected)}")
    if value["id"] not in CONTROL_IDS:
        raise DataChangeEvidenceError(f"{label}.id is invalid")
    if not isinstance(value["required"], bool):
        raise DataChangeEvidenceError(f"{label}.required must be boolean")
    status = _status(value["status"], f"{label}.status")
    _nullable_ref(value["evidence_ref"], f"{label}.evidence_ref")
    if value["required"] and status == "N_A":
        raise DataChangeEvidenceError(f"{label}: required control cannot be N_A")
    if not value["required"] and status != "N_A":
        raise DataChangeEvidenceError(f"{label}: non-required control must be N_A")
    if not value["required"] and value["evidence_ref"] is not None:
        raise DataChangeEvidenceError(f"{label}: N_A control must not carry evidence")
    return value


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise DataChangeEvidenceError("root must be an object")
    expected = {"schema", "change", "rehearsal", "recovery", "invariants", "controls"}
    if set(document) != expected:
        raise DataChangeEvidenceError(f"root keys must equal {sorted(expected)}")
    if document["schema"] != SCHEMA:
        raise DataChangeEvidenceError(f"schema must equal {SCHEMA}")
    _validate_change(document["change"])
    _validate_rehearsal(document["rehearsal"])
    _validate_recovery(document["recovery"])
    if not isinstance(document["invariants"], list) or not document["invariants"]:
        raise DataChangeEvidenceError("invariants must be a non-empty list")
    invariants = [_validate_invariant(item, i) for i, item in enumerate(document["invariants"])]
    invariant_ids = [item["id"] for item in invariants]
    if len(invariant_ids) != len(set(invariant_ids)):
        raise DataChangeEvidenceError("invariants contain duplicate ids")
    if not isinstance(document["controls"], list):
        raise DataChangeEvidenceError("controls must be a list")
    controls = [_validate_control(item, i) for i, item in enumerate(document["controls"])]
    control_ids = [item["id"] for item in controls]
    if len(control_ids) != len(set(control_ids)):
        raise DataChangeEvidenceError("controls contain duplicate ids")
    if set(control_ids) != CONTROL_IDS:
        raise DataChangeEvidenceError(f"controls must account for exactly {sorted(CONTROL_IDS)}")
    return document


def evaluate(document: dict[str, Any]) -> dict[str, Any]:
    validate_document(document)
    failures: list[str] = []
    incomplete: list[str] = []

    change = document["change"]
    if change["scope_status"] == "FAIL":
        failures.append("ACTUAL_CHANGE_SCOPE_MISMATCH")
    elif change["scope_status"] != "PASS":
        incomplete.append("CHANGE_SCOPE_NOT_PROVEN")

    rehearsal = document["rehearsal"]
    if rehearsal["status"] == "FAIL":
        failures.append("REHEARSAL_FAILED")
    elif rehearsal["status"] != "PASS":
        incomplete.append("REHEARSAL_NOT_PROVEN")
    if rehearsal["status"] == "PASS":
        for key, reason in (
            ("environment_ref", "REHEARSAL_ENVIRONMENT_EVIDENCE_MISSING"),
            ("fixture_ref", "REHEARSAL_FIXTURE_EVIDENCE_MISSING"),
            ("execution_ref", "REHEARSAL_EXECUTION_EVIDENCE_MISSING"),
            ("verification_ref", "REHEARSAL_VERIFICATION_EVIDENCE_MISSING"),
        ):
            if rehearsal[key] is None:
                incomplete.append(reason)

    invariant_results = []
    for invariant in document["invariants"]:
        inv_failures: list[str] = []
        inv_incomplete: list[str] = []
        for phase in ("pre", "post"):
            status = invariant[f"{phase}_status"]
            ref = invariant[f"{phase}_ref"]
            if status == "FAIL":
                inv_failures.append(f"{phase.upper()}_INVARIANT_FAILED")
            elif status != "PASS":
                inv_incomplete.append(f"{phase.upper()}_INVARIANT_NOT_PROVEN")
            elif ref is None:
                inv_incomplete.append(f"{phase.upper()}_INVARIANT_EVIDENCE_MISSING")
        if inv_failures:
            failures.append(("CRITICAL_" if invariant["critical"] else "") + "INVARIANT_FAILED:" + invariant["id"])
            status = "FAIL"
        elif inv_incomplete:
            incomplete.append("INVARIANT_INCOMPLETE:" + invariant["id"])
            status = "INCOMPLETE"
        else:
            status = "PASS"
        invariant_results.append({"id": invariant["id"], "status": status, "critical": invariant["critical"], "reasons": inv_failures + inv_incomplete})

    control_results = []
    for control in document["controls"]:
        if not control["required"]:
            control_results.append({"id": control["id"], "status": "N_A"})
            continue
        if control["status"] == "FAIL":
            failures.append("CONTROL_FAILED:" + control["id"])
            status = "FAIL"
        elif control["status"] != "PASS":
            incomplete.append("CONTROL_NOT_PROVEN:" + control["id"])
            status = "INCOMPLETE"
        elif control["evidence_ref"] is None:
            incomplete.append("CONTROL_EVIDENCE_MISSING:" + control["id"])
            status = "INCOMPLETE"
        else:
            status = "PASS"
        control_results.append({"id": control["id"], "status": status})

    recovery = document["recovery"]
    if recovery["strategy"] == "NONE":
        failures.append("RECOVERY_STRATEGY_MISSING")
    else:
        if recovery["status"] == "FAIL":
            failures.append("RECOVERY_EXERCISE_FAILED")
        elif recovery["status"] != "PASS":
            incomplete.append("RECOVERY_NOT_PROVEN")
        elif recovery["evidence_ref"] is None:
            incomplete.append("RECOVERY_EVIDENCE_MISSING")

    if change["destructive"]:
        if recovery["backup_status"] == "FAIL":
            failures.append("BACKUP_FAILED")
        elif recovery["backup_status"] != "PASS":
            incomplete.append("BACKUP_NOT_PROVEN")
        elif recovery["backup_ref"] is None:
            incomplete.append("BACKUP_EVIDENCE_MISSING")
    else:
        if recovery["backup_status"] not in {"PASS", "N_A"}:
            if recovery["backup_status"] == "FAIL":
                failures.append("OPTIONAL_BACKUP_FAILED")
            else:
                incomplete.append("OPTIONAL_BACKUP_INCONCLUSIVE")
        if recovery["backup_status"] == "PASS" and recovery["backup_ref"] is None:
            incomplete.append("BACKUP_EVIDENCE_MISSING")
        if recovery["backup_status"] == "N_A" and recovery["backup_ref"] is not None:
            incomplete.append("BACKUP_N_A_WITH_EVIDENCE")

    if failures:
        overall = "FAIL"
    elif incomplete:
        overall = "INCOMPLETE"
    else:
        overall = "PASS"

    return {
        "schema": REPORT_SCHEMA,
        "status": overall,
        "change_id": change["id"],
        "change_kind": change["kind"],
        "failures": sorted(set(failures)),
        "incomplete": sorted(set(incomplete)),
        "invariant_results": invariant_results,
        "control_results": control_results,
        "claims": {
            "database_executed_by_evaluator": False,
            "production_change_authorized": False,
            "provider_specific_correctness_claim": False,
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
    except (OSError, json.JSONDecodeError, DataChangeEvidenceError) as exc:
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
