#!/usr/bin/env python3
"""S6 active routing for Semantic Routing v2.

Semantic v2 becomes the canonical semantic-policy channel while the frozen v1.5
assessment remains a monotonic deterministic safety floor. The model-assisted
extractor still has no authority to choose packs, risk, implementation approval,
or release approval: only the deterministic composer can translate validated
Semantic IR into governance.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from .contracts import Extractor, PolicyComposer, REVIEW_REQUIRED, semantic_ir_digest

ACTIVE_ROUTING_SCHEMA = "sef.semantic-routing.v2"
RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3, "R4": 4}


def _canonical_digest(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _legacy_view(assessment: Mapping[str, Any]) -> dict[str, Any]:
    packs = assessment.get("packs")
    if not isinstance(packs, list):
        packs = assessment.get("required_packs")
    procedures = assessment.get("procedures")
    if not isinstance(procedures, list):
        procedures = assessment.get("required_procedures")
    return {
        "risk": assessment.get("risk") if assessment.get("risk") in RISK_ORDER else None,
        "packs": sorted({str(v) for v in (packs or []) if isinstance(v, str)}),
        "procedures": sorted({str(v) for v in (procedures or []) if isinstance(v, str)}),
        "implementation_allowed": assessment.get("implementation_allowed")
        if isinstance(assessment.get("implementation_allowed"), bool)
        else None,
        "implementation_gate": assessment.get("implementation_gate")
        if isinstance(assessment.get("implementation_gate"), str)
        else None,
    }


def _max_known_risk(left: str | None, right: str | None) -> str | None:
    known = [value for value in (left, right) if value in RISK_ORDER]
    if not known:
        return None
    return max(known, key=lambda value: RISK_ORDER[value])


def _merge_resolved_policy(
    legacy: Mapping[str, Any],
    semantic_policy: Mapping[str, Any],
) -> dict[str, Any]:
    legacy_norm = _legacy_view(legacy)
    semantic_risk = semantic_policy.get("risk") if semantic_policy.get("risk") in RISK_ORDER else None
    risk = _max_known_risk(legacy_norm["risk"], semantic_risk)
    packs = sorted(set(legacy_norm["packs"]) | {
        str(v) for v in (semantic_policy.get("packs") or []) if isinstance(v, str)
    })
    procedures = sorted(set(legacy_norm["procedures"]) | {
        str(v) for v in (semantic_policy.get("procedures") or []) if isinstance(v, str)
    })

    legacy_blocks = legacy_norm["implementation_allowed"] is False
    semantic_blocks = semantic_policy.get("implementation_allowed") is False
    implementation_allowed = not (legacy_blocks or semantic_blocks)
    if semantic_blocks:
        gate = str(semantic_policy.get("implementation_gate") or "BLOCKED_BY_SEMANTIC_POLICY")
    elif legacy_blocks:
        gate = str(legacy_norm["implementation_gate"] or "BLOCKED_BY_LEGACY_SAFETY_FLOOR")
    else:
        gate = "READY"

    return {
        "status": "ACTIVE",
        "risk": risk,
        "minimum_known_risk": risk,
        "packs": packs,
        "procedures": procedures,
        "implementation_allowed": implementation_allowed,
        "implementation_gate": gate,
        "release_decision": "NOT_RELEASE_AUTHORITY",
        "release_eligible": False,
        "legacy_safety_floor_applied": bool(
            legacy_norm["risk"] in RISK_ORDER
            and (semantic_risk not in RISK_ORDER or RISK_ORDER[legacy_norm["risk"]] > RISK_ORDER[semantic_risk])
            or set(legacy_norm["packs"]) - set(semantic_policy.get("packs") or [])
            or set(legacy_norm["procedures"]) - set(semantic_policy.get("procedures") or [])
            or legacy_blocks
        ),
    }


def _merge_blocked_policy(
    legacy: Mapping[str, Any],
    semantic_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Fail closed without presenting a low numeric risk for unresolved semantics."""
    legacy_norm = _legacy_view(legacy)
    semantic_packs = {str(v) for v in (semantic_policy.get("packs") or []) if isinstance(v, str)}
    semantic_procedures = {
        str(v) for v in (semantic_policy.get("procedures") or []) if isinstance(v, str)
    }
    status = str(semantic_policy.get("status") or "SEMANTIC_REVIEW_REQUIRED")
    if status == "INVALID_IR":
        gate = "BLOCKED_INVALID_IR"
    else:
        status = REVIEW_REQUIRED
        gate = "BLOCKED_SEMANTIC_REVIEW"
    return {
        "status": status,
        "risk": None,
        "minimum_known_risk": legacy_norm["risk"],
        "packs": sorted(set(legacy_norm["packs"]) | semantic_packs),
        "procedures": sorted(set(legacy_norm["procedures"]) | semantic_procedures),
        "implementation_allowed": False,
        "implementation_gate": gate,
        "release_decision": "NOT_RELEASE_AUTHORITY",
        "release_eligible": False,
        "legacy_safety_floor_applied": bool(
            legacy_norm["risk"] or legacy_norm["packs"] or legacy_norm["procedures"]
        ),
    }


class ActiveSemanticRouter:
    """Canonical Semantic Routing v2 integration with a v1.5 safety floor."""

    def __init__(self, extractor: Extractor, composer: PolicyComposer) -> None:
        self.extractor = extractor
        self.composer = composer

    def evaluate(
        self,
        *,
        request: str,
        project_context: Mapping[str, Any],
        deterministic_assessment: Mapping[str, Any],
    ) -> dict[str, Any]:
        legacy = copy.deepcopy(dict(deterministic_assessment))
        legacy_before = _canonical_digest(legacy)

        semantic_ir = self.extractor.extract(request, project_context)
        semantic_policy = self.composer.compose(semantic_ir)
        semantic_status = str(semantic_policy.get("status") or "UNKNOWN")
        blocked = semantic_status in {REVIEW_REQUIRED, "INVALID_IR"} or semantic_policy.get("risk") is None
        canonical_policy = (
            _merge_blocked_policy(legacy, semantic_policy)
            if blocked
            else _merge_resolved_policy(legacy, semantic_policy)
        )

        legacy_after = _canonical_digest(legacy)
        if legacy_before != legacy_after:
            raise RuntimeError("active semantic routing mutated frozen deterministic assessment")

        evidence = {
            "schema": ACTIVE_ROUTING_SCHEMA,
            "mode": "ACTIVE_V2_HYBRID",
            "canonical_source": "semantic-v2-with-v1.5-safety-floor",
            "canonical_policy": canonical_policy,
            "semantic_ir": semantic_ir,
            "semantic_ir_digest": semantic_ir_digest(semantic_ir),
            "semantic_policy": semantic_policy,
            "deterministic_safety_floor": legacy,
            "deterministic_safety_floor_digest": legacy_before,
            "deterministic_safety_floor_changed": False,
            "metadata": {
                "phase": "S6",
                "semantic_policy_authority": True,
                "provider_policy_authority": False,
                "deterministic_safety_floor_authority": True,
                "release_authority": False,
                "actual_diff_policy": "DETERMINISTIC_FIRST",
            },
        }
        evidence["routing_digest"] = _canonical_digest(evidence)
        return evidence
