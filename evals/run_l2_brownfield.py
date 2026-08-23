#!/usr/bin/env python3
"""External-agent L2 brownfield evaluation runner.

The runner is provider-agnostic: an operator supplies a wrapper command for Codex
or Claude. A deterministic reference adapter exists only to validate the harness
and can never produce accepted L2 evidence.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

EVAL_ROOT = Path(__file__).resolve().parent
L2_ROOT = EVAL_ROOT / "l2"
SCENARIO_SCHEMA = "sef.eval.l2.brownfield.v1"
REPORT_SCHEMA = "sef.eval.l2.brownfield-report.v1"
TRIAL_SCHEMA = "sef.eval.l2.brownfield-trial.v1"
SUPPORTED_HARNESSES = {"codex", "claude", "reference"}
DEPENDENCY_MANIFESTS = {
    "requirements.txt", "requirements-dev.txt", "pyproject.toml", "poetry.lock",
    "pipfile", "pipfile.lock", "package.json", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", "bun.lock", "bun.lockb", "go.mod", "go.sum", "cargo.toml",
    "cargo.lock", "gemfile", "gemfile.lock", "composer.json", "composer.lock",
}
FRAMEWORK_PROTECTED = ["AGENTS.md", "CLAUDE.md", ".sef/sef.py"]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update(path.read_bytes()); h.update(b"\0")
    return h.hexdigest()


def run_process(argv: list[str], cwd: Path, env: dict[str, str] | None = None, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_process(["git", *args], repo, timeout=60)


def git_ok(repo: Path, *args: str) -> str:
    cp = git(repo, *args)
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr[-2000:]}")
    return cp.stdout.strip()


def init_git(repo: Path) -> None:
    git_ok(repo, "init", "-q")
    git_ok(repo, "config", "user.name", "SEF L2 Evaluator")
    git_ok(repo, "config", "user.email", "sef-l2@example.invalid")
    git_ok(repo, "add", "-A")
    git_ok(repo, "commit", "-qm", "eval: fixture baseline")


def checkpoint(repo: Path, message: str) -> str:
    git_ok(repo, "add", "-A")
    cp = git(repo, "diff", "--cached", "--quiet")
    if cp.returncode not in (0, 1):
        raise RuntimeError(cp.stderr[-2000:])
    if cp.returncode == 1:
        git_ok(repo, "commit", "-qm", message)
    return git_ok(repo, "rev-parse", "HEAD")


def changed_paths(repo: Path, baseline: str) -> list[str]:
    tracked = set(filter(None, git_ok(repo, "diff", "--name-only", baseline).splitlines()))
    untracked = set(filter(None, git_ok(repo, "ls-files", "--others", "--exclude-standard").splitlines()))
    return sorted(tracked | untracked)


def hash_paths(repo: Path, paths: list[str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for rel in paths:
        p = repo / rel
        out[rel] = sha256_file(p) if p.is_file() else None
    return out


def assertion(assertion_id: str, passed: bool, expected: Any, observed: Any) -> dict[str, Any]:
    return {
        "id": assertion_id,
        "status": "PASS" if passed else "FAIL",
        "expected": expected,
        "observed": observed,
    }


def scenario_errors(s: dict[str, Any], path: Path) -> list[str]:
    errors: list[str] = []
    for key in ("schema", "id", "source_scenario", "set", "layer", "family", "severity", "fixture", "trials_min", "project_brief", "request", "grader"):
        if key not in s:
            errors.append(f"{path}: missing {key}")
    if s.get("schema") != SCENARIO_SCHEMA:
        errors.append(f"{path}: wrong schema")
    if s.get("set") != "DEV" or s.get("layer") != "L2":
        errors.append(f"{path}: only DEV/L2 scenarios are accepted")
    if not isinstance(s.get("trials_min"), int) or int(s.get("trials_min", 0)) < 1:
        errors.append(f"{path}: trials_min must be >= 1")
    grader = s.get("grader")
    if not isinstance(grader, dict):
        errors.append(f"{path}: grader must be an object")
    else:
        if not isinstance(grader.get("test_commands", []), list):
            errors.append(f"{path}: grader.test_commands must be a list")
        probe = grader.get("behavior_probe")
        if not isinstance(probe, dict) or not all(k in probe for k in ("module", "callable", "cases")):
            errors.append(f"{path}: behavior_probe is incomplete")
    return errors


def load_scenarios(root: Path, ids: set[str] | None = None) -> tuple[list[dict[str, Any]], list[str]]:
    scenarios: list[dict[str, Any]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for path in sorted(root.glob("*.json")):
        try:
            s = load_json(path)
        except Exception as exc:
            errors.append(f"{path}: {type(exc).__name__}: {exc}")
            continue
        sid = str(s.get("id") or path.stem)
        if ids and sid not in ids:
            continue
        errors.extend(scenario_errors(s, path))
        if sid in seen:
            errors.append(f"duplicate scenario id: {sid}")
        seen.add(sid); scenarios.append(s)
    if ids:
        missing = sorted(ids - seen)
        errors.extend(f"requested scenario not found: {sid}" for sid in missing)
    return scenarios, errors


def validate_fixtures(scenarios: list[dict[str, Any]], fixture_root: Path) -> list[str]:
    errors: list[str] = []
    for s in scenarios:
        fixture = fixture_root / str(s["fixture"])
        if not fixture.is_dir():
            errors.append(f"{s['id']}: fixture not found: {fixture}")
            continue
        grader = s["grader"]
        for rel in grader.get("protected_paths", []):
            if not (fixture / rel).is_file():
                errors.append(f"{s['id']}: protected fixture path missing: {rel}")
    return errors


def clean_agent_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def run_behavior_probe(repo: Path, probe: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    spec = json.dumps(probe, ensure_ascii=False)
    env = clean_agent_env(); env["SEF_L2_PROBE"] = spec
    code = r'''
import importlib, json, os, sys
spec=json.loads(os.environ['SEF_L2_PROBE'])
sys.path.insert(0, os.getcwd())
module=importlib.import_module(spec['module'])
fn=getattr(module,spec['callable'])
observed=[]
for case in spec['cases']:
    value=fn(*case.get('args',[]))
    observed.append({'expected':case.get('expected'),'observed':value})
    if value != case.get('expected'):
        print(json.dumps(observed,ensure_ascii=False)); raise SystemExit(1)
print(json.dumps(observed,ensure_ascii=False))
'''
    cp = run_process([sys.executable, "-c", code], repo, env=env, timeout=60)
    observed: Any
    try:
        observed = json.loads(cp.stdout.strip().splitlines()[-1]) if cp.stdout.strip() else []
    except Exception:
        observed = {"stdout": cp.stdout[-1000:], "stderr": cp.stderr[-1000:]}
    return cp.returncode == 0, {"cases": observed, "returncode": cp.returncode, "stderr": cp.stderr[-1000:]}


def application_paths(paths: list[str]) -> list[str]:
    return sorted(p for p in paths if not p.startswith(".sef/"))


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def execute_trial(
    scenario: dict[str, Any],
    trial_index: int,
    sef: Path,
    fixture_root: Path,
    harness: str,
    model: str,
    agent_version: str,
    agent_command: str,
    sef_revision: str,
    timeout: int,
) -> dict[str, Any]:
    sid = str(scenario["id"])
    trial_id = f"{sid}-{harness}-{trial_index:04d}"
    fixture = fixture_root / str(scenario["fixture"])
    fixture_sha = tree_digest(fixture)
    command_hash = hashlib.sha256(agent_command.encode("utf-8")).hexdigest()
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix=f"sef-l2-{sid.lower()}-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture, repo)
        try:
            init_git(repo)
            init_cp = run_process([sys.executable, str(sef), "init", str(repo), "--brief", str(scenario["project_brief"])], repo, timeout=120)
            if init_cp.returncode != 0:
                raise RuntimeError(f"SEF init process failed: {init_cp.stderr[-2000:]}")
            try:
                init_payload = json.loads(init_cp.stdout)
            except Exception as exc:
                raise RuntimeError(f"SEF init did not return JSON: {exc}: {init_cp.stdout[-2000:]}")
            if init_payload.get("status") != "PASS":
                raise RuntimeError(f"SEF init status is not PASS: {init_payload}")
            baseline = checkpoint(repo, "eval: SEF-managed L2 baseline")

            protected = list(dict.fromkeys([*FRAMEWORK_PROTECTED, *scenario["grader"].get("protected_paths", [])]))
            protected_before = hash_paths(repo, protected)

            request_file = Path(tmp) / "request.txt"
            result_file = Path(tmp) / "agent-result.json"
            request_file.write_text(str(scenario["request"]) + "\n", encoding="utf-8")
            rendered = agent_command.format(
                repo=str(repo),
                request_file=str(request_file),
                result_file=str(result_file),
                eval_root=str(EVAL_ROOT),
                scenario_id=sid,
            )
            argv = shlex.split(rendered)
            if not argv:
                raise RuntimeError("agent command resolved to an empty argv")
            env = clean_agent_env()
            env.update({
                "SEF_L2_REPO": str(repo),
                "SEF_L2_REQUEST": str(scenario["request"]),
                "SEF_L2_SCENARIO_ID": sid,
                "SEF_L2_HARNESS": harness,
                "SEF_L2_TRIAL_ID": trial_id,
                "SEF_L2_RESULT_PATH": str(result_file),
            })
            timed_out = False
            try:
                agent = run_process(argv, repo, env=env, timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                agent = subprocess.CompletedProcess(argv, 124, stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "", stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "timeout")

            paths = changed_paths(repo, baseline)
            app_paths = application_paths(paths)
            grader = scenario["grader"]
            assertions: list[dict[str, Any]] = []
            assertions.append(assertion("agent-process", agent.returncode == 0 and not timed_out, 0, agent.returncode))

            test_observations: list[dict[str, Any]] = []
            for i, command in enumerate(grader.get("test_commands", []), 1):
                cp = run_process(shlex.split(str(command)), repo, env=clean_agent_env(), timeout=120)
                test_observations.append({"command": command, "returncode": cp.returncode, "stdout": cp.stdout[-1000:], "stderr": cp.stderr[-1000:]})
                assertions.append(assertion(f"test-command-{i}", cp.returncode == 0, 0, cp.returncode))

            probe_ok, probe_observed = run_behavior_probe(repo, grader["behavior_probe"])
            assertions.append(assertion("behavior-probe", probe_ok, "all cases match", probe_observed))

            required_patterns = [str(x) for x in grader.get("required_changed_patterns", [])]
            for pattern in required_patterns:
                matched = sorted(p for p in app_paths if fnmatch.fnmatch(p, pattern))
                assertions.append(assertion(f"required-change:{pattern}", bool(matched), True, matched))

            allowed_patterns = [str(x) for x in grader.get("allowed_changed_patterns", [])]
            outside = sorted(p for p in app_paths if not matches_any(p, allowed_patterns))
            assertions.append(assertion("application-scope", not outside, allowed_patterns, outside))

            max_files = int(grader.get("max_application_changed_files", 999999))
            assertions.append(assertion("change-count-budget", len(app_paths) <= max_files, f"<= {max_files}", len(app_paths)))

            protected_after = hash_paths(repo, protected)
            protected_changes = sorted(rel for rel in protected if protected_before.get(rel) != protected_after.get(rel))
            assertions.append(assertion("protected-files-unchanged", not protected_changes, [], protected_changes))

            if grader.get("forbid_dependency_manifests"):
                dependency_changes = sorted(p for p in app_paths if Path(p).name.lower() in DEPENDENCY_MANIFESTS)
                assertions.append(assertion("no-dependency-manifest-change", not dependency_changes, [], dependency_changes))

            transcript = (agent.stdout or "") + "\n" + (agent.stderr or "")
            trace_cfg = grader.get("trace_review") if isinstance(grader.get("trace_review"), dict) else {}
            debt_terms = [str(x).lower() for x in trace_cfg.get("non_scoring_debt_terms", [])]
            debt_signal = bool(debt_terms) and any(term in transcript.lower() for term in debt_terms)

            status = "PASS" if assertions and all(a["status"] == "PASS" for a in assertions) else "FAIL"
            duration_ms = int((time.monotonic() - started) * 1000)
            return {
                "schema": TRIAL_SCHEMA,
                "scenario_id": sid,
                "source_scenario": scenario["source_scenario"],
                "trial_id": trial_id,
                "layer": "L2",
                "severity": scenario["severity"],
                "status": status,
                "harness": harness,
                "model": model,
                "agent_version": agent_version,
                "agent_command_sha256": command_hash,
                "sef_revision": sef_revision,
                "sef_source_sha256": sha256_file(sef),
                "fixture_sha256": fixture_sha,
                "baseline_revision": baseline,
                "agent_returncode": agent.returncode,
                "timed_out": timed_out,
                "duration_ms": duration_ms,
                "changed_paths": paths,
                "application_changed_paths": app_paths,
                "assertions": assertions,
                "observed": {
                    "tests": test_observations,
                    "behavior_probe": probe_observed,
                    "trace_review": {
                        "debt_disclosure_signal": debt_signal,
                        "terms": debt_terms,
                        "scoring": False,
                    },
                    "agent_result_file_present": result_file.is_file(),
                    "stdout_tail": (agent.stdout or "")[-4000:],
                    "stderr_tail": (agent.stderr or "")[-4000:],
                },
                "limitations": (["G2/human review is still required to judge the quality of unrelated-debt disclosure."] if debt_terms else []),
            }
        except Exception as exc:
            return {
                "schema": TRIAL_SCHEMA,
                "scenario_id": sid,
                "source_scenario": scenario.get("source_scenario"),
                "trial_id": trial_id,
                "layer": "L2",
                "severity": scenario.get("severity"),
                "status": "HARNESS_ERROR",
                "harness": harness,
                "model": model,
                "agent_version": agent_version,
                "agent_command_sha256": command_hash,
                "sef_revision": sef_revision,
                "sef_source_sha256": sha256_file(sef),
                "fixture_sha256": fixture_sha,
                "assertions": [],
                "limitations": [f"{type(exc).__name__}: {exc}"],
            }


def summarize(scenarios: list[dict[str, Any]], trials: list[dict[str, Any]], harness: str, requested_trials: int) -> dict[str, Any]:
    by_scenario: dict[str, Any] = {}
    for scenario in scenarios:
        sid = str(scenario["id"])
        rows = [t for t in trials if t.get("scenario_id") == sid]
        passed = sum(t.get("status") == "PASS" for t in rows)
        minimum = int(scenario["trials_min"])
        by_scenario[sid] = {
            "minimum_trials": minimum,
            "observed_trials": len(rows),
            "passed_trials": passed,
            "first_attempt_status": rows[0].get("status") if rows else "NOT_RUN",
            "success_rate": (passed / len(rows)) if rows else None,
            "all_required_trials_pass": len(rows) >= minimum and all(t.get("status") == "PASS" for t in rows[:minimum]),
            "failure_signatures": [
                {
                    "trial_id": t.get("trial_id"),
                    "status": t.get("status"),
                    "failed_assertions": [a.get("id") for a in t.get("assertions", []) if a.get("status") != "PASS"],
                    "limitations": t.get("limitations", []),
                }
                for t in rows if t.get("status") != "PASS"
            ],
        }
    harness_errors = [t.get("trial_id") for t in trials if t.get("status") == "HARNESS_ERROR"]
    enough = all(len([t for t in trials if t.get("scenario_id") == s["id"]]) >= int(s["trials_min"]) for s in scenarios)
    all_pass = enough and not harness_errors and all(v["all_required_trials_pass"] for v in by_scenario.values())
    if harness == "reference":
        claim_state = "HARNESS_REFERENCE_ONLY" if not harness_errors and all(t.get("status") == "PASS" for t in trials) else "HARNESS_REFERENCE_FAILED"
    elif not trials:
        claim_state = "NOT_RUN"
    elif not enough:
        claim_state = "INSUFFICIENT_TRIALS"
    else:
        claim_state = "PASS" if all_pass else "FAIL"
    return {
        "harness": harness,
        "requested_trials_per_scenario": requested_trials,
        "trial_count": len(trials),
        "harness_errors": harness_errors,
        "claim_state": claim_state,
        "scenarios": by_scenario,
    }


def validate_command(args: argparse.Namespace) -> int:
    scenarios, errors = load_scenarios(Path(args.scenarios).resolve(), set(args.ids.split(",")) if args.ids else None)
    errors.extend(validate_fixtures(scenarios, Path(args.fixtures).resolve()))
    payload = {"status": "PASS" if not errors else "FAIL", "scenario_count": len(scenarios), "errors": errors}
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not errors else 1


def run_command(args: argparse.Namespace) -> int:
    sef = Path(args.sef).resolve()
    scenarios, errors = load_scenarios(Path(args.scenarios).resolve(), set(args.ids.split(",")) if args.ids else None)
    errors.extend(validate_fixtures(scenarios, Path(args.fixtures).resolve()))
    if args.harness not in SUPPORTED_HARNESSES:
        errors.append(f"unsupported harness: {args.harness}")
    if not sef.is_file():
        errors.append(f"SEF runtime not found: {sef}")
    actual_sha = sha256_file(sef) if sef.is_file() else None
    if args.expected_sef_sha256 and actual_sha != args.expected_sef_sha256:
        errors.append(f"SEF SHA-256 mismatch: expected {args.expected_sef_sha256}, observed {actual_sha}")
    if args.harness in {"codex", "claude"} and (not args.model or not args.agent_version):
        errors.append("real L2 harnesses require --model and --agent-version metadata")
    if not args.agent_command.strip():
        errors.append("--agent-command is required for run")
    if args.trials < 1:
        errors.append("--trials must be >= 1")
    if errors:
        report = {
            "schema": REPORT_SCHEMA,
            "status": "HARNESS_ERROR",
            "claim_state": "NOT_RUN",
            "errors": errors,
            "sef_revision": args.sef_revision,
            "sef_source_sha256": actual_sha,
            "challenge_status": "SEALED",
            "challenge_ids_executed": [],
            "results": [],
        }
        encoded = json.dumps(report, indent=2, sort_keys=True)
        if args.output:
            Path(args.output).write_text(encoded + "\n", encoding="utf-8")
        print(encoded)
        return 2

    self_test = run_process([sys.executable, str(sef), "self-test"], sef.parent, timeout=180)
    if self_test.returncode != 0:
        errors.append("SEF self-test process failed")
    else:
        try:
            payload = json.loads(self_test.stdout)
            if payload.get("status") != "PASS":
                errors.append(f"SEF self-test status: {payload.get('status')}")
        except Exception:
            errors.append("SEF self-test output was not valid JSON")
    if errors:
        report = {
            "schema": REPORT_SCHEMA,
            "status": "HARNESS_ERROR",
            "claim_state": "NOT_RUN",
            "errors": errors,
            "sef_revision": args.sef_revision,
            "sef_source_sha256": actual_sha,
            "challenge_status": "SEALED",
            "challenge_ids_executed": [],
            "results": [],
        }
        encoded = json.dumps(report, indent=2, sort_keys=True)
        if args.output:
            Path(args.output).write_text(encoded + "\n", encoding="utf-8")
        print(encoded); return 2

    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        for i in range(1, args.trials + 1):
            results.append(execute_trial(
                scenario, i, sef, Path(args.fixtures).resolve(), args.harness,
                args.model, args.agent_version, args.agent_command,
                args.sef_revision, args.timeout,
            ))
    summary = summarize(scenarios, results, args.harness, args.trials)
    report = {
        "schema": REPORT_SCHEMA,
        "status": "PASS" if not summary["harness_errors"] else "HARNESS_ERROR",
        "claim_state": summary["claim_state"],
        "evidence_class": "HARNESS_REFERENCE_ONLY" if args.harness == "reference" else "AGENT_IN_THE_LOOP",
        "sef_revision": args.sef_revision,
        "sef_source_sha256": actual_sha,
        "harness": args.harness,
        "model": args.model,
        "agent_version": args.agent_version,
        "challenge_status": "SEALED",
        "challenge_ids_executed": [],
        "summary": summary,
        "results": results,
        "limitations": (["Reference-agent runs validate harness solvability only and are not Codex/Claude evidence."] if args.harness == "reference" else []),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    if summary["claim_state"] in {"PASS", "HARNESS_REFERENCE_ONLY"}:
        return 0
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="SEF L2 brownfield external-agent harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate")
    v.add_argument("--scenarios", default=str(L2_ROOT / "scenarios"))
    v.add_argument("--fixtures", default=str(L2_ROOT / "fixtures"))
    v.add_argument("--ids", default="")

    r = sub.add_parser("run")
    r.add_argument("--sef", default=str(EVAL_ROOT.parent / "sef.py"))
    r.add_argument("--sef-revision", required=True)
    r.add_argument("--expected-sef-sha256", default="")
    r.add_argument("--scenarios", default=str(L2_ROOT / "scenarios"))
    r.add_argument("--fixtures", default=str(L2_ROOT / "fixtures"))
    r.add_argument("--ids", default="")
    r.add_argument("--harness", choices=sorted(SUPPORTED_HARNESSES), required=True)
    r.add_argument("--model", default="")
    r.add_argument("--agent-version", default="")
    r.add_argument("--agent-command", required=True)
    r.add_argument("--trials", type=int, default=3)
    r.add_argument("--timeout", type=int, default=300)
    r.add_argument("--output")

    args = p.parse_args()
    return validate_command(args) if args.cmd == "validate" else run_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
