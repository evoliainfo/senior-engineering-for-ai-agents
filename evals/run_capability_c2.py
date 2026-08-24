#!/usr/bin/env python3
"""Deterministic DEV qualification for C2 foundation capabilities.

This evaluates capability contracts, method coverage, flexibility/context properties,
registry integrity, reserved pilot separation, lifecycle coverage documentation and
legacy runtime integrity. It does not call a model and does not claim agent outcome value.

C2 is a regression gate after later capability tranches are added. It therefore proves
that the six C2 capabilities remain present and satisfy their original contracts; it
must not require the entire catalog to remain permanently fixed at six entries.
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
CASES_PATH = ROOT / "evals" / "capability_c2_cases.json"
RESERVATIONS_PATH = ROOT / "evals" / "capability_c2_pilot_reservations.json"
DELIVERY_CONTRACT = ROOT / "docs" / "SENIOR_DELIVERY_CONTRACT.md"
REPORT_PATH = ROOT / "eval-results" / "capability-c2-report.json"
GENERATED_MANIFEST_PATH = ROOT / "eval-results" / "capabilities-manifest.generated.json"

CAPABILITIES = [
    "repository-discovery",
    "requirements-to-acceptance",
    "implementation-planning",
    "tdd-bug-reproduction",
    "systematic-debugging",
    "verification-before-completion",
]

CONTEXT_MARKERS = {
    "repository-discovery": ["smallest useful repository map", "do not keep reading files"],
    "requirements-to-acceptance": ["skip a formal acceptance contract for trivial", "do not add generic non-functional requirements by reflex"],
    "implementation-planning": ["for a trivial local edit", "plan can shrink for small tasks"],
    "tdd-bug-reproduction": ["do not force a synthetic red phase", "smallest relevant regression set"],
    "systematic-debugging": ["for an obvious local defect", "debug the narrowest real path"],
    "verification-before-completion": ["smallest sufficient evidence set", "do not reload the whole repository"],
}

RIGID_TOOL_PATTERNS = [
    re.compile(r"\balways use\s+(npm|pnpm|yarn|bun|pytest|playwright|jest|vitest)\b", re.I),
    re.compile(r"\bminimum\s+80%\s+coverage\b", re.I),
    re.compile(r"\bmust use\s+(next\.js|react|supabase|postgres(?:ql)?)\b", re.I),
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(name: str, ok: bool, detail: str = "") -> dict[str, str]:
    return {"name": name, "status": "PASS" if ok else "FAIL", "detail": detail}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_markdown_text(text: str) -> str:
    """Normalize presentation-only Markdown so contract checks target meaning."""
    normalized = text.lower()
    for marker in ("**", "__", "`"):
        normalized = normalized.replace(marker, "")
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    checks: list[dict[str, str]] = []

    cases_doc = _load_json(CASES_PATH)
    cases = cases_doc.get("cases", [])
    case_ids = [case.get("id") for case in cases]
    cases_by_cap: dict[str, list[dict]] = {cap: [] for cap in CAPABILITIES}
    for case in cases:
        cap = case.get("capability")
        if cap in cases_by_cap:
            cases_by_cap[cap].append(case)

    corpus_ok = (
        cases_doc.get("schema") == "sef.eval.capability-c2.v1"
        and cases_doc.get("independent_holdout") is False
        and len(cases) == 18
        and len(set(case_ids)) == 18
        and all(len(cases_by_cap[cap]) == 3 for cap in CAPABILITIES)
    )
    checks.append(_check("C2-CORPUS-STRUCTURE", corpus_ok, f"cases={len(cases)} unique={len(set(case_ids))}"))

    skill_text: dict[str, str] = {}
    metadata: dict[str, dict] = {}
    for cap in CAPABILITIES:
        skill_path = CAP_ROOT / cap / "SKILL.md"
        meta_path = CAP_ROOT / cap / "capability.json"
        skill_text[cap] = _normalize_markdown_text(skill_path.read_text(encoding="utf-8"))
        metadata[cap] = _load_json(meta_path)

    for case in cases:
        cap = case["capability"]
        text = skill_text[cap]
        patterns = [_normalize_markdown_text(str(value)) for value in case.get("required_patterns", [])]
        missing = [pattern for pattern in patterns if pattern not in text]
        checks.append(
            _check(
                case["id"],
                bool(patterns) and not missing,
                "all method clauses covered" if not missing else f"missing={missing}",
            )
        )

    for cap in CAPABILITIES:
        expected = sorted(case["id"] for case in cases_by_cap[cap])
        actual = sorted(metadata[cap].get("evals", []))
        checks.append(_check(f"C2-EVAL-LINK-{cap}", actual == expected, f"expected={expected} actual={actual}"))

    for cap in CAPABILITIES:
        text = skill_text[cap]
        words = re.findall(r"\b[\w'-]+\b", text)
        has_adaptation = "repository" in text or "project" in text
        has_evidence = "evidence" in text or "verification" in text
        has_failure_modes = "anti-pattern" in text or "failure modes" in text
        has_context_design = all(marker in text for marker in CONTEXT_MARKERS[cap])
        rigid_hits = [pattern.pattern for pattern in RIGID_TOOL_PATTERNS if pattern.search(text)]
        length_ok = 300 <= len(words) <= 3000
        quality_ok = all([has_adaptation, has_evidence, has_failure_modes, has_context_design, length_ok, not rigid_hits])
        detail = (
            f"words={len(words)} adaptation={has_adaptation} evidence={has_evidence} "
            f"failure_modes={has_failure_modes} context={has_context_design} rigid_hits={rigid_hits}"
        )
        checks.append(_check(f"C2-QUALITY-{cap}", quality_ok, detail))

    reservations_doc = _load_json(RESERVATIONS_PATH)
    reservations = reservations_doc.get("reservations", [])
    reservation_caps = [item.get("capability") for item in reservations]
    pilot_ok = (
        reservations_doc.get("finalize_after_candidate_freeze") is True
        and len(reservations) == 6
        and sorted(reservation_caps) == sorted(CAPABILITIES)
        and len({item.get("id") for item in reservations}) == 6
        and all(item.get("scenario_content") is None for item in reservations)
    )
    checks.append(_check("C2-PILOT-SEPARATION", pilot_ok, f"reservations={len(reservations)} content_redacted={pilot_ok}"))

    # C2 is a regression slice of an extensible registry. Later tranches may add
    # entries, but every original C2 capability must remain registered and valid.
    manifest = build_manifest(CAP_ROOT)
    manifest_ids = [entry["id"] for entry in manifest["capabilities"]]
    missing_c2 = sorted(set(CAPABILITIES) - set(manifest_ids))
    registry_ok = not missing_c2 and manifest_ids == sorted(manifest_ids)
    checks.append(
        _check(
            "C2-REGISTRY",
            registry_ok,
            f"catalog_count={manifest['capability_count']} c2_present={not missing_c2} missing_c2={missing_c2}",
        )
    )

    lifecycle = DELIVERY_CONTRACT.read_text(encoding="utf-8").lower()
    required_lifecycle = [
        "stage 0 — problem and outcome framing",
        "stage 1 — requirements and acceptance",
        "stage 2 — project/repository understanding",
        "stage 3 — solution architecture and technical decisions",
        "stage 4 — implementation planning",
        "stage 5 — implementation",
        "stage 6 — test, debug and quality verification",
        "stage 7 — security, data and operational review",
        "stage 8 — code/diff review and release readiness",
        "stage 9 — deployment execution",
        "stage 10 — post-deployment verification",
        "stage 11 — handoff and maintainability",
        "greenfield and brownfield paths",
        "must not claim full idea-to-production lifecycle coverage",
    ]
    missing_lifecycle = [value for value in required_lifecycle if value not in lifecycle]
    checks.append(_check("C2-SENIOR-DELIVERY-CONTRACT", not missing_lifecycle, f"missing={missing_lifecycle}"))

    sums = (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    expected_sef = None
    for line in sums:
        parts = line.split()
        if len(parts) >= 2 and parts[-1] == "sef.py":
            expected_sef = parts[0]
            break
    actual_sef = _sha256(ROOT / "sef.py")
    runtime_ok = bool(expected_sef) and expected_sef == actual_sef
    checks.append(_check("C2-LEGACY-RUNTIME-INTEGRITY", runtime_ok, f"expected={expected_sef} actual={actual_sef}"))

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    GENERATED_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    pass_count = sum(check["status"] == "PASS" for check in checks)
    fail_count = len(checks) - pass_count
    report = {
        "schema": "sef.eval.capability-c2-report.v1",
        "status": "PASS" if fail_count == 0 else "FAIL",
        "independent_holdout_claim": False,
        "agent_outcome_claim": False,
        "provider_calls": 0,
        "capability_count": manifest["capability_count"],
        "c2_capability_count": len(CAPABILITIES),
        "case_count": len(cases),
        "check_count": len(checks),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "manifest_content_sha256": manifest["content_sha256"],
        "sef_runtime_sha256": actual_sef,
        "checks": checks,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
