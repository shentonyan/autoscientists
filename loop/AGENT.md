# Loop procedure

Instructions for the agent on each wake-up. Read `PROTOCOL.md` first; it explains
why each step exists.

## Governor

- One card per wake-up. Stop when it is finished or blocked.
- Stop at the first failed `verify`. Record it; do not work around it.
- If the last three cards were all `inconclusive`, stop and ask the maintainer
  to look at the question rather than starting a fourth.
- Never push to `main`. Never merge.

## Steps

1. `git pull`, then `python -m autosci status` and `python -m unittest discover -s tests`.
   If the ledger chain is broken or a test fails, stop and write that in
   `state/journal.md`.
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
   Set `predicted_verdict` for each hypothesis before running.
6. `python -m autosci cycle <card-id>`.
7. If `verify` fails: do not edit locked files. Journal what failed. If the design
   was wrong, create a new card id.
8. Write `reports/<card-id>.notes.md` with the interpretation, marking anything
   beyond the recorded results as conjecture, then `python -m autosci report <card-id>`
   to regenerate the report with the notes hash.
9. Add one entry to `state/journal.md` (at most ten lines) and set the queue item
   to `done` or `blocked`.
10. Commit on branch `loop/<card-id>` and push. Open a **draft** pull request.

## Commits and pull requests

- Every commit message and every pull request body ends with this line:

  `Disclosure: produced by the AutoScientists research loop; this PR was prepared with an AI assistant and is reviewed by the maintainer.`

  It is true only once the maintainer has reviewed the pull request, so pull
  requests stay in draft until then.
- Keep the repository free of personal information: no email addresses, machine
  details, local paths, or references to private projects. Commit under the
  maintainer's GitHub noreply identity.
- Do not put links to tooling sessions in commit messages or pull request text.
