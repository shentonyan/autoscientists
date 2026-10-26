# Public BTC futures: open-interest crash, rebound and weak taker-flow event test

Card `aqua-futures-events` · run `3dadd638fe75c9ca` · evidence level **L3**: sourced: level 2, and every cited source is recorded as verified

## Question

Does an independently specified short filter following a past OI decline, negative prior return and unconfirmed positive rebound show positive test PNL or incremental PNL over a validation-chosen baseline? Training July-August 2024, selection September, final test October-December, all fixed before performance inspection. One unit initial notional per separate 30-minute short; arithmetic, not compounded, PNL. The independent check shares input samples and selected thresholds but separately reconstructs masks and fee-adjusted PNL. The checksum source concerns archive bytes only.

## Hypotheses (preregistered)

| id | statement | falsifier | predicted | obtained | match |
|---|---|---|---|---|---|
| H1 | The validation-selected full OI/rebound/flow filter has positive mean daily arithmetic test PNL after one-basis-point cost per leg and realized fixed-notional funding accrual. | The circular seven-day-block bootstrap 95% interval for mean test daily PNL lies wholly below zero. An interval including zero, fewer than twenty test trades, or no eligible validation candidate is inconclusive. | inconclusive | **inconclusive** | yes |
| H2 | The full filter has positive incremental mean daily test PNL over the reference chosen solely on validation among cash, price-only, OI-only and flow-only baselines at the same per-trade notional; exposure need not be equal. | The paired seven-day-block bootstrap 95% interval for incremental daily PNL lies wholly below zero. Zero-containing intervals or the H1 sample-size gates are inconclusive. | inconclusive | **inconclusive** | yes |
| H3 | Negative economic control: increasing the per-leg trading fee from one to five basis points, with exactly the same trade decisions, increases total arithmetic test PNL. | At least one trade is present and the higher fee lowers total PNL by its exact fee difference; no trades means inconclusive. | refuted | **refuted** | yes |

### Evaluation detail

**H1**

- arithmetic_pnl: -0.0257721
- interval: [-0.0005699684397716192, 1.4395347517754325e-05]
- mean_daily_pnl: -0.000280132
- test_days: 92
- test_trades: 19

**H2**

- incremental_mean_daily_pnl: -0.000280132
- interval: [-0.0005699684397716192, 1.4395347517754325e-05]
- reference: cash

**H3**

- cost_1bp_pnl: -0.0257721
- cost_5bp_pnl: -0.0409721

## Independent cross-checks

| check | observed | reference | tolerance | ok |
|---|---|---|---|---|
| cash independently aggregated short PNL and trade count | 0 | 0 | 1e-10 | yes |
| price_only independently aggregated short PNL and trade count | -0.241826 | -0.241826 | 1e-10 | yes |
| oi_only independently aggregated short PNL and trade count | 0.0903428 | 0.0903428 | 1e-10 | yes |
| flow_only independently aggregated short PNL and trade count | -0.154093 | -0.154093 | 1e-10 | yes |
| full independently aggregated short PNL and trade count | -0.0257721 | -0.0257721 | 1e-10 | yes |
| higher round-trip fee obeys closed-form PNL decrement | -0.0152 | -0.0152 | 1e-10 | yes |

## Provenance

- seeds: 20261027
- card sha256: `9d2acc05b81e5391ba4eb177924ce3397e2242c2ca307e84a90b4885e6bdf658`
- experiment sha256: `95d2e8360411ec37acab09b21bdb77a8d38aa745edfc31a92f8299c7baf1c13e`
- results sha256: `1557071eb98d203755dcf3c15d097fcf7df480adff3422a4b8d3f20559feb1cb`
- ledger entry: seq 2, `7f8b5f5894743a54bf6fcd67c670485616dccce0f556ad56ac14812b04f9966b`
- cited sources (all recorded as verified; evidence kind in brackets): binance-public-archives (primary-text)

## Interpretation (author prose, not covered by verification)

The profitability and incremental-performance hypotheses were both inconclusive. The full filter produced 19 test trades, below the preregistered minimum of 20, and the daily PNL interval includes zero. The full-filter arithmetic PNL was -0.0257721. The validation-selected reference was cash.

The fee negative control was refuted. Increasing the per-leg fee lowered arithmetic PNL from -0.0257721 to -0.0409721 with unchanged trade decisions.

[conjecture] The OI-only baseline's positive test PNL is exploratory. It was not the reference selected on validation and must not be promoted using this already-observed test quarter. This study does not establish that adding weak-flow confirmation improves a deleveraging-rebound strategy.

[conjecture] Source registration and independent recomputation do not prove point-in-time data availability, execution realism or economic validity. Publication latency, fixed-notional funding and fee assumptions remain approximations. This is an independently specified event study, not a reproduction of withheld deployed expressions.

_notes sha256: `4d9f4805055c5c0d38024818fb20c42b124bdfb0e1daa32bde4c09173f944044`_
