# Contributing to the SEF Public Beta

Thank you for testing Senior Engineering for AI Coding Agents.

The most valuable contribution during the beta is **reproducible evidence that SEF routed, framed, verified, or blocked a real engineering task incorrectly**.

## High-value reports

Please report cases such as:

- SEF classified a high-risk change as low risk;
- a relevant specialist pack or execution playbook was not selected;
- an irrelevant pack created unnecessary friction;
- the agent started implementation before important product/context decisions were resolved;
- the agent claimed completion despite missing evidence;
- a frontend/backend/database boundary was handled at the wrong layer;
- an auth, tenant, privacy, migration, recovery, release, or production concern was missed;
- a trivial R0 task became bureaucratic;
- adoption changed or destroyed unrelated existing work;
- Codex and Claude Code behaved materially differently under the same SEF project state;
- `task-guidance` was insufficient for a real framework/database/runtime situation.

## Good bug report

Include:

1. **SEF version**
2. **Coding agent** and version/mode if known
3. **Project stack**
4. **Exact user request**
5. **Relevant project context** without secrets
6. **SEF plan/risk/packs/playbooks returned**
7. **What the agent actually changed**
8. **Verification/release result**
9. **Expected engineering behavior**
10. A minimal reproduction when possible

Do not include API keys, credentials, production customer data, private source code you are not allowed to disclose, or exploitable security details in a public issue.

## Design principles for changes

Changes to SEF should preserve these properties:

- **proportionality**: low-risk changes stay lightweight;
- **fail closed on material uncertainty**: unknown critical context is not silently treated as safe;
- **work preservation**: unrelated user work is not destroyed to simplify automation;
- **no fake evidence**: absent/unknown evidence does not become PASS;
- **no self-approval**: the implementing agent cannot satisfy independent/human gates by assertion;
- **actual-diff authority**: implementation reality can escalate the initial plan;
- **stack awareness without fake universality**: use actual repository conventions and authoritative platform docs;
- **agent-agnostic core**: provider adapters should not fork the engineering policy into incompatible systems.

## Pull requests

The beta is currently accepting feedback first. Before making a large architectural pull request, open an issue describing the problem, the failure case, and the proposed control/procedure change.

Small documentation corrections and reproducible test cases are welcome directly.

## Security

For potentially exploitable security issues, follow [SECURITY.md](SECURITY.md) and do not publish working exploit details in a public issue.

## Licensing note

This repository does not currently grant an open-source license. Public visibility does not automatically grant permission to copy, redistribute, or commercially reuse the code. Contribution/licensing terms may be formalized before broader external contributions are accepted.
