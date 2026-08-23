#!/usr/bin/env python3
"""Acceptance runner for Semantic Routing v2 S0 contracts and S1 shadow bridge."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from semantic_v2.bridge_v15 import shadow_bridge
from semantic_v2.contracts import (
    SEMANTIC_IR_SCHEMA,
    semantic_ir_digest,
    validate_semantic_ir,
)

ROOT = Path(__file__).resolve().parent.parent
CONTROLS = ROOT / "evals" / "semantic_v2" / "s0_s1_controls.json"


def _prov() -> list[dict[str, Any]]:
    return [{
        "source_kind": "request",
        "locator": "request:0-20",
        "extractor": "contract-test",
        "confidence": 1.0,
        "ambiguity": "none",
    }]


def _valid_ir() -> dict[str, Any]:
    return {
        "schema": SEMANTIC_IR_SCHEMA,
        "extractor": {"name": "contract-test", "version": "1", "mode": "replay"},
        "request": {"digest": hashlib.sha256(b"sample").hexdigest(), "text_available": True},
        "facts": [{
            "id": "fact-1",
            "kind": "ACCESS_CONTROL_BOUNDARY",
            "material": True,
            "subject": "actor",
            "object": "resource",
            "attributes": {"scope_label": "arbitrary-open-vocabulary-label"},
            "provenance": _prov(),
        }],
        "uncertainties": [],
        "review_state": "RESOLVED",
        "metadata": {"phase": "S0"},
    }


def _record(results: list[dict[str, Any]], cid: str, passed: bool, detail: Any) -> None:
    results.append({"id": cid, "status": "PASS" if passed else "FAIL", "detail": detail})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="semantic-v2-s0-s1.json")
    args = parser.parse_args()

    results: list[dict[str, Any]] = []

    # S0: valid typed IR.
    base = _valid_ir()
    errors = validate_semantic_ir(base)
    _record(results, "S0-VALID-001", not errors, errors)

    # S0: material unresolved semantics must require explicit review.
    review = copy.deepcopy(base)
    review["uncertainties"] = [{
        "id": "u-1",
        "relation_hint": "access boundary",
        "material": True,
        "state": "AMBIGUOUS",
        "reason": "scope relation cannot be resolved",
        "provenance": _prov(),
    }]
    review["review_state"] = "SEMANTIC_REVIEW_REQUIRED"
    errors = validate_semantic_ir(review)
    _record(results, "S0-REVIEW-001", not errors, errors)

    wrong_review = copy.deepcopy(review)
    wrong_review["review_state"] = "RESOLVED"
    errors = validate_semantic_ir(wrong_review)
    _record(results, "S0-REVIEW-NEG-001", any("SEMANTIC_REVIEW_REQUIRED" in e for e in errors), errors)

    # S0: extractor output may not smuggle policy authority.
    forbidden = copy.deepcopy(base)
    forbidden["metadata"]["risk"] = "R1"
    errors = validate_semantic_ir(forbidden)
    _record(results, "S0-NO-POLICY-AUTHORITY-001", any("policy-authority field forbidden" in e for e in errors), errors)

    # S0: provenance is mandatory.
    no_prov = copy.deepcopy(base)
    no_prov["facts"][0]["provenance"] = []
    errors = validate_semantic_ir(no_prov)
    _record(results, "S0-PROVENANCE-001", any("provenance" in e for e in errors), errors)

    # S0: duplicate fact IDs are invalid.
    duplicate = copy.deepcopy(base)
    duplicate["facts"].append(copy.deepcopy(duplicate["facts"][0]))
    errors = validate_semantic_ir(duplicate)
    _record(results, "S0-IDENTITY-001", any("duplicate fact id" in e for e in errors), errors)

    # S1: audited bridge cases.
    catalog = json.loads(CONTROLS.read_text(encoding="utf-8"))
    if catalog.get("schema") != "sef.eval.semantic-v2-s0-s1.v1":
        _record(results, "S1-CATALOG", False, "unexpected control schema")
    else:
        for control in catalog.get("controls", []):
            cid = str(control["id"])
            assessment = copy.deepcopy(control["assessment"])
            before = copy.deepcopy(assessment)
            first = shadow_bridge(assessment, request_text=f"request for {cid}", source_id=cid)
            second = shadow_bridge(assessment, request_text=f"request for {cid}", source_id=cid)
            ir = first["semantic_ir"]
            errors = validate_semantic_ir(ir)
            kinds = sorted(f["kind"] for f in ir["facts"])
            expected = sorted(control.get("expected_fact_kinds", []))
            expected_unmapped = sorted(control.get("expected_unmapped", []))
            unmapped = sorted(ir.get("metadata", {}).get("unmapped_legacy_signals", []))
            policy_keys = {"packs", "risk", "procedures", "implementation_allowed", "release_eligible"}
            serialized_ir = json.dumps(ir, sort_keys=True)
            leaked_policy_key = any(f'"{key}"' in serialized_ir for key in policy_keys)
            passed = all([
                not errors,
                assessment == before,
                first["canonical_output"] == before,
                first["canonical_output_changed"] is False,
                kinds == expected,
                unmapped == expected_unmapped,
                first["semantic_ir_digest"] == second["semantic_ir_digest"] == semantic_ir_digest(ir),
                not leaked_policy_key,
                ir.get("metadata", {}).get("mode") == "SHADOW_ONLY",
                ir.get("metadata", {}).get("open_vocabulary_claim") is False,
            ])
            _record(results, cid, passed, {
                "validation_errors": errors,
                "observed_fact_kinds": kinds,
                "expected_fact_kinds": expected,
                "unmapped": unmapped,
                "digest": first["semantic_ir_digest"],
                "canonical_preserved": first["canonical_output"] == before,
                "policy_authority_leaked": leaked_policy_key,
            })

    counts: dict[str, int] = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    status = "PASS" if counts == {"PASS": len(results)} else "FAIL"
    report = {
        "schema": "sef.eval.semantic-v2-s0-s1-report.v1",
        "status": status,
        "phase": "S0_S1",
        "canonical_routing_changed": False,
        "open_vocabulary_extractor_implemented": False,
        "policy_composer_implemented": False,
        "counts": counts,
        "results": results,
    }
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
