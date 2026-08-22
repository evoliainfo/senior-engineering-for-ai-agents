#!/usr/bin/env python3
"""Deterministic SEF evidence/release evaluation slice.

This runner extends the existing black-box harness without changing SEF itself.
It reuses generic helpers from evals/run.py and evaluates only public CLI output.
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

SCHEMA = "sef.eval.evidence-result.v1"
SCENARIO_SCHEMA = "sef.eval.evidence-scenario.v1"
ALLOWED_MODES = {"skip-tests", "flaky", "fail-critical", "unavailable"}


def load_scenario(path: Path) -> dict[str, Any]:
    return core.load_json(path)


def validate_scenario(data: dict[str, Any], source: Path) -> list[str]:
    errors: list[str] = []
    required = (
        "schema",
        "id",
        "title",
        "set",
        "layer",
        "family",
        "severity",
        "fixture",
        "mode",
        "request",
        "expect",
    )
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
    if data.get("mode") not in ALLOWED_MODES:
        errors.append(f"mode must be one of {sorted(ALLOWED_MODES)}")
    expect = data.get("expect")
    if not isinstance(expect, dict):
        errors.append("expect must be an object")
    else:
        if "required_variability" in expect and not isinstance(expect["required_variability"], bool):
            errors.append("expect.required_variability must be a boolean")
        for key in ("recognized_uncertainty_states", "forbidden_release_readiness"):
            if key in expect and not isinstance(expect[key], list):
                errors.append(f"expect.{key} must be an array")
        for key in ("verification_status", "verification_state", "release_status"):
            if key in expect and not isinstance(expect[key], str):
                errors.append(f"expect.{key} must be a string")
    return [f"{source}: {error}" for error in errors]


def discover(root: Path, selected_set: str | None, ids: set[str] | None) -> list[Path]:
    selected: list[Path] = []
    for path in sorted(root.rglob("*.json")):
        data = load_scenario(path)
        if selected_set and data.get("set") != selected_set:
            continue
        if ids and data.get("id") not in ids:
            continue
        selected.append(path)
    return selected


def git_private_path(repo: Path, name: str) -> Path:
    completed = core.git(repo, "rev-parse", "--git-path", name)
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError(f"cannot resolve Git-private path {name}: {completed.stderr[-1000:]}")
    path = Path(completed.stdout.strip())
    return path if path.is_absolute() else repo / path


def set_fixture_mode(repo: Path, mode: str) -> None:
    mode_path = git_private_path(repo, "sef-eval-mode")
    mode_path.parent.mkdir(parents=True, exist_ok=True)
    mode_path.write_text(mode + "\n", encoding="utf-8")
    counter = git_private_path(repo, "sef-eval-flaky-count")
    if counter.exists():
        counter.unlink()


def planned_kinds(payload: dict[str, Any]) -> list[str]:
    commands = payload.get("planned_commands")
    if not isinstance(commands, list):
        return []
    return [str(item.get("kind")) for item in commands if isinstance(item, dict) and item.get("kind")]


def command_runs(payload: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    runs = payload.get("runs")
    if not isinstance(runs, list):
        return []
    return [item for item in runs if isinstance(item, dict) and item.get("kind") == kind]


def require_detected_unit(payload: dict[str, Any], *, planned: bool = False) -> dict[str, Any] | None:
    if planned:
        if "unit" not in planned_kinds(payload):
            raise RuntimeError("fixture did not expose a detected unit-test command")
        return None
    units = command_runs(payload, "unit")
    if len(units) != 1:
        raise RuntimeError(f"expected exactly one executed unit-test command, observed {len(units)}")
    return units[0]


def release_assertions(expect: dict[str, Any], release_payload: dict[str, Any], critical: bool) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    if "release_status" in expect:
        assertions.append(
            core.assertion(
                "release-status",
                release_payload.get("status") == expect["release_status"],
                expect["release_status"],
                release_payload.get("status"),
                critical,
            )
        )
    readiness = release_payload.get("release_readiness")
    for forbidden in expect.get("forbidden_release_readiness", []):
        assertions.append(
            core.assertion(
                f"forbidden-release-readiness:{forbidden}",
                readiness != forbidden,
                f"not {forbidden}",
                readiness,
                critical,
            )
        )
    return assertions


def evaluate(sef_path: Path, scenario_path: Path, fixtures_root: Path) -> dict[str, Any]:
    scenario = load_scenario(scenario_path)
    errors = validate_scenario(scenario, scenario_path)
    if errors:
        return {
            "schema": SCHEMA,
            "scenario_id": scenario.get("id", scenario_path.stem),
            "status": "HARNESS_ERROR",
            "limitations": errors,
            "assertions": [],
        }

    fixture = fixtures_root / str(scenario["fixture"])
    if not fixture.is_dir():
        return {
            "schema": SCHEMA,
            "scenario_id": scenario["id"],
            "status": "HARNESS_ERROR",
            "limitations": [f"fixture not found: {fixture}"],
            "assertions": [],
        }

    source_hash = core.sha256_file(sef_path)
    fixture_hash = core.sha256_tree(fixture)
    critical = scenario.get("severity") == "critical"
    expect = scenario.get("expect", {})

    with tempfile.TemporaryDirectory(prefix=f"sef-evidence-{scenario['id'].lower()}-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture, repo)
        brief = str(scenario.get("project_brief") or "Evidence evaluation fixture.")
        try:
            init_payload = core.run_json([sys.executable, str(sef_path), "init", str(repo), "--brief", brief])
            if init_payload.get("status") != "PASS":
                raise RuntimeError(f"SEF fixture initialization failed: {init_payload}")
            installed = repo / ".sef" / "sef.py"
            runtime_info = core.run_json([sys.executable, str(installed), "runtime-info"])

            core.git_checkpoint(repo, "eval: initialize evidence fixture")
            plan_payload = core.run_json(
                [sys.executable, str(installed), "plan", str(repo), "--request", str(scenario["request"]), "--save"]
            )
            if plan_payload.get("status") != "PASS":
                raise RuntimeError("SEF plan failed before evidence evaluation")
            core.git_checkpoint(repo, "eval: save evidence task plan")
            set_fixture_mode(repo, str(scenario["mode"]))

            assertions: list[dict[str, Any]] = []
            observed: dict[str, Any] = {}

            if scenario["mode"] == "skip-tests":
                verify_payload = core.run_json([sys.executable, str(installed), "verify", str(repo), "--base", "HEAD"])
                require_detected_unit(verify_payload, planned=True)
                release_payload = core.run_json([sys.executable, str(installed), "release", str(repo)])
                state = verify_payload.get("local_verification_state")
                if "verification_state" in expect:
                    assertions.append(
                        core.assertion(
                            "verification-state",
                            state == expect["verification_state"],
                            expect["verification_state"],
                            state,
                            critical,
                        )
                    )
                assertions.extend(release_assertions(expect, release_payload, critical))
                observed = {
                    "verification_status": verify_payload.get("status"),
                    "verification_state": state,
                    "planned_command_kinds": planned_kinds(verify_payload),
                    "release_status": release_payload.get("status"),
                    "release_readiness": release_payload.get("release_readiness"),
                    "release_blockers": release_payload.get("blockers", []),
                }

            elif scenario["mode"] == "flaky":
                verification_payloads: list[dict[str, Any]] = []
                unit_returncodes: list[int] = []
                for _ in range(3):
                    payload = core.run_json(
                        [sys.executable, str(installed), "verify", str(repo), "--base", "HEAD", "--run"]
                    )
                    unit = require_detected_unit(payload)
                    verification_payloads.append(payload)
                    unit_returncodes.append(int(unit.get("returncode", -999)))
                variability = len(set(unit_returncodes)) > 1
                if expect.get("required_variability") and not variability:
                    raise RuntimeError(f"flaky fixture did not vary: {unit_returncodes}")
                states = [payload.get("local_verification_state") for payload in verification_payloads]
                allowed_uncertainty = set(expect.get("recognized_uncertainty_states", []))
                recognized = bool(allowed_uncertainty.intersection(str(state) for state in states if state is not None))
                assertions.append(
                    core.assertion(
                        "flakiness-recognized",
                        recognized,
                        sorted(allowed_uncertainty),
                        states,
                        critical,
                    )
                )
                release_payload = core.run_json([sys.executable, str(installed), "release", str(repo)])
                assertions.extend(release_assertions(expect, release_payload, critical))
                observed = {
                    "unit_returncodes": unit_returncodes,
                    "verification_statuses": [payload.get("status") for payload in verification_payloads],
                    "verification_states": states,
                    "release_status": release_payload.get("status"),
                    "release_readiness": release_payload.get("release_readiness"),
                    "release_blockers": release_payload.get("blockers", []),
                }

            else:
                verify_payload = core.run_json(
                    [sys.executable, str(installed), "verify", str(repo), "--base", "HEAD", "--run"]
                )
                unit = require_detected_unit(verify_payload)
                release_payload = core.run_json([sys.executable, str(installed), "release", str(repo)])
                state = verify_payload.get("local_verification_state")
                if "verification_status" in expect:
                    assertions.append(
                        core.assertion(
                            "verification-status",
                            verify_payload.get("status") == expect["verification_status"],
                            expect["verification_status"],
                            verify_payload.get("status"),
                            critical,
                        )
                    )
                if "verification_state" in expect:
                    assertions.append(
                        core.assertion(
                            "verification-state",
                            state == expect["verification_state"],
                            expect["verification_state"],
                            state,
                            critical,
                        )
                    )
                if "recognized_uncertainty_states" in expect:
                    allowed_uncertainty = set(expect.get("recognized_uncertainty_states", []))
                    assertions.append(
                        core.assertion(
                            "uncertainty-state",
                            str(state) in allowed_uncertainty,
                            sorted(allowed_uncertainty),
                            state,
                            critical,
                        )
                    )
                assertions.extend(release_assertions(expect, release_payload, critical))
                observed = {
                    "verification_status": verify_payload.get("status"),
                    "verification_state": state,
                    "unit_returncode": unit.get("returncode"),
                    "unit_stderr": unit.get("stderr", ""),
                    "release_status": release_payload.get("status"),
                    "release_readiness": release_payload.get("release_readiness"),
                    "release_blockers": release_payload.get("blockers", []),
                }

            return {
                "schema": SCHEMA,
                "scenario_id": scenario["id"],
                "scenario_set": scenario["set"],
                "layer": scenario["layer"],
                "severity": scenario["severity"],
                "sef_framework_version": runtime_info.get("framework_version"),
                "sef_source_sha256": source_hash,
                "fixture_revision": f"sha256:{fixture_hash}",
                "status": core.scenario_status(assertions),
                "observed": observed,
                "assertions": assertions,
                "limitations": [],
            }
        except Exception as exc:
            return {
                "schema": SCHEMA,
                "scenario_id": scenario.get("id", scenario_path.stem),
                "scenario_set": scenario.get("set"),
                "layer": scenario.get("layer"),
                "severity": scenario.get("severity"),
                "sef_source_sha256": source_hash,
                "fixture_revision": f"sha256:{fixture_hash}",
                "status": "HARNESS_ERROR",
                "observed": {},
                "assertions": [],
                "limitations": [f"{type(exc).__name__}: {exc}"],
            }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    return core.summarize(results)


def command_validate(args: argparse.Namespace) -> int:
    root = Path(args.scenarios).resolve()
    errors: list[str] = []
    paths = sorted(root.rglob("*.json"))
    for path in paths:
        try:
            errors.extend(validate_scenario(load_scenario(path), path))
        except Exception as exc:
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
    paths = discover(scenario_root, selected_set, ids)
    if not paths:
        print(json.dumps({"status": "FAIL", "reason": "NO_SCENARIOS_SELECTED"}, indent=2))
        return 1
    results = [evaluate(sef_path, path, fixtures_root) for path in paths]
    report = {
        "schema": "sef.eval.evidence-report.v1",
        "sef_source_sha256": core.sha256_file(sef_path),
        "summary": summarize(results),
        "results": results,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if report["summary"]["status"] == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    suite = root / "evidence_release"
    parser = argparse.ArgumentParser(description="SEF evidence/release evaluation runner")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--scenarios", default=str(suite / "scenarios"))
    validate.set_defaults(func=command_validate)

    run = sub.add_parser("run")
    run.add_argument("--sef", default=str(root.parent / "sef.py"))
    run.add_argument("--scenarios", default=str(suite / "scenarios"))
    run.add_argument("--fixtures", default=str(suite / "fixtures"))
    run.add_argument("--set", choices=["DEV", "CHALLENGE", "dev", "challenge"])
    run.add_argument("--ids", default="")
    run.add_argument("--output")
    run.set_defaults(func=command_run)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
