# Card and experiment shapes

Read this when writing a card or an experiment module. The worked example is
`cards/auction-calibration.json` with `experiments/auction_calibration.py`.

## Card (`cards/<id>.json`)

| field | meaning |
|---|---|
| `id` | lowercase words joined by `-`; also the file name |
| `title`, `question` | keep `question` short: the report pastes it verbatim |
| `experiment` | module name in `experiments/` (underscores) |
| `params` | JSON object passed to every function |
| `seeds` | list of integers; `run` is called once per seed |
| `hypotheses` | list of `{id, statement, falsifier, predicted_verdict}`; verdict is `supported` or `refuted` |
| `sources` | source ids from `state/sources.jsonl` |
| `depends_on`, `supersedes` | optional lists of card ids |

`python -m autosci new <id>` writes a template; `validate` checks it. `new` does not
touch the queue: add or update the item in `state/QUEUE.md` yourself, in the format
`- [todo|done|blocked] title: idea and direction`.

## Experiment module

- `run(params, seed) -> dict`: JSON-serialisable raw results for one seed.
- `evaluate(params, per_seed) -> {hypothesis_id: {"verdict": ..., "detail": ...}}`.
  `per_seed` maps seed to the `run` output. Put the numbers the notes will quote
  (estimates, bounds, standard errors) in `detail`; lint checks notes against them.
- `crosscheck(params, per_seed) -> list of {name, observed, reference, tolerance, ok}`:
  a different route to the same quantity. Do not import the helpers `run` uses.

## Recording the design review

Put the short version (what refutes each hypothesis, what the control is, what the
cross-check shares with the experiment) in the card's `question` or each `falsifier`.
Put anything long in the journal entry. Notes do not exist before the lock.
