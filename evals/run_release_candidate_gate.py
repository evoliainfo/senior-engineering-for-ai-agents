#!/usr/bin/env python3
"""Aggregate deterministic evidence for the frozen SEF candidate.

A PASS from this runner means the recorded evidence is internally consistent and
all deterministic regression surfaces still pass on the exact frozen runtime.
It does NOT imply release eligibility. After the official CHALLENGE v3 critical
failure the manifest may deliberately report ARCHITECTURE_DECISION_REQUIRED and
release_eligible=false while this evidence-consistency gate remains green.
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
        blockers.append("historical independent holdout state is not CONSUMED")

    if first_challenge.get("candidate_commit") != manifest.get("consumed_holdout", {}).get("official_candidate_commit"):
        blockers.append("first challenge candidate commit no longer matches immutable historical evidence")
    if first_challenge.get("candidate_runtime_sha256") != manifest.get("consumed_holdout", {}).get("official_candidate_runtime_sha256"):
        blockers.append("first challenge runtime identity no longer matches immutable historical evidence")
    if first_challenge.get("runtime_mutation_allowed") is not False:
        blockers.append("first challenge manifest no longer forbids candidate runtime mutation")

    consumed_v2 = manifest.get("consumed_holdout_v2", {})
    if consumed_v2.get("name") != "CHALLENGE_V2" or consumed_v2.get("independent_holdout_claim") is not False:
        blockers.append("CHALLENGE v2 is not explicitly preserved as consumed historical evidence")
    if consumed_v2.get("current_use") != "CONSUMED_REGRESSION_ONLY":
        blockers.append("CHALLENGE v2 current use is not regression-only")

    release_decision = manifest.get("release_decision")
    if release_decision == "ARCHITECTURE_DECISION_REQUIRED":
        consumed_v3 = manifest.get("consumed_holdout_v3", {})
        verdict = consumed_v3.get("official_verdict") or {}
        if consumed_v3.get("name") != "CHALLENGE_V3":
            blockers.append("terminal manifest is missing CHALLENGE v3 evidence")
        if consumed_v3.get("official_candidate_commit") != manifest.get("freeze_commit"):
            blockers.append("CHALLENGE v3 did not execute the frozen candidate commit")
        if consumed_v3.get("official_candidate_runtime_sha256") != expected_sha:
            blockers.append("CHALLENGE v3 runtime identity differs from frozen runtime")
        if consumed_v3.get("catalog_sha256") != "acf2d37f2c5692a05acca90b7116b3fd66c10ed1ba103e288596d310d564bacb":
            blockers.append("CHALLENGE v3 catalog identity mismatch")
        if verdict.get("pass") != 9 or verdict.get("fail") != 1 or verdict.get("critical_failures") != ["V3-AUTH-002"]:
            blockers.append("CHALLENGE v3 official verdict is not the recorded 9/10 critical-failure result")
        if consumed_v3.get("harness_integrity") != "PASS" or consumed_v3.get("official_independent_verdict") is not True:
            blockers.append("CHALLENGE v3 is not recorded as a valid official independent verdict")
        if consumed_v3.get("current_use") != "CONSUMED_REGRESSION_ONLY" or consumed_v3.get("independent_holdout_claim") is not False:
            blockers.append("CHALLENGE v3 post-run reuse semantics are not regression-only")
        if consumed_v3.get("official_workflow_run") != 32657568114 or consumed_v3.get("artifact_id") != 9497844102:
            blockers.append("CHALLENGE v3 workflow/artifact evidence identity mismatch")
        if consumed_v3.get("artifact_digest") != "sha256:702e855db549d229e4b186dda522c77dccbc37e318db86cdde1de60469a4ca0d":
            blockers.append("CHALLENGE v3 artifact digest mismatch")
        if manifest.get("release_eligible") is not False:
            blockers.append("terminal manifest must explicitly block release eligibility")
        if dev_manifest.get("future_independent_holdout_required") is not None:
            blockers.append("finite holdout program incorrectly requests another independent holdout")
        if dev_manifest.get("independent_holdout_program_state") != "STOPPED_AFTER_V3_CRITICAL_STRUCTURAL_FAILURE":
            blockers.append("DEV coverage manifest does not record terminal holdout state")
        future = manifest.get("future_holdout", {})
        if future.get("name") is not None or future.get("creation_allowed") is not False:
            blockers.append("terminal manifest does not explicitly forbid CHALLENGE v4")
    else:
        future = manifest.get("future_holdout", {})
        if future.get("name") != "CHALLENGE_V3":
            blockers.append("pre-terminal manifest does not identify CHALLENGE v3 as the next holdout")

    forbidden_v4_paths: list[str] = []
    for path in EVALS.rglob("*"):
        rel = path.relative_to(ROOT).as_posix().lower()
        if any(token in rel for token in ("challenge_v4", "challenge-v4", "challenge4")):
            forbidden_v4_paths.append(rel)
    if forbidden_v4_paths:
        blockers.append("CHALLENGE v4 content exists despite finite completion policy: " + ", ".join(sorted(forbidden_v4_paths)))

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
    required_markers = [expected_sha, "38/38 PASS", "10/10 PASS", "14/14 PASS", "CONSUMED_REGRESSION_ONLY"]
    if release_decision == "ARCHITECTURE_DECISION_REQUIRED":
        required_markers.extend(["CHALLENGE v3", "9/10 PASS", "V3-AUTH-002", "ARCHITECTURE_DECISION_REQUIRED"])
    for required_text in required_markers:
        if required_text not in readme:
            blockers.append(f"evals/README.md missing current release-state marker: {required_text}")

    evidence_consistent = not blockers
    output = {
        "schema": "sef.eval.release-candidate-gate.v1",
        "status": "PASS" if evidence_consistent else "FAIL",
        "meaning": "evidence consistency and frozen-runtime regression status; not a release approval",
        "stage": stage,
        "candidate_runtime_sha256": actual_sha,
        "source_main_commit": manifest.get("source_main_commit"),
        "freeze_commit": manifest.get("freeze_commit"),
        "runtime_mutation_allowed_in_b3": manifest.get("runtime_mutation_allowed_in_b3"),
        "runtime_mutation_allowed_after_freeze": manifest.get("runtime_mutation_allowed_after_freeze"),
        "release_decision": release_decision,
        "release_eligible": manifest.get("release_eligible"),
        "architecture_decision_required": release_decision == "ARCHITECTURE_DECISION_REQUIRED",
        "independent_holdout_claim": False,
        "suites": normalized,
        "known_l2_status": manifest.get("real_l2_status"),
        "blockers": blockers,
        "evidence_consistent": evidence_consistent,
        "freeze_ready": evidence_consistent and release_decision is None,
    }
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if evidence_consistent else 1


if __name__ == "__main__":
    raise SystemExit(main())
