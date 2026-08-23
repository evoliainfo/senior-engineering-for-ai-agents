"""Semantic Routing v2 architecture.

This package remains separate from the frozen root-level ``sef.py`` runtime.
S0-S4 code must not alter canonical v1.5 routing.
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
from .policy_composer import DeterministicPolicyComposer, composer_rule_coverage
from .shadow_integration import ShadowRouter, compare_policies, summarize_shadow_results

__all__ = [
    "SEMANTIC_IR_SCHEMA",
    "Extractor",
    "ModelAssistedExtractor",
    "PolicyComposer",
    "SemanticProvider",
    "DeterministicPolicyComposer",
    "ShadowRouter",
    "bridge_legacy_assessment",
    "compare_policies",
    "composer_rule_coverage",
    "semantic_ir_digest",
    "semantic_review_required",
    "shadow_bridge",
    "summarize_shadow_results",
    "validate_semantic_ir",
]
