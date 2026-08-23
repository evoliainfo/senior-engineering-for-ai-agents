#!/usr/bin/env python3
"""S4 shadow integration for Semantic Routing v2.

The frozen v1.5 assessment remains canonical. Semantic v2 executes beside it and
produces evidence only. This module never promotes v2 output into the canonical
result.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from .contracts import REVIEW_REQUIRED, Extractor, PolicyComposer, semantic_ir_digest
from .policy_composer import COMPOSITION_RULES, FACT_POLICY_RULES

SHADOW_SCHEMA = "sef.semantic-shadow.v1"
RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}
COMPARABLE_PROCEDURES = {
    str(procedure)
    for rule in [*FACT_POLICY_RULES.values(), *COMPOSITION_RULES]
    for procedure in rule.get("procedures", [])
}


def _canonical_digest(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _legacy_policy(assessment: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize the public v1.5 evaluation surface without inventing semantics.

    v1.5 may emit baseline procedures unrelated to the semantic rule families that
    S3 currently composes. Those remain in canonical evidence but are excluded from
    downgrade comparison until a v2 semantic rule owns them.
    """
    packs = assessment.get("packs")
    if not isinstance(packs, list):
        packs = assessment.get("required_packs")
    procedures = assessment.get("procedures")
    if not isinstance(procedures, list):
        procedures = assessment.get("required_procedures")
    governed_procedures = {
        str(v)
        for v in (procedures or [])
        if isinstance(v, str) and str(v) in COMPARABLE_PROCEDURES
    }
    return {
        "risk": assessment.get("risk") if assessment.get("risk") in RISK_ORDER else None,
        "packs": sorted({str(v) for v in (packs or []) if isinstance(v, str)}),
        "procedures": sorted(governed_procedures),
        "implementation_allowed": assessment.get("implementation_allowed")
        if isinstance(assessment.get("implementation_allowed"), bool)
        else None,
    }


def compare_policies(legacy: Mapping[str, Any], v2: Mapping[str, Any]) -> dict[str, Any]:
    """Classify shadow differences conservatively.

    Safety downgrade means v2 loses a known legacy obligation, lowers known risk,
    or permits implementation where legacy blocks it. Review/invalid states block
    promotion separately because no final v2 decision exists to compare.
    """
    legacy_norm = _legacy_policy(legacy)
    v2_status = str(v2.get("status") or "UNKNOWN")
    v2_risk = v2.get("risk") if v2.get("risk") in RISK_ORDER else None
    v2_packs = {str(v) for v in (v2.get("packs") or []) if isinstance(v, str)}
    v2_procedures = {str(v) for v in (v2.get("procedures") or []) if isinstance(v, str)}
    legacy_packs = set(legacy_norm["packs"])
    legacy_procedures = set(legacy_norm["procedures"])

    missing_packs = sorted(legacy_packs - v2_packs)
    added_packs = sorted(v2_packs - legacy_packs)
    missing_procedures = sorted(legacy_procedures - v2_procedures)
    added_procedures = sorted(v2_procedures - legacy_procedures)

    legacy_risk = legacy_norm["risk"]
    risk_downgrade = (
        legacy_risk in RISK_ORDER
        and v2_risk in RISK_ORDER
        and RISK_ORDER[str(v2_risk)] < RISK_ORDER[str(legacy_risk)]
    )
    risk_upgrade = (
        legacy_risk in RISK_ORDER
        and v2_risk in RISK_ORDER
        and RISK_ORDER[str(v2_risk)] > RISK_ORDER[str(legacy_risk)]
    )
    implementation_downgrade = (
        legacy_norm["implementation_allowed"] is False
        and v2.get("implementation_allowed") is True
    )
    implementation_upgrade = (
        legacy_norm["implementation_allowed"] is True
        and v2.get("implementation_allowed") is False
    )

    review_block = v2_status == REVIEW_REQUIRED
    invalid_block = v2_status == "INVALID_IR"
    unresolved_block = review_block or invalid_block or v2_risk is None
    safety_downgrade = bool(
        missing_packs or missing_procedures or risk_downgrade or implementation_downgrade
    )

    exact_agreement = (
        not unresolved_block
        and legacy_risk == v2_risk
        and not missing_packs
        and not added_packs
        and not missing_procedures
        and not added_procedures
        and (
            legacy_norm["implementation_allowed"] is None
            or legacy_norm["implementation_allowed"] == v2.get("implementation_allowed")
        )
    )

    if invalid_block:
        classification = "INVALID_V2_BLOCK"
    elif review_block or v2_risk is None:
        classification = "SEMANTIC_REVIEW_BLOCK"
    elif safety_downgrade:
        classification = "SAFETY_DOWNGRADE"
    elif exact_agreement:
        classification = "AGREEMENT"
    elif risk_upgrade or added_packs or added_procedures or implementation_upgrade:
        classification = "V2_STRONGER_OR_BROADER"
    else:
        classification = "NON_SAFETY_DIVERGENCE"

    promotion_blocked = safety_downgrade or unresolved_block
    return {
        "classification": classification,
        "promotion_blocked": promotion_blocked,
        "safety_downgrade": safety_downgrade,
        "unresolved_semantic_block": unresolved_block,
        "risk": {
            "legacy": legacy_risk,
            "v2": v2_risk,
            "downgrade": bool(risk_downgrade),
            "upgrade": bool(risk_upgrade),
        },
        "packs": {
            "missing_from_v2": missing_packs,
            "added_by_v2": added_packs,
        },
        "procedures": {
            "missing_from_v2": missing_procedures,
            "added_by_v2": added_procedures,
        },
        "implementation": {
            "legacy": legacy_norm["implementation_allowed"],
            "v2": v2.get("implementation_allowed"),
            "downgrade": implementation_downgrade,
            "upgrade": implementation_upgrade,
        },
    }


class ShadowRouter:
    """Execute semantic v2 beside a canonical v1.5 assessment."""

    def __init__(self, extractor: Extractor, composer: PolicyComposer) -> None:
        self.extractor = extractor
        self.composer = composer

    def evaluate(
        self,
        *,
        request: str,
        project_context: Mapping[str, Any],
        canonical_assessment: Mapping[str, Any],
    ) -> dict[str, Any]:
        canonical = copy.deepcopy(dict(canonical_assessment))
        canonical_before = _canonical_digest(canonical)

        semantic_ir = self.extractor.extract(request, project_context)
        semantic_policy = self.composer.compose(semantic_ir)
        comparison = compare_policies(canonical, semantic_policy)

        canonical_after = _canonical_digest(canonical)
        if canonical_before != canonical_after:
            raise RuntimeError("shadow integration mutated canonical v1.5 assessment")

        evidence = {
            "schema": SHADOW_SCHEMA,
            "mode": "SHADOW_ONLY",
            "canonical_source": "v1.5",
            "canonical_output": canonical,
            "canonical_output_digest": canonical_before,
            "canonical_output_changed": False,
            "semantic_ir": semantic_ir,
            "semantic_ir_digest": semantic_ir_digest(semantic_ir),
            "semantic_policy": semantic_policy,
            "comparison": comparison,
            "promotion_gate": {
                "eligible_for_promotion": not comparison["promotion_blocked"],
                "blocked": comparison["promotion_blocked"],
                "reason": comparison["classification"] if comparison["promotion_blocked"] else None,
            },
            "metadata": {
                "phase": "S4",
                "canonical_authority": "v1.5",
                "v2_policy_authority": False,
                "live_provider_quality_validated": False,
            },
        }
        evidence["shadow_evidence_digest"] = _canonical_digest(evidence)
        return evidence


def summarize_shadow_results(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    safety_downgrades: list[str] = []
    semantic_blocks: list[str] = []
    for index, item in enumerate(results):
        comparison = item.get("comparison") if isinstance(item.get("comparison"), Mapping) else {}
        classification = str(comparison.get("classification") or "UNKNOWN")
        counts[classification] = counts.get(classification, 0) + 1
        identifier = str(item.get("id") or f"item-{index + 1}")
        if comparison.get("safety_downgrade") is True:
            safety_downgrades.append(identifier)
        if comparison.get("unresolved_semantic_block") is True:
            semantic_blocks.append(identifier)
    promotion_blocked = bool(safety_downgrades or semantic_blocks)
    return {
        "total": len(results),
        "classifications": counts,
        "safety_downgrades": safety_downgrades,
        "semantic_blocks": semantic_blocks,
        "promotion_blocked": promotion_blocked,
        "promotion_eligible": bool(results) and not promotion_blocked,
    }
