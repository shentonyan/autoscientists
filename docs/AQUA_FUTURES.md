# Public futures event study: frozen mechanism test

This follows the [initial pilot](AQUA_PILOT.md) with public BTCUSDT USD-M perpetual
open interest, taker-buy volume and realized funding. It independently specifies
the OI-crash/rebound/weak-flow mechanism described in [AQuA](https://arxiv.org/abs/2608.12841v3);
the deployed expressions in the paper remain undisclosed.

## Protocol frozen before performance inspection

| Stage | UTC dates | Retained non-overlapping samples |
|---|---|---:|
| Training | July-August 2024 | 2847 |
| Configuration and reference selection | September 2024 | 1439 |
| Reserved final evaluation | October-December 2024 | 4413 |

The new final quarter does not overlap the prior pilot's January-June data.
Only data coverage, field layout and alignment were inspected before locking;
no candidate performance was computed until the card was locked. The input CSV,
builder source, card and experiment source are pinned by hashes. Test isolation
is a procedural property; the process has no OS barrier preventing test access.

OI metrics are treated as available five minutes after their timestamp. The
as-of join tolerates at most ten minutes of staleness. A signal formed at a bar's
close enters at the open after a full additional bar, then holds for thirty
minutes. Labels crossing split boundaries are removed; positions do not overlap.
This latency rule is conservative but historical publication times are unverified.

At decision time, the prior thirty-minute OI decline and negative price return
define a deleveraging episode. A positive price rebound over the next thirty
minutes forms the price condition. The full filter additionally requires taker-buy
fraction below a fixed cutoff in this rebound window. A qualifying signal enters
a short; no sign flip is chosen after seeing test results.

The OI thresholds are training quantiles 0.8, 0.9 and 0.95. Buy-flow cutoffs are
0.45 and 0.5: six configurations in total. Selection maximizes validation mean
daily arithmetic PNL among candidates with at least five validation trades.
Using that selected configuration, validation chooses the reference among cash,
price-only, OI-only and flow-only policies. The full filter and all references use
one unit of initial notional per trade; time in the market is not matched.

Each trade pays one basis point on entry and exit, and funding is accrued on
fixed unit notional using realized rates. Funding timestamp jitter is rounded
down to whole seconds, with entry-inclusive/exit-exclusive interval ownership.
This is an approximation: actual mark-price-dependent funding, spread, impact,
latency-dependent fills and exchange fee tiers are not reproduced. PNL is added
arithmetically on initial notional, not compounded into a NAV return. Each trade's
PNL is assigned to its UTC entry date, including trades closing after midnight.

The decision interval is a circular seven-day-block bootstrap with two thousand
replicates on the ninety-two test daily PNL observations, including zero-trade
days. An interval including zero, fewer than twenty test trades, or no eligible
validation configuration produces an inconclusive verdict. This is approximate
finite-sample inference, not a theorem about a market mechanism.

## Data checks

All 196 exchange archives match their published checksums: six monthly kline
archives, six monthly funding archives and 184 daily metric archives. The raw
data contain 52992 price bars, 52990 metric rows and 552 funding records.
There are 305 zero or nonfinite OI observations, all in training dates; no OI is
imputed. The feature builder discards 128 candidate samples when an OI input is
invalid, missing or stale. Additional boundary and warm-up samples are excluded.

A separate scalar audit reconstructed four quantities on each of sixty-four
raw-data sample points: OI decline, forward return, taker-buy fraction and funding.
All 256 comparisons passed. This audit shares source bytes and economic definitions
but does not call the feature-builder sampling helper. Checksums identify bytes
against the publisher's checksum; they do not establish publication timing or
economic truth. Metadata are in `research/futures_data/quality.json` and
`research/futures_data/provenance.json`.

## Recorded results

The chosen configuration is the training 0.9 OI quantile (a log decline threshold
of 0.0046119215) and buy-flow cutoff 0.5. It had eight validation trades; cash was
the reference selected on validation. The resulting test outcomes are:

| Policy | Test trades | Arithmetic PNL on initial notional |
|---|---:|---:|
| Cash, selected reference | 0 | 0.000000 |
| Price only | 1135 | -0.241826 |
| OI only | 108 | +0.090343 |
| Flow only | 227 | -0.154093 |
| Full OI/rebound/flow filter | 19 | -0.025772 |

The full filter's daily mean is -0.000280132, with bootstrap interval
[-0.00056996844, +0.00001439535]. Both preregistered performance hypotheses are
**inconclusive**: the interval includes zero and nineteen trades do not meet the
twenty-trade minimum. The economic fee negative control is **refuted**, as intended.
Raising per-leg costs from one to five basis points lowers full-filter PNL to
-0.040972, exactly matching the closed-form fee increment.

OI-only's positive test outcome is exploratory. It was not the validation-selected
reference. Selecting it now would use the test quarter for model selection, so
no improved strategy is claimed and no minimum trade count was lowered. A new
predeclared evaluation window would be needed for a follow-up claim.

The generated [report](../reports/aqua-futures-events.md) verifies at L3: it
re-executes identically, its six independent checks pass and the cited checksum
documentation is recorded as read. L3 does not mean profitability or that every
scientific assumption is independently verified. This study has no LLM candidate
generation and does not reproduce AQuA's final factor pool or US equity model.

## Reproduce

The experiment module and feature builder use only Python's standard library;
the optional NumPy pilot is not needed. From the repository root, using your
explicit interpreter:

```text
python -m autosci verify aqua-futures-events --strict
python research/check_futures.py
```

The compact, hash-pinned input table is committed for offline CI and re-execution.
For a complete raw-data audit, restore the public archives and run:

```text
python research/futures_data.py fetch
python research/check_futures.py --raw
python research/verify_futures_data.py
```

`fetch` verifies all archives and reuses matching local files. It never replaces a
file with a different checksum silently. To regenerate features, choose a new
directory, since `build` refuses to overwrite an existing sample table:

```text
python research/futures_data.py fetch --data research/futures_data-rebuild
python research/futures_data.py build --data research/futures_data-rebuild
```

The rebuilt sample hash must match `quality.json` on the same runtime; differences
on another runtime must be investigated rather than changing the locked table.
Public archive details: [Binance public data](https://github.com/binance/binance-public-data).
