"""First Modern SEF Delivery Mission: launch a production web product."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime
from typing import Any, Iterable, Mapping

from .core import (
    DECISION_SCHEMA_ID,
    MISSION_SCHEMA_ID,
    MissionError,
    decide_next_action as _decide_next_action,
    initialize_project_state,
    validate_decision,
    validate_spec,
)


def _parse_time(value: str, label: str) -> datetime:
    normalized = value.replace("Z", "+00:00") if isinstance(value, str) and value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError) as exc:
        raise MissionError(f"{label} must be valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise MissionError(f"{label} must include a timezone")
    return parsed


def _reseal(decision: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(decision)
    value.pop("content_sha256", None)
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    value["content_sha256"] = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    validate_decision(value)
    return value


def decide_next_action(
    spec: dict[str, Any],
    state: dict[str, Any],
    *,
    at: str,
    tool_inventory: dict[str, Any] | None = None,
    capsules: Iterable[Mapping[str, Any]] = (),
    max_tool_age_seconds: int = 300,
) -> dict[str, Any]:
    """Public mission decision with a current-time guard around M4 snapshots."""
    if not isinstance(max_tool_age_seconds, int) or isinstance(max_tool_age_seconds, bool) or not 1 <= max_tool_age_seconds <= 86400:
        raise MissionError("max_tool_age_seconds must be integer between 1 and 86400")

    if tool_inventory is None:
        return _decide_next_action(
            spec,
            state,
            at=at,
            tool_inventory=None,
            capsules=capsules,
            max_tool_age_seconds=max_tool_age_seconds,
        )

    current = _parse_time(at, "at")
    captured = _parse_time(tool_inventory.get("captured_at"), "tool_inventory.captured_at")
    if captured > current:
        raise MissionError("tool inventory cannot be captured after mission decision time")
    age_seconds = (current - captured).total_seconds()
    if age_seconds <= max_tool_age_seconds:
        return _decide_next_action(
            spec,
            state,
            at=at,
            tool_inventory=tool_inventory,
            capsules=capsules,
            max_tool_age_seconds=max_tool_age_seconds,
        )

    # Evaluate without the stale snapshot so the core can reveal whether the
    # current action actually needs tool/JIT observations. Do not block a purely
    # planning action merely because the caller happened to supply an old cache.
    decision = _decide_next_action(
        spec,
        state,
        at=at,
        tool_inventory=None,
        capsules=capsules,
        max_tool_age_seconds=max_tool_age_seconds,
    )
    needs_inventory = bool(decision["tool_requirements"]) or any(
        "TOOL_STATE_NOT_REOBSERVED" in item.get("reasons", []) for item in decision["jit_readiness"]
    )
    if not needs_inventory:
        return decision

    blockers = [item for item in decision["blockers"] if item != "TOOL_INVENTORY_REQUIRED"]
    blockers.append("TOOL_INVENTORY_STALE")
    decision["blockers"] = sorted(set(blockers))
    decision["status"] = "BLOCKED"
    decision["tool_bridge"] = None
    return _reseal(decision)


__all__ = [
    "DECISION_SCHEMA_ID",
    "MISSION_SCHEMA_ID",
    "MissionError",
    "decide_next_action",
    "initialize_project_state",
    "validate_decision",
    "validate_spec",
]
