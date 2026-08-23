# L2 Brownfield Evaluation Protocol

**Status:** executable harness design; real coding-agent trials not yet executed  
**Frozen DEV candidate:** `7302914ef8ed098a8c3d1e6ae5a0c4a811f49837`  
**Frozen candidate runtime SHA-256:** `c5fdbcf6a1a8428663c25e15247c481c1268849a2c747de8766bc0946544d6b4`  
**DEV evidence:** 38/38 deterministic scenarios PASS; CHALLENGE remains SEALED.

## Purpose

`BROWN-001` and `BROWN-003` already pass their deterministic L1 planning contracts. L1 cannot prove that a probabilistic coding agent will inspect and preserve real repository conventions while implementing a change. This protocol adds that missing L2 evidence class without changing the frozen DEV candidate or pretending that a harness self-test is an agent result.

## Claims this harness may support

For the two brownfield DEV scenarios, L2 may establish that an external coding agent:

- starts from a clean isolated repository on every trial;
- receives the SEF adapters installed from the exact candidate runtime;
- implements the requested behavior;
- preserves explicitly protected repository conventions and unrelated debt surfaces;
- keeps the diff within the allowed brownfield scope;
- runs against deterministic post-state graders;
- leaves enough transcript and environment metadata for failure inspection.

The harness does **not** treat one successful trial as release-level evidence. These are standard L2 scenarios, so the minimum is three independent trials per supported harness.

## Supported evidence harnesses

Release-level L2 evidence is recognized only for:

- `codex` through the repository's generated `AGENTS.md` adapter;
- `claude` through the generated `CLAUDE.md` adapter.

The runner intentionally does not hard-code provider CLI syntax or credentials. The operator supplies an external wrapper command. The wrapper runs inside the isolated trial repository and receives the task through environment variables.

A deterministic `reference` agent is included only to prove that the fixture and grader contracts are solvable and that the harness mechanics work. `reference` results are always marked `HARNESS_REFERENCE_ONLY`; they are never counted as Codex or Claude evidence.

## External adapter contract

The command supplied with `--agent-command` receives:

- `SEF_L2_REPO`: absolute trial repository path;
- `SEF_L2_REQUEST`: task request text;
- `SEF_L2_SCENARIO_ID`: scenario ID;
- `SEF_L2_HARNESS`: `codex`, `claude`, or `reference`;
- `SEF_L2_TRIAL_ID`: unique trial ID;
- `SEF_L2_RESULT_PATH`: optional path where a wrapper may persist structured metadata.

The command's stdout/stderr are captured. Secrets must not be printed by wrappers. The runner records only the command SHA-256, not the raw command string.

## Trial isolation

Every trial:

1. copies the declared fixture to a fresh temporary directory;
2. initializes a fresh Git repository and commits the fixture;
3. installs/adopts SEF from the exact candidate `sef.py`;
4. commits the SEF-managed baseline;
5. strips inherited `GIT_*` environment variables before launching the external adapter;
6. runs exactly one agent attempt;
7. grades the resulting repository state and records the full changed-path set;
8. destroys the temporary workspace unless a future explicit debug policy says otherwise.

No trial inherits files, Git history, SEF state or agent output from another trial.

## Deterministic grading

The L2 grader is intentionally outcome-based. It does not demand one exact implementation path. It checks:

- declared test commands succeed;
- hidden behavior probes succeed;
- required paths are changed where the task requires them;
- changed application paths stay within scenario-declared patterns;
- protected files remain byte-identical;
- SEF adapters/runtime are not rewritten by the agent;
- no dependency manifest is introduced for these dependency-free fixtures;
- the diff remains within the scenario's change-count budget.

`BROWN-003` also records whether the agent transcript mentions the known unrelated debt. That signal is **not** promoted to a deterministic G1 pass criterion; it remains a G2/human trace-review item because robust semantic disclosure cannot be established by a substring alone.

## Repetition and decision rule

For each of `BROWN-001` and `BROWN-003`:

- minimum 3 independent trials for Codex;
- minimum 3 independent trials for Claude Code;
- report first-attempt success and total trial success rate separately;
- preserve each failure signature rather than averaging it away.

A harness receives `PASS` for this brownfield L2 slice only if every required deterministic assertion passes in every required trial. Any incomplete run is `INSUFFICIENT_TRIALS` or `NOT_RUN`, never PASS.

## Current evidence state

At creation of this protocol:

- deterministic DEV: **38/38 PASS**;
- L2 Codex brownfield: **NOT_RUN**;
- L2 Claude brownfield: **NOT_RUN**;
- CHALLENGE: **SEALED**.

Therefore the 38/38 result is a deterministic L1/L0 closure claim, not yet a full cross-agent brownfield claim.

## Gate before CHALLENGE

Do not unseal the 10 CHALLENGE scenarios merely because the deterministic DEV suite is green. First either:

1. execute the required Codex/Claude L2 brownfield trials and review representative traces, or
2. explicitly record that cross-agent L2 evidence is unavailable and narrow any subsequent claim accordingly.

Unsealing CHALLENGE remains a separate deliberate decision.