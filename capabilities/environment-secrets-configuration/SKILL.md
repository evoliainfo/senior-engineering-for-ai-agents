---
name: environment-secrets-configuration
description: Design and verify safe, explicit runtime configuration across local, test, preview/staging, and production environments, keeping secrets out of source and making missing or invalid configuration fail clearly.
---

# Environment, Secrets and Configuration

Use this capability when a project depends on runtime configuration, credentials, environment-specific values, external services, or deployment settings.

## Core Principle

> Configuration should be explicit, validated, environment-aware, and safe to share; secret values should never become source code or evidence output.

The user should not need to know every environment variable a professional project requires. The agent should derive ordinary configuration needs from the architecture and integrations, then request only unavailable values/authorizations that genuinely require the user.

## 1. Inventory Configuration by Meaning

Identify configuration that changes runtime behavior, such as:

- service/API endpoints;
- database/storage connection information;
- public/non-secret application settings;
- credentials/tokens/keys;
- environment/feature flags;
- callback/base URLs;
- logging/telemetry settings;
- deployment-region/runtime values;
- integration-specific identifiers.

Do not create environment variables for values that are stable application constants without a real deployment reason.

## 2. Classify Secret vs Non-Secret

Treat credentials, private keys, access tokens, signing secrets, connection strings containing credentials, and similarly sensitive material as secrets.

Do not assume a value is safe merely because it appears in frontend tooling. Distinguish values intentionally exposed to clients from server-only secrets according to the framework/platform contract.

Never:

- hardcode real secrets;
- print secret values in logs/evidence;
- commit populated secret files;
- copy credentials into documentation/tests;
- place server secrets in client-exposed configuration.

## 3. Define Environment Boundaries

Use only the environments the delivery model needs.

Common distinctions can include:

- local/development;
- automated test;
- preview/staging;
- production.

Do not create elaborate environment hierarchies for a tiny project. But do not reuse production secrets/data by default for development or tests.

For each material environment, identify:

- which configuration names are required;
- where values are supplied;
- which values differ;
- what resources/accounts/data are isolated;
- how callbacks/origins/domains differ.

## 4. Establish a Configuration Contract

Define required names and semantics without secret contents.

A useful contract can state:

```text
NAME | secret? | required where | purpose | validation/fallback
```

Provide `.env.example` or ecosystem-equivalent templates when useful, containing placeholders or demonstrably non-sensitive examples only.

Do not include convincing fake secrets that might later be mistaken for valid credentials.

## 5. Validate Early and Clearly

Where the ecosystem permits, validate configuration at startup/build time close to the authoritative boundary.

Check as applicable:

- required value present;
- expected URL/number/enum/format;
- mutually dependent settings;
- environment-incompatible combinations;
- obvious dangerous production defaults.

Prefer one clear configuration error over obscure downstream failures.

Do not over-validate provider-specific formats that are not stable contracts.

## 6. Use Platform Secret Stores Correctly

For CI/hosting/cloud environments, use the platform's supported secret/configuration mechanism.

The agent may configure names/references when permissions allow, but should not expose secret values in command output or artifacts.

Ask the user for credential provisioning/authorization only when no connected secure mechanism can supply it. Explain **what access is needed and why**, not how the user should make unrelated technical choices.

## 7. Protect Test and Preview Environments

Tests should prefer isolated fixtures/emulators/test credentials rather than production resources.

For previews/staging:

- avoid destructive access to production data unless deliberately authorized;
- use correct callback/domain configuration;
- make third-party side effects explicit;
- distinguish test/sandbox provider environments when available.

## 8. Design Rotation and Failure Behavior Proportionally

For long-lived or production-sensitive credentials, avoid architecture that assumes a secret can never change.

Where material, document:

- who/what owns provisioning;
- where rotation happens;
- what fails if the secret is missing/revoked;
- whether restart/redeploy is required.

Do not add enterprise secret-rotation machinery to a small prototype without a real need.

## 9. Verify the Configuration Path

Evidence can include:

- template/contract contains required names but no secrets;
- ignored local secret files are not tracked;
- startup/build fails clearly for missing mandatory config;
- valid non-secret/test configuration starts correctly;
- client bundle does not receive server-only values when relevant;
- target platform has required configuration names present, without displaying values;
- preview/staging uses intended non-production resources.

Classify credential-dependent checks as `NOT_RUN`/`BLOCKED` rather than fabricating success.

## Context Budget

Load only:

1. architecture/integration configuration needs;
2. framework/platform configuration documentation relevant to exposure and deployment;
3. existing environment/config files;
4. deployment target settings metadata, not secret contents.

Do not enumerate or print the user's entire environment.

## Decision Points

### Environment variable vs config file

Follow the project's ecosystem and deployment needs. Source-controlled non-secret structured configuration can belong in config files; secrets/runtime-specific values generally belong in environment/platform secret mechanisms.

### Ask for secret now vs defer

Defer until the value is required for a meaningful integration/deployment check. Do not block unrelated implementation because a future production credential is unavailable.

### Default vs required

Use safe defaults only when behavior is unambiguous and harmless. Production-sensitive values should normally fail clearly rather than silently choosing an unsafe default.

## Anti-Patterns

Avoid:

- `.env` with real secrets committed to Git;
- logging environment dumps;
- putting server secrets into client-prefixed variables;
- one production credential reused everywhere;
- dozens of unnecessary environment variables;
- silent fallback to localhost/test behavior in production;
- asking a non-expert user to invent configuration names;
- blocking local feature work on credentials only required later for production;
- claiming provider/platform configuration exists without observing it;
- storing secrets in capability/agent metadata.

## Evidence Contract

For a material configured project, be able to answer:

1. What runtime configuration is required and why?
2. Which values are secrets vs intentionally public?
3. Which environments need which values/resources?
4. How are missing/invalid values detected?
5. Are secret values excluded from source, logs, tests, docs and evidence?
6. How does the deployment target receive configuration?
7. Which credential-dependent checks remain unavailable?

## Handoff

Use `implementation-planning` once required configuration contracts are known.

Use `architecture-conformant-implementation` when integrations/features consume the configuration.

Future `deployment-execution` owns actual target deployment/configuration application and must not assume configuration presence solely from this design capability.
