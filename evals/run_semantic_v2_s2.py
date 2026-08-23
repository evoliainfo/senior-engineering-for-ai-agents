#!/usr/bin/env python3
"""Acceptance runner for Semantic Routing v2 S2.

This validates the provider boundary, fail-closed behavior and open-vocabulary
transport semantics. It does not claim that any live model/provider has passed a
semantic-quality benchmark.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Mapping

from semantic_v2.contracts import FORBIDDEN_POLICY_KEYS, REVIEW_REQUIRED, REVIEW_RESOLVED, validate_semantic_ir
from semantic_v2.model_extractor import ModelAssistedExtractor

ROOT = Path(__file__).resolve().parents[1]
CONTROLS_PATH = ROOT / "evals" / "semantic_v2" / "s2_controls.json"
EXTRACTOR_SOURCE = ROOT / "semantic_v2" / "model_extractor.py"


class StaticProvider:
    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = copy.deepcopy(dict(payload))
        self.last_contract: dict[str, Any] | None = None

    def extract_semantics(
        self,
        request: str,
        project_context: Mapping[str, Any],
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        self.last_contract = copy.deepcopy(dict(contract))
        return copy.deepcopy(self.payload)


class ErrorProvider:
    def extract_semantics(
        self,
        request: str,
        project_context: Mapping[str, Any],
        contract: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        raise RuntimeError("simulated provider outage")


def provenance(locator: str = "request:0-64") -> list[dict[str, Any]]:
    return [
        {
            "source_kind": "request",
            "locator": locator,
            "confidence": 0.97,
            "ambiguity": "none",
        }
    ]


def access_payload(label: str, *, material: bool = False) -> dict[str, Any]:
    return {
        "complete": True,
        "facts": [
            {
                "id": "access-boundary",
                "kind": "ACCESS_CONTROL_BOUNDARY",
                "material": material,
                "subject": "editor",
                "object": "record",
                "attributes": {
                    "scope_label": label,
                    "allowed_within_scope": True,
                    "denied_across_scope": True,
                },
                "provenance": provenance(),
            },
            {
                "id": "partition-isolation",
                "kind": "PARTITION_ISOLATION",
                "material": material,
                "subject": "record",
                "object": label,
                "attributes": {
                    "literal_scope_label": label,
                    "cross_scope_denial": True,
                },
                "provenance": provenance("request:20-100"),
            },
        ],
        "uncertainties": [],
    }


def contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if str(key) in FORBIDDEN_POLICY_KEYS or contains_forbidden_key(nested):
                return True
    elif isinstance(value, list):
        return any(contains_forbidden_key(item) for item in value)
    return False


def result(control_id: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {
        "id": control_id,
        "status": "PASS" if passed else "FAIL",
        "detail": detail,
    }


def run_control(control: Mapping[str, Any]) -> tuple[dict[str, Any], set[str] | None]:
    cid = str(control["id"])
    kind = str(control["kind"])
    request = str(control["request"])
    context = {"evaluation": "S2", "control_id": cid}
    fact_kinds: set[str] | None = None

    if kind == "open_scope":
        label = str(control["scope_label"])
        provider = StaticProvider(access_payload(label))
        extractor = ModelAssistedExtractor(provider, provider_name="scripted-eval-provider")
        ir = extractor.extract(request, context)
        fact_kinds = {str(f["kind"]) for f in ir.get("facts", [])}
        literals = {
            str(f.get("attributes", {}).get("scope_label") or f.get("attributes", {}).get("literal_scope_label"))
            for f in ir.get("facts", [])
        }
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_RESOLVED
            and fact_kinds == {"ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"}
            and label in literals
            and all(f.get("material") is True for f in ir.get("facts", []))
            and not contains_forbidden_key(ir)
            and ir.get("metadata", {}).get("provider_output_accepted") is True
        )
        return result(
            cid,
            passed,
            {
                "scope_label": label,
                "fact_kinds": sorted(fact_kinds),
                "literal_labels": sorted(literals),
                "review_state": ir.get("review_state"),
            },
        ), fact_kinds

    if kind == "empty_complete":
        extractor = ModelAssistedExtractor(
            StaticProvider({"complete": True, "facts": [], "uncertainties": []}),
            provider_name="scripted-eval-provider",
        )
        ir = extractor.extract(request, context)
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_RESOLVED
            and ir.get("facts") == []
            and ir.get("uncertainties") == []
            and ir.get("metadata", {}).get("provider_output_accepted") is True
        )
        return result(cid, passed, {"review_state": ir.get("review_state"), "facts": len(ir.get("facts", []))}), None

    if kind == "incomplete":
        extractor = ModelAssistedExtractor(
            StaticProvider({"complete": False, "facts": [], "uncertainties": []}),
            provider_name="scripted-eval-provider",
        )
        ir = extractor.extract(request, context)
        states = [u.get("state") for u in ir.get("uncertainties", [])]
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_REQUIRED
            and states == ["AMBIGUOUS"]
            and all(u.get("material") is True for u in ir.get("uncertainties", []))
        )
        return result(cid, passed, {"review_state": ir.get("review_state"), "states": states}), None

    if kind == "provider_error":
        extractor = ModelAssistedExtractor(ErrorProvider(), provider_name="unavailable-eval-provider")
        ir = extractor.extract(request, context)
        states = [u.get("state") for u in ir.get("uncertainties", [])]
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_REQUIRED
            and states == ["UNAVAILABLE"]
            and ir.get("metadata", {}).get("fail_closed") is True
            and ir.get("metadata", {}).get("provider_output_accepted") is False
        )
        return result(cid, passed, {"review_state": ir.get("review_state"), "states": states}), None

    if kind == "top_level_policy_injection":
        payload = access_payload("group")
        payload["risk"] = "R1"
        extractor = ModelAssistedExtractor(StaticProvider(payload), provider_name="hostile-eval-provider")
        ir = extractor.extract(request, context)
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_REQUIRED
            and ir.get("metadata", {}).get("provider_output_accepted") is False
            and [u.get("state") for u in ir.get("uncertainties", [])] == ["INVALID"]
            and not contains_forbidden_key(ir)
        )
        return result(cid, passed, {"review_state": ir.get("review_state"), "accepted": ir.get("metadata", {}).get("provider_output_accepted")}), None

    if kind == "nested_policy_injection":
        payload = access_payload("group")
        payload["facts"][0]["attributes"]["release_approval"] = True
        extractor = ModelAssistedExtractor(StaticProvider(payload), provider_name="hostile-eval-provider")
        ir = extractor.extract(request, context)
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_REQUIRED
            and ir.get("metadata", {}).get("provider_output_accepted") is False
            and [u.get("state") for u in ir.get("uncertainties", [])] == ["INVALID"]
            and not contains_forbidden_key(ir)
        )
        return result(cid, passed, {"review_state": ir.get("review_state"), "accepted": ir.get("metadata", {}).get("provider_output_accepted")}), None

    if kind == "bad_provenance":
        payload = access_payload("group")
        payload["facts"][0]["provenance"] = []
        extractor = ModelAssistedExtractor(StaticProvider(payload), provider_name="malformed-eval-provider")
        ir = extractor.extract(request, context)
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_REQUIRED
            and [u.get("state") for u in ir.get("uncertainties", [])] == ["INVALID"]
        )
        return result(cid, passed, {"review_state": ir.get("review_state")}), None

    if kind == "uncertainty_floor":
        payload = {
            "complete": False,
            "facts": [],
            "uncertainties": [
                {
                    "id": "possible-access-boundary",
                    "relation_hint": "access_control_boundary",
                    "material": False,
                    "state": "AMBIGUOUS",
                    "reason": "scope relation is unresolved",
                    "provenance": provenance(),
                }
            ],
        }
        extractor = ModelAssistedExtractor(StaticProvider(payload), provider_name="scripted-eval-provider")
        ir = extractor.extract(request, context)
        observed_material = [u.get("material") for u in ir.get("uncertainties", [])]
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_REQUIRED
            and observed_material == [True]
        )
        return result(cid, passed, {"material": observed_material, "review_state": ir.get("review_state")}), None

    if kind == "materiality_floor":
        payload = access_payload("business group", material=False)
        payload["facts"] = payload["facts"][:1]
        extractor = ModelAssistedExtractor(StaticProvider(payload), provider_name="scripted-eval-provider")
        ir = extractor.extract(request, context)
        observed_material = [f.get("material") for f in ir.get("facts", [])]
        passed = (
            validate_semantic_ir(ir) == []
            and ir.get("review_state") == REVIEW_RESOLVED
            and observed_material == [True]
        )
        return result(cid, passed, {"material": observed_material}), None

    if kind == "provider_contract":
        provider = StaticProvider({"complete": True, "facts": [], "uncertainties": []})
        extractor = ModelAssistedExtractor(provider, provider_name="contract-eval-provider")
        ir = extractor.extract(request, context)
        contract = provider.last_contract or {}
        forbidden = set(contract.get("forbidden_policy_keys", []))
        output_keys = set(contract.get("output_keys", []))
        passed = (
            validate_semantic_ir(ir) == []
            and {"risk", "packs", "release_approval"}.issubset(forbidden)
            and output_keys == {"complete", "facts", "uncertainties"}
            and not ({"risk", "packs", "release_approval"} & output_keys)
        )
        return result(cid, passed, {"output_keys": sorted(output_keys), "forbidden_sample": sorted({"risk", "packs", "release_approval"} & forbidden)}), None

    if kind == "source_guard":
        source = EXTRACTOR_SOURCE.read_text(encoding="utf-8").lower()
        labels = ["department", "branch", "region", "division"]
        found = [label for label in labels if label in source]
        passed = not found
        return result(cid, passed, {"hard_coded_metamorphic_labels": found}), None

    return result(cid, False, {"error": f"unsupported control kind: {kind}"}), None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls", default=str(CONTROLS_PATH))
    parser.add_argument("--output")
    args = parser.parse_args()

    with Path(args.controls).open(encoding="utf-8") as handle:
        suite = json.load(handle)
    controls = suite.get("controls", [])
    results: list[dict[str, Any]] = []
    metamorphic: dict[str, set[str]] = {}
    for control in controls:
        observed, fact_kinds = run_control(control)
        results.append(observed)
        if control.get("kind") == "open_scope" and fact_kinds is not None:
            metamorphic[str(control["id"])] = fact_kinds

    graphs = {tuple(sorted(kinds)) for kinds in metamorphic.values()}
    metamorphic_pass = len(metamorphic) == 4 and len(graphs) == 1
    results.append(
        result(
            "S2-METAMORPHIC-SCOPE-GRAPH",
            metamorphic_pass,
            {key: sorted(value) for key, value in metamorphic.items()},
        )
    )

    counts = {
        "PASS": sum(item["status"] == "PASS" for item in results),
        "FAIL": sum(item["status"] == "FAIL" for item in results),
    }
    report = {
        "schema": "sef.eval.semantic-v2-s2-report.v1",
        "phase": "S2",
        "status": "PASS" if counts["FAIL"] == 0 else "FAIL",
        "counts": counts,
        "provider_boundary_validated": counts["FAIL"] == 0,
        "live_provider_quality_validated": False,
        "canonical_routing_changed": False,
        "policy_composer_implemented": False,
        "results": results,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
