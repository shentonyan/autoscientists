# autoscientists

A small framework for running research questions as pre-registered, checkable
computations. Status: v0.1, one calibration card, no research results yet.

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
| `state/` | hash-chained ledger, source registry, queue, journal |
| `loop/AGENT.md` | procedure for an AI agent running the loop |
| `tests/` | tests, including deliberate tampering |

## Calibration

`cards/auction-calibration.json` checks the framework against two sealed-bid
auction results known in closed form, plus one hypothesis known to be false. Its
report is `reports/auction-calibration.md`.

## Limits

Checks here catch edits, missing cross-checks, uncited sources and irreproducible
results. They do not establish that a question is the right one, that a model fits
reality, or that a source is correct. See section 7 of `PROTOCOL.md`.
