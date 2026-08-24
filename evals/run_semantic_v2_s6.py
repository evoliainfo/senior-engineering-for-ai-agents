#!/usr/bin/env python3
"""S6 qualification for active Semantic Routing v2 promotion."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from semantic_v2.active_routing import ACTIVE_ROUTING_SCHEMA, ActiveSemanticRouter
from semantic_v2.model_extractor import ModelAssistedExtractor
from semantic_v2.policy_composer import DeterministicPolicyComposer

ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SOURCE = ROOT / "semantic_v2" / "active_routing.py"


def result(identifier: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"id": identifier, "status": "PASS" if passed else "FAIL", "detail": detail}


def provenance() -> list[dict[str, Any]]:
    return [{
        "source_kind": "request",
        "locator": "request",
        "confidence": 1.0,
        "ambiguity": "none",
    }]


class FixedProvider:
    def __init__(self, *, facts: list[str] | None = None, uncertainty: str | None = None) -> None:
        self.facts = list(facts or [])
        self.uncertainty = uncertainty

    def extract_semantics(
        self,
        request: str,
        project_context: Mapping[str, Any],
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        facts = [{
            "id": f"fact-{index:02d}",
            "kind": kind,
            "material": True,
            "subject": None,
            "object": None,
            "attributes": {"labels": [], "notes": ["S6 fixed semantic fact"]},
            "provenance": provenance(),
        } for index, kind in enumerate(self.facts, 1)]
        uncertainties = []
        if self.uncertainty:
            uncertainties.append({
                "id": "uncertain-01",
                "relation_hint": self.uncertainty,
                "material": True,
                "state": "AMBIGUOUS",
                "reason": "Material relation is not resolved by the supplied context.",
                "provenance": [{
                    "source_kind": "request",
                    "locator": "request",
                    "confidence": 0.0,
                    "ambiguity": "high",
                }],
            })
        return {"facts": facts, "uncertainties": uncertainties, "complete": not bool(uncertainties)}


class InvalidExtractor:
    def extract(self, request: str, project_context: Mapping[str, Any]) -> dict[str, Any]:
        return {"schema": "not-a-valid-semantic-ir", "facts": []}


def router_for(*, facts: list[str] | None = None, uncertainty: str | None = None) -> ActiveSemanticRouter:
    extractor = ModelAssistedExtractor(
        FixedProvider(facts=facts, uncertainty=uncertainty),
        provider_name="s6-fixed-provider",
    )
    return ActiveSemanticRouter(extractor, DeterministicPolicyComposer())


def evaluate(router: ActiveSemanticRouter, legacy: Mapping[str, Any]) -> dict[str, Any]:
    return router.evaluate(
        request="S6 qualification request",
        project_context={"evaluation": "S6", "development_only": True},
        deterministic_assessment=legacy,
    )


def main() -> int:
    controls: list[dict[str, Any]] = []

    low_legacy = {
        "risk": "R1",
        "packs": [],
        "procedures": [],
        "implementation_allowed": True,
        "implementation_gate": "READY",
    }
    auth = evaluate(router_for(facts=["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"]), low_legacy)
    controls.append(result(
        "S6-ACTIVE-MODE",
        auth.get("schema") == ACTIVE_ROUTING_SCHEMA
        and auth.get("mode") == "ACTIVE_V2_HYBRID"
        and auth.get("canonical_source") == "semantic-v2-with-v1.5-safety-floor"
        and auth.get("metadata", {}).get("semantic_policy_authority") is True
        and auth.get("metadata", {}).get("provider_policy_authority") is False,
        {"mode": auth.get("mode"), "metadata": auth.get("metadata")},
    ))
    controls.append(result(
        "S6-SEMANTIC-ESCALATION",
        auth["canonical_policy"]["risk"] == "R3"
        and set(auth["canonical_policy"]["packs"]) == {"AUTHORIZATION", "MULTI_TENANT"}
        and auth["canonical_policy"]["implementation_allowed"] is False,
        auth["canonical_policy"],
    ))

    high_legacy = {
        "risk": "R4",
        "packs": ["LEGACY_HIGH_IMPACT"],
        "procedures": ["legacy-authoritative-review"],
        "implementation_allowed": False,
        "implementation_gate": "BLOCKED_BY_LEGACY_CONTROL",
    }
    high_before = copy.deepcopy(high_legacy)
    floored = evaluate(router_for(), high_legacy)
    controls.append(result(
        "S6-LEGACY-RISK-FLOOR",
        floored["canonical_policy"]["risk"] == "R4"
        and "LEGACY_HIGH_IMPACT" in floored["canonical_policy"]["packs"]
        and "legacy-authoritative-review" in floored["canonical_policy"]["procedures"]
        and floored["canonical_policy"]["implementation_allowed"] is False
        and floored["canonical_policy"]["legacy_safety_floor_applied"] is True,
        floored["canonical_policy"],
    ))
    controls.append(result(
        "S6-LEGACY-IMMUTABLE",
        high_legacy == high_before and floored.get("deterministic_safety_floor_changed") is False,
        {"input_unchanged": high_legacy == high_before, "evidence_flag": floored.get("deterministic_safety_floor_changed")},
    ))

    trust = evaluate(router_for(facts=["SERVER_DESTINATION_TRUST"]), low_legacy)
    controls.append(result(
        "S6-SEMANTIC-POLICY-AUTHORITY",
        trust["canonical_policy"]["risk"] == "R3"
        and trust["canonical_policy"]["packs"] == ["WEBHOOK_TRUST"]
        and trust["canonical_policy"]["implementation_allowed"] is True,
        trust["canonical_policy"],
    ))

    ambiguous = evaluate(router_for(uncertainty="authorization boundary"), {
        "risk": "R2",
        "packs": ["LEGACY_BASE"],
        "procedures": [],
        "implementation_allowed": True,
    })
    controls.append(result(
        "S6-AMBIGUITY-FAIL-CLOSED",
        ambiguous["canonical_policy"]["status"] == "SEMANTIC_REVIEW_REQUIRED"
        and ambiguous["canonical_policy"]["risk"] is None
        and ambiguous["canonical_policy"]["minimum_known_risk"] == "R2"
        and ambiguous["canonical_policy"]["implementation_allowed"] is False
        and ambiguous["canonical_policy"]["implementation_gate"] == "BLOCKED_SEMANTIC_REVIEW",
        ambiguous["canonical_policy"],
    ))

    invalid = evaluate(ActiveSemanticRouter(InvalidExtractor(), DeterministicPolicyComposer()), low_legacy)
    controls.append(result(
        "S6-INVALID-IR-FAIL-CLOSED",
        invalid["canonical_policy"]["status"] == "INVALID_IR"
        and invalid["canonical_policy"]["risk"] is None
        and invalid["canonical_policy"]["implementation_allowed"] is False
        and invalid["canonical_policy"]["implementation_gate"] == "BLOCKED_INVALID_IR",
        invalid["canonical_policy"],
    ))

    resolved_low = evaluate(router_for(), low_legacy)
    controls.append(result(
        "S6-LOW-RISK-NEGATIVE-PRESERVED",
        resolved_low["canonical_policy"]["risk"] == "R1"
        and resolved_low["canonical_policy"]["packs"] == []
        and resolved_low["canonical_policy"]["implementation_allowed"] is True
        and resolved_low["canonical_policy"]["implementation_gate"] == "READY",
        resolved_low["canonical_policy"],
    ))

    repeated_a = evaluate(router_for(facts=["EXTERNAL_OPERATIONAL_DEPENDENCY"]), low_legacy)
    repeated_b = evaluate(router_for(facts=["EXTERNAL_OPERATIONAL_DEPENDENCY"]), copy.deepcopy(low_legacy))
    controls.append(result(
        "S6-DETERMINISTIC-ROUTING",
        repeated_a == repeated_b and repeated_a.get("routing_digest") == repeated_b.get("routing_digest"),
        {"digest_a": repeated_a.get("routing_digest"), "digest_b": repeated_b.get("routing_digest")},
    ))

    controls.append(result(
        "S6-NO-RELEASE-AUTHORITY",
        all(item["canonical_policy"]["release_eligible"] is False
            and item["canonical_policy"]["release_decision"] == "NOT_RELEASE_AUTHORITY"
            for item in [auth, floored, trust, ambiguous, invalid, resolved_low]),
        {"release_decisions": sorted({item["canonical_policy"]["release_decision"] for item in [auth, floored, trust, ambiguous, invalid, resolved_low]})},
    ))

    source = ACTIVE_SOURCE.read_text(encoding="utf-8").lower()
    forbidden_provider_coupling = [token for token in ["openai_responses_provider", "gpt-5.6", "department", "branch", "region", "division", "portfolio", "franchise"] if token in source]
    controls.append(result(
        "S6-NO-PROVIDER-OR-NOUN-COUPLING",
        not forbidden_provider_coupling,
        {"forbidden_tokens_found": forbidden_provider_coupling},
    ))

    controls.append(result(
        "S6-DIRECT-EVIDENCE-FIRST",
        auth.get("metadata", {}).get("actual_diff_policy") == "DETERMINISTIC_FIRST"
        and auth.get("metadata", {}).get("deterministic_safety_floor_authority") is True,
        auth.get("metadata"),
    ))

    counts = {"PASS": 0, "FAIL": 0}
    for control in controls:
        counts[control["status"]] += 1
    report = {
        "schema": "sef.eval.semantic-v2-s6-report.v1",
        "phase": "S6_PROMOTION",
        "status": "PASS" if counts["FAIL"] == 0 else "FAIL",
        "counts": counts,
        "control_count": len(controls),
        "active_routing_promoted": counts["FAIL"] == 0,
        "frozen_candidate_created": False,
        "canonical_v15_runtime_changed": False,
        "independent_holdout_claim": False,
        "results": controls,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    output = ROOT / "semantic-v2-s6-promotion.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
