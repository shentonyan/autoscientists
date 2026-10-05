# Journal

One entry per wake-up, newest last, at most ten lines each.

## 2026-10-05: bootstrap

- Added the framework (`autosci/`), the procedure (`loop/AGENT.md`) and the protocol.
- Ran `auction-calibration`: all three hypotheses came out as predicted (H1 supported,
  H2 supported, H3 refuted), all cross-checks passed, evidence level L2.
- 21 tests pass, including tampering with the card, experiment, run file, ledger and report.
- Not done: no research question has been run yet; the queue is empty.

## 2026-10-05: survey and evolution interface

- Surveyed 21 related projects (`docs/SURVEY.md`). Evidence is tool summaries, not primary
  text; every source is recorded with that kind and its hash.
- Added: governor, prediction calibration, card dependencies, notes lint, frozen-core guard,
  mutation self-test (13 corruptions, each must be caught by its intended check), variant archive.
- First self-test run reported 13 of 13, but three notes corruptions were being caught only
  because the report was stale. Fixed so the lint has to catch them; still 13 of 13.
- 54 tests pass. The calibration card still verifies at L2.
- Not done: no research question has been run; no schedule is set.
