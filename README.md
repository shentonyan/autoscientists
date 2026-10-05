# autoscientists

A small framework for running research questions as pre-registered, checkable
computations. Status: v0.2, one calibration card, no research results yet.

The idea is narrow. Before an experiment runs, its hypotheses and the outcomes that
would refute them are written down and hashed. After it runs, a separate step
re-executes it, compares the result with an independently computed reference, and
generates the report from recorded data. Free-text interpretation is kept apart and
labelled as unverified. `PROTOCOL.md` describes the rules and their limits.

Standard library only. Tested on Python 3.13; other versions are untested.

## Use

```
python -m autosci new my-card        # write an empty card
python -m autosci validate my-card
python -m autosci lock my-card       # pre-register
python -m autosci run my-card
python -m autosci verify my-card     # re-execute and check independently
python -m autosci report my-card
python -m autosci cycle my-card      # validate, lock, run, report, verify
python -m autosci status
python -m autosci govern             # should the loop stop and ask a human?
python -m autosci calibration        # how often predicted verdicts matched
python -m autosci lint my-card       # notes: numbers and sources must be grounded
python -m autosci guard --base origin/main   # changes to the frozen core
python -m autosci selftest           # corrupt a copy on purpose; the verifier must notice
python -m autosci evolve status      # variant archive for changes to the framework
python -m unittest discover -s tests
```

An experiment is a file in `experiments/` with three functions: `run`, `evaluate`
and `crosscheck`. See `experiments/auction_calibration.py`.

## Layout

| path | contents |
|---|---|
| `autosci/` | the framework |
| `cards/` | research cards and their locks |
| `experiments/` | experiment modules |
| `runs/` | one JSON record per run |
| `reports/` | generated reports, plus optional `*.notes.md` |
| `state/` | hash-chained ledger and variant archive, source registry and its evidence, governor limits, frozen-core manifest, queue, journal |
| `loop/AGENT.md` | procedure for an AI agent running the loop |
| `docs/SURVEY.md` | what related projects do, with sources and what could not be confirmed |
| `docs/EVOLUTION.md` | how the framework may change itself, and what is frozen |
| `tests/` | tests, including deliberate tampering |

## Calibration

`cards/auction-calibration.json` checks the framework against two sealed-bid
auction results known in closed form, plus one hypothesis known to be false. Its
report is `reports/auction-calibration.md`.

## Changing the framework

The framework's own checks are frozen: changes to them need the maintainer. Other
parts can be proposed as recorded variants and are measured against a fixed
benchmark before review. The rules are in `docs/EVOLUTION.md`.

## Limits

Checks here catch edits, missing cross-checks, uncited sources, unsupported numbers
in notes and irreproducible results. They do not establish that a question is the right one, that a model fits
reality, or that a source is correct. See section 9 of `PROTOCOL.md`.
