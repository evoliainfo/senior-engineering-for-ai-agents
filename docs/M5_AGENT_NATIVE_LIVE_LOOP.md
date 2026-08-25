# M5 Agent-Native Live Loop

Status: implementation slice for `launch-production-web-product`

## Purpose

This slice makes the existing M5 contracts directly operable by the **active coding-agent session** without creating a second Codex client or a parallel tool ecosystem.

The normal path is:

```text
active Codex session
  -> tools/delivery_mission.py prepare
  -> exact M5 decision + execution plan
  -> Codex uses its already-available native/plugin/MCP tools
  -> tools/delivery_mission.py register
  -> tools/delivery_mission.py attach-pack (when required)
  -> tools/delivery_mission.py finalize
  -> tools/delivery_mission.py accept
  -> M5 evidence gate
  -> Project State +1 only on PASS
```

SEF does not launch another model and does not own provider credentials in this path.

## Why not a second Codex App Server client?

Codex App Server is the first-class OpenAI protocol for products that embed or remotely drive the Codex harness. SEF's first Codex path is different: SEF is installed in the project that the active Codex session is already operating.

Running a second Codex client merely to tell the active Codex session what to do would duplicate the harness and create a second authorization/tool surface. The first mission therefore uses the agent-native project Skill + CLI boundary. App Server remains a valid future embedding surface if SEF is later exposed as an external application/client.

## Run workspace

`prepare` freezes these exact inputs beneath a new run directory:

- `spec.json`
- `state.before.json`
- `decision.json`
- `plan.json`
- integrity-sealed `run.json`

The run id is derived from the exact mission decision digest. A non-empty run directory is never silently reused.

The run manifest is `sef.agent-native-mission-run.launch-production-web-product.v1` and tracks only compact run/evidence metadata. It contains no provider secret values.

## CLI

### 1. Prepare

```bash
python3 tools/delivery_mission.py prepare \
  --spec .sef/mission/mission.json \
  --state .sef/project-state.json \
  --inventory .sef/tool-inventory.json \
  --capsule .sef/expertise/provider.json \
  --run-dir .sef/mission-runs/<run>
```

If the decision is blocked, no executable run is created. The CLI returns the exact blockers.

If the decision is ready, the returned plan names:

- Project State domains to load;
- exact JIT capsule ids + SHA-256 digests;
- exact M4 capability/surface bindings;
- active M3 packs;
- required artifact slots;
- action sequence and result contract.

### 2. Execute with the active harness

Codex performs the action using the exact surfaces selected in the plan. SEF does not reinterpret a tool name or grant new authorization here.

### 3. Snapshot evidence

```bash
python3 tools/delivery_mission.py register \
  --run-dir .sef/mission-runs/<run> \
  --source <tool-output-file> \
  --id EVID-1 \
  --kind implementation-change \
  --producer TOOL \
  --slot <slot-id> \
  --capability source_control \
  --surface <exact-selected-surface-id>
```

`register` copies the bytes into the run workspace and calculates SHA-256 itself. For `TOOL` evidence, capability and surface must exactly match the execution plan.

The original source file may later change without changing the snapshotted evidence. If the copied run artifact changes after registration/finalization, the downstream M5 evidence gate detects the SHA mismatch.

### 4. Attach active pack observations

When the plan activates an Expert Pack, the agent/harness creates the observation JSON required by that pack and registers it as an artifact. Then:

```bash
python3 tools/delivery_mission.py attach-pack \
  --run-dir .sef/mission-runs/<run> \
  --pack-id web-experience-visual-quality \
  --artifact-id VISUAL-OBS
```

Only packs active in the exact decision/plan can be attached. Evidence-bearing fields inside the observation remain subject to the existing M5 tool-evidence checks and pack evaluator.

### 5. Finalize

```bash
python3 tools/delivery_mission.py finalize \
  --run-dir .sef/mission-runs/<run> \
  --status SUCCEEDED
```

A `SUCCEEDED` result cannot be finalized while a required plan slot or active pack observation is missing. The CLI emits a sealed `execution-result.json` using the exact result contract from the plan.

### 6. Accept

```bash
python3 tools/delivery_mission.py accept \
  --run-dir .sef/mission-runs/<run> \
  --state .sef/project-state.json
```

`accept` calls the existing public M5 evidence API. It verifies the current Project State still matches the pre-execution state, verifies artifact bytes/hashes and selected M4 provenance, recomputes active M3 evaluators, persists the receipt and advances M1 exactly one delivery state only on `PASS`.

A finalized run cannot be accepted twice.

## Qualification

The deterministic CI qualification crosses a real process/filesystem boundary:

- invoke `tools/delivery_mission.py` as separate Python processes;
- create a READY implementation action from an ARCHITECTED Project State;
- register required evidence using real temporary files;
- compute and validate hashes on snapshotted bytes;
- finalize a sealed execution result;
- accept the result and observe exactly one state transition;
- mutate evidence after finalization and prove acceptance fails;
- change current Project State and prove stale execution evidence fails;
- substitute a non-selected M4 surface and prove registration fails;
- reject missing slots, duplicate slots, inactive packs, empty evidence, run-manifest tampering, run-directory reuse and double acceptance.

## Explicit non-claims

This slice makes the active-session integration **operational**, but its CI qualification still performs:

- 0 model calls;
- 0 network calls;
- 0 provider calls;
- 0 browser calls.

Therefore it does **not** by itself prove that a real Codex session successfully shipped a real web product.

M5 end-to-end completion still requires external evidence from at least one real Codex run covering browser behavior, preview/staging or authorized deployment, post-deploy verification and fresh-session continuation. Those should be captured as benchmark/live-qualification evidence rather than faked inside deterministic CI.
