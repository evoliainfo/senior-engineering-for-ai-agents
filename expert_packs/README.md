# SEF Stable Expert Packs

Stable Expert Packs carry durable **executable** specialty capability for Delivery Missions. They are intentionally different from ordinary prompt-only skills and from volatile provider/framework knowledge acquired through JIT Expertise.

## Bundle layout

```text
expert_packs/<pack-id>/
├── SKILL.md
├── pack.json
├── scripts/       # SCRIPT entry points
├── evaluators/    # EVALUATOR entry points
├── collectors/    # COLLECTOR entry points
├── adapters/      # ADAPTER entry points
├── fixtures/      # deterministic/adversarial fixtures
└── references/    # durable reference material
```

Only the directories actually needed by a pack should exist.

## Required properties

Every discovered pack must:

- use a portable `SKILL.md` with frontmatter `name` equal to the pack id;
- use semantic versioning;
- declare evidence-based activation conditions;
- declare abstract tool requirements without embedding provider credentials/configuration;
- provide at least one real executable entry point;
- declare required and produced evidence;
- declare failure modes, recovery actions and stop conditions;
- contain no credential-shaped secret values;
- keep entry-point paths confined to their declared content roots;
- remain small enough for deterministic integrity indexing.

The registry fingerprints every file in the bundle. A changed fixture, script, adapter, reference or metadata file changes the pack digest.

## What does not belong here

Do not create a Stable Expert Pack merely to restate generic coding advice or current provider syntax. Use JIT Expertise for volatile provider/framework contracts. Add a stable pack when durable executable behavior, fixtures, evaluators or evidence collection measurably improves delivery outcomes.

## M3 scope

M3 first establishes this contract. The roadmap then permits only three initial pack implementations:

1. `web-experience-visual-quality`
2. `data-change-safety`
3. `production-evidence-operations`

Those packs require their own focused evaluation before any broader catalog expansion.
