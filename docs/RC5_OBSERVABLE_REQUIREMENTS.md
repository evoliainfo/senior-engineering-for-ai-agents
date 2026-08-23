# RC-5 — Observable requirements / Dynamic DoD

Target failures: `REQ-003`, `REQ-005` from the full 38-scenario DEV closure.

## Contract

RC-5 converts vague quality adjectives into observable planning obligations without inventing business values.

### `REQ-003` — performance

For vague performance language such as `fast`, `faster`, `performant`, `responsive`, `low latency`, or equivalent optimization language where no measurable target is supplied, the plan must require:

- an explicit measurable performance target (latency/throughput/response-time/capacity as applicable); and
- benchmark/load/measurement evidence against that target before a success claim.

SEF must **not** invent a numeric target such as `200 ms`.

### `REQ-005` — secure and robust

For vague `secure` / `robust` / `resilient` quality language, the plan must convert applicable qualities into observable acceptance/verification obligations, including:

- security criteria and negative/abuse-path verification where material;
- robustness/resilience/failure/error behavior as observable criteria; and
- test/verification evidence rather than treating adjectives as already satisfied.

## Safety boundaries

- No change to RC-1 routing, RC-2 polarity, RC-3 task materiality, RC-4 evidence semantics.
- No new human decision unless an authoritative target/business rule is genuinely required.
- No fabricated numeric SLO/SLA/latency/throughput target.
- Existing explicit measurable requirements are preserved and not replaced.
- CHALLENGE remains sealed.

## Admission gates

1. `REQ-003` PASS.
2. `REQ-005` PASS.
3. Full general DEV routing/diff runner has zero PASS→FAIL regressions.
4. Evidence/Release current-runtime scenarios remain passing where previously passing.
5. RC-1/RC-2/RC-3/RC-4 permanent gates remain green.
6. Full 38-scenario closure improves from 33/38 to at least 35/38, with no new failure IDs.
