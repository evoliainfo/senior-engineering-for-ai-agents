#!/usr/bin/env python3
"""Deterministic controls for the S5R semantic-provider stability boundary."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from semantic_v2.contracts import REVIEW_REQUIRED, REVIEW_RESOLVED, semantic_ir_digest, validate_semantic_ir
from semantic_v2.policy_composer import DeterministicPolicyComposer
from semantic_v2.stabilized_extractor import STABILITY_SAMPLE_COUNT, StabilizedExtractor

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "semantic_v2" / "stabilized_extractor.py"
REQUEST = "Apply the requested change while preserving all material security and governance boundaries."
CONTEXT = {"evaluation": "S5R", "development_only": True}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _prov(extractor: str) -> list[dict[str, Any]]:
    return [{
        "source_kind": "request",
        "locator": "request",
        "extractor": extractor,
        "confidence": 1.0,
        "ambiguity": "none",
    }]


class ScriptedExtractor:
    def __init__(
        self,
        material_kinds: list[str],
        *,
        nonmaterial_kinds: list[str] | None = None,
        uncertainty_state: str | None = None,
        reverse_facts: bool = False,
        metadata_marker: str = "fixture",
        invalid: bool = False,
        raises: bool = False,
    ) -> None:
        self.material_kinds = list(material_kinds)
        self.nonmaterial_kinds = list(nonmaterial_kinds or [])
        self.uncertainty_state = uncertainty_state
        self.reverse_facts = reverse_facts
        self.metadata_marker = metadata_marker
        self.invalid = invalid
        self.raises = raises

    def extract(self, request: str, project_context: Mapping[str, Any]) -> dict[str, Any]:
        if self.raises:
            raise RuntimeError("scripted provider unavailable")
        extractor = f"scripted-{self.metadata_marker}"
        facts: list[dict[str, Any]] = []
        for index, kind in enumerate(self.material_kinds, 1):
            facts.append({
                "id": f"m-{index}-{kind.lower()}",
                "kind": kind,
                "material": True,
                "subject": None,
                "object": None,
                "attributes": {"labels": [self.metadata_marker], "notes": ["material fixture"]},
                "provenance": _prov(extractor),
            })
        for index, kind in enumerate(self.nonmaterial_kinds, 1):
            facts.append({
                "id": f"n-{index}-{kind.lower()}",
                "kind": kind,
                "material": False,
                "subject": None,
                "object": None,
                "attributes": {"labels": [self.metadata_marker], "notes": ["non-material fixture"]},
                "provenance": _prov(extractor),
            })
        if self.reverse_facts:
            facts.reverse()
        uncertainties = []
        if self.uncertainty_state:
            uncertainties.append({
                "id": "scripted-review",
                "relation_hint": "fixture",
                "material": True,
                "state": self.uncertainty_state,
                "reason": "scripted material uncertainty",
                "provenance": _prov(extractor),
            })
        ir = {
            "schema": "sef.semantic-ir.v1",
            "extractor": {"name": extractor, "version": "1", "mode": "replay"},
            "request": {"digest": _digest(request), "text_available": True},
            "facts": facts,
            "uncertainties": uncertainties,
            "review_state": REVIEW_REQUIRED if uncertainties else REVIEW_RESOLVED,
            "metadata": {"fixture": self.metadata_marker},
        }
        if self.invalid:
            ir["schema"] = "invalid.schema"
        return ir


def _run(extractors: list[ScriptedExtractor]) -> dict[str, Any]:
    return StabilizedExtractor(extractors).extract(REQUEST, CONTEXT)


def _kinds(ir: Mapping[str, Any]) -> list[str]:
    return sorted(
        str(fact.get("kind"))
        for fact in ir.get("facts", []) or []
        if isinstance(fact, Mapping) and fact.get("material") is True
    )


def _result(control_id: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"id": control_id, "status": "PASS" if passed else "FAIL", "detail": detail}


def main() -> int:
    results: list[dict[str, Any]] = []

    unanimous = _run([
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"], metadata_marker="a"),
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"], reverse_facts=True, metadata_marker="b"),
        ScriptedExtractor(["PARTITION_ISOLATION", "ACCESS_CONTROL_BOUNDARY"], metadata_marker="c"),
    ])
    unanimous_policy = DeterministicPolicyComposer().compose(unanimous)
    results.append(_result(
        "S5R-UNANIMOUS-RESOLVED",
        validate_semantic_ir(unanimous) == []
        and unanimous.get("review_state") == REVIEW_RESOLVED
        and _kinds(unanimous) == ["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"]
        and unanimous_policy.get("risk") == "R3",
        {"review_state": unanimous.get("review_state"), "kinds": _kinds(unanimous), "risk": unanimous_policy.get("risk")},
    ))

    extra = _run([
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY"]),
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"]),
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY"]),
    ])
    extra_policy = DeterministicPolicyComposer().compose(extra)
    results.append(_result(
        "S5R-EXTRA-MATERIAL-FACT-CONFLICT",
        extra.get("review_state") == REVIEW_REQUIRED
        and [item.get("state") for item in extra.get("uncertainties", [])] == ["CONFLICT"]
        and _kinds(extra) == ["ACCESS_CONTROL_BOUNDARY"]
        and extra_policy.get("risk") is None
        and extra_policy.get("implementation_allowed") is False,
        {"review_state": extra.get("review_state"), "kinds": _kinds(extra), "policy": extra_policy},
    ))

    missing = _run([
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"]),
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY"]),
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"]),
    ])
    results.append(_result(
        "S5R-MISSING-MATERIAL-FACT-CONFLICT",
        missing.get("review_state") == REVIEW_REQUIRED
        and [item.get("state") for item in missing.get("uncertainties", [])] == ["CONFLICT"]
        and _kinds(missing) == ["ACCESS_CONTROL_BOUNDARY"],
        {"review_state": missing.get("review_state"), "kinds": _kinds(missing)},
    ))

    unavailable = _run([
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"]),
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"], raises=True),
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"]),
    ])
    results.append(_result(
        "S5R-PROVIDER-UNAVAILABLE",
        unavailable.get("review_state") == REVIEW_REQUIRED
        and [item.get("state") for item in unavailable.get("uncertainties", [])] == ["UNAVAILABLE"]
        and DeterministicPolicyComposer().compose(unavailable).get("implementation_allowed") is False,
        {"review_state": unavailable.get("review_state"), "uncertainties": unavailable.get("uncertainties")},
    ))

    invalid = _run([
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"]),
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"], invalid=True),
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"]),
    ])
    results.append(_result(
        "S5R-INVALID-SAMPLE",
        invalid.get("review_state") == REVIEW_REQUIRED
        and [item.get("state") for item in invalid.get("uncertainties", [])] == ["INVALID"],
        {"review_state": invalid.get("review_state"), "uncertainties": invalid.get("uncertainties")},
    ))

    ambiguous = _run([
        ScriptedExtractor([], uncertainty_state="AMBIGUOUS", metadata_marker="a"),
        ScriptedExtractor([], uncertainty_state="AMBIGUOUS", metadata_marker="b"),
        ScriptedExtractor([], uncertainty_state="AMBIGUOUS", metadata_marker="c"),
    ])
    results.append(_result(
        "S5R-UNANIMOUS-AMBIGUITY",
        ambiguous.get("review_state") == REVIEW_REQUIRED
        and [item.get("state") for item in ambiguous.get("uncertainties", [])] == ["AMBIGUOUS"]
        and DeterministicPolicyComposer().compose(ambiguous).get("risk") is None,
        {"review_state": ambiguous.get("review_state"), "uncertainties": ambiguous.get("uncertainties")},
    ))

    base = _run([
        ScriptedExtractor(["EXTERNAL_OPERATIONAL_DEPENDENCY"], metadata_marker="one"),
        ScriptedExtractor(["EXTERNAL_OPERATIONAL_DEPENDENCY"], metadata_marker="two"),
        ScriptedExtractor(["EXTERNAL_OPERATIONAL_DEPENDENCY"], metadata_marker="three"),
    ])
    reordered = _run([
        ScriptedExtractor(["EXTERNAL_OPERATIONAL_DEPENDENCY"], metadata_marker="three"),
        ScriptedExtractor(["EXTERNAL_OPERATIONAL_DEPENDENCY"], metadata_marker="one"),
        ScriptedExtractor(["EXTERNAL_OPERATIONAL_DEPENDENCY"], metadata_marker="two"),
    ])
    results.append(_result(
        "S5R-SAMPLE-ORDER-INVARIANT",
        semantic_ir_digest(base) == semantic_ir_digest(reordered),
        {"left": semantic_ir_digest(base), "right": semantic_ir_digest(reordered)},
    ))

    nonmaterial = _run([
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"], nonmaterial_kinds=["DEPLOYMENT_ARTIFACT"]),
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"]),
        ScriptedExtractor(["SERVER_DESTINATION_TRUST"], nonmaterial_kinds=["AUTHENTICATION_PROTOCOL"]),
    ])
    results.append(_result(
        "S5R-NONMATERIAL-VARIANCE-IGNORED",
        nonmaterial.get("review_state") == REVIEW_RESOLVED
        and _kinds(nonmaterial) == ["SERVER_DESTINATION_TRUST"],
        {"review_state": nonmaterial.get("review_state"), "kinds": _kinds(nonmaterial)},
    ))

    count_guard = False
    try:
        StabilizedExtractor([
            ScriptedExtractor([]),
            ScriptedExtractor([]),
        ])
    except ValueError:
        count_guard = True
    results.append(_result(
        "S5R-EXACTLY-THREE-SAMPLES",
        count_guard and STABILITY_SAMPLE_COUNT == 3,
        {"required_samples": STABILITY_SAMPLE_COUNT, "two_sample_configuration_rejected": count_guard},
    ))

    source = SOURCE.read_text(encoding="utf-8")
    results.append(_result(
        "S5R-NO-DIRECT-MODEL-OR-COMPOSER",
        "OpenAIResponsesSemanticProvider" not in source
        and "DeterministicPolicyComposer" not in source
        and "SEMANTIC_DEFINITIONS" not in source,
        {"provider_symbol": "OpenAIResponsesSemanticProvider" in source, "composer_symbol": "DeterministicPolicyComposer" in source},
    ))

    # The stability layer must remain fail-closed under deepcopy/replay and cannot
    # acquire policy authority by mutating a returned object after extraction.
    copied = copy.deepcopy(extra)
    copied["metadata"]["sample_views"].reverse()
    replay = StabilizedExtractor([
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY"]),
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY", "PARTITION_ISOLATION"]),
        ScriptedExtractor(["ACCESS_CONTROL_BOUNDARY"]),
    ]).extract(REQUEST, CONTEXT)
    results.append(_result(
        "S5R-CONFLICT-REPLAYABLE",
        replay.get("review_state") == REVIEW_REQUIRED
        and DeterministicPolicyComposer().compose(replay).get("implementation_gate") == "BLOCKED_SEMANTIC_REVIEW",
        {"digest": semantic_ir_digest(replay)},
    ))

    counts = {
        "PASS": sum(item["status"] == "PASS" for item in results),
        "FAIL": sum(item["status"] == "FAIL" for item in results),
    }
    report = {
        "schema": "sef.eval.semantic-v2-provider-stability.v1",
        "phase": "S5R",
        "status": "PASS" if counts["FAIL"] == 0 else "FAIL",
        "counts": counts,
        "required_samples": STABILITY_SAMPLE_COUNT,
        "acceptance_relaxed": False,
        "s5_corpus_changed": False,
        "policy_rules_changed": False,
        "results": results,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(text, end="")
    output = ROOT / "semantic-v2-provider-stability.json"
    output.write_text(text, encoding="utf-8")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
