# SEF Capabilities

SEF vNext capabilities are modular senior-engineering methods for coding agents.

The agent-facing surface follows the portable Agent Skills pattern: each capability has a `SKILL.md` containing the instructions the coding agent can use directly. SEF-specific composition, evaluation and guardrail metadata lives in the adjacent `capability.json` sidecar so the skill remains useful without the SEF runtime.

```text
capabilities/<capability-id>/
├── SKILL.md
├── capability.json
├── references/        # optional, progressive disclosure
└── examples/          # optional, progressive disclosure
```

## Design rules

- Capability IDs use lowercase kebab-case.
- `SKILL.md` frontmatter `name` must exactly equal the directory/capability ID.
- `SKILL.md` contains the useful engineering method, not SEF runtime configuration.
- `capability.json` contains only deterministic metadata for composition/evaluation.
- No model name, provider API key or provider endpoint belongs in capability metadata.
- Related capabilities form a directed acyclic graph. Handoffs must not recurse forever.
- `references/` and `examples/` are indexed for integrity but are not loaded into the capability core by the registry. The harness may load them when useful.
- Capabilities should specify invariants, decision points and verification while preserving implementation freedom.
- Hard guardrails belong in targeted `guardrail_hooks`, not in every capability by default.

## `capability.json` schema v1

Required fields:

```json
{
  "schema_version": 1,
  "id": "repository-discovery",
  "version": "0.1.0",
  "category": "foundation",
  "status": "experimental",
  "purpose": "Map an existing repository before material change.",
  "activate_when": ["Working in an unfamiliar existing repository"],
  "inputs": ["user intent", "repository state"],
  "outputs": ["relevant architecture map"],
  "related_capabilities": [],
  "guardrail_hooks": [],
  "evals": ["CAP-BROWN-001"]
}
```

Allowed categories: `foundation`, `specialist`, `workflow`, `project`.

Allowed statuses: `experimental`, `candidate`, `stable`.

Optional field: `tags` (list of strings).

## Registry commands

```bash
python3 tools/capability_registry.py validate
python3 tools/capability_registry.py manifest
python3 tools/capability_registry.py check-manifest
```

The generated `capabilities/manifest.json` is canonical, deterministically ordered and includes SHA-256 hashes of the skill, metadata and optional resource files.

## Template

Copy `capabilities/_template/` when starting a new capability, rename the directory and replace every placeholder. The `_template` directory is intentionally excluded from the generated capability manifest.
