#!/usr/bin/env python3
"""S0 contracts for Semantic Routing v2.

The semantic layer describes facts and uncertainty only. It has no authority to
select governance packs, risk levels, implementation approval or release status.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Protocol

SEMANTIC_IR_SCHEMA = "sef.semantic-ir.v1"
REVIEW_RESOLVED = "RESOLVED"
REVIEW_REQUIRED = "SEMANTIC_REVIEW_REQUIRED"
UNCERTAINTY_STATES = {"AMBIGUOUS", "UNAVAILABLE", "CONFLICT", "INVALID"}
EXTRACTOR_MODES = {"deterministic_legacy", "model_assisted", "replay"}
SOURCE_KINDS = {"request", "project_context", "legacy_assessment", "replay_fixture"}
AMBIGUITY_LEVELS = {"none", "low", "medium", "high"}

# Typed semantic relation vocabulary. Domain labels remain open vocabulary inside
# attributes; policy concepts/packs never appear here.
FACT_KINDS = {
    "ACCESS_CONTROL_BOUNDARY",
    "PARTITION_ISOLATION",
    "AUTHENTICATION_PROTOCOL",
    "SERVER_DESTINATION_TRUST",
    "EXTERNAL_OPERATIONAL_DEPENDENCY",
    "CONSEQUENTIAL_DECISION",
    "LIVE_DATA_TRANSFORMATION",
    "CAPACITY_MATERIALITY",
    "PRODUCTION_RELEASE_CHANGE",
    "DEPLOYMENT_ARTIFACT",
    "BUILD_SUPPLY_CHAIN",
    "UNTRUSTED_FILE_INPUT",
}

# These fields represent policy authority and are forbidden anywhere in extractor
# output. Provenance strings may name historical evidence, but not as decision keys.
FORBIDDEN_POLICY_KEYS = {
    "pack",
    "packs",
    "risk",
    "risk_level",
    "procedures",
    "implementation_allowed",
    "implementation_gate",
    "release_eligible",
    "release_approval",
}


class Extractor(Protocol):
    """Provider-neutral semantic extractor contract.

    Implementations return Semantic IR facts only. They may not emit policy packs,
    risk or release approval.
    """

    def extract(self, request: str, project_context: Mapping[str, Any]) -> dict[str, Any]:
        ...


class PolicyComposer(Protocol):
    """Deterministic composer contract.

    A composer consumes *validated* Semantic IR and maps it to policy outputs.
    Implementations must not call a semantic provider while composing.
    """

    def compose(self, semantic_ir: Mapping[str, Any]) -> dict[str, Any]:
        ...


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def semantic_ir_digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def semantic_review_required(value: Mapping[str, Any]) -> bool:
    for uncertainty in value.get("uncertainties", []) or []:
        if isinstance(uncertainty, Mapping) and uncertainty.get("material") is True:
            return True
    return False


def _walk_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            if key_text in FORBIDDEN_POLICY_KEYS:
                errors.append(f"{path}.{key_text}: policy-authority field forbidden in Semantic IR")
            errors.extend(_walk_forbidden_keys(nested, f"{path}.{key_text}"))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            errors.extend(_walk_forbidden_keys(nested, f"{path}[{index}]"))
    return errors


def _validate_provenance(entries: Any, path: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(entries, list) or not entries:
        return [f"{path}: at least one provenance entry is required"]
    for index, entry in enumerate(entries):
        p = f"{path}[{index}]"
        if not isinstance(entry, Mapping):
            errors.append(f"{p}: expected object")
            continue
        required = {"source_kind", "locator", "extractor", "confidence", "ambiguity"}
        missing = sorted(required - set(entry))
        if missing:
            errors.append(f"{p}: missing {', '.join(missing)}")
            continue
        if entry.get("source_kind") not in SOURCE_KINDS:
            errors.append(f"{p}.source_kind: unsupported value")
        if not isinstance(entry.get("locator"), str) or not entry.get("locator"):
            errors.append(f"{p}.locator: non-empty string required")
        if not isinstance(entry.get("extractor"), str) or not entry.get("extractor"):
            errors.append(f"{p}.extractor: non-empty string required")
        confidence = entry.get("confidence")
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 1:
            errors.append(f"{p}.confidence: number in [0,1] required")
        if entry.get("ambiguity") not in AMBIGUITY_LEVELS:
            errors.append(f"{p}.ambiguity: unsupported value")
    return errors


def validate_semantic_ir(value: Mapping[str, Any]) -> list[str]:
    """Return contract violations. Empty list means valid.

    Validation is intentionally stdlib-only so it can run in the existing SEF
    environment without adding a dependency merely for S0.
    """

    errors: list[str] = []
    if not isinstance(value, Mapping):
        return ["$: expected object"]

    allowed_top = {"schema", "extractor", "request", "facts", "uncertainties", "review_state", "metadata"}
    unknown_top = sorted(set(value) - allowed_top)
    if unknown_top:
        errors.append(f"$: unsupported top-level keys: {', '.join(unknown_top)}")
    if value.get("schema") != SEMANTIC_IR_SCHEMA:
        errors.append("$.schema: expected sef.semantic-ir.v1")

    extractor = value.get("extractor")
    if not isinstance(extractor, Mapping):
        errors.append("$.extractor: expected object")
    else:
        if not isinstance(extractor.get("name"), str) or not extractor.get("name"):
            errors.append("$.extractor.name: non-empty string required")
        if not isinstance(extractor.get("version"), str) or not extractor.get("version"):
            errors.append("$.extractor.version: non-empty string required")
        if extractor.get("mode") not in EXTRACTOR_MODES:
            errors.append("$.extractor.mode: unsupported value")

    request = value.get("request")
    if not isinstance(request, Mapping):
        errors.append("$.request: expected object")
    else:
        digest = request.get("digest")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append("$.request.digest: 64-character SHA-256 hex required")
        elif any(ch not in "0123456789abcdef" for ch in digest.lower()):
            errors.append("$.request.digest: SHA-256 must be hexadecimal")
        if not isinstance(request.get("text_available"), bool):
            errors.append("$.request.text_available: boolean required")

    facts = value.get("facts")
    fact_ids: set[str] = set()
    if not isinstance(facts, list):
        errors.append("$.facts: expected array")
    else:
        for index, fact in enumerate(facts):
            p = f"$.facts[{index}]"
            if not isinstance(fact, Mapping):
                errors.append(f"{p}: expected object")
                continue
            required = {"id", "kind", "material", "subject", "object", "attributes", "provenance"}
            missing = sorted(required - set(fact))
            if missing:
                errors.append(f"{p}: missing {', '.join(missing)}")
                continue
            fid = fact.get("id")
            if not isinstance(fid, str) or not fid:
                errors.append(f"{p}.id: non-empty string required")
            elif fid in fact_ids:
                errors.append(f"{p}.id: duplicate fact id {fid}")
            else:
                fact_ids.add(fid)
            if fact.get("kind") not in FACT_KINDS:
                errors.append(f"{p}.kind: unsupported semantic fact kind")
            if not isinstance(fact.get("material"), bool):
                errors.append(f"{p}.material: boolean required")
            if fact.get("subject") is not None and not isinstance(fact.get("subject"), str):
                errors.append(f"{p}.subject: string or null required")
            if fact.get("object") is not None and not isinstance(fact.get("object"), str):
                errors.append(f"{p}.object: string or null required")
            if not isinstance(fact.get("attributes"), Mapping):
                errors.append(f"{p}.attributes: object required")
            errors.extend(_validate_provenance(fact.get("provenance"), f"{p}.provenance"))

    uncertainties = value.get("uncertainties")
    uncertainty_ids: set[str] = set()
    if not isinstance(uncertainties, list):
        errors.append("$.uncertainties: expected array")
    else:
        for index, uncertainty in enumerate(uncertainties):
            p = f"$.uncertainties[{index}]"
            if not isinstance(uncertainty, Mapping):
                errors.append(f"{p}: expected object")
                continue
            required = {"id", "relation_hint", "material", "state", "reason", "provenance"}
            missing = sorted(required - set(uncertainty))
            if missing:
                errors.append(f"{p}: missing {', '.join(missing)}")
                continue
            uid = uncertainty.get("id")
            if not isinstance(uid, str) or not uid:
                errors.append(f"{p}.id: non-empty string required")
            elif uid in uncertainty_ids:
                errors.append(f"{p}.id: duplicate uncertainty id {uid}")
            else:
                uncertainty_ids.add(uid)
            if not isinstance(uncertainty.get("relation_hint"), str) or not uncertainty.get("relation_hint"):
                errors.append(f"{p}.relation_hint: non-empty string required")
            if not isinstance(uncertainty.get("material"), bool):
                errors.append(f"{p}.material: boolean required")
            if uncertainty.get("state") not in UNCERTAINTY_STATES:
                errors.append(f"{p}.state: unsupported value")
            if not isinstance(uncertainty.get("reason"), str) or not uncertainty.get("reason"):
                errors.append(f"{p}.reason: non-empty string required")
            errors.extend(_validate_provenance(uncertainty.get("provenance"), f"{p}.provenance"))

    expected_review = REVIEW_REQUIRED if semantic_review_required(value) else REVIEW_RESOLVED
    if value.get("review_state") != expected_review:
        errors.append(f"$.review_state: expected {expected_review}")
    if not isinstance(value.get("metadata"), Mapping):
        errors.append("$.metadata: expected object")

    errors.extend(_walk_forbidden_keys(value))
    return errors
