# Fixed US-equity proxy: preregistered, not yet a reproduction result

This study is locked before model training and test scoring. It approximates the
paper's minute-equity task, but cannot establish an exact replication: the original
factor pool, full universe and model details are unavailable. Fixed surviving
stocks and unresolved public-source adjustments further limit interpretation.

The public candidate is [ggaddam/OHLCV-1m](https://huggingface.co/datasets/ggaddam/OHLCV-1m),
revision `ef1551b11d8ee3e35c7521cf36deee155b43e77d`. Its dataset-card summary does
not match the actual file inventory. Source coverage ends in July 2025; licensing
and corporate-action adjustment provenance are not established. Raw and derived
prices are local, ignored artifacts and are not included in this repository.

## Protocol

- Fixed AAPL, MSFT, JPM and XOM, one-minute New York regular-session data.
- Identical duplicate minutes are merged; conflicting minutes are dropped. No
  imputation; invalid or incomplete feature windows are excluded.
- Sixty-four-minute histories, eleven causal price/volume/time features, training-only
  normalization. Thirty-minute open-to-open targets start one full minute after
  the last observed bar closes, with no overlap or overnight holding.
- Training 2010-2017, validation 2018-2019, full 2020 embargo, test 2021-July 2025.
- CNN32 Huber, CNN32 Huber plus IC penalty, CNN64 Huber plus IC penalty; GRU32
  Huber and GRU32 Huber plus IC penalty as controls. All share cross-stock attention
  and ticker identity parameters. Three seeds each; ridge is an additional control.
- At most twenty epochs, five-epoch validation-IC patience, AdamW learning rate
  0.0003. Test outcomes never determine configuration, checkpoint or trading rule.
- CNN and GRU configurations maximize absolute mean per-stock validation Pearson
  IC, with validation-only sign calibration. The half-long/half-short portfolio
  buys the greatest forecast and sells the least. Dispersion thresholds are the
  validation 50th/75th/90th percentiles. Cash is chosen if no eligible validation
  rule with at least one hundred active intervals earns positive net PNL.
- Contiguous interval positions are netted; session gaps liquidate. Cost is one
  basis point per absolute unit notional traded, five basis points under stress.
  PNL uses fixed notional; borrow and financing beyond those costs are unknown.

The [frozen plan](../research/equity_plan.json) pins sources and the joint decision
rule: positive IC lower bound, positive incremental IC lower bound versus the
validation-selected GRU, positive mean daily net PNL lower bound with at least one
hundred active test intervals, positive stress PNL, and nonnegative PNL in every
observed test year. Intervals use one thousand resamples of twenty trading-day
blocks. Failure of this conjunction does not prove absence of profitable signals.

## Status and rerunning

The card `aqua-equity-proxy` is locked; collection/training/evaluation is in progress.
No test scores are reported here. The six synthetic data/accounting checks and
GPU forward/backward/optimizer smoke passed before training. The optional data
environment is separate from the optional PyTorch training environment and the
framework's standard-library core.

Pass separate local directories to these commands; do not add cached prices or
forecast labels to a public PR:

```text
python research/equity_collect.py --output CACHE --workers 6
python research/prepare_equity.py --cache CACHE --output PREPARED
```

Before training, write `PREPARED/plan.json` with `trainer_sha256` from the frozen
source plan, `inputs_sha256` from the prepared quality record, and
`source_plan_sha256` from `research/equity_plan.json`. The trainer refuses a mismatch.

```text
python research/train_equity.py --inputs PREPARED --output MODELS --device cuda
```

Copy `forecasts.npz` and `training.json` to ignored `research/equity_artifacts/`,
then run/report/verify the locked card. This optional card needs NumPy and local
artifacts; unlike the prior exported BTC forecasts, its input prices/labels are
not shipped. Verification replays pinned-source forecast evaluation, not original
model recovery, GPU training or public-source correctness.
