# Extended research: walk-forward policy and hybrid-model confirmation

Neither experiment meets the declared empirical success target. This document
records the complete protocol and negative/inconclusive outcomes, rather than
promoting a test-selected winner. The original undisclosed AQuA factor pool,
equity universe and exact model remain unavailable.

## Frozen 2025 walk-forward policy

The [card and report](../reports/aqua-walk-forward.md) evaluate three consecutive
quarters, April-December 2025. Training expands from July 2024 and ends before
the preceding validation quarter. Each quarter chooses among cash and twelve
OI/rebound candidates (four training quantiles crossed with absent, weak or
strong buy-flow confirmation). Validation selection maximizes mean daily PNL
minus 1.645 standard errors, with at least twenty validation trades except cash.
This penalty is a selection heuristic, not a valid post-selection confidence bound.

The fixed trading cost is 2bp per leg (fee plus extra execution allowance), with
5bp stress. Minimum aggregate test activity is one hundred trades. Joint success
requires positive net and baseline-incremental block intervals, nonnegative
individual quarters and positive stress PNL. The fixed OI-only q90 reference is
the lead from the prior study; the original weak-flow q90 rule is also recorded.

Cash is selected in all three quarters. There are zero trades and zero PNL; the
OI-only reference loses 0.0788169 on initial notional. This is not demonstrated
profitability or a statistically supported improvement. H1/H2 are inconclusive,
H3 (the fee negative control) is inconclusive under zero trades, and H4 is refuted.
The reported zero Sharpe field is a coding convention; conventional Sharpe for
an all-zero series is undefined. The actual run's accounting cross-checks are
zero-trade comparisons; separate synthetic tests exercise nonzero PNL and fees.

All 389 public 2025 archives match their published checksums. The 17504 retained
samples rebuild identically. A separate scalar raw-data audit passes 256
comparisons. The policy is frozen before scores are computed, according to the
operator journal; the hashes do not independently certify chronology or prevent
an operator from accessing test data.

## Independent CNN/attention architecture implementation

The [confirmation report](../reports/aqua-hybrid-confirmation.md) evaluates an
independent model-development pilot, not a replica of a hidden model.

- Training: July 2024-September 2025, 21546 samples.
- Checkpoint/configuration/threshold selection: October-December 2025, 4415 samples.
- Held-out forecast evaluation: January-September 2026, 13103 samples.

Input is a trailing 64-bar history of nine causal features: close/open return,
one-bar close return, log volume, taker-buy fraction, six-bar momentum,
twelve-bar realized volatility, OI change and two known time-of-day encodings.
Feature normalization and target scaling use training observations only. Execution
is delayed by one full additional five-minute bar; targets are non-overlapping
thirty-minute open-to-open returns, with split boundaries purged.

Two hybrid widths (32 and 64) use 3/7-kernel convolutions, a temporal Transformer,
gated last/mean pooling and an MLP head. GRU32 and ridge are baselines. Neural
architectures average seeds 7, 19 and 43: nine seed runs total. Optimizer is
AdamW, learning rate 0.0003, Huber loss, batch 256, at most sixteen epochs,
with four-epoch validation-IC patience. These are our declared choices, not
parameters disclosed by the original paper. The single-contract task has no
equity-panel cross-sectional block or sector-neutral portfolio.

Before training, `research/model_forecasts/plan.json` pins trainer and evaluator
sources, splits, candidate models, sign calibration, threshold quantiles, costs
and success criteria. Selection chooses a CNN width by absolute ensemble
validation IC; sign is calibrated only on validation. For each model, thresholds
are the 80/90/95 percentiles of absolute validation predictions. A model abstains
if no eligible validation threshold earns positive net PNL. Test scores are never
used to change the selected model, sign or threshold.

| Predictor | Global test Pearson IC, validation-calibrated direction |
|---|---:|
| Selected CNN32 ensemble | 0.00589120 |
| CNN64 ensemble, descriptive | 0.00991114 |
| GRU32 ensemble, reference | 0.01843661 |
| Ridge, descriptive | 0.00020524 |

The selected CNN's 14-day-block interval is [-0.01572992, 0.02925058]. Its paired
IC-difference interval versus GRU is [-0.03564201, 0.01243826]. Both contain zero.
Trading rules abstain after validation losses; there are no selected-model test
trades or net gains. All four confirmation hypotheses are inconclusive. CNN64
and GRU's descriptive test scores must not be used to switch the selected model.

## Reproduction and evidence scope

Both cards verify at L3: their recorded computations replay, declared independent
checks pass and checksum documentation is recorded as read. For the model card,
this certifies evaluation of pinned forecasts, not GPU training or the original
architecture's correctness. The source/economic assumptions remain unverified.

The optional training environment used PyTorch 2.9.1 with CUDA 12.8 and NumPy
2.2.6. Current memory headroom and a forward/backward/optimizer smoke were checked
before training. Raw model inputs rebuild identically; checkpoint inference
replays within 1e-7 absolute prediction tolerance. That replay shares model code.
Full nine-member training was independently repeated in a fresh output directory;
every exported prediction matched exactly on the same runtime. This is a
same-runtime repeatability result, not a cross-hardware or original-paper result.

CPU-only evaluation, without PyTorch:

```text
python -m autosci verify aqua-walk-forward --strict
python -m autosci verify aqua-hybrid-confirmation --strict
python research/check_walk_forward.py
python research/check_model_evaluator.py
```

Raw-data reconstruction:

```text
python research/futures_walk_data.py fetch
python research/verify_walk_data.py
python research/futures_model_data.py
```

For optional GPU inference/retraining, use a separate environment matching
`research/requirements-model.txt`, an explicit interpreter and verified live
headroom. Restore the earlier raw futures archives too. Checkpoint files and
the compressed input cache are not committed, while predictions, metadata and
the pre-training plan are. A fresh training run in another output directory is:

```text
python research/retrain_hybrid.py --output new-training-run --device cuda
```

Never replace a locked card's forecasts or input table after a new run. Different
runtime outcomes require new versioned records. The archived run remains the
evidence for its original verdict.

## Closer equity-task data: audit in progress

The public `ggaddam/OHLCV-1m` candidate is being audited before any strategy scores.
Its pinned revision is `ef1551b11d8ee3e35c7521cf36deee155b43e77d`. File listing has
403 monthly files through July 2025; its small README size metadata does not
describe the full listing. It does not provide the entire 2025 calendar year.
Source adjustment handling and license/provenance are not established by the
dataset card alone. Prices are not redistributed in this repository.

The audit preselects AAPL, MSFT, JPM and XOM, checks OHLC bounds and duplicate
timestamps, and records timezone/coverage summaries without model returns. This
fixed survivor panel is not the undisclosed original point-in-time universe.
Independent equity results would require an explicitly frozen processing and
evaluation plan, and could not be labeled exact AQuA replication.
