#!/usr/bin/env python3
"""One-shot standard CHALLENGE grader for the frozen 38/38 DEV candidate.

All scenario contracts must be committed before this runner is executed. This
runner may add only predeclared challenge assertions; it never edits the runtime
or weakens a scenario after observing candidate output.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import run as core
import run_dev_closure_extra as semantic

SCHEMA = "sef.eval.challenge-standard-report.v1"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _group_match(text: str, terms: list[Any]) -> bool:
    low = text.lower()
    return any(str(term).lower() in low for term in terms)


def _custom_assertions(scenario: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    custom = scenario.get("challenge_expect") if isinstance(scenario.get("challenge_expect"), dict) else {}
    if not custom:
        return []
    critical = scenario.get("severity") == "critical"
    observed = result.get("observed") if isinstance(result.get("observed"), dict) else {}
    assertions: list[dict[str, Any]] = []

    if scenario.get("phase") == "plan":
        plan_observed = observed
    else:
        plan_observed = observed.get("initial_plan") if isinstance(observed.get("initial_plan"), dict) else {}
    dod_text = _text(plan_observed.get("definition_of_done", []))

    for index, group in enumerate(custom.get("required_dod_term_groups", []), 1):
        terms = list(group) if isinstance(group, list) else []
        matched = [str(term) for term in terms if str(term).lower() in dod_text.lower()]
        assertions.append(core.assertion(
            f"challenge-dod-group-{index}",
            bool(terms) and bool(matched),
            {"any_of": terms},
            {"matched": matched},
            critical,
        ))

    human_text = _text(observed.get("human_decisions_needed", []))
    for term in custom.get("required_human_decision_terms", []):
        present = str(term).lower() in human_text.lower()
        assertions.append(core.assertion(
            f"challenge-human-decision:{term}", present, True, present, critical
        ))

    if scenario.get("phase") == "verify":
        actual = observed.get("actual_diff") if isinstance(observed.get("actual_diff"), dict) else {}
        new_procedures = set(actual.get("newly_required_procedures") or [])
        for procedure in custom.get("forbidden_new_procedures", []):
            assertions.append(core.assertion(
                f"challenge-forbidden-new-procedure:{procedure}",
                procedure not in new_procedures,
                False,
                procedure in new_procedures,
                critical,
            ))

        if custom.get("require_diff_escalation"):
            initial_risk = plan_observed.get("risk")
            actual_risk = actual.get("risk")
            if initial_risk in core.RISK_ORDER and actual_risk in core.RISK_ORDER:
                passed: bool | None = core.RISK_ORDER[actual_risk] > core.RISK_ORDER[initial_risk]
            else:
                passed = None
            assertions.append(core.assertion(
                "challenge-actual-diff-risk-escalation",
                passed,
                "actual risk strictly higher than initial-plan risk",
                {"initial": initial_risk, "actual": actual_risk},
                critical,
            ))

        pack_any = [str(x) for x in custom.get("required_actual_pack_any", [])]
        if pack_any:
            actual_packs = set(actual.get("packs") or [])
            matched = sorted(set(pack_any) & actual_packs)
            assertions.append(core.assertion(
                "challenge-required-actual-pack-any",
                bool(matched),
                {"any_of": pack_any},
                matched,
                critical,
            ))

    return assertions


def evaluate(sef: Path, scenario_path: Path, fixtures: Path) -> dict[str, Any]:
    scenario = core.load_json(scenario_path)
    if scenario.get("set") != "CHALLENGE":
        return {
            "schema": SCHEMA,
            "scenario_id": scenario.get("id", scenario_path.stem),
            "status": "HARNESS_ERROR",
            "assertions": [],
            "limitations": ["standard challenge runner accepts CHALLENGE scenarios only"],
        }
    if scenario.get("phase") == "plan":
        result = semantic.evaluate_plan(sef, scenario_path, fixtures)
    else:
        result = core.evaluate_scenario(sef, scenario_path, fixtures)
    if result.get("status") == "HARNESS_ERROR":
        return result
    assertions = list(result.get("assertions") or [])
    assertions.extend(_custom_assertions(scenario, result))
    result["assertions"] = assertions
    result["status"] = core.scenario_status(assertions)
    result["schema"] = "sef.eval.challenge-standard-result.v1"
    return result


def main() -> int:
    root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument("--sef", default=str(root.parent / "sef.py"))
    p.add_argument("--scenarios", default=str(root / "scenarios/challenge"))
    p.add_argument("--fixtures", default=str(root / "fixtures"))
    p.add_argument("--ids", required=True)
    p.add_argument("--expected-sef-sha256", required=True)
    p.add_argument("--output")
    a = p.parse_args()

    sef = Path(a.sef).resolve()
    actual_sha = core.sha256_file(sef)
    if actual_sha != a.expected_sef_sha256:
        report = {"schema": SCHEMA, "status": "HARNESS_ERROR", "reason": "SEF_SHA256_MISMATCH", "expected": a.expected_sef_sha256, "observed": actual_sha, "results": []}
        encoded = json.dumps(report, indent=2, sort_keys=True)
        if a.output: Path(a.output).write_text(encoded + "\n", encoding="utf-8")
        print(encoded); return 2

    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    paths = sorted(Path(a.scenarios).glob("*.json"))
    by_id = {core.load_json(path).get("id"): path for path in paths}
    missing = [sid for sid in ids if sid not in by_id]
    unexpected = sorted(set(by_id) - set(ids))
    if missing or unexpected or len(by_id) != len(ids):
        report = {"schema": SCHEMA, "status": "HARNESS_ERROR", "reason": "SCENARIO_ACCOUNTING_MISMATCH", "missing": missing, "unexpected": unexpected, "results": []}
        encoded = json.dumps(report, indent=2, sort_keys=True)
        if a.output: Path(a.output).write_text(encoded + "\n", encoding="utf-8")
        print(encoded); return 2

    results = [evaluate(sef, by_id[sid], Path(a.fixtures).resolve()) for sid in ids]
    summary = core.summarize(results)
    report = {
        "schema": SCHEMA,
        "status": "PASS" if not any(r.get("status") == "HARNESS_ERROR" for r in results) else "HARNESS_ERROR",
        "sef_source_sha256": actual_sha,
        "scenario_ids": ids,
        "summary": summary,
        "results": results,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if a.output: Path(a.output).write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if report["status"] == "HARNESS_ERROR": return 2
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
