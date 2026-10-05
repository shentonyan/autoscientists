# Tutorial: one question, start to finish

This walks through `examples/quickstart/`, a complete card that was produced by
following the `autoscientists` skill on a toy question: for two fair dice, is
P(sum >= 10) exactly 1/6, and is P(sum is prime) greater than 1/3? It has its own
ledger, so you can rerun it without touching the main repository.

Commands below use the repository root as the working directory. On Windows
PowerShell the same commands work unchanged.

## 1. Look at what was pre-registered

```
python -m autosci --root examples/quickstart validate dice-sum
```

Open `examples/quickstart/cards/dice-sum.json`. Each hypothesis has a `falsifier`
(the recorded number that would make it false) and a `predicted_verdict`, both written
before any run. H3 is a negative control: it claims 1/5, which is known to be false.

## 2. Check the lock

`dice-sum.lock.json` holds SHA-256 hashes of the card and of `experiments/dice_sum.py`.
Change one character in either and the next command refuses to continue:

```
python -m autosci --root examples/quickstart verify dice-sum
```

## 3. Re-execute and cross-check

`verify` re-runs the experiment and compares it with `crosscheck`, which computes the
same probabilities by exact enumeration with no shared code. Passing means evidence
level L2.

## 4. Read the generated report and the notes

`reports/dice-sum.md` is generated from the ledger. `reports/dice-sum.notes.md` is the
interpretation; every number in it must appear in the recorded results, and opinion is
tagged `[conjecture]`:

```
python -m autosci --root examples/quickstart lint dice-sum --strict
```

## 5. Break it on purpose

Copy the folder, edit a number in the notes, and run `lint` again; it fails. Then run
`python -m autosci selftest` in the main repository to see the same idea applied
systematically (13 deliberate corruptions, each must be caught by its intended check).

## 6. Run your own

Add an idea to `state/QUEUE.md` and ask an agent that has the skills in `.claude/skills/`
to run the loop, or follow `.claude/skills/autoscientists/SKILL.md` by hand. See
`docs/ARCHITECTURE.md` for how the pieces fit.
