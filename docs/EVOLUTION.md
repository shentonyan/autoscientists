# Evolution policy

How the framework may change itself, and what stops it from changing the thing
that judges it. This is a staged, gated path toward self-improvement. It is not
autonomous self-modification: nothing here merges without the maintainer.

## What exists

- `python -m autosci evolve propose`: records a change as a *variant* (the files it
  touches with their hashes, its parent, a note), runs the benchmark on it and
  records the result in the hash-chained archive `state/archive.jsonl`.
- `python -m autosci evolve status`: shows the lineage and each variant's gate result.
- `python -m autosci evolve adopt`: records, after the maintainer has merged a
  variant, that it was adopted and by whom. It is a record, not a decision.
- `python -m autosci guard --base origin/main`: lists changes to the frozen core
  relative to the approved branch.

## Tiers

| tier | what | who may change it | how |
|---|---|---|---|
| 0, frozen core | `autosci/*.py`, the calibration card and its experiment, `tests/*.py`, `PROTOCOL.md`, this file, `state/governor.json`; the list is `state/protected.json` | the maintainer | a pull request the maintainer authors or approves. The loop may draft a proposal, but `guard --base` will report it as a change to the frozen core. That is intended. |
| 1, gated | `loop/AGENT.md`, new experiments and cards, documentation | the loop proposes, the maintainer merges | record with `evolve propose`; the gate must pass; the pull request stays in draft until reviewed |
| 2, free | notes, queue, journal, runs, reports, the source registry | the loop | normal work |

The reason for tier 0: the evaluator must not be edited by the thing it evaluates.
If the loop could change the verifier, the self-test and the calibration card in
the same pull request that claims an improvement, a passing score would mean
nothing.

## The gate

A variant passes only if all of these hold:

1. the self-test baseline is clean and every deliberate corruption is caught by the
   check meant to catch it;
2. the calibration card verifies at level 2 or better;
3. the unit tests pass;
4. the self-test score is not lower than the parent variant's.

The gate says the numbers are fine. It does not say the change is wise or that it
left the frozen core alone. `tier0_changed` in the variant's entry lists any
frozen-core differences.

## Rules

1. **Evaluator separation.** A change must not both modify tier 0 and claim an
   improvement measured by the tier 0 code it modified. Measure such a change with
   the checker from the approved base checkout, and say so in the pull request.
2. **One purpose per variant**, with a parent and a note that states what it is
   meant to improve.
3. **No benchmark, no claim.** An improvement is stated as a score on the same
   benchmark as its parent. Where there is no automatic score, say that the change is
   a judgment call and let the reviewer decide.
4. **Goodhart.** The self-test measures only the corruptions it lists, and prints
   what it does not measure. A high score is not a safety result. Adding corruptions
   is a tier 0 change.
5. **Bounds.** `govern` decides when to stop. The limits are in a protected file.
6. **Execution.** Experiments are code that runs in the workspace. Model-written
   experiment code is reviewed in the pull request before it merges. If experiment
   code starts to be generated in volume, move execution into a container.
7. **Adoption is the maintainer's.** `evolve adopt` is run after the merge.

## What can be improved automatically, and what cannot

- The verifier's ability to detect tampering has an automatic score, the self-test.
- Changes to the procedure in `loop/AGENT.md` have no automatic score. They are judged
  by the maintainer's review and, over time, by the prediction hit rate from
  `calibration`, which means nothing until there are at least ten predictions.
- Nothing here measures whether research questions are well chosen.

## Not built yet

Held-out calibration cards the loop never sees; tasks with automatic scores on which
strategies could be compared; population search over variants; a reviewer from a
second model family. Each would be added as a variant under this policy.
