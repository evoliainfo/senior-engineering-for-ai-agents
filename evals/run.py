#!/usr/bin/env python3
"""SEF Evaluation Harness bootstrap runner.

This runner evaluates the public SEF CLI as a black box. It intentionally does
not import private SEF functions and does not modify the runtime under test.

Initial scope: deterministic L0/L1 plan-routing scenarios. Later PRs can extend
this runner to actual-diff, verification, release and agent-in-the-loop layers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCHEMA = "sef.eval.result.v1"
SCENARIO_SCHEMA = "sef.eval.scenario.v1"
RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: top-level JSON value must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(rel).to_bytes(8, "big"))
        digest.update(rel)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def run_json(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    env = os.environ.copy()
    # Avoid inherited hook/CI git variables redirecting fixture git commands.
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX"):
        env.pop(key, None)
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
        check=False,
    )
    stdout = completed.stdout.strip()
    try:
        payload = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Command did not return JSON (exit={completed.returncode}): {' '.join(command)}\n"
            f"stdout={stdout[-2000:]}\nstderr={completed.stderr[-2000:]}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Command returned non-object JSON: {' '.join(command)}")
    payload["_process_returncode"] = completed.returncode
    if completed.stderr.strip():
        payload["_process_stderr"] = completed.stderr.strip()[-4000:]
    return payload


def validate_scenario(data: dict[str, Any], source: Path) -> list[str]:
    errors: list[str] = []
    required = ("schema", "id", "title", "set", "layer", "family", "severity", "fixture", "phase", "request", "expect")
    for key in required:
        if key not in data:
            errors.append(f"missing required field: {key}")
    if data.get("schema") != SCENARIO_SCHEMA:
        errors.append(f"schema must be {SCENARIO_SCHEMA}")
    if data.get("set") not in {"DEV", "CHALLENGE"}:
        errors.append("set must be DEV or CHALLENGE")
    if data.get("layer") not in {"L0", "L1", "L2", "L3"}:
        errors.append("layer must be L0, L1, L2 or L3")
    if data.get("severity") not in {"low", "standard", "high", "critical"}:
        errors.append("severity must be low, standard, high or critical")
    if data.get("phase") not in {"plan", "verify", "release"}:
        errors.append("phase must be plan, verify or release")
    expectation = data.get("expect")
    if not isinstance(expectation, dict):
        errors.append("expect must be an object")
    risk = expectation.get("risk", {}) if isinstance(expectation, dict) else {}
    if risk and not isinstance(risk, dict):
        errors.append("expect.risk must be an object")
    elif isinstance(risk, dict):
        for key in ("exact", "minimum"):
            if key in risk and risk[key] not in RISK_ORDER:
                errors.append(f"expect.risk.{key} must be one of {sorted(RISK_ORDER)}")
    for key in (
        "required_packs",
        "forbidden_packs",
        "required_execution_contexts",
        "forbidden_execution_contexts",
        "required_procedures",
    ):
        if isinstance(expectation, dict) and key in expectation and not isinstance(expectation[key], list):
            errors.append(f"expect.{key} must be an array")
    return [f"{source}: {error}" for error in errors]


def discover_scenarios(root: Path, selected_set: str | None, ids: set[str] | None) -> list[Path]:
    paths = sorted(root.rglob("*.json"))
    selected: list[Path] = []
    for path in paths:
        data = load_json(path)
        if selected_set and data.get("set") != selected_set:
            continue
        if ids and data.get("id") not in ids:
            continue
        selected.append(path)
    return selected


def assertion(assertion_id: str, passed: bool | None, expected: Any, observed: Any, critical: bool) -> dict[str, Any]:
    if passed is True:
        status = "PASS"
    elif passed is False:
        status = "FAIL"
    else:
        status = "INCONCLUSIVE"
    return {
        "id": assertion_id,
        "status": status,
        "critical": critical,
        "expected": expected,
        "observed": observed,
    }


def grade_plan(scenario: dict[str, Any], payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
    assessment = plan.get("assessment") if isinstance(plan.get("assessment"), dict) else {}
    observed = {
        "status": payload.get("status"),
        "risk": assessment.get("risk"),
        "action_class": assessment.get("action_class"),
        "packs": assessment.get("required_packs", []),
        "execution_contexts": assessment.get("execution_contexts", []),
        "procedures": plan.get("procedures", []),
        "implementation_allowed": plan.get("implementation_allowed"),
        "implementation_gate": plan.get("implementation_gate"),
        "definition_of_done": plan.get("definition_of_done", []),
    }
    expect = scenario.get("expect", {})
    critical = scenario.get("severity") == "critical"
    assertions: list[dict[str, Any]] = []

    assertions.append(assertion("command-status", payload.get("status") == "PASS", "PASS", payload.get("status"), critical))

    risk_expect = expect.get("risk", {}) if isinstance(expect.get("risk", {}), dict) else {}
    observed_risk = observed.get("risk")
    if "exact" in risk_expect:
        assertions.append(assertion("risk-exact", observed_risk == risk_expect["exact"], risk_expect["exact"], observed_risk, critical))
    if "minimum" in risk_expect:
        passed = None if observed_risk not in RISK_ORDER else RISK_ORDER[observed_risk] >= RISK_ORDER[risk_expect["minimum"]]
        assertions.append(assertion("risk-minimum", passed, risk_expect["minimum"], observed_risk, critical))

    packs = set(observed.get("packs") or [])
    for pack in expect.get("required_packs", []):
        assertions.append(assertion(f"required-pack:{pack}", pack in packs, True, pack in packs, critical))
    for pack in expect.get("forbidden_packs", []):
        assertions.append(assertion(f"forbidden-pack:{pack}", pack not in packs, False, pack in packs, critical))

    contexts = set(observed.get("execution_contexts") or [])
    for context in expect.get("required_execution_contexts", []):
        assertions.append(assertion(f"required-execution-context:{context}", context in contexts, True, context in contexts, critical))
    for context in expect.get("forbidden_execution_contexts", []):
        assertions.append(assertion(f"forbidden-execution-context:{context}", context not in contexts, False, context in contexts, critical))

    procedures = set(observed.get("procedures") or [])
    for procedure in expect.get("required_procedures", []):
        assertions.append(assertion(f"required-procedure:{procedure}", procedure in procedures, True, procedure in procedures, critical))

    if "implementation_allowed" in expect:
        assertions.append(
            assertion(
                "implementation-allowed",
                observed.get("implementation_allowed") is expect["implementation_allowed"],
                expect["implementation_allowed"],
                observed.get("implementation_allowed"),
                critical,
            )
        )
    return assertions, observed


def scenario_status(assertions: list[dict[str, Any]]) -> str:
    if any(item["status"] == "FAIL" for item in assertions):
        return "FAIL"
    if any(item["status"] == "INCONCLUSIVE" for item in assertions):
        return "INCONCLUSIVE"
    return "PASS"


def evaluate_scenario(sef_path: Path, scenario_path: Path, fixtures_root: Path) -> dict[str, Any]:
    scenario = load_json(scenario_path)
    validation_errors = validate_scenario(scenario, scenario_path)
    if validation_errors:
        return {
            "schema": SCHEMA,
            "scenario_id": scenario.get("id", scenario_path.stem),
            "status": "HARNESS_ERROR",
            "limitations": validation_errors,
            "assertions": [],
        }

    fixture = fixtures_root / scenario["fixture"]
    if not fixture.is_dir():
        return {
            "schema": SCHEMA,
            "scenario_id": scenario["id"],
            "status": "HARNESS_ERROR",
            "limitations": [f"fixture not found: {fixture}"],
            "assertions": [],
        }

    source_hash = sha256_file(sef_path)
    fixture_hash = sha256_tree(fixture)
    with tempfile.TemporaryDirectory(prefix=f"sef-eval-{scenario['id'].lower()}-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture, repo)
        baseline_brief = str(scenario.get("project_brief") or "Evaluation fixture project.")
        init_payload = run_json([sys.executable, str(sef_path), "init", str(repo), "--brief", baseline_brief])
        if init_payload.get("status") != "PASS":
            return {
                "schema": SCHEMA,
                "scenario_id": scenario["id"],
                "status": "HARNESS_ERROR",
                "sef_source_sha256": source_hash,
                "fixture_revision": f"sha256:{fixture_hash}",
                "limitations": ["SEF fixture initialization failed"],
                "initialization": init_payload,
                "assertions": [],
            }
        installed = repo / ".sef" / "sef.py"
        runtime_info = run_json([sys.executable, str(installed), "runtime-info"])

        if scenario["phase"] == "plan":
            payload = run_json(
                [sys.executable, str(installed), "plan", str(repo), "--request", str(scenario["request"]), "--save"]
            )
            assertions, observed = grade_plan(scenario, payload)
        else:
            # Later layers must be explicit. Never infer a pass for unsupported phases.
            payload = {}
            observed = {}
            assertions = [
                assertion(
                    "phase-supported-by-bootstrap-runner",
                    None,
                    scenario["phase"],
                    "plan-only bootstrap runner",
                    scenario.get("severity") == "critical",
                )
            ]

        return {
            "schema": SCHEMA,
            "scenario_id": scenario["id"],
            "scenario_set": scenario["set"],
            "layer": scenario["layer"],
            "severity": scenario["severity"],
            "sef_framework_version": runtime_info.get("framework_version"),
            "sef_source_sha256": source_hash,
            "fixture_revision": f"sha256:{fixture_hash}",
            "status": scenario_status(assertions),
            "observed": observed,
            "assertions": assertions,
            "limitations": [],
        }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    critical_failures: list[str] = []
    for result in results:
        status = str(result.get("status", "UNKNOWN"))
        counts[status] = counts.get(status, 0) + 1
        if result.get("severity") == "critical" and status != "PASS":
            critical_failures.append(str(result.get("scenario_id")))
    return {
        "total": len(results),
        "counts": counts,
        "critical_failures": critical_failures,
        "status": "PASS" if results and counts.get("PASS", 0) == len(results) else "FAIL",
    }


def command_validate(args: argparse.Namespace) -> int:
    scenario_root = Path(args.scenarios).resolve()
    errors: list[str] = []
    paths = sorted(scenario_root.rglob("*.json"))
    for path in paths:
        try:
            errors.extend(validate_scenario(load_json(path), path))
        except Exception as exc:  # validation command must report every malformed file
            errors.append(f"{path}: {exc}")
    report = {"status": "PASS" if not errors else "FAIL", "scenario_count": len(paths), "errors": errors}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


def command_run(args: argparse.Namespace) -> int:
    sef_path = Path(args.sef).resolve()
    scenario_root = Path(args.scenarios).resolve()
    fixtures_root = Path(args.fixtures).resolve()
    ids = {item.strip() for item in args.ids.split(",") if item.strip()} if args.ids else None
    selected_set = args.set.upper() if args.set else None
    paths = discover_scenarios(scenario_root, selected_set, ids)
    if not paths:
        print(json.dumps({"status": "FAIL", "reason": "NO_SCENARIOS_SELECTED"}, indent=2))
        return 1
    results = [evaluate_scenario(sef_path, path, fixtures_root) for path in paths]
    report = {
        "schema": "sef.eval.report.v1",
        "sef_source_sha256": sha256_file(sef_path),
        "summary": summarize(results),
        "results": results,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["summary"]["status"] == "PASS" else 1


def command_self_test(args: argparse.Namespace) -> int:
    validate_args = argparse.Namespace(scenarios=args.scenarios)
    if command_validate(validate_args) != 0:
        return 1
    return command_run(args)


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="SEF deterministic evaluation harness")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate scenario contracts")
    validate.add_argument("--scenarios", default=str(root / "scenarios"))
    validate.set_defaults(func=command_validate)

    for name, func in (("run", command_run), ("self-test", command_self_test)):
        cmd = sub.add_parser(name)
        cmd.add_argument("--sef", default=str(root.parent / "sef.py"))
        cmd.add_argument("--scenarios", default=str(root / "scenarios"))
        cmd.add_argument("--fixtures", default=str(root / "fixtures"))
        cmd.add_argument("--set", choices=["DEV", "CHALLENGE", "dev", "challenge"])
        cmd.add_argument("--ids", default="")
        cmd.add_argument("--output")
        cmd.set_defaults(func=func)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
