#!/usr/bin/env python3
"""Verify RC-1 shadow detector against frozen contracts and independent probes.

This is an observational gate. It never invokes or changes SEF routing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rc1_shadow import detect_concepts, detected_ids  # noqa: E402

EXPECTED_METAMORPHIC = {
    "MET-001": "AUTHORIZATION",
    "MET-002": "AUTHORIZATION",
    "MET-003": "DATABASE_MIGRATION",
    "MET-004": "DATABASE_MIGRATION",
    "MET-005": "WEBHOOK_TRUST",
    "MET-006": "WEBHOOK_TRUST",
    "MET-007": "EXTERNAL_SUPPLIER",
    "MET-008": "EXTERNAL_SUPPLIER",
    "MET-009": "BACKGROUND_JOB",
    "MET-010": "BACKGROUND_JOB",
    "MET-011": "SEO_WEB_DISCOVERABILITY",
    "MET-012": "SEO_WEB_DISCOVERABILITY",
}


def load_scenarios(path: Path):
    for file in sorted(path.glob("*.json")):
        yield file, json.loads(file.read_text(encoding="utf-8"))


def record(rows, failures, scenario, kind, request, expected):
    result = detect_concepts(request)
    ids = detected_ids(result)
    ok = (expected in ids) if expected else (not ids)
    rows.append({"scenario": scenario, "kind": kind, "expected": expected or [], "detected": sorted(ids), "ok": ok})
    if not ok:
        failures.append(f"{scenario}: expected {expected or []}, got {sorted(ids)}")


def main() -> int:
    failures = []
    rows = []

    for _, scenario in load_scenarios(ROOT / "evals/rc1_candidate/metamorphic"):
        sid = scenario["id"]
        record(rows, failures, sid, "metamorphic", scenario["request"], EXPECTED_METAMORPHIC[sid])

    for _, scenario in load_scenarios(ROOT / "evals/rc1_candidate/negative_controls"):
        record(rows, failures, scenario["id"], "negative_control", scenario["request"], None)

    probes = json.loads((ROOT / "evals/rc1_shadow_probe_requests.json").read_text(encoding="utf-8"))
    for index, probe in enumerate(probes.get("positive", []), 1):
        record(rows, failures, f"PROBE-POS-{index:02d}", "independent_positive", probe["request"], probe["concept"])
    for index, probe in enumerate(probes.get("negative", []), 1):
        record(rows, failures, f"PROBE-NEG-{index:02d}", "independent_negative", probe["request"], None)

    report = {
        "mode": "SHADOW_ONLY",
        "routing_effect": "NONE",
        "summary": {
            "total": len(rows),
            "pass": sum(1 for row in rows if row["ok"]),
            "fail": sum(1 for row in rows if not row["ok"]),
        },
        "results": rows,
        "failures": failures,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
