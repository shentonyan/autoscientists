# Loop procedure

Instructions for the agent on each wake-up. Read `PROTOCOL.md` first; it explains
why each step exists.

## Governor

- One card per wake-up. Stop when it is finished or blocked.
- Run `python -m autosci govern` first, and `govern --card <id>` once the card
  exists. If it says STOP, write the reason in the journal and stop; the limits are
  in `state/governor.json` and are not yours to change.
- Stop at the first failed `verify`. Record it; do not work around it.
- Never push to `main`. Never merge.
- Never edit the frozen core (listed in `state/protected.json`). If a change to it
  seems necessary, write the proposal in the journal and stop; see
  `docs/EVOLUTION.md`.

## Steps

1. `git pull`, then `python -m autosci status`, `python -m autosci govern`,
   `python -m autosci guard` and `python -m unittest discover -s tests`. If the ledger
   chain is broken, the frozen core differs from its manifest, or a test fails, stop
   and write that in `state/journal.md`.
2. Read `state/QUEUE.md`. Take the first item marked `todo`. If there is none,
   write one line in the journal and stop.
3. **Design review before locking.** Write down, in the card's `question` or in the
   notes, answers to:
   - What outcome would refute each hypothesis?
   - Is there a negative control, a case where the answer is known to be no?
   - Is there an independent cross-check, and does it share code or assumptions
     with the experiment?
   - Is the sample size enough to tell the effect from noise?
   - Is the question answerable by computation or by sources that can be read?
4. If the idea needs prior work, fetch and read the sources. Record each with
   `source-add`. Mark `verified` only with the text that was read as
   `--evidence-file`.
5. Write the card and the experiment module (`run`, `evaluate`, `crosscheck`).
   Set `predicted_verdict` for each hypothesis before running. If the card builds on
   an earlier result, declare it in `depends_on`; if it revises an earlier card,
   set `supersedes`.
6. `python -m autosci cycle <card-id>`.
7. If `verify` fails: do not edit locked files. Journal what failed. If the design
   was wrong, create a new card id.
8. Write `reports/<card-id>.notes.md` with the interpretation. Tag each line that is
   not a plain statement of a recorded result: `[conjecture]` for opinion,
   `[context]` plus `[src:ID]` for background. Then run
   `python -m autosci report <card-id>` to regenerate the report with the notes hash,
   and `python -m autosci lint <card-id> --strict`. Resolve every `DATA_NEEDED` or
   `CITATION NEEDED` marker before the pull request is marked ready.
   **Independent review:** start a separate agent with fresh context. Give it the card,
   the generated report and the notes, and nothing about how they were produced. Ask
   it to list claims in the notes that the report does not support. Record what it
   found in the journal. This is the same model family and is not enforced by code, so
   it is weaker than a cross-family review; say so in the journal.
9. Add one entry to `state/journal.md` (at most ten lines) and set the queue item
   to `done` or `blocked`.
10. Commit on branch `loop/<card-id>` and push. Open a **draft** pull request.

## Changing the framework itself

Only tier 1 files (this file, new experiments, documentation) may be changed by the
loop, as a variant: edit on a branch, then
`python -m autosci evolve propose --component <file> --parent <id> --note "<what it should improve>" --base origin/main`.
If the gate fails, say so in the pull request; do not weaken the benchmark to make it
pass. `evolve adopt` is for the maintainer to run after the merge.

## Commits and pull requests

- Every commit message and every pull request body ends with this line:

  `Disclosure: produced by the AutoScientists research loop; this PR was prepared with an AI assistant and is reviewed by the maintainer.`

  It is true only once the maintainer has reviewed the pull request, so pull
  requests stay in draft until then.
- Keep the repository free of personal information: no email addresses, machine
  details, local paths, or references to private projects. Commit under the
  maintainer's GitHub noreply identity.
- Do not put links to tooling sessions in commit messages or pull request text.
