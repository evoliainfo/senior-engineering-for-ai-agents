#!/usr/bin/env python3
"""Deterministic M1 qualification for SEF Project State Spine."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from project_state import (  # noqa: E402
    DELIVERY_STATES,
    DOMAINS,
    ProjectStateError,
    add_entry,
    add_evidence,
    advance_delivery_state,
    canonical_digest,
    new_state,
    regress_delivery_state,
    seal_state,
    select_context,
    validate_state,
    write_state,
)

REPORT_PATH = ROOT / "eval-results" / "project-state-m1-report.json"
SCHEMA_PATH = ROOT / "project_state" / "project-state.schema.json"
T0 = "2026-08-24T14:00:00Z"
T1 = "2026-08-24T14:01:00Z"
T2 = "2026-08-24T14:02:00Z"
T3 = "2026-08-24T14:03:00Z"
T4 = "2026-08-24T14:04:00Z"


def _base_state() -> dict:
    return new_state(
        project_id="demo-project",
        product_statement="Deliver a useful web product slice for the target user.",
        evidence_locator="conversation://product-frame/1",
        at=T0,
    )


def _expect_error(fn, contains: str | None = None) -> str:
    try:
        fn()
    except ProjectStateError as exc:
        message = str(exc)
        if contains and contains not in message:
            raise AssertionError(f"expected {contains!r} in {message!r}") from exc
        return message
    raise AssertionError("expected ProjectStateError")


def control_schema_contract_alignment() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    enum = schema["properties"]["delivery_state"]["enum"]
    domains = schema["$defs"]["domains"]["required"]
    assert tuple(enum) == DELIVERY_STATES
    assert tuple(domains) == DOMAINS
    assert schema["properties"]["schema"]["const"] == "sef.project-state.v1"
    return {"delivery_states": len(enum), "domains": len(domains)}


def control_minimal_state_is_evidence_backed() -> dict:
    state = _base_state()
    validate_state(state)
    assert state["delivery_state"] == "FRAMED"
    assert state["transitions"][0]["evidence_refs"] == ["EVID-FRAME-001"]
    assert state["domains"]["product"][0]["kind"] == "FACT"
    assert state["content_sha256"] == canonical_digest(state)
    return {"revision": state["revision"], "digest": state["content_sha256"]}


def control_typed_fact_requires_real_evidence() -> dict:
    state = _base_state()
    state = add_evidence(
        state,
        evidence_id="EVID-REQ-001",
        kind="acceptance-contract",
        locator="repo://docs/acceptance.md",
        observed_at=T1,
    )
    state = add_entry(
        state,
        domain="requirements",
        entry_id="REQ-001",
        kind="FACT",
        statement="The critical journey has an observable acceptance contract.",
        authority="REPOSITORY",
        evidence_refs=["EVID-REQ-001"],
        updated_at=T2,
    )
    assert state["domains"]["requirements"][0]["evidence_refs"] == ["EVID-REQ-001"]
    message = _expect_error(
        lambda: add_entry(
            state,
            domain="requirements",
            entry_id="REQ-002",
            kind="FACT",
            statement="An unsupported fact must not enter project truth.",
            authority="ENGINEERING",
            evidence_refs=[],
            updated_at=T3,
        ),
        "FACT requires evidence",
    )
    return {"supported_fact": True, "unsupported_rejected": message}


def control_assumptions_remain_explicit() -> dict:
    state = add_entry(
        _base_state(),
        domain="architecture",
        entry_id="ASSUME-001",
        kind="ASSUMPTION",
        statement="A single deployable service is assumed sufficient until scale evidence disagrees.",
        authority="ENGINEERING",
        evidence_refs=[],
        updated_at=T1,
    )
    entry = state["domains"]["architecture"][0]
    assert entry["kind"] == "ASSUMPTION"
    assert entry["evidence_refs"] == []
    return {"assumption_without_fake_evidence": True}


def control_broken_evidence_reference_fails() -> dict:
    state = _base_state()
    message = _expect_error(
        lambda: add_entry(
            state,
            domain="quality",
            entry_id="QUALITY-001",
            kind="FACT",
            statement="Tests passed.",
            authority="SYSTEM",
            evidence_refs=["EVID-MISSING"],
            updated_at=T1,
        ),
        "unknown evidence",
    )
    return {"rejected": message}


def control_digest_detects_tampering() -> dict:
    state = _base_state()
    tampered = copy.deepcopy(state)
    tampered["domains"]["product"][0]["statement"] = "Tampered after sealing"
    message = _expect_error(lambda: validate_state(tampered), "digest mismatch")
    return {"rejected": message}


def control_secret_shaped_values_are_rejected() -> dict:
    secret_value = "sk-exampleSecretValue123456789"
    message = _expect_error(
        lambda: new_state(
            project_id="secret-demo",
            product_statement=f"Temporary api_key={secret_value}",
            evidence_locator="conversation://unsafe/1",
            at=T0,
        ),
        "secret value",
    )
    return {"rejected": message}


def control_advance_requires_correct_evidence_kind() -> dict:
    state = _base_state()
    wrong = add_evidence(
        state,
        evidence_id="EVID-WRONG-001",
        kind="local-verification",
        locator="artifact://local-test",
        observed_at=T1,
    )
    message = _expect_error(
        lambda: advance_delivery_state(
            wrong,
            to_state="ARCHITECTED",
            evidence_refs=["EVID-WRONG-001"],
            at=T2,
            reason="Architecture was allegedly decided.",
        ),
        "architecture-decision",
    )
    correct = add_evidence(
        state,
        evidence_id="EVID-ARCH-001",
        kind="architecture-decision",
        locator="repo://docs/architecture.md",
        observed_at=T1,
    )
    advanced = advance_delivery_state(
        correct,
        to_state="ARCHITECTED",
        evidence_refs=["EVID-ARCH-001"],
        at=T2,
        reason="Architecture decision is recorded in repository evidence.",
    )
    assert advanced["delivery_state"] == "ARCHITECTED"
    return {"wrong_kind_rejected": message, "correct_kind_advanced": True}


def control_delivery_state_cannot_be_skipped() -> dict:
    state = _base_state()
    state = add_evidence(
        state,
        evidence_id="EVID-IMPL-001",
        kind="implementation-change",
        locator="git://commit/abc123",
        observed_at=T1,
    )
    message = _expect_error(
        lambda: advance_delivery_state(
            state,
            to_state="IMPLEMENTED",
            evidence_refs=["EVID-IMPL-001"],
            at=T2,
            reason="Skip architecture.",
        ),
        "must be ARCHITECTED",
    )
    return {"rejected": message}


def _implemented_state() -> dict:
    state = _base_state()
    state = add_evidence(
        state,
        evidence_id="EVID-ARCH-001",
        kind="architecture-decision",
        locator="repo://docs/architecture.md",
        observed_at=T1,
    )
    state = advance_delivery_state(
        state,
        to_state="ARCHITECTED",
        evidence_refs=["EVID-ARCH-001"],
        at=T2,
        reason="Architecture is evidence-backed.",
    )
    state = add_evidence(
        state,
        evidence_id="EVID-IMPL-001",
        kind="implementation-change",
        locator="git://commit/abc123",
        observed_at=T3,
    )
    return advance_delivery_state(
        state,
        to_state="IMPLEMENTED",
        evidence_refs=["EVID-IMPL-001"],
        at=T4,
        reason="Implementation change exists.",
    )


def control_regression_lowers_delivery_truth() -> dict:
    state = _implemented_state()
    state = add_evidence(
        state,
        evidence_id="EVID-REGRESS-001",
        kind="runtime-regression",
        locator="ci://run/failed-after-rebase",
        observed_at="2026-08-24T14:05:00Z",
    )
    regressed = regress_delivery_state(
        state,
        to_state="FRAMED",
        evidence_refs=["EVID-REGRESS-001"],
        at="2026-08-24T14:06:00Z",
        reason="Architecture and implementation claims are stale after a material reset.",
    )
    assert regressed["delivery_state"] == "FRAMED"
    assert regressed["transitions"][-1]["kind"] == "REGRESS"
    return {"from": "IMPLEMENTED", "to": regressed["delivery_state"]}


def control_invalidated_evidence_cannot_promote() -> dict:
    state = add_evidence(
        _base_state(),
        evidence_id="EVID-ARCH-STALE",
        kind="architecture-decision",
        locator="repo://docs/stale-architecture.md",
        observed_at=T1,
        status="INVALIDATED",
    )
    message = _expect_error(
        lambda: advance_delivery_state(
            state,
            to_state="ARCHITECTED",
            evidence_refs=["EVID-ARCH-STALE"],
            at=T2,
            reason="Stale architecture must not promote state.",
        ),
        "invalidated evidence",
    )
    return {"rejected": message}


def control_selective_context_excludes_unrelated_history() -> dict:
    state = _base_state()
    state = add_evidence(
        state,
        evidence_id="EVID-ARCH-001",
        kind="architecture-decision",
        locator="repo://docs/architecture.md",
        observed_at=T1,
    )
    state = add_entry(
        state,
        domain="architecture",
        entry_id="ARCH-001",
        kind="DECISION",
        statement="Use one deployable application for the first delivery.",
        authority="ENGINEERING",
        evidence_refs=["EVID-ARCH-001"],
        updated_at=T2,
    )
    context = select_context(state, ["architecture"])
    assert list(context["domains"]) == ["architecture"]
    assert [item["id"] for item in context["evidence"]] == ["EVID-ARCH-001"]
    assert "EVID-FRAME-001" not in json.dumps(context)
    return {"domains_loaded": 1, "evidence_loaded": 1}


def control_fresh_session_roundtrip() -> dict:
    state = _implemented_state()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "project-state.json"
        write_state(path, state)
        before = path.read_bytes()
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "project_state.py"), "validate", str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        payload = json.loads(result.stdout)
        assert payload["status"] == "PASS"
        assert payload["content_sha256"] == state["content_sha256"]
        after = path.read_bytes()
        assert before == after, "fresh-session validation must not mutate state"
    return {"fresh_process": True, "digest_preserved": True}


def control_canonical_digest_is_order_stable() -> dict:
    state = _base_state()
    reordered = {key: state[key] for key in reversed(list(state.keys()))}
    assert canonical_digest(reordered) == canonical_digest(state)
    assert seal_state(reordered)["content_sha256"] == state["content_sha256"]
    return {"digest": state["content_sha256"]}


def control_domain_contract_is_closed() -> dict:
    state = _base_state()
    broken = copy.deepcopy(state)
    broken["domains"].pop("observability")
    broken = seal_state(broken)
    message = _expect_error(lambda: validate_state(broken), "domains must match schema")
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
    ("M1-01-schema-contract", control_schema_contract_alignment),
    ("M1-02-minimal-evidence-state", control_minimal_state_is_evidence_backed),
    ("M1-03-typed-fact-evidence", control_typed_fact_requires_real_evidence),
    ("M1-04-explicit-assumption", control_assumptions_remain_explicit),
    ("M1-05-broken-evidence-ref", control_broken_evidence_reference_fails),
    ("M1-06-digest-tamper", control_digest_detects_tampering),
    ("M1-07-secret-value-guard", control_secret_shaped_values_are_rejected),
    ("M1-08-transition-evidence-kind", control_advance_requires_correct_evidence_kind),
    ("M1-09-no-state-skip", control_delivery_state_cannot_be_skipped),
    ("M1-10-regression-truth", control_regression_lowers_delivery_truth),
    ("M1-11-invalidated-evidence", control_invalidated_evidence_cannot_promote),
    ("M1-12-selective-context", control_selective_context_excludes_unrelated_history),
    ("M1-13-fresh-session-roundtrip", control_fresh_session_roundtrip),
    ("M1-14-canonical-order", control_canonical_digest_is_order_stable),
    ("M1-15-closed-domain-contract", control_domain_contract_is_closed),
    ("M1-16-runtime-integrity", control_legacy_runtime_integrity),
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
        "schema": "sef.eval.project-state-m1.v1",
        "stage": "M1_PROJECT_STATE_SPINE",
        "status": "PASS" if passed == len(results) else "FAIL",
        "control_count": len(results),
        "pass_count": passed,
        "fail_count": len(results) - passed,
        "provider_calls": 0,
        "agent_outcome_claim": False,
        "independent_holdout_claim": False,
        "runtime_mutation_expected": False,
        "results": results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
