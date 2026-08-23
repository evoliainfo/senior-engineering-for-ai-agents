#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import candidate

ROOT = Path(__file__).resolve().parent
CASES = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))


def build_observation(raw):
    return candidate.from_command_result(
        check_id=raw["check_id"],
        revision=raw["revision"],
        attempt=raw["attempt"],
        required=raw["required"],
        returncode=raw.get("returncode"),
        adapter_state=raw.get("adapter_state"),
        stderr=raw.get("stderr", ""),
    )


rows = []
failures = []
for case in CASES:
    observations = [build_observation(o) for o in case.get("observations", [])]
    evidence = candidate.synthesize(
        observations,
        revision=case["revision"],
        required_checks=case.get("required_checks", []),
        optional_checks=case.get("optional_checks", []),
    )
    release = candidate.release_gate(
        evidence=evidence,
        current_revision=case.get("release_revision", case["revision"]),
        dirty=case.get("dirty", False),
        unresolved_material_confirmations=case.get("unresolved_material_confirmations", []),
    )
    checks = [
        ("state", evidence["state"], case["expected_state"]),
        ("release", release["release_readiness"], case["expected_release"]),
    ]
    ok = all(actual == expected for _, actual, expected in checks)
    if case.get("expected_blocker"):
        blocker_ok = case["expected_blocker"] in release["blockers"]
        checks.append(("blocker", blocker_ok, True))
        ok = ok and blocker_ok
    if case.get("expected_blocker_prefix"):
        blocker_ok = any(b.startswith(case["expected_blocker_prefix"]) for b in release["blockers"])
        checks.append(("blocker_prefix", blocker_ok, True))
        ok = ok and blocker_ok

    row = {
        "id": case["id"],
        "kind": case["kind"],
        "expected_state": case["expected_state"],
        "observed_state": evidence["state"],
        "expected_release": case["expected_release"],
        "observed_release": release["release_readiness"],
        "blockers": release["blockers"],
        "pass": ok,
    }
    rows.append(row)
    if not ok:
        failures.append({"id": case["id"], "checks": checks, "row": row})

out = Path("artifacts/rc4-evidence-release")
out.mkdir(parents=True, exist_ok=True)
(out / "observations.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
(out / "summary.json").write_text(
    json.dumps(
        {
            "total": len(rows),
            "passed": sum(r["pass"] for r in rows),
            "treatments": sum(r["kind"] == "treatment" for r in rows),
            "controls": sum(r["kind"] == "control" for r in rows),
            "failures": failures,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(f"RC-4 isolated evidence reducer: {sum(r['pass'] for r in rows)}/{len(rows)} PASS")
for row in rows:
    print(
        row["id"],
        row["expected_state"], "->", row["observed_state"],
        row["expected_release"], "->", row["observed_release"],
        "PASS" if row["pass"] else "FAIL",
        row["blockers"],
    )
if failures:
    raise SystemExit(json.dumps(failures, ensure_ascii=False))
