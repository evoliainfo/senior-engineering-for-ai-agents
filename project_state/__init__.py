"""SEF Project State Spine.

A deterministic, provider-neutral project continuity layer for Delivery Missions.
"""

from .core import (
    AUTHORITIES,
    DELIVERY_STATES,
    DOMAINS,
    ENTRY_KINDS,
    EVIDENCE_KIND_FOR_STATE,
    ProjectStateError,
    add_entry,
    add_evidence,
    advance_delivery_state,
    canonical_digest,
    load_state,
    new_state,
    regress_delivery_state,
    seal_state,
    select_context,
    validate_state,
    write_state,
)

__all__ = [
    "AUTHORITIES",
    "DELIVERY_STATES",
    "DOMAINS",
    "ENTRY_KINDS",
    "EVIDENCE_KIND_FOR_STATE",
    "ProjectStateError",
    "add_entry",
    "add_evidence",
    "advance_delivery_state",
    "canonical_digest",
    "load_state",
    "new_state",
    "regress_delivery_state",
    "seal_state",
    "select_context",
    "validate_state",
    "write_state",
]
