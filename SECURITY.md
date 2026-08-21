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

## Repository and release integrity

The repository's permanent runtime validation workflow is designed to run on every pull request targeting `main` and every push to `main`. The intended protected-branch policy is to require the `validate` job before merge and to prevent bypasses except for explicit repository-administration recovery.

Release tags are immutable release identities. For release tags matching `v*`, `.github/workflows/attest-release.yml` verifies the exact tagged source before attestation:

- `sef.py` and `SHA256SUMS` must exist;
- the release notes for the exact tag must exist;
- the runtime version must agree with the release tag family;
- `sha256sum -c SHA256SUMS` must pass;
- the Python runtime must compile;
- the embedded SEF self-test must pass.

After those gates, GitHub Actions generates signed build-provenance attestations for `sef.py`, `SHA256SUMS`, and the tag's release notes using GitHub artifact attestations/Sigstore.

A downloaded runtime from an attested release can be verified with GitHub CLI:

```bash
gh attestation verify sef.py \
  -R evoliainfo/senior-engineering-for-ai-agents \
  --signer-workflow evoliainfo/senior-engineering-for-ai-agents/.github/workflows/attest-release.yml
```

The checksum and provenance attestation are complementary: the checksum detects content changes against the published manifest, while the attestation binds the artifact digest to an authenticated GitHub Actions identity and workflow execution.

## Supported beta

Security fixes are currently targeted at the latest public beta version. Older beta snapshots may not receive backports.
