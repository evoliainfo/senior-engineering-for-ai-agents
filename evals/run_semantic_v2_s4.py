#!/usr/bin/env python3
"""Acceptance runner for Semantic Routing v2 S4 shadow integration."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping

from semantic_v2 import DeterministicPolicyComposer, ModelAssistedExtractor, ShadowRouter
from semantic_v2.shadow_integration import compare_policies, summarize_shadow_results

ROOT = Path(__file__).resolve().parents[1]
CONTROLS = ROOT / "evals" / "semantic_v2" / "s4_controls.json"
FIXTURES = ROOT / "evals" / "fixtures"
SEF = ROOT / "sef.py"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def run_process(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX"):
        env.pop(key, None)
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=180,
    )


def run_json(command: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    completed = run_process(command, cwd=cwd)
    try:
        payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"non-JSON command output: {' '.join(command)}; stderr={completed.stderr[-1200:]}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError("command output must be a JSON object")
    if completed.returncode != 0 or payload.get("status") != "PASS":
        raise RuntimeError(
            f"command failed: {' '.join(command)}; rc={completed.returncode}; "
            f"payload={canonical_json(payload)[:1800]}; stderr={completed.stderr[-1200:]}"
        )
    return payload


def legacy_plan(*, fixture_name: str, project_brief: str, request: str) -> dict[str, Any]:
    fixture = FIXTURES / fixture_name
    if not fixture.is_dir():
        raise RuntimeError(f"fixture not found: {fixture_name}")
    with tempfile.TemporaryDirectory(prefix="sef-semantic-s4-") as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(fixture, repo)
        run_json([sys.executable, str(SEF), "init", str(repo), "--brief", project_brief])
        installed = repo / ".sef" / "sef.py"
        payload = run_json(
            [sys.executable, str(installed), "plan", str(repo), "--request", request, "--save"]
        )
    plan = payload.get("plan") if isinstance(payload.get("plan"), Mapping) else {}
    assessment = plan.get("assessment") if isinstance(plan.get("assessment"), Mapping) else {}
    return {
        "risk": assessment.get("risk"),
        "packs": list(assessment.get("required_packs") or []),
        "procedures": list(plan.get("procedures") or []),
        "implementation_allowed": plan.get("implementation_allowed"),
        "implementation_gate": plan.get("implementation_gate"),
        "action_class": assessment.get("action_class"),
        "execution_contexts": list(assessment.get("execution_contexts") or []),
    }


class StaticProvider:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = copy.deepcopy(dict(payload))

    def extract_semantics(
        self,
        request: str,
        project_context: Mapping[str, Any],
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        return copy.deepcopy(self.payload)


class InvalidIRExtractor:
    def extract(self, request: str, project_context: Mapping[str, Any]) -> dict[str, Any]:
        return {"schema": "invalid-semantic-ir"}


def provenance() -> list[dict[str, Any]]:
    return [
        {
            "source_kind": "request",
            "locator": "request",
            "confidence": 0.99,
            "ambiguity": "none",
        }
    ]


def semantic_payload(kinds: list[str]) -> dict[str, Any]:
    facts: list[dict[str, Any]] = []
    for index, kind in enumerate(kinds, 1):
        facts.append(
            {
                "id": f"s4-fact-{index:02d}",
                "kind": kind,
                "material": True,
                "subject": None,
                "object": None,
                "attributes": {"s4_scripted_fact": True},
                "provenance": provenance(),
            }
        )
    return {"complete": True, "facts": facts, "uncertainties": []}


def result(control_id: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"id": control_id, "status": "PASS" if passed else "FAIL", "detail": detail}


def composed_policy(
    *,
    risk: str | None,
    packs: list[str],
    procedures: list[str] | None = None,
    implementation_allowed: bool = True,
    status: str = "COMPOSED",
) -> dict[str, Any]:
    return {
        "status": status,
        "risk": risk,
        "packs": packs,
        "procedures": procedures or [],
        "implementation_allowed": implementation_allowed,
    }


def run_parallel_case(case: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    cid = str(case["id"])
    request = str(case["request"])
    legacy = legacy_plan(
        fixture_name=str(case["fixture"]),
        project_brief=str(case["project_brief"]),
        request=request,
    )
    provider = StaticProvider(semantic_payload([str(v) for v in case.get("semantic_fact_kinds", [])]))
    extractor = ModelAssistedExtractor(provider, provider_name="s4-scripted-provider")
    router = ShadowRouter(extractor, DeterministicPolicyComposer())
    legacy_before = copy.deepcopy(legacy)
    shadow = router.evaluate(
        request=request,
        project_context={"project_brief": str(case["project_brief"]), "s4_control": cid},
        canonical_assessment=legacy,
    )
    repeat = router.evaluate(
        request=request,
        project_context={"project_brief": str(case["project_brief"]), "s4_control": cid},
        canonical_assessment=legacy,
    )
    comparison = shadow["comparison"]
    facts = shadow["semantic_ir"].get("facts", [])
    provenance_ok = bool(facts or not case.get("semantic_fact_kinds")) and all(
        isinstance(f.get("provenance"), list) and bool(f.get("provenance")) for f in facts
    )
    passed = (
        legacy == legacy_before
        and shadow.get("canonical_output") == legacy_before
        and shadow.get("canonical_output_changed") is False
        and shadow.get("mode") == "SHADOW_ONLY"
        and shadow.get("metadata", {}).get("canonical_authority") == "v1.5"
        and shadow.get("metadata", {}).get("v2_policy_authority") is False
        and shadow.get("metadata", {}).get("live_provider_quality_validated") is False
        and comparison.get("classification") == case.get("expect_classification")
        and comparison.get("promotion_blocked") is False
        and provenance_ok
        and shadow.get("shadow_evidence_digest") == repeat.get("shadow_evidence_digest")
    )
    detail = {
        "legacy": legacy,
        "v2": shadow.get("semantic_policy"),
        "comparison": comparison,
        "canonical_unchanged": legacy == legacy_before,
        "provenance_recorded": provenance_ok,
        "deterministic_shadow_digest": shadow.get("shadow_evidence_digest") == repeat.get("shadow_evidence_digest"),
    }
    evidence = {"id": cid, **shadow}
    return result(cid, passed, detail), evidence


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", default=str(CONTROLS))
    parser.add_argument("--output")
    args = parser.parse_args()

    suite = json.loads(Path(args.controls).read_text(encoding="utf-8"))
    cases = suite.get("parallel_cases") if isinstance(suite, Mapping) else None
    if suite.get("schema") != "sef.eval.semantic-v2-s4-controls.v1" or not isinstance(cases, list) or not cases:
        raise SystemExit("invalid S4 controls")

    results: list[dict[str, Any]] = []
    shadow_evidence: list[dict[str, Any]] = []
    for case in cases:
        observed, evidence = run_parallel_case(case)
        results.append(observed)
        shadow_evidence.append(evidence)

    # Adversarial comparator controls.
    cmp_risk = compare_policies(
        {"risk": "R3", "packs": ["AUTHORIZATION"], "procedures": []},
        composed_policy(risk="R2", packs=["AUTHORIZATION"]),
    )
    results.append(result("S4-DOWNGRADE-RISK", cmp_risk["classification"] == "SAFETY_DOWNGRADE" and cmp_risk["promotion_blocked"] is True and cmp_risk["risk"]["downgrade"] is True, cmp_risk))

    cmp_pack = compare_policies(
        {"risk": "R3", "packs": ["AUTHORIZATION", "MULTI_TENANT"], "procedures": []},
        composed_policy(risk="R3", packs=["AUTHORIZATION"]),
    )
    results.append(result("S4-DOWNGRADE-PACK", cmp_pack["classification"] == "SAFETY_DOWNGRADE" and cmp_pack["packs"]["missing_from_v2"] == ["MULTI_TENANT"], cmp_pack))

    cmp_proc = compare_policies(
        {"risk": "R3", "packs": ["AUTHORIZATION"], "procedures": ["security-authentication-authorization"]},
        composed_policy(risk="R3", packs=["AUTHORIZATION"], procedures=[]),
    )
    results.append(result("S4-DOWNGRADE-PROCEDURE", cmp_proc["classification"] == "SAFETY_DOWNGRADE" and cmp_proc["procedures"]["missing_from_v2"] == ["security-authentication-authorization"], cmp_proc))

    cmp_impl = compare_policies(
        {"risk": "R3", "packs": ["REGULATED_DOMAIN"], "procedures": [], "implementation_allowed": False},
        composed_policy(risk="R3", packs=["REGULATED_DOMAIN"], implementation_allowed=True),
    )
    results.append(result("S4-DOWNGRADE-IMPLEMENTATION", cmp_impl["classification"] == "SAFETY_DOWNGRADE" and cmp_impl["implementation"]["downgrade"] is True, cmp_impl))

    cmp_stronger = compare_policies(
        {"risk": "R2", "packs": ["AUTH_PROTOCOL"], "procedures": []},
        composed_policy(risk="R3", packs=["AUTH_PROTOCOL", "EXTERNAL_SUPPLIER"]),
    )
    results.append(result("S4-V2-STRONGER", cmp_stronger["classification"] == "V2_STRONGER_OR_BROADER" and cmp_stronger["promotion_blocked"] is False, cmp_stronger))

    review_payload = {
        "complete": False,
        "facts": [],
        "uncertainties": [
            {
                "id": "s4-review",
                "relation_hint": "access_control_boundary",
                "material": False,
                "state": "AMBIGUOUS",
                "reason": "scope relationship is unclear",
                "provenance": provenance(),
            }
        ],
    }
    review_router = ShadowRouter(
        ModelAssistedExtractor(StaticProvider(review_payload), provider_name="s4-review-provider"),
        DeterministicPolicyComposer(),
    )
    review_shadow = review_router.evaluate(
        request="Change access rules for a business partition whose relation is unclear.",
        project_context={"s4": "review"},
        canonical_assessment={"risk": "R1", "packs": [], "procedures": [], "implementation_allowed": True},
    )
    review_cmp = review_shadow["comparison"]
    results.append(result("S4-SEMANTIC-REVIEW-BLOCK", review_cmp["classification"] == "SEMANTIC_REVIEW_BLOCK" and review_cmp["promotion_blocked"] is True and review_cmp["safety_downgrade"] is False, review_cmp))

    invalid_router = ShadowRouter(InvalidIRExtractor(), DeterministicPolicyComposer())
    invalid_shadow = invalid_router.evaluate(
        request="Invalid IR test",
        project_context={},
        canonical_assessment={"risk": "R1", "packs": [], "procedures": [], "implementation_allowed": True},
    )
    invalid_cmp = invalid_shadow["comparison"]
    results.append(result("S4-INVALID-IR-BLOCK", invalid_cmp["classification"] == "INVALID_V2_BLOCK" and invalid_cmp["promotion_blocked"] is True, invalid_cmp))

    clean_summary = summarize_shadow_results(shadow_evidence)
    results.append(result("S4-SUMMARY-CLEAN", clean_summary["promotion_eligible"] is True and clean_summary["promotion_blocked"] is False and not clean_summary["safety_downgrades"] and not clean_summary["semantic_blocks"], clean_summary))

    blocked_evidence = copy.deepcopy(shadow_evidence[:1])
    blocked_evidence.append({"id": "synthetic-downgrade", "comparison": cmp_pack})
    blocked_summary = summarize_shadow_results(blocked_evidence)
    results.append(result("S4-SUMMARY-BLOCKS-DOWNGRADE", blocked_summary["promotion_blocked"] is True and blocked_summary["safety_downgrades"] == ["synthetic-downgrade"], blocked_summary))

    counts = {
        "PASS": sum(item["status"] == "PASS" for item in results),
        "FAIL": sum(item["status"] == "FAIL" for item in results),
    }
    report = {
        "schema": "sef.eval.semantic-v2-s4-report.v1",
        "phase": "S4",
        "status": "PASS" if counts["FAIL"] == 0 else "FAIL",
        "counts": counts,
        "parallel_live_v15_cases": len(cases),
        "canonical_v15_authority_preserved": all(item["status"] == "PASS" for item in results[: len(cases)]),
        "semantic_v2_policy_authority": False,
        "live_provider_quality_validated": False,
        "safety_downgrade_gate_validated": counts["FAIL"] == 0,
        "shadow_evidence": shadow_evidence,
        "results": results,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
