---
name: autoscientists
description: Run one research question through the AutoScientists pre-registered, verification-first loop - design a card, lock it, run it, re-verify it independently, write grounded notes, and open a draft pull request. Use this whenever the user gives a research idea, hypothesis, or question to test computationally, asks to continue the research loop, work the queue, run a card, or "wake up" the loop, or mentions pre-registration, cards, the ledger, or autosci - even if they do not name the skill.
when_to_use: Also use for "verify this result", "why did verify fail", or "write notes for this card".
---

# AutoScientists loop

You turn one idea into one pre-registered, independently checked result. The point of
every step is that a reader can tell what was claimed *before* the data existed, what
the data actually said, and which sentences are only your opinion. Skipping a step
usually produces something that looks finished and cannot be trusted, so follow the
order. `PROTOCOL.md` has the reasoning; read it once if you have not.

## Hard limits (a human owns these)

- One card per wake-up. Stop when it is finished or blocked.
- Run `python -m autosci govern` first, and `govern --card <id>` once the card exists.
  If it says STOP, write the reason in `state/journal.md` and stop. Limits live in
  `state/governor.json`; they are not yours to change.
- Stop at the first failed `verify`. Record it. Do not work around it.
- Never push to `main`, never merge, never edit files listed in `state/protected.json`
  (the frozen core). If a change there seems necessary, write the proposal in the
  journal and stop. `docs/EVOLUTION.md` explains the tiers.
- Everything you push ends with the Disclosure line (see Publishing).

## Procedure

1. **Preflight.** `git pull` (skip if there is no remote), then
   `python -m autosci status`, `govern`, `guard`, and
   `python -m unittest discover -s tests`. A broken ledger chain, a frozen-core
   mismatch, or a failing test means stop and journal it, even if it predates your
   work: you cannot tell a legitimate change from tampering, the maintainer can.
2. **Pick the work.** Take the first `todo` item in `state/QUEUE.md`. If the user gave
   an idea directly, use that and add it to the queue as `todo` first so it is
   tracked. Nothing to do: one journal line, stop.
3. **Design review before locking.** Use the `autosci-card-design` skill. A locked card
   cannot be fixed, only superseded, so spend the effort here.
4. **Sources, only if the idea needs prior work.** Use the `autosci-sources` skill.
   Never cite something you did not read.
5. **Write the card and experiment.** `python -m autosci new <id>`, fill in the card,
   write `experiments/<module>.py` with `run`, `evaluate`, `crosscheck`. Field and
   return shapes are in `card-schema.md` next to this file. Set `predicted_verdict` on every hypothesis
   *before* running; this feeds calibration. Use `depends_on` / `supersedes` when the
   card builds on or revises another.
6. **Cycle.** `python -m autosci cycle <id>` (validate, lock, run, report, verify).
7. **If verify fails:** do not touch locked files. Journal what failed. If the design
   was wrong, make a new card id.
8. **Notes.** Write `reports/<id>.notes.md`. Every number must appear in the recorded
   results. Tag anything that is not a plain statement of a recorded result:
   `[conjecture]` for opinion, `[context]` plus `[src:ID]` for background. Then
   `python -m autosci report <id>` and `python -m autosci lint <id> --strict`. Resolve
   every `DATA_NEEDED` and `CITATION NEEDED` marker.
9. **Independent review.** Start the `autosci-reviewer` subagent (defined in
   `.claude/agents/autosci-reviewer.md`, read-only) with only the card,
   the generated report and the notes. Do not tell it how they were made. Journal what
   it found, and say it is the same model family, so it is a weaker check than review
   by a different model or a person.
10. **Journal and publish.** One entry in `state/journal.md` (at most ten lines,
    including what you did *not* establish), set the queue item to `done` or `blocked`,
    commit on `loop/<id>`, push, open a **draft** PR.

## Reading the output

`calibration` prints "excluded calibration cards: N": N counts hypotheses on cards
whose id contains "calibration"; they are left out of the hit rate. Below 10 counted
predictions the hit rate means nothing; say so rather than quoting it.

## Reporting results honestly

Report the verdict the verifier produced, not the one you hoped for. A refuted
hypothesis is a result. If calibration or governor flags something, say so. In the
journal and PR, separate "recorded and re-verified" from "my interpretation" from
"not established".

## Publishing

Every commit message and PR body contains this line, verbatim, as its own final
paragraph (a `Co-Authored-By:` trailer may follow it in commits):

`Disclosure: produced by the AutoScientists research loop; this PR was prepared with an AI assistant and is reviewed by the maintainer.`

It becomes true only after the maintainer reviews, hence draft PRs. Keep personal
information out of files and history: no emails, machine details, local paths, or
private projects. Never put tooling-session links in commit or PR text. Commit under the maintainer's
configured git identity, not a personal email.

## Changing the framework itself

Only tier 1 (this skill, `loop/AGENT.md`, new experiments, docs) may be changed by the
loop, as a variant: branch, edit, then
`python -m autosci evolve propose --component <file> --parent <id> --note "<what it should improve>" --base origin/main`.
If the gate fails, say so in the PR; never weaken the benchmark to pass it.
`evolve adopt` is the maintainer's.

## Command reference

`new`, `validate`, `lock`, `run`, `verify`, `report`, `cycle`, `status`, `source-add`,
`govern`, `calibration`, `lint`, `guard`, `selftest`, `evolve`. Use
`python -m autosci <command> --help` for flags. `--root <dir>` runs against another
checkout, for example `examples/quickstart`.
