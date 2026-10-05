# Contributing

Run the checks before opening a pull request:

```
python -m unittest discover -s tests
python -m autosci selftest
python -m autosci guard --base origin/main
python scripts/make_figures.py --check
```

- Changes to the frozen core (`state/protected.json`) need the maintainer and are listed
  by `guard`. After an approved change, `python -m autosci guard --update` refreshes the
  manifest in the same pull request.
- Cards and locks are immutable once locked. To revise a card, add a new one that sets
  `supersedes`.
- Do not edit generated reports or ledger lines by hand.
- Keep the repository free of personal information.
- Every pull request body ends with the disclosure line in the template when an AI
  assistant prepared it.
- Ideas for the loop: open a "Research idea" issue or add an item to `state/QUEUE.md`.

Standard library only; please do not add dependencies.
