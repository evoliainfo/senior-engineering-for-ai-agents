#!/usr/bin/env python3
"""Deterministic DEV qualification for C3 senior-inception capabilities.

C3 validates the six new capability contracts, their proportionality and composition
with the six C2 capabilities, the protected C4 pilot reservation, manifest integrity,
and the frozen deterministic beta runtime. It makes no agent-outcome or independent
benchmark claim and performs no model/provider call.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.capability_registry import build_manifest  # noqa: E402

CAP_ROOT = ROOT / "capabilities"
CASES_PATH = ROOT / "evals" / "capability_c3_cases.json"
PILOT_RESERVATIONS = ROOT / "evals" / "capability_c4_pilot_reservations.json"
ROADMAP = ROOT / "docs" / "SENIOR_DELIVERY_BUILD_PLAN_V2.md"
REPORT_PATH = ROOT / "eval-results" / "capability-c3-report.json"
GENERATED_MANIFEST_PATH = ROOT / "eval-results" / "capabilities-manifest.generated.json"

C2_CAPABILITIES = [
    "repository-discovery",
    "requirements-to-acceptance",
    "implementation-planning",
    "tdd-bug-reproduction",
    "systematic-debugging",
    "verification-before-completion",
]

C3_CAPABILITIES = [
    "product-problem-framing",
    "solution-architecture-stack-selection",
    "project-bootstrap-foundations",
    "environment-secrets-configuration",
    "architecture-conformant-implementation",
    "code-review-diff-review",
]

EXPECTED_CATALOG = sorted(C2_CAPABILITIES + C3_CAPABILITIES)

CONTEXT_MARKERS = {
    "product-problem-framing": ["for a tiny feature request", "do not read the full repository"],
    "solution-architecture-stack-selection": ["avoid scoring dozens of generic qualities", "do not perform encyclopedic technology research"],
    "project-bootstrap-foundations": ["do not pre-load specialist guides", "do not build a complex delivery pipeline"],
    "environment-secrets-configuration": ["do not enumerate or print the user's entire environment", "do not block unrelated implementation"],
    "architecture-conformant-implementation": ["for a tiny, obvious edit", "avoid generic checklists disconnected from the task"],
    "code-review-diff-review": ["for a trivial, obvious one-line change", "review proportionally"],
}

RIGID_TOOL_PATTERNS = [
    re.compile(r"\balways use\s+(npm|pnpm|yarn|bun|pytest|playwright|jest|vitest)\b", re.I),
    re.compile(r"\bminimum\s+80%\s+coverage\b", re.I),
    re.compile(r"\bmust use\s+(next\.js|react|supabase|postgres(?:ql)?|vercel|aws)\b", re.I),
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize(text: str) -> str:
    normalized = text.lower()
    for marker in ("**", "__", "`", ">"):
        normalized = normalized.replace(marker, "")
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    checks: list[dict[str, str]] = []

    cases_doc = _load_json(CASES_PATH)
    cases = cases_doc.get("cases", [])
    case_ids = [case.get("id") for case in cases]
    cases_by_cap: dict[str, list[dict]] = {cap: [] for cap in C3_CAPABILITIES}
    for case in cases:
        cap = case.get("capability")
        if cap in cases_by_cap:
            cases_by_cap[cap].append(case)

    corpus_ok = (
        cases_doc.get("schema") == "sef.eval.capability-c3.v1"
        and cases_doc.get("independent_holdout") is False
        and len(cases) == 18
        and len(set(case_ids)) == 18
        and all(len(cases_by_cap[cap]) == 3 for cap in C3_CAPABILITIES)
    )
    checks.append(_check("C3-CORPUS-STRUCTURE", corpus_ok, f"cases={len(cases)} unique={len(set(case_ids))}"))

    texts: dict[str, str] = {}
    metadata: dict[str, dict] = {}
    for cap in C3_CAPABILITIES:
        texts[cap] = _normalize((CAP_ROOT / cap / "SKILL.md").read_text(encoding="utf-8"))
        metadata[cap] = _load_json(CAP_ROOT / cap / "capability.json")

    # 18 preregistered DEV method-contract cases.
    for case in cases:
        cap = case["capability"]
        patterns = [_normalize(str(value)) for value in case.get("required_patterns", [])]
        missing = [pattern for pattern in patterns if pattern not in texts[cap]]
        checks.append(
            _check(
                case["id"],
                bool(patterns) and not missing,
                "all method clauses covered" if not missing else f"missing={missing}",
            )
        )

    # Metadata must point exactly to its preregistered C3 cases.
    for cap in C3_CAPABILITIES:
        expected = sorted(case["id"] for case in cases_by_cap[cap])
        actual = sorted(metadata[cap].get("evals", []))
        checks.append(_check(f"C3-EVAL-LINK-{cap}", actual == expected, f"expected={expected} actual={actual}"))

    # C3 capability quality: sufficiently explicit method, evidence/failure contract,
    # proportional context design, and no universal tooling mandates.
    for cap in C3_CAPABILITIES:
        text = texts[cap]
        words = re.findall(r"\b[\w'-]+\b", text)
        has_evidence = "evidence contract" in text or "verification of capability use" in text
        has_failure_modes = "anti-pattern" in text or "failure modes" in text
        has_context_design = all(_normalize(marker) in text for marker in CONTEXT_MARKERS[cap])
        has_user_authority_boundary = (
            "ask" in text and "user" in text
            and ("decision" in text or "authority" in text or "trade-off" in text)
        )
        rigid_hits = [pattern.pattern for pattern in RIGID_TOOL_PATTERNS if pattern.search(text)]
        length_ok = 300 <= len(words) <= 3000
        quality_ok = all([
            has_evidence,
            has_failure_modes,
            has_context_design,
            has_user_authority_boundary,
            length_ok,
            not rigid_hits,
        ])
        checks.append(
            _check(
                f"C3-QUALITY-{cap}",
                quality_ok,
                (
                    f"words={len(words)} evidence={has_evidence} failure_modes={has_failure_modes} "
                    f"context={has_context_design} user_boundary={has_user_authority_boundary} rigid_hits={rigid_hits}"
                ),
            )
        )

    # Freeze-before-content separation for the C4 value pilot.
    pilot = _load_json(PILOT_RESERVATIONS)
    reservations = pilot.get("reservations", [])
    green = [item for item in reservations if item.get("track") == "greenfield"]
    brown = [item for item in reservations if item.get("track") == "brownfield"]
    pilot_ok = (
        pilot.get("candidate_freeze_required_before_finalization") is True
        and pilot.get("scenario_content_withheld") is True
        and pilot.get("independent_holdout_claim") is False
        and len(reservations) == 12
        and len(green) == 6
        and len(brown) == 6
        and len({item.get("id") for item in reservations}) == 12
        and all(item.get("scenario_content") is None for item in reservations)
    )
    checks.append(_check("C3-C4-PILOT-SEPARATION", pilot_ok, f"slots={len(reservations)} green={len(green)} brown={len(brown)}"))

    # Registry must now contain exactly the measured 12-capability core. Catalog
    # expansion is forbidden until the C4 value pilot passes.
    manifest = build_manifest(CAP_ROOT)
    manifest_ids = [entry["id"] for entry in manifest["capabilities"]]
    catalog_ok = manifest["capability_count"] == 12 and manifest_ids == EXPECTED_CATALOG
    checks.append(_check("C3-REGISTRY-12-CORE", catalog_ok, f"count={manifest['capability_count']} ids={manifest_ids}"))

    # The authoritative roadmap must preserve the stop-and-measure rule.
    roadmap = _normalize(ROADMAP.read_text(encoding="utf-8"))
    required_roadmap = [
        "pause expansion after the first 12 capabilities",
        "do not immediately build more skills after c3",
        "freeze the 12-capability core",
        "6 brownfield tasks",
        "6 greenfield/inception-to-implemented-slice tasks",
        "improves vs codex alone by at least 8 percentage points",
    ]
    missing_roadmap = [item for item in required_roadmap if _normalize(item) not in roadmap]
    checks.append(_check("C3-ROADMAP-ANTI-CATALOG-LOOP", not missing_roadmap, f"missing={missing_roadmap}"))

    # Frozen deterministic beta runtime remains immutable during capability work.
    expected_sef = None
    for line in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == "sef.py":
            expected_sef = parts[0]
            break
    actual_sef = _sha256(ROOT / "sef.py")
    runtime_ok = bool(expected_sef) and expected_sef == actual_sef
    checks.append(_check("C3-LEGACY-RUNTIME-INTEGRITY", runtime_ok, f"expected={expected_sef} actual={actual_sef}"))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    pass_count = sum(check["status"] == "PASS" for check in checks)
    fail_count = len(checks) - pass_count
    report = {
        "schema": "sef.eval.capability-c3-report.v1",
        "status": "PASS" if fail_count == 0 else "FAIL",
        "stage": "C3_SENIOR_INCEPTION_AND_IMPLEMENTATION",
        "independent_holdout_claim": False,
        "agent_outcome_claim": False,
        "provider_calls": 0,
        "c3_capability_count": len(C3_CAPABILITIES),
        "catalog_capability_count": manifest["capability_count"],
        "case_count": len(cases),
        "check_count": len(checks),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "manifest_content_sha256": manifest["content_sha256"],
        "sef_runtime_sha256": actual_sef,
        "checks": checks,
    }
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
