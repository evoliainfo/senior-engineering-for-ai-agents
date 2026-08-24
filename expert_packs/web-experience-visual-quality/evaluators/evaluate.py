#!/usr/bin/env python3
"""Evaluate structured browser/visual evidence for the web visual-quality pack.

This evaluator never performs browser work itself. It grades observations
collected by the active harness and distinguishes observed defects from missing
or inconclusive evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "sef.web-visual-observations.v1"
REPORT_SCHEMA = "sef.web-visual-quality-report.v1"
OBS_STATUSES = {"PASS", "FAIL", "NOT_RUN", "INCONCLUSIVE"}
SEVERITIES = {"BLOCKER", "MATERIAL", "ADVISORY"}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")


class VisualEvidenceError(ValueError):
    pass


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VisualEvidenceError(f"{label} must be a non-empty string")
    return value


def _item_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise VisualEvidenceError(f"{label} must be a compact stable identifier")
    return value


def _unique_ids(items: list[dict[str, Any]], label: str) -> None:
    ids = [_item_id(item.get("id"), f"{label}.id") for item in items]
    if len(ids) != len(set(ids)):
        raise VisualEvidenceError(f"{label} contains duplicate ids")


def _validate_case(case: Any, index: int) -> dict[str, Any]:
    label = f"required_cases[{index}]"
    if not isinstance(case, dict):
        raise VisualEvidenceError(f"{label} must be an object")
    expected = {"id", "state", "viewport", "accessibility_required"}
    if set(case) != expected:
        raise VisualEvidenceError(f"{label} keys must equal {sorted(expected)}")
    _item_id(case["id"], f"{label}.id")
    _text(case["state"], f"{label}.state")
    _text(case["viewport"], f"{label}.viewport")
    if not isinstance(case["accessibility_required"], bool):
        raise VisualEvidenceError(f"{label}.accessibility_required must be boolean")
    return case


def _validate_discrepancy(item: Any, label: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise VisualEvidenceError(f"{label} must be an object")
    expected = {"id", "severity", "statement", "resolved"}
    if set(item) != expected:
        raise VisualEvidenceError(f"{label} keys must equal {sorted(expected)}")
    _item_id(item["id"], f"{label}.id")
    if item["severity"] not in SEVERITIES:
        raise VisualEvidenceError(f"{label}.severity is invalid")
    _text(item["statement"], f"{label}.statement")
    if not isinstance(item["resolved"], bool):
        raise VisualEvidenceError(f"{label}.resolved must be boolean")
    return item


def _validate_observation(obs: Any, index: int) -> dict[str, Any]:
    label = f"observations[{index}]"
    if not isinstance(obs, dict):
        raise VisualEvidenceError(f"{label} must be an object")
    expected = {
        "id", "case_id", "iteration", "interaction_status", "screenshot_ref",
        "capture_stable", "accessibility_status", "accessibility_ref", "discrepancies"
    }
    if set(obs) != expected:
        raise VisualEvidenceError(f"{label} keys must equal {sorted(expected)}")
    _item_id(obs["id"], f"{label}.id")
    _item_id(obs["case_id"], f"{label}.case_id")
    if not isinstance(obs["iteration"], int) or isinstance(obs["iteration"], bool) or obs["iteration"] < 1:
        raise VisualEvidenceError(f"{label}.iteration must be integer >= 1")
    if obs["interaction_status"] not in OBS_STATUSES:
        raise VisualEvidenceError(f"{label}.interaction_status is invalid")
    if obs["screenshot_ref"] is not None:
        _text(obs["screenshot_ref"], f"{label}.screenshot_ref")
    if not isinstance(obs["capture_stable"], bool):
        raise VisualEvidenceError(f"{label}.capture_stable must be boolean")
    if obs["accessibility_status"] not in OBS_STATUSES:
        raise VisualEvidenceError(f"{label}.accessibility_status is invalid")
    if obs["accessibility_ref"] is not None:
        _text(obs["accessibility_ref"], f"{label}.accessibility_ref")
    if not isinstance(obs["discrepancies"], list):
        raise VisualEvidenceError(f"{label}.discrepancies must be a list")
    validated = [_validate_discrepancy(item, f"{label}.discrepancies[{i}]") for i, item in enumerate(obs["discrepancies"])]
    _unique_ids(validated, f"{label}.discrepancies")
    return obs


def validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise VisualEvidenceError("root must be an object")
    expected = {"schema", "target", "required_cases", "observations"}
    if set(document) != expected:
        raise VisualEvidenceError(f"root keys must equal {sorted(expected)}")
    if document["schema"] != SCHEMA:
        raise VisualEvidenceError(f"schema must equal {SCHEMA}")
    target = document["target"]
    if not isinstance(target, dict) or set(target) != {"kind", "locator"}:
        raise VisualEvidenceError("target must contain exactly kind and locator")
    _text(target["kind"], "target.kind")
    _text(target["locator"], "target.locator")
    if not isinstance(document["required_cases"], list) or not document["required_cases"]:
        raise VisualEvidenceError("required_cases must be a non-empty list")
    cases = [_validate_case(item, i) for i, item in enumerate(document["required_cases"])]
    _unique_ids(cases, "required_cases")
    if not isinstance(document["observations"], list):
        raise VisualEvidenceError("observations must be a list")
    observations = [_validate_observation(item, i) for i, item in enumerate(document["observations"])]
    _unique_ids(observations, "observations")
    case_ids = {item["id"] for item in cases}
    unknown = sorted({item["case_id"] for item in observations} - case_ids)
    if unknown:
        raise VisualEvidenceError(f"observations reference unknown cases: {unknown}")
    return document


def evaluate(document: dict[str, Any]) -> dict[str, Any]:
    validate_document(document)
    by_case: dict[str, list[dict[str, Any]]] = {}
    for obs in document["observations"]:
        by_case.setdefault(obs["case_id"], []).append(obs)
    for items in by_case.values():
        items.sort(key=lambda item: (item["iteration"], item["id"]))

    case_results = []
    overall = "PASS"
    for case in document["required_cases"]:
        history = by_case.get(case["id"], [])
        if not history:
            case_results.append({"case_id": case["id"], "status": "INCOMPLETE", "reason": "MISSING_OBSERVATION"})
            overall = "INCOMPLETE" if overall == "PASS" else overall
            continue
        current = history[-1]
        incomplete_reasons: list[str] = []
        fail_reasons: list[str] = []
        if current["interaction_status"] == "FAIL":
            fail_reasons.append("INTERACTION_FAILED")
        elif current["interaction_status"] != "PASS":
            incomplete_reasons.append("INTERACTION_NOT_PROVEN")
        if current["screenshot_ref"] is None:
            incomplete_reasons.append("VISUAL_CAPTURE_MISSING")
        if not current["capture_stable"]:
            incomplete_reasons.append("CAPTURE_NOT_COMPARABLE")
        if case["accessibility_required"]:
            if current["accessibility_status"] == "FAIL":
                fail_reasons.append("ACCESSIBILITY_FAILED")
            elif current["accessibility_status"] != "PASS":
                incomplete_reasons.append("ACCESSIBILITY_NOT_PROVEN")
            if current["accessibility_ref"] is None:
                incomplete_reasons.append("ACCESSIBILITY_EVIDENCE_MISSING")
        unresolved_material = [
            item["id"] for item in current["discrepancies"]
            if not item["resolved"] and item["severity"] in {"BLOCKER", "MATERIAL"}
        ]
        if unresolved_material:
            fail_reasons.append("UNRESOLVED_MATERIAL_DISCREPANCY")
        if fail_reasons:
            status = "FAIL"
            reason = ",".join(sorted(set(fail_reasons)))
            overall = "FAIL"
        elif incomplete_reasons:
            status = "INCOMPLETE"
            reason = ",".join(sorted(set(incomplete_reasons)))
            if overall == "PASS":
                overall = "INCOMPLETE"
        else:
            status = "PASS"
            reason = "EVIDENCE_SUFFICIENT"
        case_results.append({
            "case_id": case["id"],
            "status": status,
            "reason": reason,
            "observation_id": current["id"],
            "iteration": current["iteration"],
            "history_count": len(history),
            "unresolved_material_discrepancies": unresolved_material,
        })

    return {
        "schema": REPORT_SCHEMA,
        "status": overall,
        "target": document["target"],
        "required_case_count": len(document["required_cases"]),
        "observed_case_count": len({item["case_id"] for item in document["observations"]}),
        "case_results": case_results,
        "claims": {
            "browser_executed_by_evaluator": False,
            "wcag_conformance_claim": False,
            "pixel_perfect_claim": False,
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
    except (OSError, json.JSONDecodeError, VisualEvidenceError) as exc:
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
