# Frozen three-quarter walk-forward OI/rebound research policy

Card `aqua-walk-forward` · run `9ad10ec0892047f6` · evidence level **L3**: sourced: level 2, and every cited source is recorded as verified

## Question

Can a fixed selection algorithm achieve positive and baseline-improving 2025 April-December out-of-sample PNL, with quarterly decisions based exclusively on earlier data? Prior 2024 results motivated the candidate family and are development data. Before any 2025 strategy performance inspection, freeze quarterly expanding training, preceding-quarter validation, thirteen candidates including cash, confidence-penalized selection, two-bp per-leg combined fees/slippage, and five-bp stress cost. Research success requires H1, H2 and H4 supported; this would be an independent crypto result, not replication of undisclosed AQuA factors or its equity model.

## Hypotheses (preregistered)

| id | statement | falsifier | predicted | obtained | match |
|---|---|---|---|---|---|
| H1 | The frozen walk-forward research policy has positive mean daily arithmetic OOS PNL across April-December 2025 after two basis points per leg and fixed-notional funding accrual. | The fourteen-day circular-block bootstrap 95% interval is wholly negative; zero-containing intervals or fewer than one hundred aggregate test trades are inconclusive. | inconclusive | **inconclusive** | yes |
| H2 | The research policy has positive incremental mean daily OOS PNL over the frozen OI-only training-q90 reference, with each threshold estimated solely before the corresponding validation quarter. | The paired fourteen-day-block bootstrap interval is wholly negative; zero-containing intervals or fewer than one hundred strategy trades are inconclusive. | inconclusive | **inconclusive** | yes |
| H3 | Negative economic control: increasing cost per leg from two to five basis points with the same trades increases aggregate arithmetic PNL. | At least one trade and higher costs reduce PNL by the exact declared fee increment; no trades is inconclusive. | refuted | **inconclusive** | NO |
| H4 | Every selected test quarter has nonnegative arithmetic PNL and aggregate PNL remains strictly positive at five-basis-point per-leg stress cost. | Any test quarter is negative or aggregate stress-cost PNL is not strictly positive. | refuted | **refuted** | yes |

### Evaluation detail

**H1**

- annualized_daily_sharpe: 0
- days: 275
- interval: [0.0, 0.0]
- pnl: 0
- trades: 0

**H2**

- interval: [-0.00015234518867879884, 0.0007307201813591664]
- mean_incremental_daily: 0.000286607
- oi_reference_pnl: -0.0788169

**H3**

- base_pnl: 0
- higher_cost_pnl: 0

**H4**

- quarterly_pnl: [0.0, 0.0, 0.0]
- stress_pnl: 0

## Independent cross-checks

| check | observed | reference | tolerance | ok |
|---|---|---|---|---|
| 2025-04-01 independent masks and PNL | 0 | 0 | 1e-10 | yes |
| 2025-07-01 independent masks and PNL | 0 | 0 | 1e-10 | yes |
| 2025-10-01 independent masks and PNL | 0 | 0 | 1e-10 | yes |
| fixed-decision cost decrement | 0 | -0 | 1e-10 | yes |

## Provenance

- seeds: 20261027
- card sha256: `093b68b5a25e5b41ca2b7ca7c07bbf78b85b0d02113d5395267868ea21e5780a`
- experiment sha256: `fa45131ea3a2ee901bbb86e74871d91f8f3bb1e1c2d2ce564024bb237cd956eb`
- results sha256: `6287828e8acaea37fe2e3de26ad059d9a787e7cb57b89643168e66d23bfe07fc`
- ledger entry: seq 3, `a0b3ab50ae1a9e521b5f55f4a21bf39610cdd1cdcf416905d8baddc7b9694ad6`
- cited sources (all recorded as verified; evidence kind in brackets): binance-public-archives (primary-text)

## Interpretation (author prose, not covered by verification)

The policy selected cash in every test quarter and made no trades. Its arithmetic PNL was zero. The software reports zero in the Sharpe field by convention; conventional Sharpe is undefined for an all-zero return series. Both performance hypotheses were inconclusive; the stability and positive stress-PNL hypothesis was refuted. The fee negative control was inconclusive because there were no trades.

The frozen OI-only reference had arithmetic PNL -0.0788169. Avoiding this loss does not establish a statistically supported improvement: the paired interval includes zero and the policy did not meet its minimum test-trade count.

This outcome does not meet the card's stated research-success target. The reported cross-checks are zero-trade comparisons; they do not demonstrate nonzero trade accounting on this particular market outcome.

[conjecture] Abstention is a useful possible output, but this run does not establish a profitable strategy, universal predictive failure of open interest, or faithful replication of undisclosed AQuA results.

The report does not independently timestamp-certify its procedural freeze claims or establish economic correctness from source registration.

_notes sha256: `4702f2bd39c9e5070031eb1b61c7909877677ceddbbf3881233f281a9d767b83`_
