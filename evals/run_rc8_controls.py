#!/usr/bin/env python3
"""Run RC-8 research controls without treating expected baseline misses as CI failure.

A HARNESS_ERROR or accounting defect is fatal. Ordinary PASS/FAIL outcomes are
measurement data: this runner exists to freeze the pre-remediation behavior before
any sef.py change.
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
CATALOG = EVALS / "rc8_controls.json"
RUNNER = EVALS / "run.py"
FIXTURES = EVALS / "fixtures"
SEF = ROOT / "sef.py"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="rc8-control-baseline.json")
    args = parser.parse_args()

    catalog = load_json(CATALOG)
    if catalog.get("schema") != "sef.eval.rc8-controls.v1":
        raise SystemExit("unexpected RC-8 control catalog schema")
    scenarios = catalog.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise SystemExit("RC-8 control catalog is empty")

    ids = [str(item.get("id")) for item in scenarios if isinstance(item, dict)]
    if len(ids) != len(scenarios) or len(set(ids)) != len(ids):
        raise SystemExit("RC-8 control IDs must be present and unique")

    with tempfile.TemporaryDirectory(prefix="sef-rc8-controls-") as tmp:
        scenario_root = Path(tmp) / "scenarios"
        scenario_root.mkdir(parents=True)
        for item in scenarios:
            (scenario_root / f"{item['id']}.json").write_text(
                json.dumps(item, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

        validate = subprocess.run(
            [sys.executable, str(RUNNER), "validate", "--scenarios", str(scenario_root)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            validation = json.loads(validate.stdout)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"control validation returned invalid JSON: {validate.stdout[-2000:]}") from exc
        if validate.returncode != 0 or validation.get("status") != "PASS":
            print(json.dumps({"status": "HARNESS_ERROR", "validation": validation}, indent=2))
            return 2

        report_path = Path(tmp) / "raw-report.json"
        run = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "run",
                "--sef",
                str(SEF),
                "--scenarios",
                str(scenario_root),
                "--fixtures",
                str(FIXTURES),
                "--set",
                "DEV",
                "--output",
                str(report_path),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if not report_path.exists():
            print(json.dumps({"status": "HARNESS_ERROR", "reason": "missing raw report", "stderr": run.stderr[-2000:]}, indent=2))
            return 2
        raw = load_json(report_path)

    results = raw.get("results") if isinstance(raw.get("results"), list) else []
    observed_ids = [str(item.get("scenario_id")) for item in results if isinstance(item, dict)]
    harness_errors = [
        str(item.get("scenario_id"))
        for item in results
        if isinstance(item, dict) and item.get("status") == "HARNESS_ERROR"
    ]
    accounting = {
        "expected": len(ids),
        "observed": len(observed_ids),
        "unique_observed": len(set(observed_ids)),
        "missing": sorted(set(ids) - set(observed_ids)),
        "unexpected": sorted(set(observed_ids) - set(ids)),
        "duplicates": sorted({item for item in observed_ids if observed_ids.count(item) > 1}),
    }
    integrity_ok = (
        not harness_errors
        and accounting["expected"] == accounting["observed"] == accounting["unique_observed"]
        and not accounting["missing"]
        and not accounting["unexpected"]
        and not accounting["duplicates"]
    )

    by_hypothesis: dict[str, dict[str, int]] = {}
    for item in results:
        sid = str(item.get("scenario_id"))
        parts = sid.split("-")
        hypothesis = parts[1] if len(parts) >= 3 else "UNKNOWN"
        status = str(item.get("status", "UNKNOWN"))
        bucket = by_hypothesis.setdefault(hypothesis, {})
        bucket[status] = bucket.get(status, 0) + 1

    output = {
        "schema": "sef.eval.rc8-control-baseline.v1",
        "status": "MEASURED" if integrity_ok else "HARNESS_ERROR",
        "purpose": "Pre-remediation RC-8 control observations; PASS/FAIL are diagnostic data, not a release verdict.",
        "sef_source_sha256": sha256(SEF),
        "catalog_sha256": sha256(CATALOG),
        "accounting": accounting,
        "harness_errors": harness_errors,
        "by_hypothesis": by_hypothesis,
        "raw_summary": raw.get("summary"),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: output[k] for k in ("status", "sef_source_sha256", "catalog_sha256", "accounting", "harness_errors", "by_hypothesis", "raw_summary")}, indent=2, sort_keys=True))
    return 0 if integrity_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
