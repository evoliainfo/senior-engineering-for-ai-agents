# RC-1 shadow implementation scope

- Added `rc1_shadow.py`: standalone concept normalization/detection with evidence spans.
- Added six candidate concept mappings matching the accepted RC-1 architecture.
- Added a shadow evaluator over the 24 frozen contracts plus 12 independent probes.
- Added a dedicated GitHub Actions workflow that publishes shadow evidence.
- Kept `sef.py`, embedded policy payload, `SHA256SUMS`, authoritative routing, packs, risk, and execution contexts unchanged.

Promotion criterion: review CI evidence first. Any activation of shadow observations into authoritative routing must happen in a later, explicit change.
