---
name: project-bootstrap-foundations
description: Create the smallest maintainable greenfield repository foundation implied by the chosen architecture, including project structure, executable verification surfaces, configuration conventions, and developer guidance without speculative infrastructure.
---

# Project Bootstrap Foundations

Use this capability after a greenfield architecture/stack decision when the repository must be created or materially initialized.

## Core Principle

> Bootstrap the engineering foundation the project needs now, while leaving obvious extension points for later work.

Do not equate "senior" with generating every possible tool, folder, service, CI workflow, Docker file, abstraction, or environment on day one.

## 1. Confirm the Bootstrap Contract

Before creating files, know:

- selected architecture/stack;
- first delivery boundary;
- expected deployment/runtime model;
- primary package/build/test conventions;
- configuration/secrets needs already known;
- material project instructions or user constraints.

If stack choice is still unresolved, return to `solution-architecture-stack-selection` rather than letting a framework initializer make the architecture decision implicitly.

## 2. Use Official/Established Initialization Paths Carefully

When the chosen ecosystem has an authoritative project initializer, it can be a good starting point if it produces a structure compatible with the requirements.

Before accepting generated output:

- inspect what it added;
- remove clearly unused optional features when safe;
- understand generated scripts/configuration;
- do not blindly accept telemetry, example apps, demo credentials, or unnecessary dependencies;
- preserve lockfiles/reproducibility conventions.

A generator is scaffolding, not architecture authority.

## 3. Establish a Minimal Repository Shape

Create only boundaries justified by the architecture.

A maintainable bootstrap should make it obvious:

- where application/source code lives;
- where tests live according to ecosystem conventions;
- where configuration is defined;
- where generated/vendor artifacts belong;
- where documentation/instructions live when needed;
- how multiple packages/services relate if the architecture genuinely requires them.

Avoid placeholder directories for hypothetical future layers.

## 4. Establish Executable Quality Surfaces

A project should have a clear way to answer the basic engineering questions relevant to its stack.

Where supported/applicable, establish repository-native commands or equivalents for:

- dependency/install reproducibility;
- development/startup;
- test execution;
- build/package;
- type/static checking;
- lint/format consistency.

Do not install tools solely to make this list complete. For example, a language with compile-time checks may not need a separate type checker; a tiny backend may not need browser E2E tooling at bootstrap.

Run the initialized surfaces at least once where the environment permits, and record anything unavailable rather than assuming generated configuration works.

## 5. Create the First Useful Test/Verification Anchor

Establish at least one meaningful executable check appropriate to the project, such as:

- a minimal unit/domain test;
- an application startup/smoke check;
- a route/component test;
- a build assertion;
- another ecosystem-native verification.

The goal is to prove the test/build surface is executable before feature complexity accumulates.

Do not write meaningless tests whose only purpose is to increase test count.

## 6. Establish Configuration Boundaries

Create safe configuration conventions without embedding secrets.

Normally this includes:

- documented required environment/configuration names when known;
- local example/template values only when safe;
- `.gitignore` or equivalent protection for local secret files;
- separation between source-controlled configuration and secret/runtime values.

Use `environment-secrets-configuration` for the detailed configuration contract.

## 7. Establish Source-Control Hygiene

When Git is part of the project workflow:

- ignore generated/build/dependency/secret artifacts appropriately;
- keep required lockfiles/manifests;
- avoid committing machine-local files;
- preserve executable/config permissions when relevant.

Do not rewrite global user Git settings.

## 8. Add Only Useful Developer/Agent Guidance

Documentation should answer high-leverage questions such as:

- what the project is;
- how to install/run/test/build it;
- important architecture boundaries;
- required configuration names;
- where project-specific instructions live.

Do not generate a long README full of unverified future features.

If `AGENTS.md` or another harness instruction surface is used, preserve user-owned content and add only concise project-specific guidance.

## 9. Check Deployment Compatibility Early

Before declaring bootstrap complete, verify that the initial project shape is compatible with the selected deployment model:

- correct runtime/version expectations;
- build output/start command;
- serverless/long-running/background-process assumptions;
- required storage/network support;
- configuration injection mechanism.

This is not deployment execution. It prevents discovering fundamental incompatibility after feature work.

## 10. Bootstrap Completion Evidence

A useful bootstrap evidence summary can include:

```text
BOOTSTRAP EVIDENCE
Architecture/stack basis:
Repository structure created:
Install/dependency check:
Build/static checks:
Test/smoke check:
Configuration boundary:
Deployment compatibility checked:
Anything NOT_RUN/UNAVAILABLE:
```

## Context Budget

Load only:

1. architecture/stack decision;
2. first-delivery requirements;
3. current authoritative initializer/tool documentation when necessary;
4. deployment constraints;
5. generated files that need review.

Do not pre-load specialist guides for features that do not exist yet.

## Decision Points

### Add CI now?

Add minimal CI when repository collaboration/release expectations already require it or when it is cheap and clearly valuable. Do not build a complex delivery pipeline before the project has a stable verification surface.

### Add containers now?

Use containers when deployment/development consistency requires them. Do not add Docker solely as a symbol of production readiness.

### Monorepo vs single project

Use a monorepo/workspace only when multiple deployable/package boundaries genuinely exist or shared ownership makes it valuable. Do not manufacture packages for architectural aesthetics.

## Anti-Patterns

Avoid:

- running a framework generator and treating all generated files as correct/necessary;
- installing dozens of "best practice" dependencies before requirements exist;
- empty layered architecture directories;
- fake tests;
- hardcoded secrets or committed `.env` values;
- unverified build/test scripts;
- Docker/CI/microservices by default;
- documentation for features not implemented;
- deployment-incompatible local assumptions;
- asking the user to choose routine scaffolding details.

## Evidence Contract

Bootstrap is credible when:

1. repository structure traces to the chosen architecture;
2. dependency installation/reproducibility conventions are established;
3. meaningful build/test/static surfaces execute or are truthfully unavailable;
4. configuration/secrets have a safe boundary;
5. generated content was reviewed rather than blindly accepted;
6. the project can progress into feature implementation without an immediate structural rewrite;
7. the selected deployment model is not obviously incompatible.

## Handoff

Use `environment-secrets-configuration` to complete runtime configuration contracts.

Use `implementation-planning` for the first product slice.

Use `architecture-conformant-implementation` when implementation begins.
