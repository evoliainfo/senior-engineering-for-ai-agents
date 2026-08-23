"""Semantic Routing v2 shadow architecture.

This package is deliberately separate from the frozen root-level ``sef.py`` runtime.
S0/S1 code must not alter canonical v1.5 routing.
"""

from .contracts import (
    SEMANTIC_IR_SCHEMA,
    Extractor,
    PolicyComposer,
    semantic_ir_digest,
    semantic_review_required,
    validate_semantic_ir,
)
from .bridge_v15 import bridge_legacy_assessment, shadow_bridge

__all__ = [
    "SEMANTIC_IR_SCHEMA",
    "Extractor",
    "PolicyComposer",
    "bridge_legacy_assessment",
    "semantic_ir_digest",
    "semantic_review_required",
    "shadow_bridge",
    "validate_semantic_ir",
]
