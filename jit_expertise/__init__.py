"""SEF Just-In-Time Expertise contract.

This package validates and fingerprints compact expertise capsules compiled from
current project evidence, authoritative sources and available tool surfaces.
It performs no network or model calls itself.
"""

from .core import (
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

__all__ = [
    "CAPSULE_STATUSES",
    "SOURCE_TIERS",
    "SUBJECT_KINDS",
    "JITExpertiseError",
    "compile_capsule",
    "evaluate_invalidation",
    "project_context_digest",
    "rank_sources",
    "tool_snapshot_digest",
    "validate_capsule",
]
