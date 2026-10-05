# autoscientists

[![CI](https://github.com/shentonyan/autoscientists/actions/workflows/ci.yml/badge.svg)](https://github.com/shentonyan/autoscientists/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.10%E2%80%933.13-blue)
![dependencies](https://img.shields.io/badge/dependencies-none-lightgrey)
![status](https://img.shields.io/badge/status-v0.3%2C%20no%20research%20results%20yet-orange)

A small framework for running research questions as pre-registered, checkable
computations, designed to be driven by an AI agent and checked without trusting it.

![The research loop](docs/img/workflow.svg)

Before an experiment runs, its hypotheses and the outcomes that would refute them are
written down and hashed. After it runs, a separate step re-executes it, compares the
result with an independently computed reference, and generates the report from
recorded data. Free-text interpretation is kept apart and labelled as unverified.
`PROTOCOL.md` has the rules and their limits.

Standard library only. CI runs Python 3.10 to 3.13.

## Try it in two minutes

```
git clone https://github.com/shentonyan/autoscientists
cd autoscientists
python -m autosci --root examples/quickstart verify dice-sum
python -m autosci selftest
```

The first command re-executes a finished example and checks it against an exact
enumeration. The second corrupts a copy of the repository on purpose, 13 different
ways, and requires the verifier to notice each one. `docs/TUTORIAL.md` walks through
the example.

## What it checks

![Self-test matrix](docs/img/selftest.svg)

The calibration card reproduces two sealed-bid auction results known in closed form and
refutes one claim known to be false. The simulation and the closed form agree:

![Calibration](docs/img/calibration.svg)

Results get an evidence level, and the ledger is hash-chained:

![Evidence ladder](docs/img/evidence.svg)

![Ledger](docs/img/ledger.svg)

## Who may change what

![Trust tiers](docs/img/tiers.svg)

The framework's own checks are frozen: changes to them need the maintainer, and
`python -m autosci guard --base origin/main` lists them. Other parts can be proposed as
recorded variants and measured against a fixed benchmark before review
(`docs/EVOLUTION.md`).

## Using it with an AI agent

| you use | do this |
|---|---|
| Claude Code | open the repository; the `autoscientists` skill in `.claude/skills/` triggers when you give it a research idea. `CLAUDE.md` imports `AGENTS.md`. |
| another coding agent | point it at `AGENTS.md`; the procedure is `.claude/skills/autoscientists/SKILL.md` |
| no agent | run the commands yourself, see `docs/TUTORIAL.md` |

Ideas go in `state/QUEUE.md`. The agent takes one per wake-up, opens a **draft** pull
request, and stops at the first failed verification. Frequency and scheduling are up to
you; nothing in the repository schedules itself.

## Commands

```
python -m autosci new my-card        # write an empty card
python -m autosci cycle my-card      # validate, lock, run, report, verify
python -m autosci verify my-card     # re-execute and check independently
python -m autosci lint my-card       # notes: numbers and sources must be grounded
python -m autosci status             # cards, ledger chain, sources
python -m autosci govern             # should the loop stop and ask a human?
python -m autosci calibration        # how often predicted verdicts matched
python -m autosci guard --base origin/main   # changes to the frozen core
python -m autosci selftest           # corrupt a copy on purpose
python -m autosci evolve status      # variant archive
python -m unittest discover -s tests
python scripts/make_figures.py       # regenerate docs/img/*.svg
```

An experiment is a file in `experiments/` with `run`, `evaluate` and `crosscheck`.
Shapes are in `.claude/skills/autoscientists/card-schema.md`.

## Layout

| path | contents |
|---|---|
| `autosci/` | the framework (frozen core) |
| `cards/`, `experiments/` | research cards with locks; experiment modules |
| `runs/`, `reports/` | one JSON record per run; generated reports and `*.notes.md` |
| `state/` | ledger, variant archive, source registry, governor limits, manifest, queue, journal |
| `examples/quickstart/` | a complete, self-contained example |
| `.claude/` | skills, read-only reviewer agent, permission settings |
| `docs/` | `ARCHITECTURE.md`, `TUTORIAL.md`, `EVOLUTION.md`, `SURVEY.md`, figures |
| `scripts/` | figure generator |
| `tests/` | tests, including deliberate tampering |

## Limits

Checks here catch edits, missing cross-checks, uncited sources, unsupported numbers in
notes and irreproducible results. They do not establish that a question is the right
one, that a model fits reality, or that a source is correct. The independent reviewer is
the same model family as the author. See section 9 of `PROTOCOL.md`, and the FAQ in
`docs/ARCHITECTURE.md`.

## Contributing and security

See `CONTRIBUTING.md` and `SECURITY.md`. Pull requests carry a disclosure line; see
`.github/PULL_REQUEST_TEMPLATE.md`.
