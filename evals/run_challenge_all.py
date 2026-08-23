#!/usr/bin/env python3
"""One-shot 10-scenario CHALLENGE orchestrator for frozen candidate 7302914e."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SCHEMA = "sef.eval.challenge-report.v1"


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_report(command: list[str], output: Path) -> tuple[int, dict[str, Any]]:
    cp = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if not output.is_file():
        raise RuntimeError(f"runner produced no report: {' '.join(command)}\nstdout={cp.stdout[-2000:]}\nstderr={cp.stderr[-2000:]}")
    return cp.returncode, load(output)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sef", default=str(ROOT.parent / "sef.py"))
    p.add_argument("--manifest", default=str(ROOT / "challenge_manifest.json"))
    p.add_argument("--output", default="challenge-report.json")
    a = p.parse_args()

    sef = Path(a.sef).resolve()
    manifest = load(Path(a.manifest).resolve())
    expected_sha = str(manifest["candidate_runtime_sha256"])
    actual_sha = sha256_file(sef)
    harness_errors: list[str] = []
    if actual_sha != expected_sha:
        harness_errors.append(f"runtime SHA mismatch: expected {expected_sha}, observed {actual_sha}")
    if manifest.get("runtime_mutation_allowed") is not False:
        harness_errors.append("manifest must explicitly forbid runtime mutation")
    expected_ids = [str(x) for x in manifest.get("expected_ids", [])]
    standard_ids = [str(x) for x in manifest.get("standard_runner_ids", [])]
    state_ids = [str(x) for x in manifest.get("state_runner_ids", [])]
    if len(expected_ids) != 10 or len(set(expected_ids)) != 10:
        harness_errors.append(f"expected_ids must contain exactly 10 unique IDs: {expected_ids}")
    if sorted(set(standard_ids + state_ids)) != sorted(expected_ids):
        harness_errors.append("runner ID partitions do not exactly cover expected challenge IDs")
    if state_ids != ["EVID-002"]:
        harness_errors.append(f"state runner partition changed unexpectedly: {state_ids}")

    reports: list[tuple[str, int, dict[str, Any]]] = []
    if not harness_errors:
        with tempfile.TemporaryDirectory(prefix="sef-challenge-all-") as tmp:
            temp = Path(tmp)
            standard_out = temp / "standard.json"
            state_out = temp / "state.json"
            standard_cmd = [
                sys.executable, str(ROOT / "run_challenge_standard.py"),
                "--sef", str(sef),
                "--scenarios", str(ROOT / "scenarios/challenge"),
                "--fixtures", str(ROOT / "fixtures"),
                "--ids", ",".join(standard_ids),
                "--expected-sef-sha256", expected_sha,
                "--output", str(standard_out),
            ]
            state_cmd = [
                sys.executable, str(ROOT / "run_challenge_state.py"),
                "--sef", str(sef),
                "--scenario", str(ROOT / "challenge_state/EVID-002.json"),
                "--fixtures", str(ROOT / "evidence_release/fixtures"),
                "--expected-sef-sha256", expected_sha,
                "--output", str(state_out),
            ]
            for name, command, path in (("standard", standard_cmd, standard_out), ("state", state_cmd, state_out)):
                try:
                    code, report = run_report(command, path)
                    reports.append((name, code, report))
                    if code not in (0, 1):
                        harness_errors.append(f"{name} runner returned harness exit code {code}")
                    if report.get("status") == "HARNESS_ERROR":
                        harness_errors.append(f"{name} runner reported HARNESS_ERROR")
                except Exception as exc:
                    harness_errors.append(f"{name} runner exception: {type(exc).__name__}: {exc}")

    results: list[dict[str, Any]] = []
    for name, _, report in reports:
        rows = report.get("results")
        if not isinstance(rows, list):
            harness_errors.append(f"{name}: results is not a list")
            continue
        for row in rows:
            item = dict(row); item["challenge_runner"] = name; results.append(item)

    observed_ids = [str(r.get("scenario_id")) for r in results]
    duplicates = sorted({sid for sid in observed_ids if observed_ids.count(sid) > 1})
    missing = sorted(set(expected_ids) - set(observed_ids))
    unexpected = sorted(set(observed_ids) - set(expected_ids))
    if duplicates: harness_errors.append("duplicate challenge results: " + ", ".join(duplicates))
    if missing: harness_errors.append("missing challenge results: " + ", ".join(missing))
    if unexpected: harness_errors.append("unexpected challenge results: " + ", ".join(unexpected))
    if len(results) != 10: harness_errors.append(f"observed challenge results={len(results)}, expected=10")
    hashes = sorted({str(r.get("sef_source_sha256")) for r in results if r.get("sef_source_sha256")})
    if results and hashes != [expected_sha]:
        harness_errors.append(f"result runtime hashes are not uniformly frozen: {hashes}")
    harness_error_ids = sorted(str(r.get("scenario_id")) for r in results if r.get("status") == "HARNESS_ERROR")
    if harness_error_ids:
        harness_errors.append("scenario HARNESS_ERROR: " + ", ".join(harness_error_ids))

    counts: dict[str, int] = {}
    for r in results:
        status = str(r.get("status", "UNKNOWN")); counts[status] = counts.get(status, 0) + 1
    failures = sorted(str(r.get("scenario_id")) for r in results if r.get("status") != "PASS")
    critical = set(str(x) for x in manifest.get("critical_ids", []))
    critical_failures = sorted(sid for sid in failures if sid in critical)
    benchmark_status = "PASS" if not failures and len(results) == 10 else "FAIL"
    report = {
        "schema": SCHEMA,
        "candidate_commit": manifest.get("candidate_commit"),
        "candidate_baseline_ref": manifest.get("candidate_baseline_ref"),
        "sef_source_sha256": actual_sha,
        "holdout_status": "OPENED_EXECUTED",
        "holdout_reuse_status": "CONTAMINATED_FOR_FUTURE_TUNING",
        "rerun_policy": manifest.get("rerun_policy"),
        "runtime_mutation_allowed": False,
        "real_l2_status": manifest.get("real_l2_status"),
        "accounting": {
            "expected": 10,
            "observed": len(results),
            "unique_observed": len(set(observed_ids)),
            "missing": missing,
            "unexpected": unexpected,
            "duplicates": duplicates,
        },
        "harness_integrity": "PASS" if not harness_errors else "FAIL",
        "harness_errors": harness_errors,
        "benchmark": {
            "status": benchmark_status if not harness_errors else "INVALID",
            "counts": counts,
            "failures": failures,
            "critical_failures": critical_failures,
        },
        "results": sorted(results, key=lambda r: str(r.get("scenario_id"))),
    }
    Path(a.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("candidate_commit", "sef_source_sha256", "holdout_status", "holdout_reuse_status", "accounting", "harness_integrity", "harness_errors", "benchmark", "real_l2_status")}, indent=2, sort_keys=True))
    if harness_errors: return 2
    return 0 if benchmark_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
