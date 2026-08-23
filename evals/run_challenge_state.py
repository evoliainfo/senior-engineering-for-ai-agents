#!/usr/bin/env python3
"""Stateful one-shot CHALLENGE grader for evidence semantics."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import run as core

SCHEMA = "sef.eval.challenge-state-result.v1"
SCENARIO_SCHEMA = "sef.eval.challenge-state.v1"


def load(path: Path) -> dict[str, Any]:
    return core.load_json(path)


def validate(s: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ("schema", "id", "set", "layer", "family", "severity", "fixture", "request", "expect"):
        if key not in s:
            errors.append(f"missing {key}")
    if s.get("schema") != SCENARIO_SCHEMA:
        errors.append(f"wrong schema: {s.get('schema')}")
    if s.get("set") != "CHALLENGE" or s.get("layer") != "L1":
        errors.append("state runner accepts CHALLENGE/L1 only")
    if s.get("id") != "EVID-002":
        errors.append("state runner is locked to EVID-002 for this holdout")
    return errors


def result_assert(assertion_id: str, passed: bool, expected: Any, observed: Any, critical: bool = True) -> dict[str, Any]:
    return core.assertion(assertion_id, passed, expected, observed, critical)


def evaluate(sef: Path, scenario: dict[str, Any], fixture_root: Path) -> dict[str, Any]:
    errors = validate(scenario)
    if errors:
        return {"schema": SCHEMA, "scenario_id": scenario.get("id"), "status": "HARNESS_ERROR", "assertions": [], "limitations": errors}
    fixture = fixture_root / str(scenario["fixture"])
    if not fixture.is_dir():
        return {"schema": SCHEMA, "scenario_id": scenario["id"], "status": "HARNESS_ERROR", "assertions": [], "limitations": [f"fixture not found: {fixture}"]}
    source_hash = core.sha256_file(sef)
    with tempfile.TemporaryDirectory(prefix="sef-challenge-evid002-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture, repo)
        try:
            init = core.run_json([sys.executable, str(sef), "init", str(repo), "--brief", "Security-sensitive service with required release verification evidence."])
            if init.get("status") != "PASS":
                raise RuntimeError(f"SEF init failed: {init}")
            installed = repo / ".sef/sef.py"
            core.git_checkpoint(repo, "eval: challenge evidence fixture initialized")
            record = core.run_json([
                sys.executable, str(installed), "record-evidence", str(repo),
                "challenge-security-tool", "UNAVAILABLE",
                "--detail", "Required security verification provider is unavailable for this candidate evaluation.",
                "--source", "challenge-harness",
            ])
            release = core.run_json([sys.executable, str(installed), "release", str(repo)])
            expect = scenario["expect"]
            critical = scenario.get("severity") == "critical"
            recorded = record.get("recorded") if isinstance(record.get("recorded"), dict) else {}
            aggregate = record.get("aggregate") if isinstance(record.get("aggregate"), dict) else {}
            evidence = release.get("evidence") if isinstance(release.get("evidence"), dict) else {}
            aggregate_checks = aggregate.get("checks") if isinstance(aggregate.get("checks"), list) else []
            check_states = [str(c.get("state")) for c in aggregate_checks if isinstance(c, dict)]
            assertions = [
                result_assert("record-command-status", record.get("status") == "PASS", "PASS", record.get("status"), critical),
                result_assert("recorded-state", recorded.get("state") == expect["record_state"], expect["record_state"], recorded.get("state"), critical),
                result_assert("aggregate-state", aggregate.get("state") == expect["aggregate_state"], expect["aggregate_state"], aggregate.get("state"), critical),
                result_assert("release-status", release.get("status") == expect["release_status"], expect["release_status"], release.get("status"), critical),
                result_assert("release-evidence-not-pass", evidence.get("state") != "PASS", "not PASS", evidence.get("state"), critical),
            ]
            for forbidden in expect.get("forbidden_states", []):
                assertions.append(result_assert(
                    f"forbidden-evidence-state:{forbidden}",
                    forbidden not in check_states and recorded.get("state") != forbidden,
                    False,
                    {"recorded": recorded.get("state"), "aggregate_checks": check_states},
                    critical,
                ))
            return {
                "schema": SCHEMA,
                "scenario_id": scenario["id"],
                "scenario_set": "CHALLENGE",
                "layer": "L1",
                "severity": scenario["severity"],
                "sef_source_sha256": source_hash,
                "status": core.scenario_status(assertions),
                "observed": {"record": record, "release": release},
                "assertions": assertions,
                "limitations": [],
            }
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "scenario_id": scenario.get("id"),
                "scenario_set": "CHALLENGE",
                "layer": "L1",
                "severity": scenario.get("severity"),
                "sef_source_sha256": source_hash,
                "status": "HARNESS_ERROR",
                "observed": {},
                "assertions": [],
                "limitations": [f"{type(exc).__name__}: {exc}"],
            }


def main() -> int:
    root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument("--sef", default=str(root.parent / "sef.py"))
    p.add_argument("--scenario", default=str(root / "challenge_state/EVID-002.json"))
    p.add_argument("--fixtures", default=str(root / "evidence_release/fixtures"))
    p.add_argument("--expected-sef-sha256", required=True)
    p.add_argument("--output")
    a = p.parse_args()
    sef = Path(a.sef).resolve()
    actual = core.sha256_file(sef)
    if actual != a.expected_sef_sha256:
        report = {"schema": "sef.eval.challenge-state-report.v1", "status": "HARNESS_ERROR", "reason": "SEF_SHA256_MISMATCH", "expected": a.expected_sef_sha256, "observed": actual, "results": []}
        encoded = json.dumps(report, indent=2, sort_keys=True)
        if a.output: Path(a.output).write_text(encoded + "\n", encoding="utf-8")
        print(encoded); return 2
    scenario = load(Path(a.scenario).resolve())
    one = evaluate(sef, scenario, Path(a.fixtures).resolve())
    report = {"schema": "sef.eval.challenge-state-report.v1", "status": "PASS" if one.get("status") != "HARNESS_ERROR" else "HARNESS_ERROR", "sef_source_sha256": actual, "summary": core.summarize([one]), "results": [one]}
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if a.output: Path(a.output).write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if report["status"] == "HARNESS_ERROR": return 2
    return 0 if one.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
