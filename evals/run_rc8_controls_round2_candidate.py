#!/usr/bin/env python3
"""Run calibrated RC-8 Round-2 controls against an explicit SEF candidate."""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from pathlib import Path

import run_rc8_controls as base

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "rc8_controls.json"
CALIBRATION = ROOT / "rc8_calibration_round2.json"


def load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def merge(target: dict, patch: dict) -> dict:
    out = copy.deepcopy(target)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sef", required=True)
    parser.add_argument("--output", default="rc8-control-candidate-round2.json")
    args = parser.parse_args()

    catalog = load(CATALOG)
    calibration = load(CALIBRATION)
    overrides = calibration.get("overrides", {})
    scenarios = catalog.get("scenarios", [])
    by_id = {item.get("id"): item for item in scenarios if isinstance(item, dict)}
    unknown = sorted(set(overrides) - set(by_id))
    if unknown:
        raise SystemExit(f"calibration references unknown controls: {unknown}")

    calibrated = copy.deepcopy(catalog)
    calibrated["schema"] = "sef.eval.rc8-controls.v1"
    calibrated["purpose"] = "Calibrated Round-2 controls executed against an explicit remediation candidate."
    calibrated["calibration_schema"] = calibration.get("schema")
    calibrated["calibration_base_catalog_sha256"] = calibration.get("base_catalog_sha256")
    calibrated["scenarios"] = [merge(item, overrides.get(item.get("id"), {})) for item in scenarios]

    with tempfile.TemporaryDirectory(prefix="sef-rc8-candidate-round2-") as tmp:
        calibrated_path = Path(tmp) / "rc8_controls_round2.json"
        calibrated_path.write_text(json.dumps(calibrated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        old_catalog = base.CATALOG
        old_sef = base.SEF
        old_argv = sys.argv[:]
        try:
            base.CATALOG = calibrated_path
            base.SEF = Path(args.sef).resolve()
            sys.argv = ["run_rc8_controls.py", "--output", args.output]
            return int(base.main())
        finally:
            base.CATALOG = old_catalog
            base.SEF = old_sef
            sys.argv = old_argv


if __name__ == "__main__":
    raise SystemExit(main())
