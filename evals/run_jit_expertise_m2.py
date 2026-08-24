#!/usr/bin/env python3
"""Deterministic M2 qualification for SEF Just-In-Time Expertise contract."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jit_expertise import (  # noqa: E402
    CAPSULE_STATUSES,
    SOURCE_TIERS,
    SUBJECT_KINDS,
    JITExpertiseError,
    compile_capsule,
    evaluate_invalidation,
    project_context_digest,
    rank_sources,
    tool_snapshot_digest,
    validate_capsule,
)

REPORT_PATH = ROOT / "eval-results" / "jit-expertise-m2-report.json"
SCHEMA_PATH = ROOT / "jit_expertise" / "jit-expertise.schema.json"
T0 = "2026-08-24T18:00:00Z"
T1 = "2026-08-24T18:05:00Z"
T2 = "2026-08-24T18:10:00Z"
SOURCE_DIGEST = hashlib.sha256(b"official-provider-contract-v1").hexdigest()
SECONDARY_DIGEST = hashlib.sha256(b"secondary-note").hexdigest()


def _context(*, architecture: str = "ARCH-001", revision: int = 1) -> dict:
    return {
        "schema": "sef.project-state.context.v1",
        "project_id": "demo-project",
        "delivery_state": "ARCHITECTED",
        "domains": {
            "architecture": [
                {
                    "id": architecture,
                    "kind": "DECISION",
                    "statement": "Use one web application for the first delivery.",
                }
            ],
            "integrations": [],
        },
        "evidence": [],
        # Deliberately excluded from the M2 context digest by contract.
        "revision": revision,
        "content_sha256": "f" * 64,
    }


def _source(
    source_id: str = "SRC-OFFICIAL-001",
    *,
    tier: str = "OFFICIAL",
    status: str = "OBSERVED",
    observed_at: str = T0,
    max_age_seconds: int | None = 3600,
    digest: str | None = SOURCE_DIGEST,
    subject_version: str | None = "2026-08-24",
) -> dict:
    return {
        "id": source_id,
        "tier": tier,
        "uri": f"https://docs.example.test/{source_id.lower()}",
        "observed_at": observed_at,
        "max_age_seconds": max_age_seconds,
        "content_sha256": digest,
        "subject_version": subject_version,
        "status": status,
    }


def _tool(
    capability: str = "external_provider_sandbox",
    *,
    availability: str = "AVAILABLE",
    access: str = "WRITE",
    observed_at: str = T0,
) -> dict:
    return {
        "capability": capability,
        "availability": availability,
        "access": access,
        "observed_at": observed_at,
    }


def _constraint(
    source_ref: str = "SRC-OFFICIAL-001",
    *,
    materiality: str = "MATERIAL",
    statement: str = "Verify signed callbacks before accepting provider-originated state changes.",
) -> dict:
    return {
        "id": "CONSTRAINT-001",
        "statement": statement,
        "materiality": materiality,
        "supports": [
            {
                "source_ref": source_ref,
                "anchor": "Callback verification requirements",
            }
        ],
    }


def _verification(required_tools: list[str] | None = None, source_ref: str = "SRC-OFFICIAL-001") -> dict:
    return {
        "id": "VERIFY-001",
        "description": "Exercise the provider integration in an authorized non-production surface.",
        "required_tools": required_tools if required_tools is not None else ["external_provider_sandbox"],
        "supports": [
            {
                "source_ref": source_ref,
                "anchor": "Sandbox verification surface",
            }
        ],
    }


def _compile(
    *,
    context: dict | None = None,
    sources: list[dict] | None = None,
    constraints: list[dict] | None = None,
    tools: list[dict] | None = None,
    verification_paths: list[dict] | None = None,
    uncertainties: list[dict] | None = None,
    subject: dict | None = None,
    generated_at: str = T1,
) -> dict:
    return compile_capsule(
        capsule_id="CAPSULE-DEMO-001",
        project_id="demo-project",
        mission_need="Integrate the selected external provider safely for this project.",
        subject=subject
        or {
            "kind": "EXTERNAL_PROVIDER",
            "name": "Example Provider",
            "version_context": "current observed contract",
        },
        generated_at=generated_at,
        project_context=context or _context(),
        sources=sources if sources is not None else [_source()],
        constraints=constraints if constraints is not None else [_constraint()],
        tools=tools if tools is not None else [_tool()],
        verification_paths=verification_paths if verification_paths is not None else [_verification()],
        uncertainties=uncertainties or [],
    )


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except JITExpertiseError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected JITExpertiseError")


def control_schema_contract_alignment() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["schema"]["const"] == "sef.jit-expertise.v1"
    assert set(schema["properties"]["status"]["enum"]) == CAPSULE_STATUSES
    assert set(schema["$defs"]["subject"]["properties"]["kind"]["enum"]) == SUBJECT_KINDS
    assert list(SOURCE_TIERS) == ["REPOSITORY", "OFFICIAL", "TOOL_SCHEMA", "STANDARD", "SECONDARY"]
    return {"statuses": len(CAPSULE_STATUSES), "source_tiers": len(SOURCE_TIERS)}


def control_ready_capsule_is_project_bound_and_sealed() -> dict:
    context = _context()
    capsule = _compile(context=context)
    validate_capsule(capsule)
    assert capsule["status"] == "READY"
    assert capsule["project_context_sha256"] == project_context_digest(context)
    assert capsule["tool_snapshot_sha256"] == tool_snapshot_digest(capsule["tools"])
    assert capsule["content_sha256"] != "0" * 64
    return {"status": capsule["status"], "digest": capsule["content_sha256"]}


def control_authority_precedes_recency() -> dict:
    sources = [
        _source("SRC-SECONDARY", tier="SECONDARY", observed_at=T1, digest=SECONDARY_DIGEST),
        _source("SRC-TOOL", tier="TOOL_SCHEMA", observed_at=T0),
        _source("SRC-OFFICIAL", tier="OFFICIAL", observed_at=T0),
        _source("SRC-REPO", tier="REPOSITORY", observed_at=T0),
    ]
    ranked = rank_sources(sources)
    tiers = [item["tier"] for item in ranked]
    assert tiers == ["REPOSITORY", "OFFICIAL", "TOOL_SCHEMA", "SECONDARY"]
    return {"ranked_tiers": tiers}


def control_external_provider_requires_authoritative_surface() -> dict:
    secondary = _source("SRC-SECONDARY-001", tier="SECONDARY", digest=SECONDARY_DIGEST)
    capsule = _compile(
        sources=[secondary],
        constraints=[_constraint("SRC-SECONDARY-001", materiality="ADVISORY")],
        verification_paths=[_verification([], "SRC-SECONDARY-001")],
        tools=[],
    )
    assert capsule["status"] == "BLOCKED_SOURCE_GAP"
    return {"status": capsule["status"]}


def control_material_constraint_cannot_be_secondary_only() -> dict:
    secondary = _source("SRC-SECONDARY-001", tier="SECONDARY", digest=SECONDARY_DIGEST)
    message = _expect_error(
        lambda: _compile(
            sources=[secondary],
            constraints=[_constraint("SRC-SECONDARY-001", materiality="MATERIAL")],
            verification_paths=[],
            tools=[],
        ),
        "cannot rely only on secondary sources",
    )
    return {"rejected": message}


def control_unavailable_source_cannot_support_claim() -> dict:
    unavailable = _source(status="UNAVAILABLE", digest=None)
    message = _expect_error(
        lambda: _compile(sources=[unavailable]),
        "references unavailable source",
    )
    return {"rejected": message}


def control_required_tool_gap_blocks_capsule() -> dict:
    capsule = _compile(tools=[])
    assert capsule["status"] == "BLOCKED_TOOL_GAP"
    return {"status": capsule["status"]}


def control_unauthenticated_tool_gap_blocks_capsule() -> dict:
    capsule = _compile(tools=[_tool(availability="UNAUTHENTICATED", access="NONE")])
    assert capsule["status"] == "BLOCKED_TOOL_GAP"
    return {"status": capsule["status"]}


def control_only_blocking_uncertainty_requires_review() -> dict:
    nonblocking = _compile(
        uncertainties=[
            {
                "id": "UNCERT-001",
                "statement": "A non-material provider option remains unconfirmed.",
                "blocking": False,
                "source_refs": ["SRC-OFFICIAL-001"],
            }
        ]
    )
    blocking = _compile(
        uncertainties=[
            {
                "id": "UNCERT-002",
                "statement": "Production account ownership requires a user decision.",
                "blocking": True,
                "source_refs": ["SRC-OFFICIAL-001"],
            }
        ]
    )
    assert nonblocking["status"] == "READY"
    assert blocking["status"] == "REVIEW_REQUIRED"
    return {"nonblocking": nonblocking["status"], "blocking": blocking["status"]}


def control_source_expiry_invalidates_capsule() -> dict:
    capsule = _compile(sources=[_source(max_age_seconds=300)])
    reasons = evaluate_invalidation(
        capsule,
        now="2026-08-24T19:00:00Z",
        project_context=_context(),
        tools=[_tool()],
    )
    assert "SOURCE_EXPIRED:SRC-OFFICIAL-001" in reasons
    return {"reasons": reasons}


def control_source_content_change_invalidates_capsule() -> dict:
    capsule = _compile()
    reasons = evaluate_invalidation(
        capsule,
        now=T2,
        project_context=_context(),
        tools=[_tool()],
        current_source_digests={"SRC-OFFICIAL-001": "a" * 64},
    )
    assert "SOURCE_CHANGED:SRC-OFFICIAL-001" in reasons
    return {"reasons": reasons}


def control_project_context_change_invalidates_capsule() -> dict:
    capsule = _compile()
    changed = _context(architecture="ARCH-CHANGED")
    reasons = evaluate_invalidation(capsule, now=T2, project_context=changed, tools=[_tool()])
    assert reasons == ["PROJECT_CONTEXT_CHANGED"]
    return {"reasons": reasons}


def control_unrelated_state_metadata_does_not_invalidate() -> dict:
    original = _context(revision=1)
    capsule = _compile(context=original)
    replay = _context(revision=99)
    replay["content_sha256"] = "0" * 64
    assert project_context_digest(original) == project_context_digest(replay)
    reasons = evaluate_invalidation(capsule, now=T2, project_context=replay, tools=[_tool()])
    assert reasons == []
    return {"selective_context_stable": True}


def control_tool_capability_change_invalidates_capsule() -> dict:
    capsule = _compile()
    changed_tools = [_tool(access="READ")]
    reasons = evaluate_invalidation(capsule, now=T2, project_context=_context(), tools=changed_tools)
    assert reasons == ["TOOL_CAPABILITY_CHANGED"]
    return {"reasons": reasons}


def control_secret_shaped_values_are_rejected() -> dict:
    message = _expect_error(
        lambda: _compile(
            constraints=[
                _constraint(statement="Use api_key=sk-exampleSecretValue123456789 for the provider request.")
            ]
        ),
        "credential-shaped secret value",
    )
    return {"rejected": message}


def control_digest_detects_tampering() -> dict:
    capsule = _compile()
    tampered = copy.deepcopy(capsule)
    tampered["constraints"][0]["statement"] = "Tampered after sealing."
    message = _expect_error(lambda: validate_capsule(tampered), "digest mismatch")
    return {"rejected": message}


def control_project_id_mismatch_is_rejected() -> dict:
    context = _context()
    context["project_id"] = "other-project"
    message = _expect_error(lambda: _compile(context=context), "project_id does not match")
    return {"rejected": message}


def control_legacy_runtime_integrity() -> dict:
    expected = None
    for raw in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        parts = raw.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == "sef.py":
            expected = parts[0]
            break
    assert expected
    observed = hashlib.sha256((ROOT / "sef.py").read_bytes()).hexdigest()
    assert observed == expected
    return {"sef_sha256": observed}


CONTROLS = [
    ("M2-01-schema-contract", control_schema_contract_alignment),
    ("M2-02-ready-project-bound-capsule", control_ready_capsule_is_project_bound_and_sealed),
    ("M2-03-source-authority-order", control_authority_precedes_recency),
    ("M2-04-authoritative-provider-surface", control_external_provider_requires_authoritative_surface),
    ("M2-05-no-secondary-only-material-claim", control_material_constraint_cannot_be_secondary_only),
    ("M2-06-unavailable-source-support", control_unavailable_source_cannot_support_claim),
    ("M2-07-required-tool-gap", control_required_tool_gap_blocks_capsule),
    ("M2-08-unauthenticated-tool-gap", control_unauthenticated_tool_gap_blocks_capsule),
    ("M2-09-blocking-uncertainty-only", control_only_blocking_uncertainty_requires_review),
    ("M2-10-source-expiry", control_source_expiry_invalidates_capsule),
    ("M2-11-source-content-change", control_source_content_change_invalidates_capsule),
    ("M2-12-project-context-change", control_project_context_change_invalidates_capsule),
    ("M2-13-selective-context-stability", control_unrelated_state_metadata_does_not_invalidate),
    ("M2-14-tool-capability-change", control_tool_capability_change_invalidates_capsule),
    ("M2-15-secret-value-guard", control_secret_shaped_values_are_rejected),
    ("M2-16-digest-tamper", control_digest_detects_tampering),
    ("M2-17-project-binding", control_project_id_mismatch_is_rejected),
    ("M2-18-runtime-integrity", control_legacy_runtime_integrity),
]


def main() -> int:
    results = []
    for control_id, fn in CONTROLS:
        try:
            detail = fn()
            results.append({"id": control_id, "status": "PASS", "detail": detail})
        except Exception as exc:  # preserve all evidence instead of aborting early
            results.append({"id": control_id, "status": "FAIL", "detail": {"error": repr(exc)}})

    passed = sum(item["status"] == "PASS" for item in results)
    report = {
        "schema": "sef.eval.jit-expertise-m2.v1",
        "stage": "M2_JIT_EXPERTISE_CONTRACT",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "provider_calls": 0,
        "model_calls": 0,
        "network_calls": 0,
        "agent_outcome_claim": False,
        "semantic_source_entailment_claim": False,
        "user_question_reduction_claim": False,
        "runtime_mutation_expected": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
