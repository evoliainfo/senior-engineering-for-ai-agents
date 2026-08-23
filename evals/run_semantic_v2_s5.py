#!/usr/bin/env python3
"""S5 relation-focused Semantic DEV qualification.

Replay mode validates the corpus, provider boundary and deterministic policy path.
OpenAI mode executes the same DEV corpus against a real model through the
provider-neutral semantic boundary. Replay evidence must never be presented as
live-provider evidence.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from semantic_v2.contracts import REVIEW_REQUIRED, REVIEW_RESOLVED, validate_semantic_ir
from semantic_v2.model_extractor import ModelAssistedExtractor
from semantic_v2.openai_responses_provider import OpenAIResponsesSemanticProvider
from semantic_v2.policy_composer import DeterministicPolicyComposer

ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "evals" / "semantic_v2" / "s5_corpus.json"
OPENAI_PROVIDER_SOURCE = ROOT / "semantic_v2" / "openai_responses_provider.py"
V3_CONSUMED_SOURCE_DIGEST = "f47cf769e78c97e9898a4a4a38cc726d435374069903ae74ce36936490e62743"
EXPECTED_CASE_COUNT = 35
EXPECTED_METAMORPHIC_GROUPS = {
    "AUTH-PARTITION": 8,
    "AUTH-NEGATIVE": 3,
    "TRUST-DESTINATION": 4,
    "TRUST-NEGATIVE": 2,
    "REG-DECISION": 3,
    "REG-ARITHMETIC-NEGATIVE": 3,
    "DATA-LIVE": 2,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def result(control_id: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"id": control_id, "status": "PASS" if passed else "FAIL", "detail": detail}


def provenance(locator: str = "request") -> list[dict[str, Any]]:
    return [{
        "source_kind": "request",
        "locator": locator,
        "confidence": 1.0,
        "ambiguity": "none",
    }]


class ReplayProvider:
    """Deterministic DEV fixture provider. It is never live-model evidence."""

    def __init__(self, case: Mapping[str, Any]) -> None:
        self.case = copy.deepcopy(dict(case))

    def extract_semantics(
        self,
        request: str,
        project_context: Mapping[str, Any],
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        facts = []
        for index, kind in enumerate(self.case.get("replay_fact_kinds", []), 1):
            facts.append({
                "id": f"replay-{index:02d}",
                "kind": str(kind),
                "material": True,
                "subject": None,
                "object": None,
                "attributes": {
                    "labels": [],
                    "notes": [f"S5 replay fixture {self.case.get('id')}"]
                },
                "provenance": provenance(),
            })
        uncertainty_spec = self.case.get("replay_uncertainty")
        uncertainties = []
        if isinstance(uncertainty_spec, Mapping):
            uncertainties.append({
                "id": "replay-uncertainty",
                "relation_hint": str(uncertainty_spec.get("relation_hint")),
                "material": True,
                "state": str(uncertainty_spec.get("state")),
                "reason": str(uncertainty_spec.get("reason")),
                "provenance": [{
                    "source_kind": "request",
                    "locator": "request",
                    "confidence": 0.0,
                    "ambiguity": "high",
                }],
            })
        return {
            "complete": not bool(uncertainties),
            "facts": facts,
            "uncertainties": uncertainties,
        }


def material_fact_kinds(ir: Mapping[str, Any]) -> set[str]:
    return {
        str(fact.get("kind"))
        for fact in ir.get("facts", []) or []
        if isinstance(fact, Mapping) and fact.get("material") is True
    }


def policy_view(policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": policy.get("status"),
        "risk": policy.get("risk"),
        "packs": list(policy.get("packs") or []),
        "procedures": list(policy.get("procedures") or []),
        "implementation_allowed": policy.get("implementation_allowed"),
        "implementation_gate": policy.get("implementation_gate"),
    }


def normalized_semantic_view(ir: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "review_state": ir.get("review_state"),
        "material_fact_kinds": sorted(material_fact_kinds(ir)),
        "risk": policy.get("risk"),
        "packs": sorted(policy.get("packs") or []),
        "implementation_allowed": policy.get("implementation_allowed"),
        "implementation_gate": policy.get("implementation_gate"),
    }


def corpus_integrity(corpus: Mapping[str, Any]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    cases = corpus.get("cases")
    ids = [str(case.get("id")) for case in cases or [] if isinstance(case, Mapping)]
    controls.append(result(
        "S5-CORPUS-SHAPE",
        corpus.get("schema") == "sef.eval.semantic-v2-s5-corpus.v1"
        and corpus.get("development_only") is True
        and corpus.get("independent_holdout") is False
        and isinstance(cases, list)
        and len(cases) == EXPECTED_CASE_COUNT
        and len(ids) == len(set(ids)),
        {"case_count": len(cases or []), "unique_ids": len(set(ids))},
    ))

    consumed = [case for case in cases or [] if isinstance(case, Mapping) and case.get("consumed_regression")]
    consumed_ok = (
        len(consumed) == 1
        and consumed[0].get("consumed_regression") == "V3-AUTH-002"
        and consumed[0].get("source_digest") == V3_CONSUMED_SOURCE_DIGEST
        and corpus.get("consumed_regressions") == ["V3-AUTH-002"]
    )
    controls.append(result(
        "S5-CONSUMED-HOLDOUT-LABEL",
        consumed_ok,
        {"consumed_cases": [case.get("id") for case in consumed], "source_digest": consumed[0].get("source_digest") if consumed else None},
    ))

    group_counts = Counter(
        str(case.get("metamorphic_group"))
        for case in cases or []
        if isinstance(case, Mapping) and case.get("metamorphic_group")
    )
    controls.append(result(
        "S5-METAMORPHIC-COVERAGE",
        all(group_counts.get(group) == count for group, count in EXPECTED_METAMORPHIC_GROUPS.items()),
        {"observed": dict(sorted(group_counts.items())), "expected": EXPECTED_METAMORPHIC_GROUPS},
    ))

    negative_count = sum(
        1 for case in cases or []
        if isinstance(case, Mapping) and case.get("expect", {}).get("max_material_facts") == 0
    )
    ambiguity_count = sum(
        1 for case in cases or []
        if isinstance(case, Mapping) and case.get("expect", {}).get("review_state") == REVIEW_REQUIRED
    )
    critical_count = sum(
        1 for case in cases or [] if isinstance(case, Mapping) and case.get("severity") == "critical"
    )
    controls.append(result(
        "S5-COVERAGE-FLOORS",
        negative_count >= 9 and ambiguity_count >= 3 and critical_count >= 18,
        {"negative_zero_fact_cases": negative_count, "ambiguity_cases": ambiguity_count, "critical_cases": critical_count},
    ))

    source = OPENAI_PROVIDER_SOURCE.read_text(encoding="utf-8").lower()
    corpus_only_labels = ["portfolio", "pod", "franchise", "desk"]
    hardcoded = [label for label in corpus_only_labels if label in source]
    controls.append(result(
        "S5-NO-CORPUS-NOUN-WHITELIST",
        not hardcoded,
        {"corpus_only_labels_found_in_provider_source": hardcoded},
    ))
    return controls


def evaluate_case(
    case: Mapping[str, Any],
    *,
    provider_mode: str,
    model: str,
    reasoning_effort: str,
    api_base: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    cid = str(case["id"])
    context = {
        "project_brief": str(case.get("project_brief", "")),
        "evaluation": "S5",
        "case_id": cid,
        "development_only": True,
    }
    if provider_mode == "replay":
        raw_provider: Any = ReplayProvider(case)
        provider_name = "s5-replay-provider"
    elif provider_mode == "openai":
        raw_provider = OpenAIResponsesSemanticProvider(
            model=model,
            reasoning_effort=reasoning_effort,
            api_base=api_base,
        )
        provider_name = f"openai-responses:{model}"
    else:
        raise ValueError(f"unsupported provider mode: {provider_mode}")

    extractor = ModelAssistedExtractor(raw_provider, provider_name=provider_name)
    ir = extractor.extract(str(case["request"]), context)
    policy = DeterministicPolicyComposer().compose(ir)
    expected = case.get("expect") if isinstance(case.get("expect"), Mapping) else {}
    observed_facts = material_fact_kinds(ir)
    required_facts = {str(v) for v in expected.get("required_fact_kinds", [])}
    forbidden_facts = {str(v) for v in expected.get("forbidden_fact_kinds", [])}
    required_packs = {str(v) for v in expected.get("required_packs", [])}
    observed_packs = {str(v) for v in policy.get("packs", [])}
    exact_facts = observed_facts == required_facts if expected.get("review_state") == REVIEW_RESOLVED else required_facts.issubset(observed_facts)
    max_material = expected.get("max_material_facts")

    checks = {
        "valid_ir": validate_semantic_ir(ir) == [],
        "review_state": ir.get("review_state") == expected.get("review_state"),
        "required_facts": required_facts.issubset(observed_facts),
        "forbidden_facts": not bool(forbidden_facts & observed_facts),
        "exact_resolved_fact_graph": exact_facts,
        "material_fact_ceiling": max_material is None or len(observed_facts) <= int(max_material),
        "risk": policy.get("risk") == expected.get("risk"),
        "required_packs": required_packs.issubset(observed_packs),
        "implementation_allowed": policy.get("implementation_allowed") is expected.get("implementation_allowed"),
        "policy_composer_deterministic": policy == DeterministicPolicyComposer().compose(copy.deepcopy(ir)),
    }
    passed = all(checks.values())
    detail = {
        "family": case.get("family"),
        "severity": case.get("severity"),
        "consumed_regression": case.get("consumed_regression"),
        "metamorphic_group": case.get("metamorphic_group"),
        "checks": checks,
        "expected": expected,
        "observed": {
            "review_state": ir.get("review_state"),
            "material_fact_kinds": sorted(observed_facts),
            "uncertainty_states": [u.get("state") for u in ir.get("uncertainties", []) or [] if isinstance(u, Mapping)],
            "policy": policy_view(policy),
        },
    }
    live_meta: dict[str, Any] | None = None
    if provider_mode == "openai":
        live_meta = {
            "case_id": cid,
            "response_id": raw_provider.last_response_id,
            "model_observed": raw_provider.last_model,
            "usage": dict(raw_provider.last_usage or {}),
        }
    return result(cid, passed, detail), normalized_semantic_view(ir, policy), live_meta


def metamorphic_controls(group_views: Mapping[str, list[tuple[str, dict[str, Any]]]]) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    for group, expected_count in EXPECTED_METAMORPHIC_GROUPS.items():
        entries = group_views.get(group, [])
        canonical = {canonical_json(view) for _, view in entries}
        passed = len(entries) == expected_count and len(canonical) == 1
        controls.append(result(
            f"S5-META-{group}",
            passed,
            {"count": len(entries), "expected_count": expected_count, "views": {cid: view for cid, view in entries}},
        ))
    return controls


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=str(CORPUS_PATH))
    parser.add_argument("--provider", choices=["replay", "openai", "not-run"], default="replay")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-5.6-sol"))
    parser.add_argument("--reasoning-effort", default=os.environ.get("OPENAI_REASONING_EFFORT", "medium"))
    parser.add_argument("--api-base", default=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"))
    parser.add_argument("--output")
    args = parser.parse_args()

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    if not isinstance(corpus, Mapping):
        raise SystemExit("S5 corpus must be a JSON object")

    if args.provider == "not-run":
        report = {
            "schema": "sef.eval.semantic-v2-s5-report.v1",
            "phase": "S5",
            "provider_mode": "NOT_RUN",
            "status": "NOT_RUN",
            "reason": "No live provider credential was available to this workflow run.",
            "semantic_dev_corpus_validated": False,
            "live_provider_quality_validated": False,
            "canonical_v15_routing_changed": False,
            "independent_holdout_claim": False,
            "results": [],
        }
        text = json.dumps(report, indent=2, sort_keys=True) + "\n"
        print(text, end="")
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        return 0

    results = corpus_integrity(corpus)
    group_views: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    live_metadata: list[dict[str, Any]] = []
    for case in corpus.get("cases", []):
        observed, normalized, live_meta = evaluate_case(
            case,
            provider_mode=args.provider,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            api_base=args.api_base,
        )
        results.append(observed)
        if case.get("metamorphic_group"):
            group_views[str(case["metamorphic_group"])].append((str(case["id"]), normalized))
        if live_meta is not None:
            live_metadata.append(live_meta)

    results.extend(metamorphic_controls(group_views))
    counts = {
        "PASS": sum(item["status"] == "PASS" for item in results),
        "FAIL": sum(item["status"] == "FAIL" for item in results),
    }
    all_cases_pass = all(
        item["status"] == "PASS"
        for item in results
        if str(item["id"]).startswith("S5-") and not str(item["id"]).startswith("S5-META-")
    )
    status = "PASS" if counts["FAIL"] == 0 else "FAIL"
    observed_models = sorted({str(item.get("model_observed")) for item in live_metadata if item.get("model_observed")})
    total_tokens = 0
    for item in live_metadata:
        usage = item.get("usage") if isinstance(item.get("usage"), Mapping) else {}
        value = usage.get("total_tokens")
        if isinstance(value, int):
            total_tokens += value

    report = {
        "schema": "sef.eval.semantic-v2-s5-report.v1",
        "phase": "S5",
        "provider_mode": args.provider,
        "status": status,
        "counts": counts,
        "case_count": len(corpus.get("cases", [])),
        "semantic_dev_corpus_validated": status == "PASS",
        "live_provider_quality_validated": args.provider == "openai" and status == "PASS",
        "live_provider": {
            "requested_model": args.model if args.provider == "openai" else None,
            "observed_models": observed_models,
            "reasoning_effort": args.reasoning_effort if args.provider == "openai" else None,
            "response_count": len(live_metadata),
            "total_tokens": total_tokens,
        },
        "all_case_expectations_pass": all_cases_pass,
        "canonical_v15_routing_changed": False,
        "independent_holdout_claim": False,
        "consumed_holdouts_used_as_regression_only": True,
        "results": results,
        "live_metadata": live_metadata,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
