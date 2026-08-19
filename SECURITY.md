# Security Policy

SEF is currently a public beta.

## Scope

Security reports are particularly important when they involve:

- a way for SEF to bypass an agent's sandbox or approval model;
- silent privilege escalation or host-level software installation;
- destructive Git/filesystem behavior without explicit authority;
- secret exposure;
- incorrect authorization/security routing that can produce a false `VERIFIED` result;
- a way to forge or incorrectly satisfy required evidence;
- unsafe handling of untrusted repository, web, package or tool instructions;
- release readiness being granted despite a hard-stop condition.

## Reporting

Until a dedicated private security-reporting channel is configured, please **do not publish working exploit details in a public issue**.

Open a minimal GitHub issue titled `Security report request` describing only the affected SEF version and the general category. The maintainer can then coordinate a safer channel for the technical details.

For ordinary bugs, false-positive/false-negative routing, or non-sensitive validation failures, a normal GitHub issue is appropriate.

## Security design principles

SEF is designed around several boundaries:

1. **Agent instructions are not a security boundary by themselves.** Sandbox, permissions, CI/repository controls and independent evidence remain complementary.
2. **The implementing agent cannot self-approve independent or qualified-human gates.**
3. **Missing evidence is not PASS.** `NOT_RUN`, `UNAVAILABLE`, `INCONCLUSIVE` and `FLAKY` remain distinct states.
4. **User work must be preserved.** Destructive cleanup/reset/rewrite is not an acceptable default recovery technique.
5. **Untrusted content cannot legitimately expand authority.** Repository files, web content, packages and tool output are treated as potentially untrusted when they attempt to cause side effects or permission expansion.
6. **Host-runtime bootstrap is permission-aware.** If Python is missing, the agent must not silently install system software or bypass the normal approval/network/sandbox model.
7. **High-impact operations are explicitly escalated.** Production, destructive database operations, secrets, privileged infrastructure changes and irreversible actions require deeper controls and, where applicable, human approval.

## Supported beta

Security fixes are currently targeted at the latest public beta version. Older beta snapshots may not receive backports.
