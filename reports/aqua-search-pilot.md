# Matched-budget memory-guided auction search pilot

Card `aqua-search-pilot` · run `8a7a3667c87d41e8` · evidence level **L2**: cross-checked: level 1, and every independent cross-check passed

## Question

Does interval-refinement memory beat paired IID random candidate search on independent first-price auction test samples under the same evaluation-call budget? Random and memory-disabled are intentionally identical controls. This tests a numerical search policy, not an LLM or general recursive scientific improvement. The analytic reference shares the auction distribution and sampled private values, but not the winner simulation.

## Hypotheses (preregistered)

| id | statement | falsifier | predicted | obtained | match |
|---|---|---|---|---|---|
| H1 | Memory-guided interval refinement has positive mean paired test utility gain over IID random search across the fixed seed benchmark. | The paired normal-approximation 95% interval lies wholly below zero; an interval containing zero is inconclusive. Generalization beyond this fixed synthetic auction family is not claimed. | supported | **supported** | yes |
| H2 | All modes use exactly the registered evaluation-call budget; paired random and memory-disabled results agree; every declared malformed candidate is rejected. | Any budget mismatch, control mismatch, or accepted malformed candidate. | supported | **supported** | yes |
| H3 | Negative control: truthful bidding earns positive utility in the first-price auction. | Truthful utility is zero on every seed, as the payment equals one's value upon winning. | refuted | **refuted** | yes |

### Evaluation detail

**H1**

- normal_95_high: 0.00299073
- normal_95_low: 0.00106527
- paired_mean_test_gain: 0.002028
- paired_se: 0.00049119

**H2**

- attacks: 280
- controls_identical: yes
- equal_budget: yes
- rejected: 280

**H3**

- truthful_max: 0

## Independent cross-checks

| check | observed | reference | tolerance | ok |
|---|---|---|---|---|
| test utilities vs analytic opponent CDF (familywise bound) | 0.00744739 | 0 | 0.0227197 | yes |

## Provenance

- seeds: 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234, 235, 236, 237, 238, 239, 240
- card sha256: `434bf2f7d84198caa3a789a7c3f07c439c00ea6bd7feaf8f0800b686a3facd96`
- experiment sha256: `82177d8b0143368c5bbc7d12edcd50ef000e08955ad44580ad00193d9a910c5e`
- results sha256: `b7ae73334ed36a3ece5fd3ad113d93fb7c47159671cc9044dfda18f1042747a9`
- ledger entry: seq 1, `e95d1ddd8e0223e47117d18721e350a505161f0eb20f737567ebce125a7fb3fa`

## Interpretation (author prose, not covered by verification)

The preregistered interval-refinement search hypothesis was supported on the fixed auction benchmark. The paired mean test utility gain was 0.002028, with an approximate interval from 0.00106527 to 0.00299073.

The budget and control hypothesis was supported. All 280 malformed candidate attempts were rejected. The truthful-bidding negative control was refuted.

[conjecture] These results motivate evaluating constrained search interfaces in further research tasks. They do not establish that an LLM improves its research ability, that persistent semantic memory is useful, or that the policy transfers to financial markets. The numerical search policy encodes an interval-refinement prior suited to this auction family.

[conjecture] The independent analytic check tests utility calculations, rather than proving every component of the search implementation correct. The normal approximation across the fixed seeds is a descriptive benchmark interval.

_notes sha256: `6c479d18e4664bb60213d9490219fdb80a98e2c5f6d408d2aa6d64c41ffd7cdf`_
