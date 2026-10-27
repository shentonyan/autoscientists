# CNN/attention ensembles: independent 2026 BTC confirmation

Card `aqua-hybrid-confirmation` · run `55cf5d72f8ec4568` · evidence level **L3**: sourced: level 2, and every cited source is recorded as verified

## Question

Evaluate forecasts from a pre-training-frozen CNN/attention research plan, selected only on 2025 Q4 validation and tested on January-September 2026. Three-seed CNN ensembles are compared with GRU and ridge; signs and 80/90/95 percentile trading thresholds are calibrated on validation, with abstention when no eligible threshold is profitable. The L3 layer replays evaluation of pinned forecasts, not GPU retraining. Research success requires H1/H2/H4 supported and positive stress PNL; this is not the original proprietary equity task.

## Hypotheses (preregistered)

| id | statement | falsifier | predicted | obtained | match |
|---|---|---|---|---|---|
| H1 | The validation-selected CNN ensemble has positive global held-out Pearson IC after validation-only sign calibration. | The fourteen-day block-bootstrap global-correlation interval is wholly negative; intervals containing zero are inconclusive. | inconclusive | **inconclusive** | yes |
| H2 | The validation-selected CNN threshold strategy has positive mean daily arithmetic PNL after two basis points per leg and fixed-notional funding accrual. | The fourteen-day block interval is wholly negative; intervals including zero or fewer than one hundred test trades are inconclusive. | inconclusive | **inconclusive** | yes |
| H3 | Negative economic control: increasing the cost per leg from two to five basis points on fixed trades increases PNL. | At least one trade and increased costs lower PNL; if abstaining the verdict is inconclusive. | refuted | **inconclusive** | NO |
| H4 | The validation-selected CNN ensemble improves global test Pearson IC over the three-seed GRU reference, with signs calibrated only on validation. | The paired fourteen-day block-bootstrap IC-difference interval is wholly negative; zero-containing intervals are inconclusive. | inconclusive | **inconclusive** | yes |

### Evaluation detail

**H1**

- ic: 0.0058912
- interval: [-0.015729921410489265, 0.029250581773954298]
- selected_model: cnn32

**H2**

- interval: [0.0, 0.0]
- pnl: 0
- sharpe: 0
- trades: 0

**H3**

- base_pnl: 0
- higher_cost_pnl: 0

**H4**

- gru_ic: 0.0184366
- interval: [-0.035642007529228574, 0.012438263058873212]

## Independent cross-checks

| check | observed | reference | tolerance | ok |
|---|---|---|---|---|
| cnn32 centered Pearson reference and independent trade accounting | 0.0058912 | 0.0058912 | 1e-10 | yes |
| cnn64 centered Pearson reference and independent trade accounting | 0.00991114 | 0.00991114 | 1e-10 | yes |
| gru32 centered Pearson reference and independent trade accounting | 0.0184366 | 0.0184366 | 1e-10 | yes |
| ridge centered Pearson reference and independent trade accounting | 0.000205243 | 0.000205243 | 1e-10 | yes |

## Provenance

- seeds: 20261027
- card sha256: `3f831dc92957bafb6d267c10c39d895b3c4a70e5a532d8776e41b20bbcd0b82a`
- experiment sha256: `a5e0773d1c68b8514d253ea0ebc3c62f1a105e45a584cef6413660514f423434`
- results sha256: `e5202118df4e36c628b019625b36c6e1e09a615e53719ec34e9e2e3b687e0369`
- ledger entry: seq 4, `bd9966ac2d3039eacac6fb6b08643eef65e531c0c8c2728fdad54451655287b0`
- cited sources (all recorded as verified; evidence kind in brackets): binance-public-archives (primary-text)

## Interpretation (author prose, not covered by verification)

The validation-selected CNN ensemble had test IC 0.0058912 with a zero-containing interval. The GRU test IC was 0.0184366; the paired IC-difference interval also includes zero. Predictive superiority and positive IC were inconclusive.

The selected test strategy had no trades and zero arithmetic PNL. The fee negative control was inconclusive. The report's zero Sharpe field should not be interpreted as conventional Sharpe, which is undefined for an all-zero return series.

This does not meet the card's empirical success target. The L3 result re-executes evaluation of pinned forecasts, not GPU training. Nothing in this report independently establishes training correctness, economic validity or independently certified freeze timing.

[conjecture] These single-contract crypto outcomes cannot establish original AQuA equity performance, or justify selecting another model after seeing test outcomes. Subsequent model changes require a separately declared evaluation design.

_notes sha256: `667ed425ab1c63186f2e4a3c0375534b330f22db02bb4e2cd88c4708268a65e2`_
