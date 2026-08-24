#!/usr/bin/env python3
"""Bounded stability boundary for stochastic Semantic Routing v2 extraction.

The model-assisted extractor is intentionally allowed to be stochastic. This
module prevents one stochastic sample from becoming a silently different policy
routing decision. Three independent validated Semantic IR samples are reduced to
one policy-relevant view:

- if all three agree on review state and material fact kinds, the common material
  relations are emitted as a canonical Semantic IR;
- if any material view disagrees, the output contains a material CONFLICT and
  requires semantic review;
- unavailable or invalid samples fail closed;
- policy authority remains exclusively in the deterministic composer.

The comparison deliberately ignores provider wording, IDs, provenance ordering and
non-material notes because those fields do not drive the S3 policy composer.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from .contracts import (
    Extractor,
    REVIEW_REQUIRED,
    REVIEW_RESOLVED,
    SEMANTIC_IR_SCHEMA,
    validate_semantic_ir,
)

STABILITY_SAMPLE_COUNT = 3
STABILITY_STRATEGY = "UNANIMOUS_MATERIAL_POLICY_VIEW_V1"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _context_digest(project_context: Mapping[str, Any]) -> str:
    return _digest_text(_canonical_json(dict(project_context)))


def _material_fact_kinds(ir: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted({
        str(fact.get("kind"))
        for fact in ir.get("facts", []) or []
        if isinstance(fact, Mapping) and fact.get("material") is True
    }))


def _uncertainty_states(ir: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(sorted({
        str(item.get("state"))
        for item in ir.get("uncertainties", []) or []
        if isinstance(item, Mapping) and item.get("material") is True
    }))


def _view(ir: Mapping[str, Any]) -> dict[str, Any]:
    errors = validate_semantic_ir(ir)
    if errors:
        return {
            "valid": False,
            "review_state": "INVALID",
            "material_fact_kinds": [],
            "uncertainty_states": ["INVALID"],
        }
    return {
        "valid": True,
        "review_state": str(ir.get("review_state")),
        "material_fact_kinds": list(_material_fact_kinds(ir)),
        "uncertainty_states": list(_uncertainty_states(ir)),
    }


def _policy_relevant_view(view: Mapping[str, Any]) -> str:
    """Canonical comparison key for the fields that can alter S3 governance."""
    return _canonical_json({
        "valid": bool(view.get("valid")),
        "review_state": view.get("review_state"),
        "material_fact_kinds": list(view.get("material_fact_kinds") or []),
    })


def _provenance(*, confidence: float, ambiguity: str) -> list[dict[str, Any]]:
    return [{
        "source_kind": "request",
        "locator": "stability-consensus",
        "extractor": "semantic-v2-stabilized-extractor",
        "confidence": confidence,
        "ambiguity": ambiguity,
    }]


def _canonical_fact(kind: str, sample_count: int) -> dict[str, Any]:
    return {
        "id": f"stabilized-{kind.lower().replace('_', '-')}",
        "kind": kind,
        "material": True,
        "subject": None,
        "object": None,
        "attributes": {
            "labels": [],
            "notes": [f"unanimous material semantic relation across {sample_count} samples"],
        },
        "provenance": _provenance(confidence=1.0, ambiguity="none"),
    }


def _uncertainty_state(
    views: Sequence[Mapping[str, Any]],
    *,
    unanimous: bool,
    sample_exception: bool,
) -> str | None:
    states = {
        str(state)
        for view in views
        for state in (view.get("uncertainty_states") or [])
    }
    if sample_exception or "UNAVAILABLE" in states:
        return "UNAVAILABLE"
    if "INVALID" in states or any(view.get("valid") is not True for view in views):
        return "INVALID"
    if not unanimous:
        return "CONFLICT"
    if all(view.get("review_state") == REVIEW_RESOLVED for view in views):
        return None
    if "CONFLICT" in states:
        return "CONFLICT"
    return "AMBIGUOUS"


class StabilizedExtractor:
    """Require unanimous policy-relevant semantics across exactly three samples."""

    name = "semantic-v2-stabilized-extractor"
    version = "1"

    def __init__(self, extractors: Sequence[Extractor]) -> None:
        if len(extractors) != STABILITY_SAMPLE_COUNT:
            raise ValueError(
                f"stability boundary requires exactly {STABILITY_SAMPLE_COUNT} independent extractors"
            )
        self.extractors = tuple(extractors)
        self.last_sample_irs: list[dict[str, Any] | None] = []
        self.last_sample_views: list[dict[str, Any]] = []

    def extract(self, request: str, project_context: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, str) or not request.strip():
            raise ValueError("request must be a non-empty string")
        if not isinstance(project_context, Mapping):
            raise ValueError("project_context must be an object")

        sample_irs: list[dict[str, Any] | None] = []
        views: list[dict[str, Any]] = []
        sample_exception = False
        for extractor in self.extractors:
            try:
                candidate = extractor.extract(request, project_context)
            except Exception:
                candidate = None
                sample_exception = True
            if not isinstance(candidate, Mapping):
                sample_irs.append(None)
                views.append({
                    "valid": False,
                    "review_state": "INVALID",
                    "material_fact_kinds": [],
                    "uncertainty_states": ["UNAVAILABLE" if sample_exception else "INVALID"],
                })
                continue
            copied = dict(candidate)
            sample_irs.append(copied)
            views.append(_view(copied))

        self.last_sample_irs = sample_irs
        self.last_sample_views = views

        policy_keys = {_policy_relevant_view(view) for view in views}
        unanimous = len(policy_keys) == 1
        state = _uncertainty_state(
            views,
            unanimous=unanimous,
            sample_exception=sample_exception,
        )

        material_sets = [set(view.get("material_fact_kinds") or []) for view in views]
        common_kinds = set.intersection(*material_sets) if material_sets else set()
        facts = [_canonical_fact(kind, STABILITY_SAMPLE_COUNT) for kind in sorted(common_kinds)]

        uncertainties: list[dict[str, Any]] = []
        if state is not None:
            reason = {
                "UNAVAILABLE": "at least one independent semantic extraction sample was unavailable",
                "INVALID": "at least one independent semantic extraction sample was invalid",
                "CONFLICT": "independent semantic extraction samples disagree on policy-relevant material semantics",
                "AMBIGUOUS": "independent semantic extraction samples unanimously require semantic review",
            }[state]
            uncertainties.append({
                "id": "stability-review-required",
                "relation_hint": "semantic_extraction_stability",
                "material": True,
                "state": state,
                "reason": reason,
                "provenance": _provenance(confidence=0.0, ambiguity="high"),
            })

        normalized_views = sorted(
            (
                {
                    "valid": bool(view.get("valid")),
                    "review_state": view.get("review_state"),
                    "material_fact_kinds": list(view.get("material_fact_kinds") or []),
                    "uncertainty_states": list(view.get("uncertainty_states") or []),
                }
                for view in views
            ),
            key=_canonical_json,
        )
        ir = {
            "schema": SEMANTIC_IR_SCHEMA,
            "extractor": {
                "name": self.name,
                "version": self.version,
                "mode": "model_assisted",
            },
            "request": {
                "digest": _digest_text(request),
                "text_available": True,
            },
            "facts": facts,
            "uncertainties": uncertainties,
            "review_state": REVIEW_REQUIRED if uncertainties else REVIEW_RESOLVED,
            "metadata": {
                "phase": "S5R",
                "stability_strategy": STABILITY_STRATEGY,
                "required_samples": STABILITY_SAMPLE_COUNT,
                "sample_count": len(views),
                "unanimous_policy_relevant_view": unanimous,
                "common_material_fact_kinds": sorted(common_kinds),
                "sample_views": normalized_views,
                "project_context_digest": _context_digest(project_context),
                "policy_authority": False,
            },
        }
        errors = validate_semantic_ir(ir)
        if errors:
            raise RuntimeError("stabilized Semantic IR is invalid: " + "; ".join(errors))
        return ir
