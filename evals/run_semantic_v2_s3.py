#!/usr/bin/env python3
"""Acceptance runner for Semantic Routing v2 S3 deterministic composer."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from semantic_v2.contracts import REVIEW_REQUIRED, REVIEW_RESOLVED, SEMANTIC_IR_SCHEMA, validate_semantic_ir
from semantic_v2.policy_composer import DeterministicPolicyComposer, RISK_ORDER, composer_rule_coverage

ROOT = Path(__file__).resolve().parents[1]
CONTROLS_PATH = ROOT / "evals" / "semantic_v2" / "s3_controls.json"
COMPOSER_SOURCE = ROOT / "semantic_v2" / "policy_composer.py"


def provenance(locator: str = "request:0-64") -> list[dict[str, Any]]:
    return [{
        "source_kind": "request",
        "locator": locator,
        "extractor": "s3-scripted-ir",
        "confidence": 1.0,
        "ambiguity": "none",
    }]


def fact(kind: str, *, fid: str | None = None, material: bool = True, subject: str | None = None,
         object_: str | None = None, attributes: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": fid or kind.lower().replace("_", "-"),
        "kind": kind,
        "material": material,
        "subject": subject,
        "object": object_,
        "attributes": dict(attributes or {}),
        "provenance": provenance(),
    }


def make_ir(facts: list[dict[str, Any]], *, uncertainties: list[dict[str, Any]] | None = None,
            review_state: str | None = None, metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    uncertainties = list(uncertainties or [])
    if review_state is None:
        review_state = REVIEW_REQUIRED if any(u.get("material") is True for u in uncertainties) else REVIEW_RESOLVED
    request_text = "S3 deterministic composer acceptance fixture"
    ir = {
        "schema": SEMANTIC_IR_SCHEMA,
        "extractor": {"name": "s3-scripted-ir", "version": "1", "mode": "replay"},
        "request": {
            "digest": hashlib.sha256(request_text.encode("utf-8")).hexdigest(),
            "text_available": True,
        },
        "facts": copy.deepcopy(facts),
        "uncertainties": copy.deepcopy(uncertainties),
        "review_state": review_state,
        "metadata": dict(metadata or {"phase": "S3_ACCEPTANCE"}),
    }
    return ir


def uncertainty() -> dict[str, Any]:
    return {
        "id": "scope-relation-uncertain",
        "relation_hint": "access_control_boundary",
        "material": True,
        "state": "AMBIGUOUS",
        "reason": "scope boundary remains unresolved",
        "provenance": provenance("request:12-84"),
    }


def policy_view(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": output.get("status"),
        "risk": output.get("risk"),
        "minimum_risk_from_resolved_facts": output.get("minimum_risk_from_resolved_facts"),
        "packs": output.get("packs"),
        "procedures": output.get("procedures"),
        "implementation_allowed": output.get("implementation_allowed"),
        "release_decision": output.get("release_decision"),
        "matched_rules": output.get("matched_rules"),
    }


def result(control_id: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"id": control_id, "status": "PASS" if passed else "FAIL", "detail": detail}


def auth_ir(label: str) -> dict[str, Any]:
    return make_ir([
        fact(
            "ACCESS_CONTROL_BOUNDARY",
            fid="access-boundary",
            subject="editor",
            object_="record",
            attributes={"scope_label": label, "denied_across_scope": True},
        ),
        fact(
            "PARTITION_ISOLATION",
            fid="partition-isolation",
            subject="record",
            object_=label,
            attributes={"literal_scope_label": label, "cross_scope_denial": True},
        ),
    ])


def run_control(control: Mapping[str, Any], composer: DeterministicPolicyComposer) -> tuple[dict[str, Any], dict[str, Any] | None]:
    cid = str(control["id"])
    kind = str(control["kind"])

    if kind == "authorization":
        label = str(control["scope_label"])
        ir = auth_ir(label)
        output = composer.compose(ir)
        expected_packs = {"AUTHORIZATION", "MULTI_TENANT"}
        expected_procs = {"security-authentication-authorization", "multi-tenant-isolation"}
        passed = (
            validate_semantic_ir(ir) == []
            and output.get("status") == "COMPOSED"
            and output.get("risk") == "R3"
            and set(output.get("packs", [])) == expected_packs
            and set(output.get("procedures", [])) == expected_procs
            and output.get("implementation_allowed") is True
            and output.get("metadata", {}).get("provider_calls") == 0
        )
        return result(cid, passed, {"scope_label": label, "policy": policy_view(output)}), policy_view(output)

    if kind == "single_fact":
        fk = str(control["fact_kind"])
        ir = make_ir([fact(fk)])
        output = composer.compose(ir)
        passed = (
            output.get("status") == "COMPOSED"
            and output.get("risk") == control.get("risk")
            and set(output.get("packs", [])) == set(control.get("packs", []))
            and set(output.get("procedures", [])) == set(control.get("procedures", []))
        )
        return result(cid, passed, policy_view(output)), None

    if kind == "regulated":
        ir = make_ir([fact(
            "CONSEQUENTIAL_DECISION",
            subject="system",
            object_="person-outcome",
            attributes={"decision_affects_person_right_or_access": True},
        )])
        output = composer.compose(ir)
        passed = (
            output.get("risk") == "R3"
            and output.get("packs") == ["REGULATED_DOMAIN"]
            and output.get("procedures") == ["regulated-domain-escalation"]
            and output.get("implementation_allowed") is False
            and output.get("release_decision") == "BLOCKED_REGULATED_AUTHORITY"
        )
        return result(cid, passed, policy_view(output)), None

    if kind == "data_composition":
        ir = make_ir([
            fact("LIVE_DATA_TRANSFORMATION", fid="live-transform"),
            fact("CAPACITY_MATERIALITY", fid="capacity-materiality"),
        ])
        output = composer.compose(ir)
        expected_packs = {"DATABASE_MIGRATION", "PERFORMANCE_CAPACITY_COST", "RELEASE_ENGINEERING"}
        expected_procs = {"database-migration-recovery", "performance-capacity-cost", "release-progressive-delivery"}
        passed = (
            output.get("risk") == "R3"
            and set(output.get("packs", [])) == expected_packs
            and set(output.get("procedures", [])) == expected_procs
            and "composition:large-live-data-release-closure" in output.get("matched_rules", [])
        )
        return result(cid, passed, policy_view(output)), None

    if kind == "review_block":
        ir = make_ir([
            fact("ACCESS_CONTROL_BOUNDARY", subject="editor", object_="record")
        ], uncertainties=[uncertainty()])
        output = composer.compose(ir)
        passed = (
            validate_semantic_ir(ir) == []
            and output.get("status") == REVIEW_REQUIRED
            and output.get("risk") is None
            and output.get("minimum_risk_from_resolved_facts") == "R3"
            and output.get("packs") == ["AUTHORIZATION"]
            and output.get("implementation_allowed") is False
            and output.get("release_decision") == "BLOCKED_SEMANTIC_REVIEW"
        )
        return result(cid, passed, policy_view(output)), None

    if kind == "invalid_block":
        ir = make_ir([], metadata={"phase": "S3_ACCEPTANCE", "risk": "R1"})
        output = composer.compose(ir)
        passed = (
            validate_semantic_ir(ir) != []
            and output.get("status") == "INVALID_IR"
            and output.get("risk") is None
            and output.get("packs") == []
            and output.get("implementation_allowed") is False
            and output.get("release_decision") == "BLOCKED_INVALID_IR"
        )
        return result(cid, passed, {"errors": output.get("errors"), "policy": policy_view(output)}), None

    if kind == "nonmaterial":
        ir = make_ir([fact("DEPLOYMENT_ARTIFACT", material=False)])
        output = composer.compose(ir)
        passed = (
            output.get("status") == "COMPOSED"
            and output.get("risk") == "R1"
            and output.get("packs") == []
            and output.get("procedures") == []
        )
        return result(cid, passed, policy_view(output)), None

    if kind == "idempotent":
        ir = auth_ir("workspace")
        first = composer.compose(ir)
        second = composer.compose(copy.deepcopy(ir))
        passed = first == second and first.get("composition_digest") == second.get("composition_digest")
        return result(cid, passed, {"composition_digest": first.get("composition_digest")}), None

    if kind == "monotonic":
        base_ir = make_ir([fact("ACCESS_CONTROL_BOUNDARY")])
        expanded_ir = make_ir([
            fact("ACCESS_CONTROL_BOUNDARY"),
            fact("SERVER_DESTINATION_TRUST", fid="server-trust"),
        ])
        base = composer.compose(base_ir)
        expanded = composer.compose(expanded_ir)
        base_risk = str(base.get("risk"))
        expanded_risk = str(expanded.get("risk"))
        passed = (
            set(base.get("packs", [])).issubset(set(expanded.get("packs", [])))
            and set(base.get("procedures", [])).issubset(set(expanded.get("procedures", [])))
            and RISK_ORDER[expanded_risk] >= RISK_ORDER[base_risk]
        )
        return result(cid, passed, {"base": policy_view(base), "expanded": policy_view(expanded)}), None

    if kind == "rule_coverage":
        coverage = composer_rule_coverage()
        return result(cid, coverage.get("complete") is True, coverage), None

    if kind == "source_guard":
        source = COMPOSER_SOURCE.read_text(encoding="utf-8").lower()
        forbidden_tokens = [
            "model_extractor",
            "semanticprovider",
            "extract_semantics(",
            "import openai",
            "import anthropic",
            "import requests",
            "import urllib",
            "import socket",
        ]
        found = [token for token in forbidden_tokens if token in source]
        return result(cid, not found, {"forbidden_provider_or_network_tokens": found}), None

    return result(cid, False, {"error": f"unsupported control kind: {kind}"}), None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", default=str(CONTROLS_PATH))
    parser.add_argument("--output")
    args = parser.parse_args()

    with Path(args.controls).open(encoding="utf-8") as handle:
        suite = json.load(handle)
    controls = suite.get("controls", [])
    composer = DeterministicPolicyComposer()
    results: list[dict[str, Any]] = []
    auth_views: dict[str, dict[str, Any]] = {}

    for control in controls:
        observed, auth_view = run_control(control, composer)
        results.append(observed)
        if auth_view is not None:
            auth_views[str(control["id"])] = auth_view

    normalized_auth = {
        key: {k: v for k, v in view.items() if k != "matched_rules"}
        for key, view in auth_views.items()
    }
    unique_views = {json.dumps(value, sort_keys=True) for value in normalized_auth.values()}
    metamorphic_pass = len(normalized_auth) == 4 and len(unique_views) == 1
    results.append(result("S3-METAMORPHIC-SCOPE-POLICY", metamorphic_pass, normalized_auth))

    order_ir = auth_ir("workspace")
    reordered_ir = copy.deepcopy(order_ir)
    reordered_ir["facts"] = list(reversed(reordered_ir["facts"]))
    first = composer.compose(order_ir)
    reordered = composer.compose(reordered_ir)
    order_pass = policy_view(first) == policy_view(reordered)
    results.append(result("S3-FACT-ORDER-INVARIANT", order_pass, {
        "first": policy_view(first),
        "reordered": policy_view(reordered),
    }))

    counts = {
        "PASS": sum(item["status"] == "PASS" for item in results),
        "FAIL": sum(item["status"] == "FAIL" for item in results),
    }
    report = {
        "schema": "sef.eval.semantic-v2-s3-report.v1",
        "phase": "S3",
        "status": "PASS" if counts["FAIL"] == 0 else "FAIL",
        "counts": counts,
        "deterministic_policy_composer_validated": counts["FAIL"] == 0,
        "provider_calls_allowed": False,
        "provider_calls_observed": 0,
        "canonical_v15_routing_changed": False,
        "shadow_integration_implemented": False,
        "results": results,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
