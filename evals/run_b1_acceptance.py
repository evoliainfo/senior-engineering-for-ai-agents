#!/usr/bin/env python3
"""Run the bounded B1 semantic-materiality acceptance corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
CATALOG = EVALS / "b1_controls.json"
RUNNER = EVALS / "run.py"
FIXTURES = EVALS / "fixtures"


def load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sef", required=True)
    p.add_argument("--output", default="b1-acceptance.json")
    a = p.parse_args()

    sef = Path(a.sef).resolve()
    catalog = load(CATALOG)
    scenarios = catalog.get("scenarios", [])
    if catalog.get("schema") != "sef.eval.b1-controls.v1" or not isinstance(scenarios, list) or not scenarios:
        raise SystemExit("invalid B1 control catalog")
    ids = [str(item.get("id")) for item in scenarios if isinstance(item, dict)]
    if len(ids) != len(scenarios) or len(set(ids)) != len(ids):
        raise SystemExit("B1 control IDs must be present and unique")

    with tempfile.TemporaryDirectory(prefix="sef-b1-acceptance-") as tmp:
        root = Path(tmp) / "scenarios"
        root.mkdir(parents=True)
        for item in scenarios:
            (root / f"{item['id']}.json").write_text(json.dumps(item, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        validate = subprocess.run(
            [sys.executable, str(RUNNER), "validate", "--scenarios", str(root)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        try:
            validation = json.loads(validate.stdout)
        except json.JSONDecodeError:
            print(json.dumps({"status":"HARNESS_ERROR","reason":"invalid validation JSON","stdout":validate.stdout[-2000:],"stderr":validate.stderr[-2000:]}, indent=2))
            return 2
        if validate.returncode != 0 or validation.get("status") != "PASS":
            print(json.dumps({"status":"HARNESS_ERROR","validation":validation}, indent=2))
            return 2

        raw_path = Path(tmp) / "raw.json"
        run = subprocess.run(
            [sys.executable, str(RUNNER), "run", "--sef", str(sef), "--scenarios", str(root), "--fixtures", str(FIXTURES), "--set", "DEV", "--output", str(raw_path)],
            cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if not raw_path.exists():
            print(json.dumps({"status":"HARNESS_ERROR","reason":"missing report","stderr":run.stderr[-2000:]}, indent=2))
            return 2
        raw = load(raw_path)

    results = raw.get("results", []) if isinstance(raw.get("results"), list) else []
    observed = [str(r.get("scenario_id")) for r in results if isinstance(r, dict)]
    harness_errors = [str(r.get("scenario_id")) for r in results if isinstance(r, dict) and r.get("status") == "HARNESS_ERROR"]
    accounting = {
        "expected": len(ids), "observed": len(observed), "unique_observed": len(set(observed)),
        "missing": sorted(set(ids)-set(observed)), "unexpected": sorted(set(observed)-set(ids)),
        "duplicates": sorted({x for x in observed if observed.count(x)>1}),
    }
    integrity = not harness_errors and accounting == {
        "expected":len(ids),"observed":len(ids),"unique_observed":len(ids),"missing":[],"unexpected":[],"duplicates":[]
    }
    failures = sorted(str(r.get("scenario_id")) for r in results if isinstance(r, dict) and r.get("status") != "PASS")
    counts = {}
    for r in results:
        status = str(r.get("status", "UNKNOWN")); counts[status] = counts.get(status, 0) + 1
    report = {
        "schema":"sef.eval.b1-acceptance.v1",
        "status":"PASS" if integrity and not failures else ("HARNESS_ERROR" if not integrity else "FAIL"),
        "sef_source_sha256":digest(sef),
        "catalog_sha256":digest(CATALOG),
        "accounting":accounting,
        "harness_errors":harness_errors,
        "benchmark":{"counts":counts,"failures":failures},
        "results":results,
    }
    Path(a.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("status","sef_source_sha256","catalog_sha256","accounting","harness_errors","benchmark")}, indent=2, sort_keys=True))
    if not integrity: return 2
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
