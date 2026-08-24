#!/usr/bin/env python3
"""S5R qualification: run the unchanged S5 DEV contract through 3-sample stability.

This runner deliberately reuses S5 corpus integrity, exact fact-graph expectations,
negative ceilings and metamorphic controls. A stability conflict becomes
SEMANTIC_REVIEW_REQUIRED; it does not relax or reinterpret a resolved S5 case.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from evals.run_semantic_v2_s5 import (
    CORPUS_PATH,
    ReplayProvider,
    corpus_integrity,
    material_fact_kinds,
    metamorphic_controls,
    normalized_semantic_view,
    policy_view,
    result,
)
from semantic_v2.contracts import REVIEW_RESOLVED, validate_semantic_ir
from semantic_v2.model_extractor import ModelAssistedExtractor
from semantic_v2.openai_responses_provider import OpenAIResponsesSemanticProvider
from semantic_v2.policy_composer import DeterministicPolicyComposer
from semantic_v2.stabilized_extractor import STABILITY_SAMPLE_COUNT, StabilizedExtractor

ROOT = Path(__file__).resolve().parents[1]


def _evaluate_case(
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
        "evaluation": "S5R",
        "case_id": cid,
        "development_only": True,
    }

    raw_providers: list[Any] = []
    extractors: list[ModelAssistedExtractor] = []
    for index in range(STABILITY_SAMPLE_COUNT):
        if provider_mode == "replay":
            provider: Any = ReplayProvider(case)
            provider_name = f"s5r-replay-provider-{index + 1}"
        elif provider_mode == "openai":
            provider = OpenAIResponsesSemanticProvider(
                model=model,
                reasoning_effort=reasoning_effort,
                api_base=api_base,
            )
            provider_name = f"openai-responses:{model}:sample-{index + 1}"
        else:
            raise ValueError(f"unsupported provider mode: {provider_mode}")
        raw_providers.append(provider)
        extractors.append(ModelAssistedExtractor(provider, provider_name=provider_name))

    stabilizer = StabilizedExtractor(extractors)
    ir = stabilizer.extract(str(case["request"]), context)
    policy = DeterministicPolicyComposer().compose(ir)

    expected = case.get("expect") if isinstance(case.get("expect"), Mapping) else {}
    observed_facts = material_fact_kinds(ir)
    required_facts = {str(value) for value in expected.get("required_fact_kinds", [])}
    forbidden_facts = {str(value) for value in expected.get("forbidden_fact_kinds", [])}
    required_packs = {str(value) for value in expected.get("required_packs", [])}
    observed_packs = {str(value) for value in policy.get("packs", [])}
    exact_facts = (
        observed_facts == required_facts
        if expected.get("review_state") == REVIEW_RESOLVED
        else required_facts.issubset(observed_facts)
    )
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
        "policy_composer_deterministic": policy == DeterministicPolicyComposer().compose(ir),
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
            "uncertainty_states": [
                uncertainty.get("state")
                for uncertainty in ir.get("uncertainties", []) or []
                if isinstance(uncertainty, Mapping)
            ],
            "policy": policy_view(policy),
            "stability_sample_views": list(stabilizer.last_sample_views),
        },
    }

    live_meta: dict[str, Any] | None = None
    if provider_mode == "openai":
        samples = []
        for index, provider in enumerate(raw_providers, 1):
            samples.append({
                "sample": index,
                "response_id": provider.last_response_id,
                "model_observed": provider.last_model,
                "usage": dict(provider.last_usage or {}),
            })
        live_meta = {"case_id": cid, "samples": samples}
    return result(cid, passed, detail), normalized_semantic_view(ir, policy), live_meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default=str(CORPUS_PATH))
    parser.add_argument("--provider", choices=["replay", "openai", "not-run"], default="replay")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-5.6"))
    parser.add_argument("--reasoning-effort", default=os.environ.get("OPENAI_REASONING_EFFORT", "medium"))
    parser.add_argument("--api-base", default=os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"))
    parser.add_argument("--output")
    args = parser.parse_args()

    corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
    if not isinstance(corpus, Mapping):
        raise SystemExit("S5 corpus must be a JSON object")

    if args.provider == "not-run":
        report = {
            "schema": "sef.eval.semantic-v2-s5-stability-report.v1",
            "phase": "S5R",
            "provider_mode": "NOT_RUN",
            "status": "NOT_RUN",
            "reason": "No live provider credential was available to this workflow run.",
            "stability_sample_count": STABILITY_SAMPLE_COUNT,
            "s5_acceptance_contract_changed": False,
            "semantic_dev_corpus_validated": False,
            "live_provider_quality_validated": False,
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
        observed, normalized, live_meta = _evaluate_case(
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
    status = "PASS" if counts["FAIL"] == 0 else "FAIL"

    observed_models = sorted({
        str(sample.get("model_observed"))
        for case_meta in live_metadata
        for sample in case_meta.get("samples", [])
        if sample.get("model_observed")
    })
    total_tokens = sum(
        int((sample.get("usage") or {}).get("total_tokens") or 0)
        for case_meta in live_metadata
        for sample in case_meta.get("samples", [])
    )
    response_count = sum(len(case_meta.get("samples", [])) for case_meta in live_metadata)

    report = {
        "schema": "sef.eval.semantic-v2-s5-stability-report.v1",
        "phase": "S5R",
        "provider_mode": args.provider,
        "status": status,
        "counts": counts,
        "case_count": len(corpus.get("cases", [])),
        "stability_sample_count": STABILITY_SAMPLE_COUNT,
        "s5_acceptance_contract_changed": False,
        "s5_corpus_changed": False,
        "policy_rules_changed": False,
        "semantic_dev_corpus_validated": status == "PASS",
        "live_provider_quality_validated": args.provider == "openai" and status == "PASS",
        "live_provider": {
            "requested_model": args.model if args.provider == "openai" else None,
            "observed_models": observed_models,
            "reasoning_effort": args.reasoning_effort if args.provider == "openai" else None,
            "case_count": len(live_metadata),
            "response_count": response_count,
            "expected_response_count": len(corpus.get("cases", [])) * STABILITY_SAMPLE_COUNT if args.provider == "openai" else 0,
            "total_tokens": total_tokens,
        },
        "canonical_v15_routing_changed": False,
        "independent_holdout_claim": False,
        "live_metadata": live_metadata,
        "results": results,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
