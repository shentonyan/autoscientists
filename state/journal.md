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

## AQuA implementation preflight
- User requested restricted search, experiment memory, matched-budget controls, and quantitative reproduction.
- Fresh checkout at 8148ecc; working tree was clean before preflight.
- Ledger and source evidence checks passed; governor permits continuation; all 67 tests passed.
- Frozen-core guard failed: autosci/__init__.py differs from the manifest; tests/test_repo_structure.py and tests/test_skills.py are absent from the manifest under a protected pattern.
- These differences exist in origin/main; no implementation changes have been made.
- Stopped as required by the research skill preflight. Maintainer must approve reconciliation of the protection manifest against the reviewed upstream files before research proceeds.
- No claim about search improvement or quantitative performance has been established.

## AQuA pilot design review
- Maintainer explicitly approved reconciling the protection manifest with current upstream files; guard is now clean. No verifier code was changed.
- One new card: fixed candidate interface, paired budgets, independent test draws, negative control, forty preregistered seeds.
- Memory policy is interval refinement, not an LLM. The no-memory arm is explicitly identical to the random policy; this is not three independent algorithms.
- Primary decision uses the paired normal-approximation interval; the analytic CDF check uses a familywise Hoeffding bound.
- Quant work is a separate public-data engineering pilot: fixed splits, delayed execution, non-overlapping labels, checksum-pinned data and cost sensitivity.
- Quant results are not the paper's crypto universe or undisclosed equity model. Borrow, funding and execution realism remain limitations.

## AQuA pilot results and review
- aqua-search-pilot recorded and re-verified at L2; H1 and H2 supported, H3 refuted; strict notes lint passed.
- Quant crypto-v1 replay is byte-identical; a separate scalar portfolio implementation agrees on 64 accounting checks. This is not autosci L2 certification.
- Memory-enabled retrospective rounds also replay from pre-run validation-only snapshots; prior test exposure is disclosed.
- All 67 existing tests and 9 extension checks passed. No verifier implementation or existing test changed.
- A separate read-only reviewer found no unsupported note claims; same model family, not independent human or different-family review.
- Interpretation: numerical auction search improved on this benchmark; crypto profitability and LLM research improvement were not established.
- Not established: original AQuA factors, original US equity CNN/attention model, its headline performance, real execution or memory benefit in trading.

## Futures event study: design before locking
- Direct user continuation: public data only; no original undisclosed expressions or model configurations assumed.
- Fixed July-August 2024 training, September selection and October-December final testing before any candidate performance inspection.
- Six registered OI-quantile/flow-cut configurations; best eligible validation mean daily PNL selects the filter; validation also selects its reference including cash.
- At least five validation trades and twenty test trades; insufficient counts or zero-containing paired block intervals are inconclusive.
- Seven-day circular block bootstrap with two thousand replicates; one fixed seed. This is approximate finite-sample inference, not a universal mechanism claim.
- One full bar execution delay, thirty-minute non-overlapping labels, purged split boundaries, one basis point per leg and realized fixed-notional funding approximation.
- Independent scalar mask/PNL check and closed-form fee control share only pinned sample data and the selected configuration; sixty-four raw sample points passed a separate feature audit.
- Data quality: invalid OI rows are not imputed; assumed five-minute publication lag and up-to-ten-minute as-of staleness are disclosed, not verified historical availability.
- No test-window performance has yet been computed or used for design; later refutations/inconclusive results will be retained.

## Futures event study: results and review
- aqua-futures-events recorded and re-verified at L3; H1/H2 inconclusive, H3 refuted. Strict notes lint passed.
- Full filter: nineteen test trades, below the preregistered twenty-trade minimum; mean-daily bootstrap interval includes zero. Negative PNL retained.
- OI-only is positive in this test quarter but was not the validation-selected reference; no post-test strategy promotion or threshold relaxation.
- All raw archives match published checksums; derived samples rebuilt identically and 256 independent raw alignment checks passed.
- Existing 67 tests plus 9 previous-extension and 7 new futures behavior checks passed; protected core is unchanged.
- Separate read-only reviewer found no substantive unsupported claims; same model family and not independent human or source/provenance review.
- Not established: profitable execution, historical publication latency, LLM improvement or reproduction of the undisclosed original factor pool and equity model.
