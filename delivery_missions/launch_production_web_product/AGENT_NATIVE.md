# Agent-Native Operating Entry Point

When the `launch-production-web-product` mission returns `READY_FOR_AGENT`, the active Codex session should use `tools/delivery_mission.py` rather than manually fabricating a mission result.

Nominal loop:

1. `prepare` with the current mission spec, Project State, explicit M4 tool inventory and any required JIT capsule files.
2. Read the generated `plan.json` and load only its bound context/JIT/packs.
3. Execute the action using only the exact M4 surfaces listed by the plan.
4. Use `register` for every required slot and every evidence-bearing tool output that pack observations reference.
5. Use `attach-pack` once for every active Expert Pack observation document.
6. Use `finalize` to build the sealed execution result.
7. Use `accept` to submit it to the canonical M5 evidence API and advance Project State at most one state.
8. Start a new `prepare` call from the resulting Project State.

Do not treat the plan as authorization. Do not substitute a JIT capsule, tool surface, pack scope or evidence source. If `prepare` returns `BLOCKED`, resolve the exact blocker rather than creating a run by hand.

Full contract and examples: `docs/M5_AGENT_NATIVE_LIVE_LOOP.md`.
