#!/usr/bin/env python3
"""Run the B2 positive/negative acceptance surface against an explicit SEF source."""
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
CATALOG = ROOT / "b2_controls.json"
RUNNER = ROOT / "run.py"
FIXTURES = ROOT / "fixtures"


def load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sef", default=str(ROOT.parent / "sef.py"))
    parser.add_argument("--output", default="b2-acceptance.json")
    args = parser.parse_args()

    sef = Path(args.sef).resolve()
    catalog = load(CATALOG)
    if catalog.get("schema") != "sef.eval.b2-controls.v1":
        raise SystemExit("unexpected B2 control catalog schema")
    scenarios = catalog.get("scenarios")
    if not isinstance(scenarios, list) or len(scenarios) != 10:
        raise SystemExit("B2 catalog must contain exactly 10 controls")
    ids = [str(item.get("id")) for item in scenarios if isinstance(item, dict)]
    if len(ids) != 10 or len(set(ids)) != 10:
        raise SystemExit("B2 control IDs must be present and unique")

    with tempfile.TemporaryDirectory(prefix="sef-b2-acceptance-") as tmp:
        temp = Path(tmp)
        scenario_root = temp / "scenarios"
        scenario_root.mkdir(parents=True)
        for item in scenarios:
            (scenario_root / f"{item['id']}.json").write_text(
                json.dumps(item, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        validate = subprocess.run(
            [sys.executable, str(RUNNER), "validate", "--scenarios", str(scenario_root)],
            cwd=ROOT.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            validation = json.loads(validate.stdout)
        except json.JSONDecodeError:
            print(json.dumps({"status":"HARNESS_ERROR","reason":"invalid validation JSON","stdout":validate.stdout[-2000:],"stderr":validate.stderr[-2000:]}, indent=2))
            return 2
        if validate.returncode != 0 or validation.get("status") != "PASS":
            print(json.dumps({"status":"HARNESS_ERROR","validation":validation}, indent=2))
            return 2

        raw_path = temp / "raw.json"
        run = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "run",
                "--sef",
                str(sef),
                "--scenarios",
                str(scenario_root),
                "--fixtures",
                str(FIXTURES),
                "--set",
                "DEV",
                "--output",
                str(raw_path),
            ],
            cwd=ROOT.parent,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if not raw_path.is_file():
            print(json.dumps({"status":"HARNESS_ERROR","reason":"missing raw report","stdout":run.stdout[-2000:],"stderr":run.stderr[-2000:]}, indent=2))
            return 2
        raw = load(raw_path)

    results = raw.get("results") if isinstance(raw.get("results"), list) else []
    observed = [str(item.get("scenario_id")) for item in results if isinstance(item, dict)]
    duplicates = sorted({sid for sid in observed if observed.count(sid) > 1})
    missing = sorted(set(ids) - set(observed))
    unexpected = sorted(set(observed) - set(ids))
    harness_error_ids = sorted(str(item.get("scenario_id")) for item in results if item.get("status") == "HARNESS_ERROR")
    harness_errors = []
    if duplicates: harness_errors.append("duplicates: " + ", ".join(duplicates))
    if missing: harness_errors.append("missing: " + ", ".join(missing))
    if unexpected: harness_errors.append("unexpected: " + ", ".join(unexpected))
    if harness_error_ids: harness_errors.append("HARNESS_ERROR: " + ", ".join(harness_error_ids))
    if len(results) != 10: harness_errors.append(f"observed={len(results)}, expected=10")

    counts: dict[str, int] = {}
    for item in results:
        status = str(item.get("status", "UNKNOWN"))
        counts[status] = counts.get(status, 0) + 1
    failures = sorted(str(item.get("scenario_id")) for item in results if item.get("status") != "PASS")
    report = {
        "schema":"sef.eval.b2-acceptance.v1",
        "sef_source_sha256":sha256(sef),
        "catalog_sha256":sha256(CATALOG),
        "accounting":{"expected":10,"observed":len(results),"unique_observed":len(set(observed)),"missing":missing,"unexpected":unexpected,"duplicates":duplicates},
        "harness_integrity":"PASS" if not harness_errors else "FAIL",
        "harness_errors":harness_errors,
        "benchmark":{"status":"PASS" if not failures and not harness_errors else ("INVALID" if harness_errors else "FAIL"),"counts":counts,"failures":failures},
        "results":sorted(results,key=lambda item:str(item.get("scenario_id"))),
    }
    Path(args.output).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({key:report[key] for key in ("sef_source_sha256","catalog_sha256","accounting","harness_integrity","harness_errors","benchmark")},indent=2,sort_keys=True))
    if harness_errors: return 2
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
