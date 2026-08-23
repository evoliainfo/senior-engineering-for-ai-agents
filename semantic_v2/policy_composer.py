#!/usr/bin/env python3
"""S3 deterministic policy composer for Semantic Routing v2.

The composer consumes validated Semantic IR and emits canonical governance. It
never invokes a semantic provider and never infers new semantic facts from text.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Mapping

from .contracts import FACT_KINDS, REVIEW_REQUIRED, validate_semantic_ir, semantic_ir_digest

POLICY_SCHEMA = "sef.semantic-policy.v1"
RISK_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
DEFAULT_RISK = "R1"

# Explicit relation -> governance rules. Literal business nouns never appear here.
FACT_POLICY_RULES: dict[str, dict[str, Any]] = {
    "ACCESS_CONTROL_BOUNDARY": {
        "risk": "R3",
        "packs": ["AUTHORIZATION"],
        "procedures": ["security-authentication-authorization"],
    },
    "PARTITION_ISOLATION": {
        "risk": "R3",
        "packs": ["MULTI_TENANT"],
        "procedures": ["multi-tenant-isolation"],
    },
    "AUTHENTICATION_PROTOCOL": {
        "risk": "R2",
        "packs": ["AUTH_PROTOCOL"],
        "procedures": ["security-authentication-authorization"],
    },
    "SERVER_DESTINATION_TRUST": {
        "risk": "R3",
        "packs": ["WEBHOOK_TRUST"],
        "procedures": ["webhook-external-input-trust"],
    },
    "EXTERNAL_OPERATIONAL_DEPENDENCY": {
        "risk": "R3",
        "packs": ["EXTERNAL_SUPPLIER"],
        "procedures": ["external-supplier-saas-governance"],
    },
    "CONSEQUENTIAL_DECISION": {
        "risk": "R3",
        "packs": ["REGULATED_DOMAIN"],
        "procedures": ["regulated-domain-escalation"],
        "implementation_allowed": False,
    },
    "LIVE_DATA_TRANSFORMATION": {
        "risk": "R3",
        "packs": ["DATABASE_MIGRATION"],
        "procedures": ["database-migration-recovery"],
    },
    "CAPACITY_MATERIALITY": {
        "risk": "R3",
        "packs": ["PERFORMANCE_CAPACITY_COST"],
        "procedures": ["performance-capacity-cost"],
    },
    "PRODUCTION_RELEASE_CHANGE": {
        "risk": "R2",
        "packs": ["RELEASE_ENGINEERING"],
        "procedures": ["release-progressive-delivery"],
    },
    "DEPLOYMENT_ARTIFACT": {
        "risk": "R2",
        "packs": ["CONTAINER_ENGINEERING"],
        "procedures": ["container-docker-engineering"],
    },
    "BUILD_SUPPLY_CHAIN": {
        "risk": "R2",
        "packs": ["CI_SUPPLY_CHAIN"],
        "procedures": ["ci-software-supply-chain"],
    },
    "UNTRUSTED_FILE_INPUT": {
        "risk": "R2",
        "packs": ["FILE_UPLOAD_SECURITY"],
        "procedures": [],
    },
}

# Composition rules operate only on typed fact kinds, never on free-text nouns.
COMPOSITION_RULES: tuple[dict[str, Any], ...] = (
    {
        "id": "large-live-data-release-closure",
        "requires": {"LIVE_DATA_TRANSFORMATION", "CAPACITY_MATERIALITY"},
        "risk": "R3",
        "packs": ["RELEASE_ENGINEERING"],
        "procedures": ["release-progressive-delivery"],
    },
)


def _max_risk(left: str, right: str) -> str:
    if left not in RISK_ORDER or right not in RISK_ORDER:
        raise ValueError("unknown risk level")
    return left if RISK_ORDER[left] >= RISK_ORDER[right] else right


def _canonical_digest(value: Mapping[str, Any]) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _invalid_output(ir: Mapping[str, Any], errors: list[str]) -> dict[str, Any]:
    core = {
        "schema": POLICY_SCHEMA,
        "composer": {"name": "semantic-v2-deterministic-composer", "version": "1", "mode": "deterministic"},
        "status": "INVALID_IR",
        "risk": None,
        "minimum_risk_from_resolved_facts": None,
        "packs": [],
        "procedures": [],
        "implementation_allowed": False,
        "release_decision": "BLOCKED_INVALID_IR",
        "matched_rules": [],
        "semantic_ir_digest": _canonical_digest(dict(ir)),
        "errors": list(errors),
        "metadata": {"phase": "S3", "deterministic": True, "provider_calls": 0},
    }
    core["composition_digest"] = _canonical_digest(core)
    return core


class DeterministicPolicyComposer:
    """Map validated Semantic IR relations to governance deterministically."""

    name = "semantic-v2-deterministic-composer"
    version = "1"

    def compose(self, semantic_ir: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(semantic_ir, Mapping):
            return _invalid_output({}, ["$: expected object"])
        ir = copy.deepcopy(dict(semantic_ir))
        errors = validate_semantic_ir(ir)
        if errors:
            return _invalid_output(ir, errors)

        packs: set[str] = set()
        procedures: set[str] = set()
        matched_rules: list[str] = []
        material_kinds: set[str] = set()
        risk = DEFAULT_RISK
        implementation_allowed = True

        for fact in ir.get("facts", []):
            if fact.get("material") is not True:
                continue
            kind = str(fact.get("kind"))
            material_kinds.add(kind)
            rule = FACT_POLICY_RULES.get(kind)
            if rule is None:
                # Contract coverage should prevent this, but fail closed if the
                # vocabulary expands before composer rules do.
                return _invalid_output(ir, [f"no deterministic policy rule for material fact kind: {kind}"])
            risk = _max_risk(risk, str(rule["risk"]))
            packs.update(str(value) for value in rule.get("packs", []))
            procedures.update(str(value) for value in rule.get("procedures", []))
            if rule.get("implementation_allowed") is False:
                implementation_allowed = False
            matched_rules.append(f"fact:{kind}")

        for rule in COMPOSITION_RULES:
            required = set(rule["requires"])
            if required.issubset(material_kinds):
                risk = _max_risk(risk, str(rule["risk"]))
                packs.update(str(value) for value in rule.get("packs", []))
                procedures.update(str(value) for value in rule.get("procedures", []))
                matched_rules.append(f"composition:{rule['id']}")

        review_required = ir.get("review_state") == REVIEW_REQUIRED
        final_risk: str | None = None if review_required else risk
        if review_required:
            implementation_allowed = False
            status = REVIEW_REQUIRED
            release_decision = "BLOCKED_SEMANTIC_REVIEW"
        elif not implementation_allowed:
            status = "COMPOSED"
            release_decision = "BLOCKED_REGULATED_AUTHORITY"
        else:
            status = "COMPOSED"
            release_decision = "NOT_EVALUATED"

        core = {
            "schema": POLICY_SCHEMA,
            "composer": {"name": self.name, "version": self.version, "mode": "deterministic"},
            "status": status,
            "risk": final_risk,
            "minimum_risk_from_resolved_facts": risk,
            "packs": sorted(packs),
            "procedures": sorted(procedures),
            "implementation_allowed": implementation_allowed,
            "release_decision": release_decision,
            "matched_rules": sorted(set(matched_rules)),
            "semantic_ir_digest": semantic_ir_digest(ir),
            "errors": [],
            "metadata": {
                "phase": "S3",
                "deterministic": True,
                "provider_calls": 0,
                "material_fact_kinds": sorted(material_kinds),
            },
        }
        core["composition_digest"] = _canonical_digest(core)
        return core


def composer_rule_coverage() -> dict[str, Any]:
    mapped = set(FACT_POLICY_RULES)
    declared = set(FACT_KINDS)
    return {
        "declared": sorted(declared),
        "mapped": sorted(mapped),
        "missing": sorted(declared - mapped),
        "extra": sorted(mapped - declared),
        "complete": declared == mapped,
    }
