#!/usr/bin/env python3
"""Re-run the consumed first CHALLENGE as regression evidence only.

This runner deliberately does NOT make a holdout/generalization claim. The original
10-scenario CHALLENGE has already been opened and is contaminated for tuning. It is
safe to reuse here only as a regression surface for post-CHALLENGE remediation.
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

ROOT = Path(__file__).resolve().parent
SCHEMA = "sef.eval.consumed-challenge-regression.v1"


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_report(command: list[str], output: Path) -> tuple[int, dict[str, Any]]:
    cp = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if not output.is_file():
        raise RuntimeError(
            f"runner produced no report: {' '.join(command)}\n"
            f"stdout={cp.stdout[-2000:]}\nstderr={cp.stderr[-2000:]}"
        )
    return cp.returncode, load(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sef", default=str(ROOT.parent / "sef.py"))
    parser.add_argument("--manifest", default=str(ROOT / "challenge_manifest.json"))
    parser.add_argument("--output", default="consumed-challenge-regression.json")
    args = parser.parse_args()

    sef = Path(args.sef).resolve()
    manifest = load(Path(args.manifest).resolve())
    current_sha = sha256_file(sef)
    expected_ids = [str(x) for x in manifest.get("expected_ids", [])]
    standard_ids = [str(x) for x in manifest.get("standard_runner_ids", [])]
    state_ids = [str(x) for x in manifest.get("state_runner_ids", [])]
    harness_errors: list[str] = []

    if len(expected_ids) != 10 or len(set(expected_ids)) != 10:
        harness_errors.append(f"manifest expected_ids must remain 10 unique IDs: {expected_ids}")
    if sorted(set(standard_ids + state_ids)) != sorted(expected_ids):
        harness_errors.append("runner partitions do not exactly cover consumed challenge IDs")
    if state_ids != ["EVID-002"]:
        harness_errors.append(f"state partition changed unexpectedly: {state_ids}")

    reports: list[tuple[str, int, dict[str, Any]]] = []
    if not harness_errors:
        with tempfile.TemporaryDirectory(prefix="sef-consumed-regression-") as tmp:
            temp = Path(tmp)
            standard_out = temp / "standard.json"
            state_out = temp / "state.json"
            commands = [
                (
                    "standard",
                    [
                        sys.executable,
                        str(ROOT / "run_challenge_standard.py"),
                        "--sef",
                        str(sef),
                        "--scenarios",
                        str(ROOT / "scenarios/challenge"),
                        "--fixtures",
                        str(ROOT / "fixtures"),
                        "--ids",
                        ",".join(standard_ids),
                        "--expected-sef-sha256",
                        current_sha,
                        "--output",
                        str(standard_out),
                    ],
                    standard_out,
                ),
                (
                    "state",
                    [
                        sys.executable,
                        str(ROOT / "run_challenge_state.py"),
                        "--sef",
                        str(sef),
                        "--scenario",
                        str(ROOT / "challenge_state/EVID-002.json"),
                        "--fixtures",
                        str(ROOT / "evidence_release/fixtures"),
                        "--expected-sef-sha256",
                        current_sha,
                        "--output",
                        str(state_out),
                    ],
                    state_out,
                ),
            ]
            for name, command, output in commands:
                try:
                    code, report = run_report(command, output)
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
            item = dict(row)
            item["regression_runner"] = name
            results.append(item)

    observed_ids = [str(row.get("scenario_id")) for row in results]
    duplicates = sorted({sid for sid in observed_ids if observed_ids.count(sid) > 1})
    missing = sorted(set(expected_ids) - set(observed_ids))
    unexpected = sorted(set(observed_ids) - set(expected_ids))
    if duplicates:
        harness_errors.append("duplicate results: " + ", ".join(duplicates))
    if missing:
        harness_errors.append("missing results: " + ", ".join(missing))
    if unexpected:
        harness_errors.append("unexpected results: " + ", ".join(unexpected))
    if len(results) != 10:
        harness_errors.append(f"observed results={len(results)}, expected=10")

    hashes = sorted({str(row.get("sef_source_sha256")) for row in results if row.get("sef_source_sha256")})
    if results and hashes != [current_sha]:
        harness_errors.append(f"result runtime hashes are not uniform: {hashes}")

    counts: dict[str, int] = {}
    for row in results:
        status = str(row.get("status", "UNKNOWN"))
        counts[status] = counts.get(status, 0) + 1
    failures = sorted(str(row.get("scenario_id")) for row in results if row.get("status") != "PASS")
    critical_ids = {str(x) for x in manifest.get("critical_ids", [])}
    critical_failures = sorted(sid for sid in failures if sid in critical_ids)

    report = {
        "schema": SCHEMA,
        "sef_source_sha256": current_sha,
        "evidence_class": "CONSUMED_REGRESSION_ONLY",
        "independent_holdout_claim": False,
        "original_holdout_reuse_status": "CONTAMINATED_FOR_FUTURE_TUNING",
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
            "status": "PASS" if not failures and not harness_errors else ("INVALID" if harness_errors else "FAIL"),
            "counts": counts,
            "failures": failures,
            "critical_failures": critical_failures,
        },
        "results": sorted(results, key=lambda row: str(row.get("scenario_id"))),
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("sef_source_sha256", "evidence_class", "independent_holdout_claim", "accounting", "harness_integrity", "harness_errors", "benchmark")}, indent=2, sort_keys=True))
    if harness_errors:
        return 2
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
