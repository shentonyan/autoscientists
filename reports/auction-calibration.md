# Calibration: dominant-strategy truthfulness in second-price versus first-price auctions

Card `auction-calibration` · run `30a5882060691b49` · evidence level **L2**: cross-checked: level 1, and every independent cross-check passed

## Question

Does the research loop reproduce two known results about sealed-bid auctions, and does it refute a hypothesis that is known to be false? Setting: two bidders, values and opponent draws uniform on [0, 1]; second-price opponent bids x, first-price opponent bids x/2 (the equilibrium strategy).

## Hypotheses (preregistered)

| id | statement | falsifier | predicted | obtained | match |
|---|---|---|---|---|---|
| H1 | In a second-price auction, bidding one's value is weakly dominant: no deviation on the bid grid ever beats truthful bidding on any sampled opponent bid. | At least one sample in which some grid bid earns more than the truthful bid by more than 1e-12. | supported | **supported** | yes |
| H2 | In a first-price auction against an opponent bidding x/2, bidding v/2 earns strictly more expected utility than bidding v, for every tested value v. | For some tested v the 95% lower bound of the gain (bid v/2 minus bid v) is not above zero. | supported | **supported** | yes |
| H3 | Negative control. In a first-price auction against an opponent bidding x/2, truthful bidding earns positive expected utility. | The 95% upper bound of truthful expected utility is at or below zero for every tested value. It is known to be exactly zero, so this hypothesis is expected to be refuted. | refuted | **refuted** | yes |

### Evaluation detail

**H1**

- comparisons: 4200000
- max_single_sample_gain: 0
- violations: 0

**H2**

- v=0.2: 95% lower bound: 0.0197825
- v=0.2: gain of bidding v/2 over v (mean): 0.020134
- v=0.4: 95% lower bound: 0.0795165
- v=0.4: gain of bidding v/2 over v (mean): 0.080376
- v=0.6: 95% lower bound: 0.178507
- v=0.6: gain of bidding v/2 over v (mean): 0.179796
- v=0.8: 95% lower bound: 0.318428
- v=0.8: gain of bidding v/2 over v (mean): 0.319832

**H3**

- v=0.2: 95% upper bound: 0
- v=0.2: truthful expected utility (mean): 0
- v=0.4: 95% upper bound: 0
- v=0.4: truthful expected utility (mean): 0
- v=0.6: 95% upper bound: 0
- v=0.6: truthful expected utility (mean): 0
- v=0.8: 95% upper bound: 0
- v=0.8: truthful expected utility (mean): 0

## Independent cross-checks

| check | observed | reference | tolerance | ok |
|---|---|---|---|---|
| second_price: simulated expected utility vs closed form at 84 (value, bid) points | 0 | 0 | 4.0 pooled standard errors per point | yes |
| second_price: best bid on the grid matches the closed-form optimum for every value | yes | yes | exact grid index | yes |
| first_price: simulated expected utility vs closed form at 84 (value, bid) points | 0 | 0 | 4.0 pooled standard errors per point | yes |
| first_price: best bid on the grid matches the closed-form optimum for every value | yes | yes | exact grid index | yes |
| first_price: truthful utility is exactly 0 at v=0.2 | 0 | 0 | 1e-12 | yes |
| first_price: truthful utility is exactly 0 at v=0.4 | 0 | 0 | 1e-12 | yes |
| first_price: truthful utility is exactly 0 at v=0.6 | 0 | 0 | 1e-12 | yes |
| first_price: truthful utility is exactly 0 at v=0.8 | 0 | 0 | 1e-12 | yes |

## Provenance

- seeds: 101, 102, 103, 104, 105
- card sha256: `51ed6f1a46320e4a9af73db2fc7d50606d9becb1fddbc05f3c75ceed717883a6`
- experiment sha256: `4d5889ad0274e3310f56317e0735aeabf7de8ca7a3e9316f42f2f3c0bfe0826e`
- results sha256: `904c0807e55daefde85bc01049f152d8599b9ad2e5418620b15dc7b058c51aec`
- ledger entry: seq 0, `f854c9ed672d620dbb35f9218dcf23e9d69828d493658b8ba2d844f697e69512`

## Interpretation (author prose, not covered by verification)

_none written_
