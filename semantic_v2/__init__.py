"""Semantic Routing v2 architecture.

This package remains separate from the frozen root-level ``sef.py`` runtime.
S0-S2 code must not alter canonical v1.5 routing.
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
from .model_extractor import ModelAssistedExtractor, SemanticProvider

__all__ = [
    "SEMANTIC_IR_SCHEMA",
    "Extractor",
    "ModelAssistedExtractor",
    "PolicyComposer",
    "SemanticProvider",
    "bridge_legacy_assessment",
    "semantic_ir_digest",
    "semantic_review_required",
    "shadow_bridge",
    "validate_semantic_ir",
]
