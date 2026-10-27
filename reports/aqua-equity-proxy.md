# Fixed four-stock minute-panel proxy, 2021-2025 holdout

Card `aqua-equity-proxy` · run `e60e949f7ed4c1dc` · evidence level **L2**: cross-checked: level 1, and every independent cross-check passed

## Question

Pre-training-frozen CNN/temporal/cross-stock attention ensembles versus validation-selected GRU. Fixed four survivors and unresolved source adjustment provenance make this a proxy, not original AQuA reproduction. Success requires all five frozen component conditions. Forecast artifacts are local and not redistributed. Independent scalar covariance and round-trip-netting checks share the forecasts and market assumptions, not evaluator helper functions.

## Hypotheses (preregistered)

| id | statement | falsifier | predicted | obtained | match |
|---|---|---|---|---|---|
| H1 | Validation-selected CNN mean per-stock test Pearson IC is positive. | Twenty-trading-day block interval wholly below zero refutes; zero-containing interval is inconclusive. | inconclusive | **inconclusive** | yes |
| H2 | Validation-selected CNN test IC improves over validation-selected GRU. | Paired twenty-day block IC-difference interval wholly below zero refutes; zero-containing interval is inconclusive. | inconclusive | **inconclusive** | yes |
| H3 | CNN strategy has positive mean daily net PNL after one bp per unit absolute turnover. | A wholly negative twenty-day block interval refutes; zero-containing interval or fewer than one hundred active intervals is inconclusive. | inconclusive | **refuted** | NO |
| H4 | Increasing turnover cost from one to five bp increases PNL on fixed positions. | With nonzero turnover, lower stress PNL refutes; zero turnover is inconclusive. | refuted | **refuted** | yes |
| H5 | The fixed proxy satisfies every predeclared empirical success component. | Any of IC lower bound, incremental IC lower bound, costed mean daily PNL lower bound with sufficient activity, positive stress PNL, or nonnegative each-year PNL fails. This is a joint decision rule, not proof that no profitable rule exists. | refuted | **refuted** | yes |

### Evaluation detail

**H1**

- absolute_validation_ic: {'cnn32': 0.030293428963321625, 'cnn32_ic': 0.034304731951160766, 'cnn64_ic': 0.029078710990905154, 'gru32': 0.020307366051559153, 'gru32_ic': 0.02334854062769087, 'ridge': 0.004583555437300601}
- chosen_cnn: cnn32_ic
- chosen_gru: gru32_ic
- evaluator_sha256: dee3a87207ba6c84b3b4b32826409f4f70c7066485764f1302180ce785a065ab
- forecasts_sha256: 76695ccdc0ea9c80ee47eafcac34dd0b7b4c78c195f161b651df9c77a0d29407
- joint_proxy_success: no
- mean_daily_pnl_ci: [-0.00030017727503127997, -1.0584759661531993e-05]
- primary_ic_ci: [-0.03690287210408382, 0.01874551375248172]
- primary_minus_gru_ic_ci: [-0.02469867807430825, 0.004628093860313059]
- results: {'cnn32': {'active_intervals': 1829, 'annualized_daily_sharpe': -0.7566335080816393, 'ic': -0.007748681109170507, 'per_stock_ic': [-0.0029025424877818324, -0.010806662372984163, -0.020105097484885585, 0.002819577908969553], 'pnl': -0.14893274074388335, 'stress_pnl': -1.3265327407438836, 'turnover': 2944.0, 'yearly_pnl': {'2021': -0.00886674794976167, '2022': -0.05730044483535986, '2023': -0.03251436979998077, '2024': -0.017002937443324824, '2025': -0.03324824071545622}}, 'cnn32_ic': {'active_intervals': 1613, 'annualized_daily_sharpe': -0.9295826959135784, 'ic': -0.00933167114816031, 'per_stock_ic': [0.002610500339229283, -0.012461556642444726, -0.01773304817227712, -0.009742580117148675], 'pnl': -0.1920784716633342, 'stress_pnl': -1.2536784716633345, 'turnover': 2654.0, 'yearly_pnl': {'2021': -0.0733969116076866, '2022': -0.04027024932211426, '2023': -0.00864560813047284, '2024': -0.015736036839008254, '2025': -0.05402966576405226}}, 'cnn64_ic': {'active_intervals': 0, 'annualized_daily_sharpe': None, 'ic': -0.0025823803070736742, 'per_stock_ic': [0.007776968026473712, -0.009147666967150544, -0.01354797757341929, 0.004589155285801425], 'pnl': 0.0, 'stress_pnl': 0.0, 'turnover': 0.0, 'yearly_pnl': {'2021': 0.0, '2022': 0.0, '2023': 0.0, '2024': 0.0, '2025': 0.0}}, 'gru32': {'active_intervals': 0, 'annualized_daily_sharpe': None, 'ic': -0.008895735423753286, 'per_stock_ic': [0.0050367284147773035, -0.02352706547795989, -0.00680470489280506, -0.010287899739025497], 'pnl': 0.0, 'stress_pnl': 0.0, 'turnover': 0.0, 'yearly_pnl': {'2021': 0.0, '2022': 0.0, '2023': 0.0, '2024': 0.0, '2025': 0.0}}, 'gru32_ic': {'active_intervals': 0, 'annualized_daily_sharpe': None, 'ic': 0.0002492695638795687, 'per_stock_ic': [0.009162016817464733, -0.01206890439078227, 0.006459949731973313, -0.0025559839031375022], 'pnl': 0.0, 'stress_pnl': 0.0, 'turnover': 0.0, 'yearly_pnl': {'2021': 0.0, '2022': 0.0, '2023': 0.0, '2024': 0.0, '2025': 0.0}}, 'ridge': {'active_intervals': 0, 'annualized_daily_sharpe': None, 'ic': -0.002356427734617697, 'per_stock_ic': [-0.010245367764075615, -0.024742973553564373, 0.005952892303290096, 0.019609738075879107], 'pnl': 0.0, 'stress_pnl': 0.0, 'turnover': 0.0, 'yearly_pnl': {'2021': 0.0, '2022': 0.0, '2023': 0.0, '2024': 0.0, '2025': 0.0}}}
- scope: four fixed survivors; unknown corporate-action adjustment; partial 2025; not original AQuA replication
- success_components: {'incremental_ic': False, 'nonnegative_each_year': False, 'positive_costed_pnl': False, 'positive_ic': False, 'positive_stress_pnl': False}
- training_receipt_sha256: 7e86ff944651c4ebf6ee54b81d277036c34d8da9c2ca4d5186727f97b093d6ce
- validation_selections: {'cnn32': {'cutoff': 8.572974197583032e-05, 'quantile': 0.9, 'sign': 1, 'validation_net_pnl': 0.02923718473066969}, 'cnn32_ic': {'cutoff': 0.00015305958312485378, 'quantile': 0.9, 'sign': 1, 'validation_net_pnl': 0.005450037722558919}, 'cnn64_ic': {'cutoff': None, 'quantile': None, 'sign': 1, 'validation_net_pnl': 0.0}, 'gru32': {'cutoff': None, 'quantile': None, 'sign': 1, 'validation_net_pnl': 0.0}, 'gru32_ic': {'cutoff': None, 'quantile': None, 'sign': 1, 'validation_net_pnl': 0.0}, 'ridge': {'cutoff': None, 'quantile': None, 'sign': 1, 'validation_net_pnl': 0.0}}

**H2**

- interval: [-0.02469867807430825, 0.004628093860313059]

**H3**

- active_intervals: 1613
- annualized_daily_sharpe: -0.929583
- ic: -0.00933167
- per_stock_ic: [0.002610500339229283, -0.012461556642444726, -0.01773304817227712, -0.009742580117148675]
- pnl: -0.192078
- stress_pnl: -1.25368
- turnover: 2654
- yearly_pnl: {'2021': -0.0733969116076866, '2022': -0.04027024932211426, '2023': -0.00864560813047284, '2024': -0.015736036839008254, '2025': -0.05402966576405226}

**H4**

- pnl: -0.192078
- stress_pnl: -1.25368

**H5**

- incremental_ic: no
- nonnegative_each_year: no
- positive_costed_pnl: no
- positive_ic: no
- positive_stress_pnl: no

## Independent cross-checks

| check | observed | reference | tolerance | ok |
|---|---|---|---|---|
| cnn32 scalar centered correlation and round-trip netting | -0.148933 | -0.148933 | 1e-09 | yes |
| cnn32_ic scalar centered correlation and round-trip netting | -0.192078 | -0.192078 | 1e-09 | yes |
| cnn64_ic scalar centered correlation and round-trip netting | 0 | 0 | 1e-09 | yes |
| gru32 scalar centered correlation and round-trip netting | 0 | 0 | 1e-09 | yes |
| gru32_ic scalar centered correlation and round-trip netting | 0 | 0 | 1e-09 | yes |
| ridge scalar centered correlation and round-trip netting | 0 | 0 | 1e-09 | yes |

## Provenance

- seeds: 20261027
- card sha256: `2fb0a55f016f5a9810349f8f7afef1daeb23c8c3d36ad83759d01a26c5a1b3ce`
- experiment sha256: `ab181737a1a4da8a36fb372b6fb8940c28372a573dd7844ca8c0fbd80e0d71a3`
- results sha256: `d7c9933203a5f3b1d3a58d43fc451726cf13298809261c7d424307222660601b`
- ledger entry: seq 5, `9b16b2272657cbd1d8e28c96f1c43153d3cffdda8da9cee54ea487b34fdce9f0`

## Interpretation (author prose, not covered by verification)

_none written_
