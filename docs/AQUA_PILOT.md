# AQuA-inspired restricted research and quantitative pilot

This adds application-level constrained candidate search and validation-only
memory without changing the verifier. It is an independent implementation of
disclosed design patterns, not a reproduction of AQuA's undisclosed factors or
model. Paper: [AQuA v3](https://arxiv.org/abs/2608.12841v3).

## Recorded results

The locked `aqua-search-pilot` card compares twelve evaluation calls per policy
over forty fixed seeds. Memory-guided interval refinement has a paired mean
test-utility improvement of 0.002028; the normal-approximation interval is
[0.00106527, 0.00299073]. The verifier reports L2. Every one of the 280 declared
malformed candidate attempts is rejected; the truthful-bidding negative control
is refuted. See the generated [report](../reports/aqua-search-pilot.md).

This is a numerical search policy with an interval-refinement prior. It does not
establish improvement in LLM research ability or semantic memory. Random and
memory-disabled are the same paired control, not separate independent methods.
Equal evaluation-call budgets do not imply equal wall-clock cost.

The independent crypto pilot uses BTCUSDT, ETHUSDT and BNBUSDT spot five-minute
bars from January through June 2024. January–March is training, April is
validation, and May–June is testing. All eighteen archives match the exchange's
published SHA256 checksums. The input is 157248 asset-bars; the test comprises
2927 non-overlapping thirty-minute periods per asset after boundary purging.

| Selected predictor | Mean per-asset test Spearman IC | Gross return | Net return at 1bp one-way | Net annualized Sharpe |
|---|---:|---:|---:|---:|
| Factor (both search policies select the same candidate) | 0.066783 | -2.103% | -25.173% | -9.808 |
| Ridge baseline | 0.002960 | +1.745% | -27.234% | -10.401 |

These are short-period hypothetical dollar-neutral portfolios. IC is an
average of per-asset time-series Spearman correlations; it is neither the
paper's combined-factor metric nor its equity Pearson metric. Positive IC does
not guarantee positive portfolio returns. The pilot provides no evidence that
memory improves trading results. No parameters were adjusted to improve these
test results after viewing them.

The cost is charged on absolute traded notional, including final liquidation:
1bp one-way equals 2bp for entering and exiting an unchanged unit exposure.
The code also records 0, 2 and 5bp one-way cost sensitivity. There is no claim
that this accounting exactly matches the paper's cost convention.

## Reproduce

Use an explicit Python interpreter. The quantitative extension was checked with
Python 3.12 and NumPy 2.5.3; `research/requirements.txt` is optional and separate
from the standard-library-only core. From the repository root:

```text
python -m autosci verify aqua-search-pilot --strict
python research/check_pilot.py
python research/quant_pilot.py fetch
python research/verify_quant.py
python research/quant_pilot.py run --out research/results/new-run
```

The replay command checks newline-normalized selection and metrics and reports
raw byte identity separately (Git LF and Windows CRLF can differ), plus sixty-four
scalar portfolio comparisons using a separately written algorithm. The scalar
audit shares input data and signals; it checks accounting, not the correctness
of market data or the economic mechanism. Quant results do not carry an autosci
L2 certification. Existing result directories cannot be overwritten by `run`.

Data source and format: [Binance public data](https://github.com/binance/binance-public-data).
Archive URLs and hashes are in `research/data/provenance.json`. Run `fetch` to
restore data if it is absent; large archives are excluded from Git.

## What changed

- `experiments/aqua_search.py`: self-contained locked auction experiment with a
  strict declarative bid interface, paired controls and an analytic utility check.
- `research/quant_pilot.py`: registered factor candidates, fixed time splits,
  ridge selection on validation only, next-open execution, purged non-overlapping
  labels and turnover-cost sensitivity.
- `research/research_memory.py`: scoped, hash-chained validation history. No test
  result field is accepted. The scope fingerprints train/validation data and code.
- `research/verify_quant.py`: byte replay and an independent scalar P&L audit.
- `research/check_pilot.py`: future-perturbation, label timing, round-trip cost,
  candidate rejection, ties and cross-run memory tests.

For a continuing validation search, use a separate result directory each time:

```text
python research/quant_pilot.py run --out research/results/memory-round-1 --memory research/memory/crypto.jsonl
python research/quant_pilot.py run --out research/results/memory-round-2 --memory research/memory/crypto.jsonl
python research/verify_quant.py --out research/results/memory-round-2
```

Each run stores its pre-run ledger snapshot for replay. Continuing runs have
additional accumulated search budget; compare them only with controls using the
same cumulative budget. The registry has thirty-six candidates and refuses to
silently recycle exhausted candidates. Repeated tests on this already viewed
May–June window are retrospective diagnostics, not fresh out-of-sample evidence.
Concurrent writers to the same memory file are not supported.

## Boundaries and next work

The interface is not an OS sandbox, nor a cryptographic barrier preventing a
human or process from reading tests. The chain detects record edits but cannot
prevent complete chain rewriting. Checksums authenticate downloaded bytes
against published checksums, not the economic accuracy of those bytes.

No LLM API is called. Candidate proposals use numerical search. A later agent
adapter must emit only the registered schema and retain the same evaluator.
There is no evidence yet for cross-run memory improving real-market performance.

The paper withholds deployed factor expressions, exact convolutional settings,
feature construction, normalization and labels. Its Part I uses crypto signals
including open interest and flow; this first pilot uses spot OHLCV only and
does not reconstruct those mechanisms. Its Part II uses 2010–2019 intraday US
equity training, a 2020 embargo and 2021–2025 tests; neither that data nor the
CNN/attention hybrid is supplied by this pilot. The example DSL in the paper
is illustrative and is not treated as the actual model specification.

The next public-data extension should add futures open interest and taker-flow
events, a separate later test window, an LLM proposal adapter and a declared
hybrid-model implementation. Equity experiments require a historical intraday
dataset with corporate-action treatment and a point-in-time universe. Any such
extension must declare its differences from AQuA before final testing.

Borrow fees, perpetual funding, bid/ask spread, impact and latency are omitted.
Short positions on spot data are hypothetical. No live trading is implemented.

## Protection manifest reconciliation

The fresh upstream checkout at `8148ecc` failed its own guard because the
manifest predated the current version file and two added test files. The
maintainer explicitly authorized updating those three manifest entries.
No protected implementation or existing test was changed. Guard now passes.
