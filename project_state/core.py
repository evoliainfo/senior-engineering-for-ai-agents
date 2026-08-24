"""Deterministic Project State Spine for SEF.

The state layer is deliberately provider-neutral and standard-library only. It
stores compact engineering continuity, references evidence instead of copying
logs, and refuses delivery-state promotion without the evidence kind required
for that transition.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCHEMA_ID = "sef.project-state.v1"

DOMAINS = (
    "product",
    "requirements",
    "architecture",
    "interfaces",
    "data",
    "identity_access",
    "integrations",
    "environments",
    "quality",
    "security",
    "release",
    "deployments",
    "observability",
    "open_decisions",
    "known_risks",
)

DELIVERY_STATES = (
    "FRAMED",
    "ARCHITECTED",
    "IMPLEMENTED",
    "VERIFIED_LOCAL",
    "PREVIEW_VERIFIED",
    "RELEASE_READY",
    "DEPLOYED",
    "POST_DEPLOY_VERIFIED",
)

EVIDENCE_KIND_FOR_STATE = {
    "FRAMED": "product-frame",
    "ARCHITECTED": "architecture-decision",
    "IMPLEMENTED": "implementation-change",
    "VERIFIED_LOCAL": "local-verification",
    "PREVIEW_VERIFIED": "preview-verification",
    "RELEASE_READY": "release-readiness",
    "DEPLOYED": "deployment",
    "POST_DEPLOY_VERIFIED": "post-deploy-verification",
}

ENTRY_KINDS = {"FACT", "DECISION", "ASSUMPTION", "UNRESOLVED"}
AUTHORITIES = {"USER", "REPOSITORY", "ENGINEERING", "EXTERNAL", "SYSTEM"}
ENTRY_STATUSES = {"ACTIVE", "RESOLVED", "SUPERSEDED"}
EVIDENCE_STATUSES = {"OBSERVED", "INVALIDATED"}
TRANSITION_KINDS = {"ADVANCE", "REGRESS"}

PROJECT_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

# These patterns intentionally target credential-shaped values, not ordinary
# discussion of secrets/configuration. The state can say that a secret is
# required; it must never contain the secret value itself.
SECRET_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(
        r"(?i)\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*[^\s,;]{8,}"
    ),
)

TOP_LEVEL_KEYS = {
    "schema",
    "project_id",
    "revision",
    "delivery_state",
    "updated_at",
    "domains",
    "evidence",
    "transitions",
    "content_sha256",
}
ENTRY_KEYS = {"id", "kind", "statement", "authority", "status", "evidence_refs", "updated_at"}
EVIDENCE_KEYS = {"id", "kind", "locator", "observed_at", "status", "sha256"}
TRANSITION_KEYS = {"id", "kind", "from_state", "to_state", "at", "evidence_refs", "reason"}


class ProjectStateError(ValueError):
    """Raised when Project State Spine integrity or semantics are invalid."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _parse_timestamp(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ProjectStateError(f"{label} must be a non-empty ISO-8601 timestamp")
    normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ProjectStateError(f"{label} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ProjectStateError(f"{label} must include a timezone")


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing:
        raise ProjectStateError(f"{label} missing keys: {', '.join(sorted(missing))}")
    if unknown:
        raise ProjectStateError(f"{label} unknown keys: {', '.join(sorted(unknown))}")


def _require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ITEM_ID_RE.fullmatch(value):
        raise ProjectStateError(f"{label} must be a compact stable identifier")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectStateError(f"{label} must be a non-empty string")
    return value


def _require_unique_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ProjectStateError(f"{label} must be a list of non-empty strings")
    if len(value) != len(set(value)):
        raise ProjectStateError(f"{label} must not contain duplicates")
    return value


def _scan_secret_values(value: Any, path: str = "state") -> None:
    if isinstance(value, str):
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(value):
                raise ProjectStateError(f"credential-shaped secret value detected at {path}")
    elif isinstance(value, dict):
        for key, child in value.items():
            _scan_secret_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_secret_values(child, f"{path}[{index}]")


def canonical_digest(state: dict[str, Any]) -> str:
    """Return a stable digest over state content, excluding its digest field."""
    payload = copy.deepcopy(state)
    payload.pop("content_sha256", None)
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def seal_state(state: dict[str, Any]) -> dict[str, Any]:
    """Deep-copy state and attach its canonical integrity digest."""
    sealed = copy.deepcopy(state)
    sealed["content_sha256"] = canonical_digest(sealed)
    return sealed


def _validate_evidence(evidence: list[Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(evidence, list):
        raise ProjectStateError("evidence must be a list")
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(evidence):
        label = f"evidence[{index}]"
        if not isinstance(item, dict):
            raise ProjectStateError(f"{label} must be an object")
        _require_exact_keys(item, EVIDENCE_KEYS, label)
        evidence_id = _require_id(item["id"], f"{label}.id")
        if evidence_id in by_id:
            raise ProjectStateError(f"duplicate evidence id: {evidence_id}")
        if not isinstance(item["kind"], str) or not KEBAB_RE.fullmatch(item["kind"]):
            raise ProjectStateError(f"{label}.kind must be lowercase kebab-case")
        _require_string(item["locator"], f"{label}.locator")
        _parse_timestamp(item["observed_at"], f"{label}.observed_at")
        if item["status"] not in EVIDENCE_STATUSES:
            raise ProjectStateError(f"{label}.status is invalid")
        if item["sha256"] is not None and (
            not isinstance(item["sha256"], str) or not SHA256_RE.fullmatch(item["sha256"])
        ):
            raise ProjectStateError(f"{label}.sha256 must be null or a lowercase SHA-256")
        by_id[evidence_id] = item
    return by_id


def _validate_entries(domains: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]) -> set[str]:
    if not isinstance(domains, dict):
        raise ProjectStateError("domains must be an object")
    if set(domains) != set(DOMAINS):
        missing = set(DOMAINS) - set(domains)
        unknown = set(domains) - set(DOMAINS)
        raise ProjectStateError(
            f"domains must match schema; missing={sorted(missing)} unknown={sorted(unknown)}"
        )

    entry_ids: set[str] = set()
    for domain in DOMAINS:
        entries = domains[domain]
        if not isinstance(entries, list):
            raise ProjectStateError(f"domains.{domain} must be a list")
        for index, entry in enumerate(entries):
            label = f"domains.{domain}[{index}]"
            if not isinstance(entry, dict):
                raise ProjectStateError(f"{label} must be an object")
            _require_exact_keys(entry, ENTRY_KEYS, label)
            entry_id = _require_id(entry["id"], f"{label}.id")
            if entry_id in entry_ids:
                raise ProjectStateError(f"duplicate state entry id: {entry_id}")
            entry_ids.add(entry_id)
            if entry["kind"] not in ENTRY_KINDS:
                raise ProjectStateError(f"{label}.kind is invalid")
            _require_string(entry["statement"], f"{label}.statement")
            if entry["authority"] not in AUTHORITIES:
                raise ProjectStateError(f"{label}.authority is invalid")
            if entry["status"] not in ENTRY_STATUSES:
                raise ProjectStateError(f"{label}.status is invalid")
            refs = _require_unique_string_list(entry["evidence_refs"], f"{label}.evidence_refs")
            _parse_timestamp(entry["updated_at"], f"{label}.updated_at")
            missing_refs = [ref for ref in refs if ref not in evidence_by_id]
            if missing_refs:
                raise ProjectStateError(f"{label} references unknown evidence: {missing_refs}")
            if entry["kind"] in {"FACT", "DECISION"} and not refs:
                raise ProjectStateError(f"{label} {entry['kind']} requires evidence")
            if entry["kind"] == "UNRESOLVED" and entry["status"] != "ACTIVE":
                raise ProjectStateError(f"{label} UNRESOLVED entry must remain ACTIVE")
            if domain == "open_decisions" and entry["kind"] not in {"UNRESOLVED", "DECISION"}:
                raise ProjectStateError(f"{label} must be UNRESOLVED or DECISION")
    return entry_ids


def _validate_transitions(
    transitions: list[Any],
    delivery_state: str,
    evidence_by_id: dict[str, dict[str, Any]],
) -> None:
    if not isinstance(transitions, list) or not transitions:
        raise ProjectStateError("transitions must be a non-empty list")
    transition_ids: set[str] = set()
    previous_to: str | None = None
    for index, transition in enumerate(transitions):
        label = f"transitions[{index}]"
        if not isinstance(transition, dict):
            raise ProjectStateError(f"{label} must be an object")
        _require_exact_keys(transition, TRANSITION_KEYS, label)
        transition_id = _require_id(transition["id"], f"{label}.id")
        if transition_id in transition_ids:
            raise ProjectStateError(f"duplicate transition id: {transition_id}")
        transition_ids.add(transition_id)
        if transition["kind"] not in TRANSITION_KINDS:
            raise ProjectStateError(f"{label}.kind is invalid")
        from_state = transition["from_state"]
        to_state = transition["to_state"]
        if from_state is not None and from_state not in DELIVERY_STATES:
            raise ProjectStateError(f"{label}.from_state is invalid")
        if to_state not in DELIVERY_STATES:
            raise ProjectStateError(f"{label}.to_state is invalid")
        _parse_timestamp(transition["at"], f"{label}.at")
        _require_string(transition["reason"], f"{label}.reason")
        refs = _require_unique_string_list(transition["evidence_refs"], f"{label}.evidence_refs")
        if not refs:
            raise ProjectStateError(f"{label} requires evidence")
        missing_refs = [ref for ref in refs if ref not in evidence_by_id]
        if missing_refs:
            raise ProjectStateError(f"{label} references unknown evidence: {missing_refs}")
        invalidated = [ref for ref in refs if evidence_by_id[ref]["status"] != "OBSERVED"]
        if invalidated:
            raise ProjectStateError(f"{label} references invalidated evidence: {invalidated}")

        if index == 0:
            if from_state is not None or to_state != "FRAMED" or transition["kind"] != "ADVANCE":
                raise ProjectStateError("initial transition must ADVANCE from null to FRAMED")
        else:
            if from_state != previous_to:
                raise ProjectStateError(f"{label}.from_state must equal previous transition target")
            from_index = DELIVERY_STATES.index(from_state)
            to_index = DELIVERY_STATES.index(to_state)
            if transition["kind"] == "ADVANCE" and to_index != from_index + 1:
                raise ProjectStateError(f"{label} ADVANCE must move exactly one delivery state")
            if transition["kind"] == "REGRESS" and to_index >= from_index:
                raise ProjectStateError(f"{label} REGRESS must move to an earlier delivery state")

        if transition["kind"] == "ADVANCE":
            required_kind = EVIDENCE_KIND_FOR_STATE[to_state]
            observed_kinds = {evidence_by_id[ref]["kind"] for ref in refs}
            if required_kind not in observed_kinds:
                raise ProjectStateError(
                    f"{label} ADVANCE to {to_state} requires evidence kind {required_kind}"
                )
        previous_to = to_state

    if previous_to != delivery_state:
        raise ProjectStateError("delivery_state must equal final transition target")


def validate_state(state: dict[str, Any], *, verify_digest: bool = True) -> dict[str, Any]:
    """Validate a state document and return it unchanged on success."""
    if not isinstance(state, dict):
        raise ProjectStateError("project state root must be an object")
    _require_exact_keys(state, TOP_LEVEL_KEYS, "state")
    if state["schema"] != SCHEMA_ID:
        raise ProjectStateError(f"state.schema must equal {SCHEMA_ID}")
    if not isinstance(state["project_id"], str) or not PROJECT_ID_RE.fullmatch(state["project_id"]):
        raise ProjectStateError("project_id must be lowercase kebab-case")
    if not isinstance(state["revision"], int) or isinstance(state["revision"], bool) or state["revision"] < 1:
        raise ProjectStateError("revision must be an integer >= 1")
    if state["delivery_state"] not in DELIVERY_STATES:
        raise ProjectStateError("delivery_state is invalid")
    _parse_timestamp(state["updated_at"], "updated_at")
    if not isinstance(state["content_sha256"], str) or not SHA256_RE.fullmatch(state["content_sha256"]):
        raise ProjectStateError("content_sha256 must be a lowercase SHA-256")

    _scan_secret_values(state)
    evidence_by_id = _validate_evidence(state["evidence"])
    _validate_entries(state["domains"], evidence_by_id)
    _validate_transitions(state["transitions"], state["delivery_state"], evidence_by_id)

    if verify_digest:
        observed = canonical_digest(state)
        if observed != state["content_sha256"]:
            raise ProjectStateError(
                f"project state digest mismatch: expected {state['content_sha256']} observed {observed}"
            )
    return state


def new_state(
    *,
    project_id: str,
    product_statement: str,
    evidence_locator: str,
    at: str,
    evidence_sha256: str | None = None,
) -> dict[str, Any]:
    """Create the smallest valid evidence-backed FRAMED project state."""
    evidence = {
        "id": "EVID-FRAME-001",
        "kind": "product-frame",
        "locator": evidence_locator,
        "observed_at": at,
        "status": "OBSERVED",
        "sha256": evidence_sha256,
    }
    domains = {domain: [] for domain in DOMAINS}
    domains["product"] = [
        {
            "id": "PRODUCT-001",
            "kind": "FACT",
            "statement": product_statement,
            "authority": "USER",
            "status": "ACTIVE",
            "evidence_refs": [evidence["id"]],
            "updated_at": at,
        }
    ]
    state = {
        "schema": SCHEMA_ID,
        "project_id": project_id,
        "revision": 1,
        "delivery_state": "FRAMED",
        "updated_at": at,
        "domains": domains,
        "evidence": [evidence],
        "transitions": [
            {
                "id": "TRANSITION-001",
                "kind": "ADVANCE",
                "from_state": None,
                "to_state": "FRAMED",
                "at": at,
                "evidence_refs": [evidence["id"]],
                "reason": "Initial product outcome is framed by observed user/project evidence.",
            }
        ],
        "content_sha256": "0" * 64,
    }
    sealed = seal_state(state)
    validate_state(sealed)
    return sealed


def _next_revision(state: dict[str, Any], at: str) -> dict[str, Any]:
    updated = copy.deepcopy(state)
    updated["revision"] += 1
    updated["updated_at"] = at
    return updated


def add_evidence(
    state: dict[str, Any],
    *,
    evidence_id: str,
    kind: str,
    locator: str,
    observed_at: str,
    sha256: str | None = None,
    status: str = "OBSERVED",
) -> dict[str, Any]:
    validate_state(state)
    updated = _next_revision(state, observed_at)
    updated["evidence"].append(
        {
            "id": evidence_id,
            "kind": kind,
            "locator": locator,
            "observed_at": observed_at,
            "status": status,
            "sha256": sha256,
        }
    )
    sealed = seal_state(updated)
    validate_state(sealed)
    return sealed


def add_entry(
    state: dict[str, Any],
    *,
    domain: str,
    entry_id: str,
    kind: str,
    statement: str,
    authority: str,
    evidence_refs: Iterable[str],
    updated_at: str,
    status: str = "ACTIVE",
) -> dict[str, Any]:
    validate_state(state)
    if domain not in DOMAINS:
        raise ProjectStateError(f"unknown project-state domain: {domain}")
    updated = _next_revision(state, updated_at)
    updated["domains"][domain].append(
        {
            "id": entry_id,
            "kind": kind,
            "statement": statement,
            "authority": authority,
            "status": status,
            "evidence_refs": list(evidence_refs),
            "updated_at": updated_at,
        }
    )
    sealed = seal_state(updated)
    validate_state(sealed)
    return sealed


def advance_delivery_state(
    state: dict[str, Any],
    *,
    to_state: str,
    evidence_refs: Iterable[str],
    at: str,
    reason: str,
) -> dict[str, Any]:
    validate_state(state)
    current = state["delivery_state"]
    if current == DELIVERY_STATES[-1]:
        raise ProjectStateError("project is already at the highest delivery state")
    expected = DELIVERY_STATES[DELIVERY_STATES.index(current) + 1]
    if to_state != expected:
        raise ProjectStateError(f"next delivery state from {current} must be {expected}")
    updated = _next_revision(state, at)
    updated["delivery_state"] = to_state
    updated["transitions"].append(
        {
            "id": f"TRANSITION-{len(updated['transitions']) + 1:03d}",
            "kind": "ADVANCE",
            "from_state": current,
            "to_state": to_state,
            "at": at,
            "evidence_refs": list(evidence_refs),
            "reason": reason,
        }
    )
    sealed = seal_state(updated)
    validate_state(sealed)
    return sealed


def regress_delivery_state(
    state: dict[str, Any],
    *,
    to_state: str,
    evidence_refs: Iterable[str],
    at: str,
    reason: str,
) -> dict[str, Any]:
    """Regress delivery truth when new evidence invalidates a higher claim."""
    validate_state(state)
    current = state["delivery_state"]
    if to_state not in DELIVERY_STATES:
        raise ProjectStateError(f"unknown delivery state: {to_state}")
    if DELIVERY_STATES.index(to_state) >= DELIVERY_STATES.index(current):
        raise ProjectStateError("regression target must be earlier than current delivery state")
    updated = _next_revision(state, at)
    updated["delivery_state"] = to_state
    updated["transitions"].append(
        {
            "id": f"TRANSITION-{len(updated['transitions']) + 1:03d}",
            "kind": "REGRESS",
            "from_state": current,
            "to_state": to_state,
            "at": at,
            "evidence_refs": list(evidence_refs),
            "reason": reason,
        }
    )
    sealed = seal_state(updated)
    validate_state(sealed)
    return sealed


def select_context(state: dict[str, Any], domains: Iterable[str]) -> dict[str, Any]:
    """Return a compact state slice and only evidence referenced by that slice.

    This is the progressive-disclosure surface missions/agents should load rather
    than injecting the entire project history into every task.
    """
    validate_state(state)
    selected = list(dict.fromkeys(domains))
    unknown = [domain for domain in selected if domain not in DOMAINS]
    if unknown:
        raise ProjectStateError(f"unknown context domains: {unknown}")
    referenced: set[str] = set()
    domain_payload: dict[str, Any] = {}
    for domain in selected:
        entries = copy.deepcopy(state["domains"][domain])
        domain_payload[domain] = entries
        for entry in entries:
            referenced.update(entry["evidence_refs"])
    evidence = [copy.deepcopy(item) for item in state["evidence"] if item["id"] in referenced]
    return {
        "schema": "sef.project-context.v1",
        "project_id": state["project_id"],
        "revision": state["revision"],
        "delivery_state": state["delivery_state"],
        "domains": domain_payload,
        "evidence": evidence,
        "state_sha256": state["content_sha256"],
    }


def load_state(path: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectStateError(f"invalid project-state JSON: {exc}") from exc
    validate_state(state)
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    """Atomically write a validated canonical project-state document."""
    validate_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
