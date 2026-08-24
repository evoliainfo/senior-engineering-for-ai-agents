# Native Agent Baseline 2026

Status: decision input for SEF capability design
Date: 2026-08-24

## Purpose

SEF must not spend context, code, or product surface re-teaching behaviors that current coding agents already perform well natively.

This document establishes the minimum 2026 baseline that any proposed SEF capability must beat or materially augment.

## Current Codex baseline

Current Codex/OpenAI surfaces already provide or advertise substantial native capability, including:

- long-running end-to-end engineering tasks;
- feature development, refactors, migrations, debugging and code review;
- multi-agent/subagent execution and parallel worktrees;
- plan/review modes and repository-aware work;
- browser and computer use;
- image generation and image inputs;
- live browser application workflows;
- Skills following the Agent Skills standard;
- plugins packaging skills plus connected apps/tools;
- MCP/tool connectivity and tool search;
- GitHub integration and GitHub Actions surfaces;
- cloud/local execution environments;
- preview deployment workflows and live URLs for app/site use cases;
- dedicated security review/scanning surfaces;
- memories, long-running work, scheduled tasks and reusable Record & Replay workflows.

Therefore the following are **not differentiators by themselves**:

- "make a plan";
- "inspect the repository";
- "write tests";
- "debug systematically";
- "review the diff";
- "verify before completion";
- "pick a sensible stack";
- "configure environment variables";
- "deploy a preview";
- "run a security review".

They can remain useful internal primitives only when they improve outcomes measurably or support a higher-order capability.

## Broader 2026 coding-agent baseline

SEF must benchmark against the market ceiling, not only one harness.

Current competing agent environments also expose high-level capabilities that make many generic skills commodity:

### Cursor

Current Cursor Agent includes native browser control with visual screenshots, console output and network inspection. It explicitly supports application testing, accessibility auditing, design-to-code, screenshot-guided UI refinement and automated browser workflows without requiring a separate browser plugin.

### GitHub Copilot agents

Current GitHub Copilot agent surfaces support asynchronous repository work, planning/coding/PR workflows, parallel session orchestration, built-in agent skills, MCP connectivity and cloud-agent web interaction through Playwright. The GitHub Copilot app also positions itself around managing parallel workstreams and the PR lifecycle.

### Consequence for SEF

The competitive baseline is therefore no longer "can the agent write, test and review code?" It is closer to:

> Can an agent autonomously navigate code and tools, use a real browser, operate parallel workstreams, connect to external systems and progress toward a deployable outcome?

SEF must add value above that baseline.

## ECC baseline

ECC currently provides a broad engineering operating system rather than a small prompt pack. Its public repository includes hundreds of skills, dozens of specialized agents, hooks, rules, memory/continuous-learning concepts, security scanning, deployment patterns, production-audit methods and multi-harness support.

ECC therefore establishes an additional competitive baseline:

- breadth of specialist knowledge;
- installable reusable engineering playbooks;
- selective rules/context;
- memory and repeated-work learning;
- multi-harness packaging;
- domain-specific capabilities beyond generic software-development process.

SEF must not attempt to beat this simply by counting more SKILL.md files.

## SEF anti-commodity rule

A proposed user-facing SEF capability is rejected as a differentiator if its main value can be summarized as generic advice that a current frontier coding agent is already expected to know.

Examples of rejected standalone product claims:

- "senior planning skill";
- "code review skill";
- "debugging skill";
- "deployment checklist";
- "architecture best practices".

Such material may survive as an internal primitive, reference, evaluator, or composition element.

## What can still create value

SEF can create differentiated value when it supplies one or more of the following:

1. **Deep specialist knowledge** that the base agent cannot reliably derive from generic reasoning alone.
2. **Executable assets** such as validated scripts, scanners, templates, fixtures, migration rehearsal tools, deploy adapters or test harnesses.
3. **Connected tool workflows** that bind browser, hosting, database, auth, billing, monitoring or other systems into a verified delivery path.
4. **Current authoritative references** loaded only when a decision depends on changing external systems.
5. **Cross-domain composition** that reliably joins several specialties into one outcome without forcing the user to know which specialties are required.
6. **Real-environment evidence** rather than claims based only on source inspection.
7. **Production operating loops** including deployment verification, telemetry, rollback and incident recovery.
8. **Measured improvement** over the same agent without SEF.

## Required product test

Every user-facing SEF layer must eventually answer:

> What can the user successfully ship with SEF that the same current agent either fails more often, delivers less completely, asks more expert questions to accomplish, or cannot verify as rigorously without SEF?

If that question cannot be answered with measured evidence, the capability is not product value.