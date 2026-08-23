#!/usr/bin/env python3
"""S1 deterministic bridge from frozen v1.5 observations to Semantic IR.

This module is shadow-only. It translates *already proven* v1.5 policy signals
into typed semantic facts for migration/evidence purposes. It is not the future
open-vocabulary extractor and it never changes the canonical assessment.
"""
from __future__ import annotations

import copy
import hashlib
from typing import Any, Mapping

from .contracts import SEMANTIC_IR_SCHEMA, semantic_ir_digest, validate_semantic_ir

LEGACY_TO_FACT = {
    "AUTHORIZATION": "ACCESS_CONTROL_BOUNDARY",
    "MULTI_TENANT": "PARTITION_ISOLATION",
    "AUTH_PROTOCOL": "AUTHENTICATION_PROTOCOL",
    "WEBHOOK_TRUST": "SERVER_DESTINATION_TRUST",
    "EXTERNAL_SUPPLIER": "EXTERNAL_OPERATIONAL_DEPENDENCY",
    "REGULATED_DOMAIN": "CONSEQUENTIAL_DECISION",
    "DATABASE_MIGRATION": "LIVE_DATA_TRANSFORMATION",
    "PERFORMANCE_CAPACITY_COST": "CAPACITY_MATERIALITY",
    "RELEASE_ENGINEERING": "PRODUCTION_RELEASE_CHANGE",
    "CONTAINER_ENGINEERING": "DEPLOYMENT_ARTIFACT",
    "CI_SUPPLY_CHAIN": "BUILD_SUPPLY_CHAIN",
    "FILE_UPLOAD_SECURITY": "UNTRUSTED_FILE_INPUT",
}

MATERIAL_FACTS = {
    "ACCESS_CONTROL_BOUNDARY",
    "PARTITION_ISOLATION",
    "SERVER_DESTINATION_TRUST",
    "CONSEQUENTIAL_DECISION",
    "LIVE_DATA_TRANSFORMATION",
    "PRODUCTION_RELEASE_CHANGE",
    "BUILD_SUPPLY_CHAIN",
}


def _request_digest(assessment: Mapping[str, Any], request_text: str | None) -> str:
    if request_text is not None:
        payload = request_text
    else:
        payload = str(assessment.get("request") or assessment.get("task") or "")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bridge_legacy_assessment(
    assessment: Mapping[str, Any],
    *,
    request_text: str | None = None,
    source_id: str = "legacy-v1.5-assessment",
) -> dict[str, Any]:
    """Translate canonical v1.5 signals into Semantic IR without policy authority.

    Unknown legacy packs are deliberately preserved only in bridge metadata so the
    migration cannot silently pretend complete coverage.
    """

    raw_packs = assessment.get("packs") or []
    packs = sorted({str(value) for value in raw_packs if isinstance(value, str)})
    mapped = [(pack, LEGACY_TO_FACT[pack]) for pack in packs if pack in LEGACY_TO_FACT]
    unmapped = [pack for pack in packs if pack not in LEGACY_TO_FACT]

    facts: list[dict[str, Any]] = []
    for index, (legacy_signal, kind) in enumerate(mapped, 1):
        facts.append(
            {
                "id": f"legacy-{index:03d}-{kind.lower().replace('_', '-')}",
                "kind": kind,
                "material": kind in MATERIAL_FACTS,
                "subject": None,
                "object": None,
                "attributes": {
                    "bridge_semantics": "legacy_signal_present",
                    "source_id": source_id,
                },
                "provenance": [
                    {
                        "source_kind": "legacy_assessment",
                        "locator": f"assessment.packs[{legacy_signal}]",
                        "extractor": "semantic-v2-legacy-bridge",
                        "confidence": 1.0,
                        "ambiguity": "none",
                    }
                ],
            }
        )

    ir = {
        "schema": SEMANTIC_IR_SCHEMA,
        "extractor": {
            "name": "semantic-v2-legacy-bridge",
            "version": "1",
            "mode": "deterministic_legacy",
        },
        "request": {
            "digest": _request_digest(assessment, request_text),
            "text_available": request_text is not None,
        },
        "facts": facts,
        "uncertainties": [],
        "review_state": "RESOLVED",
        "metadata": {
            "phase": "S1",
            "mode": "SHADOW_ONLY",
            "coverage": "LEGACY_SIGNALS_ONLY",
            "open_vocabulary_claim": False,
            "mapped_signal_count": len(mapped),
            "unmapped_legacy_signals": unmapped,
        },
    }
    errors = validate_semantic_ir(ir)
    if errors:
        raise ValueError("invalid bridge output: " + "; ".join(errors))
    return ir


def shadow_bridge(
    assessment: Mapping[str, Any],
    *,
    request_text: str | None = None,
    source_id: str = "legacy-v1.5-assessment",
) -> dict[str, Any]:
    """Return canonical output unchanged beside shadow Semantic IR evidence."""

    canonical = copy.deepcopy(dict(assessment))
    ir = bridge_legacy_assessment(
        assessment,
        request_text=request_text,
        source_id=source_id,
    )
    return {
        "mode": "SHADOW_ONLY",
        "canonical_output": canonical,
        "canonical_output_changed": False,
        "semantic_ir": ir,
        "semantic_ir_digest": semantic_ir_digest(ir),
    }
