#!/usr/bin/env python3
"""One-shot standard CHALLENGE grader for the frozen 38/38 DEV candidate.

All scenario contracts must be committed before this runner is executed. This
runner may add only predeclared challenge assertions; it never edits the runtime
or weakens a scenario after observing candidate output.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import run as core

SCHEMA = "sef.eval.challenge-standard-report.v1"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _plan_evidence_text(observed: dict[str, Any]) -> str:
    fields = (
        "definition_of_done",
        "implicit_professional_requirements",
        "architecture_questions",
        "implementation_guardrails",
        "verification_strategy",
        "procedures",
        "human_decisions_needed",
    )
    return "\n".join(_text(observed.get(field, [])) for field in fields)


def _evaluate_plan(sef: Path, scenario_path: Path, fixtures: Path) -> dict[str, Any]:
    scenario = core.load_json(scenario_path)
    validation = core.validate_scenario(scenario, scenario_path)
    if validation:
        return {"schema": "sef.eval.challenge-standard-result.v1", "scenario_id": scenario.get("id"), "status": "HARNESS_ERROR", "assertions": [], "limitations": validation}
    fixture = fixtures / str(scenario["fixture"])
    if not fixture.is_dir():
        return {"schema": "sef.eval.challenge-standard-result.v1", "scenario_id": scenario["id"], "status": "HARNESS_ERROR", "assertions": [], "limitations": [f"fixture not found: {fixture}"]}
    source_hash = core.sha256_file(sef)
    fixture_hash = core.sha256_tree(fixture)
    with tempfile.TemporaryDirectory(prefix=f"sef-challenge-{scenario['id'].lower()}-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture, repo)
        try:
            init = core.run_json([sys.executable, str(sef), "init", str(repo), "--brief", str(scenario.get("project_brief") or "Challenge fixture project.")])
            if init.get("status") != "PASS":
                raise RuntimeError(f"SEF init failed: {init}")
            installed = repo / ".sef/sef.py"
            runtime = core.run_json([sys.executable, str(installed), "runtime-info"])
            payload = core.run_json([sys.executable, str(installed), "plan", str(repo), "--request", str(scenario["request"]), "--save"])
            assertions, observed = core.grade_plan(scenario, payload)
            plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
            observed.update({
                "implicit_professional_requirements": plan.get("implicit_professional_requirements", []),
                "architecture_questions": plan.get("architecture_questions", []),
                "implementation_guardrails": plan.get("implementation_guardrails", []),
                "verification_strategy": plan.get("verification_strategy", []),
                "human_decisions_needed": plan.get("human_decisions_needed", []),
                "implementation_gate": plan.get("implementation_gate"),
            })
            return {
                "schema": "sef.eval.challenge-standard-result.v1",
                "scenario_id": scenario["id"],
                "scenario_set": "CHALLENGE",
                "layer": scenario["layer"],
                "severity": scenario["severity"],
                "sef_framework_version": runtime.get("framework_version"),
                "sef_source_sha256": source_hash,
                "fixture_revision": f"sha256:{fixture_hash}",
                "status": core.scenario_status(assertions),
                "observed": observed,
                "assertions": assertions,
                "limitations": [],
            }
        except Exception as exc:
            return {
                "schema": "sef.eval.challenge-standard-result.v1",
                "scenario_id": scenario.get("id"),
                "scenario_set": "CHALLENGE",
                "layer": scenario.get("layer"),
                "severity": scenario.get("severity"),
                "sef_source_sha256": source_hash,
                "fixture_revision": f"sha256:{fixture_hash}",
                "status": "HARNESS_ERROR",
                "observed": {},
                "assertions": [],
                "limitations": [f"{type(exc).__name__}: {exc}"],
            }


def _custom_assertions(scenario: dict[str, Any], result: dict[str, Any]) -> list[dict[str, Any]]:
    custom = scenario.get("challenge_expect") if isinstance(scenario.get("challenge_expect"), dict) else {}
    critical = scenario.get("severity") == "critical"
    observed = result.get("observed") if isinstance(result.get("observed"), dict) else {}
    assertions: list[dict[str, Any]] = []

    if scenario.get("phase") == "plan":
        plan_observed = observed
    else:
        plan_observed = observed.get("initial_plan") if isinstance(observed.get("initial_plan"), dict) else {}
    evidence_text = _plan_evidence_text(plan_observed)

    # Core v1 scenario grading historically supports exact/minimum risk. The
    # challenge contract for DIFF-003 predeclares a maximum initial risk; enforce
    # that contract here before the first holdout execution rather than silently
    # ignoring it.
    plan_expect = scenario.get("plan_expect") if isinstance(scenario.get("plan_expect"), dict) else {}
    risk_expect = plan_expect.get("risk") if isinstance(plan_expect.get("risk"), dict) else {}
    maximum = risk_expect.get("maximum")
    if maximum is not None:
        initial_risk = plan_observed.get("risk")
        if maximum in core.RISK_ORDER and initial_risk in core.RISK_ORDER:
            passed: bool | None = core.RISK_ORDER[initial_risk] <= core.RISK_ORDER[maximum]
        else:
            passed = None
        assertions.append(core.assertion(
            "challenge-initial-risk-maximum",
            passed,
            maximum,
            initial_risk,
            critical,
        ))

    for index, group in enumerate(custom.get("required_dod_term_groups", []), 1):
        terms = list(group) if isinstance(group, list) else []
        matched = [str(term) for term in terms if str(term).lower() in evidence_text.lower()]
        assertions.append(core.assertion(
            f"challenge-plan-obligation-group-{index}",
            bool(terms) and bool(matched),
            {"any_of": terms},
            {"matched": matched},
            critical,
        ))

    human_text = _text(plan_observed.get("human_decisions_needed", []))
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
                passed = core.RISK_ORDER[actual_risk] > core.RISK_ORDER[initial_risk]
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
    result = _evaluate_plan(sef, scenario_path, fixtures) if scenario.get("phase") == "plan" else core.evaluate_scenario(sef, scenario_path, fixtures)
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
