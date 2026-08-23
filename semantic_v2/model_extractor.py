#!/usr/bin/env python3
"""S2 provider-neutral open-vocabulary semantic extraction boundary.

A semantic provider is treated as untrusted. It may propose facts and
uncertainties, but it cannot choose governance, risk, review status or release
approval. Invalid/unavailable provider output fails closed to a valid Semantic IR
with SEMANTIC_REVIEW_REQUIRED.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping, Protocol

from .contracts import (
    FACT_KINDS,
    FORBIDDEN_POLICY_KEYS,
    REVIEW_REQUIRED,
    REVIEW_RESOLVED,
    SEMANTIC_IR_SCHEMA,
    validate_semantic_ir,
)

MATERIAL_FACT_KINDS = {
    "ACCESS_CONTROL_BOUNDARY",
    "PARTITION_ISOLATION",
    "SERVER_DESTINATION_TRUST",
    "EXTERNAL_OPERATIONAL_DEPENDENCY",
    "CONSEQUENTIAL_DECISION",
    "LIVE_DATA_TRANSFORMATION",
    "CAPACITY_MATERIALITY",
    "PRODUCTION_RELEASE_CHANGE",
    "BUILD_SUPPLY_CHAIN",
    "UNTRUSTED_FILE_INPUT",
}

PROVIDER_OUTPUT_KEYS = {"facts", "uncertainties", "complete"}


class SemanticProvider(Protocol):
    """Provider-neutral semantic inference contract.

    Implementations can call a model, local service or deterministic replay. They
    return semantic candidates only. The wrapper owns validation and review state.
    """

    def extract_semantics(
        self,
        request: str,
        project_context: Mapping[str, Any],
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ...


def _request_digest(request: str) -> str:
    return hashlib.sha256(request.encode("utf-8")).hexdigest()


def _provenance(
    *,
    extractor_id: str,
    source_kind: str = "request",
    locator: str = "request",
    confidence: float = 0.0,
    ambiguity: str = "high",
) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "locator": locator,
        "extractor": extractor_id,
        "confidence": confidence,
        "ambiguity": ambiguity,
    }


def _fail_closed_ir(
    request: str,
    *,
    extractor_id: str,
    provider_name: str,
    state: str,
    reason: str,
) -> dict[str, Any]:
    ir = {
        "schema": SEMANTIC_IR_SCHEMA,
        "extractor": {
            "name": extractor_id,
            "version": "2",
            "mode": "model_assisted",
        },
        "request": {
            "digest": _request_digest(request),
            "text_available": True,
        },
        "facts": [],
        "uncertainties": [
            {
                "id": "semantic-provider-review-required",
                "relation_hint": "semantic_extraction",
                "material": True,
                "state": state,
                "reason": reason,
                "provenance": [
                    _provenance(extractor_id=extractor_id, confidence=0.0, ambiguity="high")
                ],
            }
        ],
        "review_state": REVIEW_REQUIRED,
        "metadata": {
            "phase": "S2",
            "provider": provider_name,
            "provider_output_accepted": False,
            "policy_authority": False,
            "fail_closed": True,
        },
    }
    errors = validate_semantic_ir(ir)
    if errors:
        raise RuntimeError("internal fail-closed IR is invalid: " + "; ".join(errors))
    return ir


def _normalize_provenance(entries: Any, extractor_id: str) -> list[dict[str, Any]]:
    if not isinstance(entries, list) or not entries:
        raise ValueError("provenance is required")
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise ValueError("provenance entry must be an object")
        normalized.append(
            {
                "source_kind": entry.get("source_kind"),
                "locator": entry.get("locator"),
                "extractor": extractor_id,
                "confidence": entry.get("confidence"),
                "ambiguity": entry.get("ambiguity"),
            }
        )
    return normalized


class ModelAssistedExtractor:
    """Strict wrapper around an open-vocabulary semantic provider.

    The provider never returns a complete Semantic IR. It proposes semantic facts
    and uncertainties; this wrapper injects identity, computes materiality floors,
    computes review state and validates the final IR.
    """

    def __init__(
        self,
        provider: SemanticProvider,
        *,
        provider_name: str,
        extractor_id: str = "semantic-v2-model-assisted",
    ) -> None:
        if not provider_name.strip():
            raise ValueError("provider_name is required")
        if not extractor_id.strip():
            raise ValueError("extractor_id is required")
        self.provider = provider
        self.provider_name = provider_name
        self.extractor_id = extractor_id

    def provider_contract(self) -> dict[str, Any]:
        return {
            "schema": "sef.semantic-provider-output.v1",
            "allowed_fact_kinds": sorted(FACT_KINDS),
            "forbidden_policy_keys": sorted(FORBIDDEN_POLICY_KEYS),
            "output_keys": sorted(PROVIDER_OUTPUT_KEYS),
            "rules": [
                "return semantic facts and uncertainties only",
                "include source provenance for every fact and uncertainty",
                "preserve literal open-vocabulary labels in attributes",
                "do not emit governance packs, risk, procedures or release decisions",
                "set complete=false when any material relation may be unresolved",
            ],
        }

    def extract(self, request: str, project_context: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(request, str) or not request.strip():
            return _fail_closed_ir(
                request if isinstance(request, str) else "",
                extractor_id=self.extractor_id,
                provider_name=self.provider_name,
                state="INVALID",
                reason="request text is empty or invalid",
            )
        if not isinstance(project_context, Mapping):
            return _fail_closed_ir(
                request,
                extractor_id=self.extractor_id,
                provider_name=self.provider_name,
                state="INVALID",
                reason="project_context must be an object",
            )

        try:
            raw = self.provider.extract_semantics(request, project_context, self.provider_contract())
        except Exception as exc:
            return _fail_closed_ir(
                request,
                extractor_id=self.extractor_id,
                provider_name=self.provider_name,
                state="UNAVAILABLE",
                reason=f"semantic provider unavailable: {type(exc).__name__}",
            )

        try:
            if not isinstance(raw, Mapping):
                raise ValueError("provider output must be an object")
            unknown = sorted(set(raw) - PROVIDER_OUTPUT_KEYS)
            if unknown:
                raise ValueError("unsupported provider output keys: " + ", ".join(unknown))
            if not isinstance(raw.get("complete"), bool):
                raise ValueError("provider output complete must be boolean")
            raw_facts = raw.get("facts")
            raw_uncertainties = raw.get("uncertainties")
            if not isinstance(raw_facts, list) or not isinstance(raw_uncertainties, list):
                raise ValueError("facts and uncertainties must be arrays")

            facts: list[dict[str, Any]] = []
            for index, fact in enumerate(raw_facts):
                if not isinstance(fact, Mapping):
                    raise ValueError(f"fact {index} must be an object")
                kind = fact.get("kind")
                if kind not in FACT_KINDS:
                    raise ValueError(f"fact {index} has unsupported kind")
                facts.append(
                    {
                        "id": fact.get("id"),
                        "kind": kind,
                        "material": True if kind in MATERIAL_FACT_KINDS else bool(fact.get("material", False)),
                        "subject": fact.get("subject"),
                        "object": fact.get("object"),
                        "attributes": fact.get("attributes"),
                        "provenance": _normalize_provenance(fact.get("provenance"), self.extractor_id),
                    }
                )

            uncertainties: list[dict[str, Any]] = []
            for index, uncertainty in enumerate(raw_uncertainties):
                if not isinstance(uncertainty, Mapping):
                    raise ValueError(f"uncertainty {index} must be an object")
                uncertainties.append(
                    {
                        "id": uncertainty.get("id"),
                        "relation_hint": uncertainty.get("relation_hint"),
                        # Provider uncertainty is never trusted as non-material in S2.
                        # A future deterministic rule may downgrade it with evidence.
                        "material": True,
                        "state": uncertainty.get("state"),
                        "reason": uncertainty.get("reason"),
                        "provenance": _normalize_provenance(
                            uncertainty.get("provenance"), self.extractor_id
                        ),
                    }
                )

            if raw.get("complete") is False and not uncertainties:
                uncertainties.append(
                    {
                        "id": "provider-incomplete",
                        "relation_hint": "semantic_extraction",
                        "material": True,
                        "state": "AMBIGUOUS",
                        "reason": "provider declared semantic extraction incomplete",
                        "provenance": [
                            _provenance(
                                extractor_id=self.extractor_id,
                                confidence=0.0,
                                ambiguity="high",
                            )
                        ],
                    }
                )

            review_state = REVIEW_REQUIRED if uncertainties else REVIEW_RESOLVED
            ir = {
                "schema": SEMANTIC_IR_SCHEMA,
                "extractor": {
                    "name": self.extractor_id,
                    "version": "2",
                    "mode": "model_assisted",
                },
                "request": {
                    "digest": _request_digest(request),
                    "text_available": True,
                },
                "facts": facts,
                "uncertainties": uncertainties,
                "review_state": review_state,
                "metadata": {
                    "phase": "S2",
                    "provider": self.provider_name,
                    "provider_output_accepted": True,
                    "provider_declared_complete": raw.get("complete"),
                    "policy_authority": False,
                    "open_vocabulary_labels_allowed": True,
                },
            }
            errors = validate_semantic_ir(ir)
            if errors:
                raise ValueError("; ".join(errors))
            return ir
        except Exception as exc:
            return _fail_closed_ir(
                request,
                extractor_id=self.extractor_id,
                provider_name=self.provider_name,
                state="INVALID",
                reason=f"semantic provider output rejected: {type(exc).__name__}: {exc}",
            )
