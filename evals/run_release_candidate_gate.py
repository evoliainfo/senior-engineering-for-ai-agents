#!/usr/bin/env python3
"""Aggregate deterministic release-candidate evidence without opening a fresh holdout.

The runner is valid both immediately before freeze and after a candidate has been
frozen. It executes only DEV/regression surfaces already available for tuning and
never discovers or executes CHALLENGE v2 content.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
MANIFEST = EVALS / "release_candidate_manifest.json"
DEV_MANIFEST = EVALS / "dev_coverage_manifest.json"
FIRST_CHALLENGE_MANIFEST = EVALS / "challenge_manifest.json"


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_report(command: list[str], output: Path) -> tuple[int, dict[str, Any], str]:
    cp = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if not output.exists():
        raise RuntimeError(
            f"runner produced no output: {' '.join(command)}\n"
            f"stdout={cp.stdout[-2000:]}\nstderr={cp.stderr[-2000:]}"
        )
    return cp.returncode, load(output), cp.stderr[-2000:]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sef", default=str(ROOT / "sef.py"))
    parser.add_argument("--output", default="release-candidate-gate.json")
    args = parser.parse_args()

    sef = Path(args.sef).resolve()
    manifest = load(MANIFEST)
    dev_manifest = load(DEV_MANIFEST)
    first_challenge = load(FIRST_CHALLENGE_MANIFEST)
    expected_sha = str(manifest.get("candidate_runtime_sha256") or "")
    actual_sha = sha256(sef)
    blockers: list[str] = []

    if manifest.get("schema") != "sef.eval.release-candidate.v1":
        blockers.append("unexpected release candidate manifest schema")

    stage = manifest.get("stage")
    if stage not in {"PRE_FREEZE_B3", "FROZEN"}:
        blockers.append(f"unexpected release-candidate stage: {stage}")

    if actual_sha != expected_sha:
        blockers.append(f"runtime hash mismatch: expected {expected_sha}, observed {actual_sha}")

    checksum = (ROOT / "SHA256SUMS").read_text(encoding="utf-8").strip()
    if checksum != f"{expected_sha}  sef.py":
        blockers.append("SHA256SUMS does not exactly identify the candidate runtime")

    if stage == "FROZEN":
        if manifest.get("freeze_commit") != manifest.get("source_main_commit"):
            blockers.append("frozen manifest does not bind freeze_commit to source_main_commit")
        if manifest.get("runtime_mutation_allowed_after_freeze") is not False:
            blockers.append("frozen manifest does not forbid runtime mutation after freeze")

    if dev_manifest.get("dev_total") != 38 or dev_manifest.get("challenge_total") != 10:
        blockers.append("DEV/CHALLENGE accounting is not 38+10")
    if dev_manifest.get("challenge_independent_holdout_status") != "CONSUMED":
        blockers.append("DEV coverage manifest does not explicitly mark the first holdout consumed")
    if dev_manifest.get("future_independent_holdout_required") != "CHALLENGE_V2":
        blockers.append("DEV coverage manifest does not require a rotated CHALLENGE v2")

    if first_challenge.get("candidate_commit") != manifest.get("consumed_holdout", {}).get("official_candidate_commit"):
        blockers.append("first challenge candidate commit no longer matches immutable historical evidence")
    if first_challenge.get("candidate_runtime_sha256") != manifest.get("consumed_holdout", {}).get("official_candidate_runtime_sha256"):
        blockers.append("first challenge runtime identity no longer matches immutable historical evidence")
    if first_challenge.get("runtime_mutation_allowed") is not False:
        blockers.append("first challenge manifest no longer forbids candidate runtime mutation")

    future = manifest.get("future_holdout", {})
    if future.get("materialized") is not False:
        blockers.append("release candidate manifest does not keep CHALLENGE v2 unmaterialized")
    if stage == "PRE_FREEZE_B3" and future.get("creation_allowed_in_b3") is not False:
        blockers.append("PRE_FREEZE_B3 manifest does not forbid CHALLENGE v2 creation during B3")
    if stage == "FROZEN" and future.get("creation_allowed_after_freeze") is not True:
        blockers.append("FROZEN manifest does not explicitly permit fresh holdout creation after freeze")

    forbidden_future_paths: list[str] = []
    for path in EVALS.rglob("*"):
        rel = path.relative_to(ROOT).as_posix().lower()
        if any(token in rel for token in ("challenge_v2", "challenge-v2", "challenge2")):
            forbidden_future_paths.append(rel)
    if forbidden_future_paths:
        blockers.append("CHALLENGE v2 content is already materialized under evals: " + ", ".join(sorted(forbidden_future_paths)))

    with tempfile.TemporaryDirectory(prefix="sef-release-candidate-") as tmp:
        t = Path(tmp)
        suites: dict[str, tuple[int, dict[str, Any], str]] = {}
        commands = {
            "dev_closure": [sys.executable, str(EVALS / "run_dev_closure_all.py"), "--sef", str(sef), "--output", str(t / "dev.json")],
            "b1_acceptance": [sys.executable, str(EVALS / "run_b1_acceptance.py"), "--sef", str(sef), "--output", str(t / "b1.json")],
            "b2_acceptance": [sys.executable, str(EVALS / "run_b2_acceptance.py"), "--sef", str(sef), "--output", str(t / "b2.json")],
            "rc8_calibrated_controls": [sys.executable, str(EVALS / "run_rc8_controls_round2_candidate.py"), "--sef", str(sef), "--output", str(t / "rc8.json")],
            "consumed_challenge_regression": [sys.executable, str(EVALS / "run_consumed_challenge_regression.py"), "--sef", str(sef), "--output", str(t / "consumed.json")],
        }
        output_paths = {
            "dev_closure": t / "dev.json",
            "b1_acceptance": t / "b1.json",
            "b2_acceptance": t / "b2.json",
            "rc8_calibrated_controls": t / "rc8.json",
            "consumed_challenge_regression": t / "consumed.json",
        }
        for name, command in commands.items():
            try:
                suites[name] = run_report(command, output_paths[name])
            except Exception as exc:
                blockers.append(f"{name}: HARNESS_ERROR: {exc}")

    normalized: dict[str, Any] = {}
    required = manifest.get("required_gates", {})
    for name, expected in required.items():
        if name not in suites:
            blockers.append(f"{name}: missing suite result")
            continue
        code, report, stderr = suites[name]
        expected_pass = int(expected.get("expected_pass", -1))
        if name == "dev_closure":
            counts = (report.get("benchmark") or {}).get("counts") or {}
            ok = (
                code == 0
                and report.get("harness_integrity") == "PASS"
                and not report.get("harness_errors")
                and counts == {"PASS": expected_pass}
                and (report.get("benchmark") or {}).get("status") == "PASS"
                and report.get("challenge_ids_executed") == []
            )
        elif name in {"b1_acceptance", "b2_acceptance"}:
            counts = (report.get("benchmark") or {}).get("counts") or {}
            ok = code == 0 and not report.get("harness_errors") and counts == {"PASS": expected_pass}
        elif name == "rc8_calibrated_controls":
            summary = report.get("raw_summary") or {}
            counts = summary.get("counts") or {}
            ok = (
                code == 0
                and report.get("status") == "MEASURED"
                and not report.get("harness_errors")
                and counts == {"PASS": expected_pass}
                and summary.get("status") == "PASS"
            )
        else:
            counts = (report.get("benchmark") or {}).get("counts") or {}
            ok = (
                code == 0
                and report.get("evidence_class") == "CONSUMED_REGRESSION_ONLY"
                and report.get("independent_holdout_claim") is False
                and report.get("harness_integrity") == "PASS"
                and not report.get("harness_errors")
                and counts == {"PASS": expected_pass}
                and (report.get("benchmark") or {}).get("status") == "PASS"
            )
        normalized[name] = {
            "status": "PASS" if ok else "FAIL",
            "exit_code": code,
            "counts": counts,
            "sef_source_sha256": report.get("sef_source_sha256"),
        }
        if not ok:
            blockers.append(f"{name}: expected {expected_pass} PASS; observed {counts}; stderr={stderr}")
        if report.get("sef_source_sha256") != expected_sha:
            blockers.append(f"{name}: suite did not execute exact candidate runtime")

    readme = (EVALS / "README.md").read_text(encoding="utf-8")
    for required_text in (expected_sha, "38/38 PASS", "10/10 PASS", "14/14 PASS", "CONSUMED_REGRESSION_ONLY", "CHALLENGE v2"):
        if required_text not in readme:
            blockers.append(f"evals/README.md missing current release-state marker: {required_text}")

    output = {
        "schema": "sef.eval.release-candidate-gate.v1",
        "status": "PASS" if not blockers else "FAIL",
        "stage": stage,
        "candidate_runtime_sha256": actual_sha,
        "source_main_commit": manifest.get("source_main_commit"),
        "freeze_commit": manifest.get("freeze_commit"),
        "runtime_mutation_allowed_in_b3": manifest.get("runtime_mutation_allowed_in_b3"),
        "runtime_mutation_allowed_after_freeze": manifest.get("runtime_mutation_allowed_after_freeze"),
        "future_holdout_materialized": bool(forbidden_future_paths),
        "first_challenge_evidence_class": "CONSUMED_REGRESSION_ONLY",
        "independent_holdout_claim": False,
        "suites": normalized,
        "known_l2_status": manifest.get("real_l2_status"),
        "blockers": blockers,
        "freeze_ready": not blockers,
    }
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if not blockers else 1


if __name__ == "__main__":
    raise SystemExit(main())
