# Two fair dice: P(sum >= 10) and P(sum is prime)

Card `dice-sum` · run `db7748cce205f4bd` · evidence level **L2**: cross-checked: level 1, and every independent cross-check passed

## Question

For the sum S of two independent fair six-sided dice, is P(S >= 10) equal to 1/6, and is P(S is prime) greater than 1/3? Design notes. Refutation: H1 and H3 are refuted if the pooled 95% interval for P(S >= 10) excludes the claimed value; H2 is refuted if the 95% upper bound is at most 1/3. Negative control: H3 claims 1/5, which is known to be false (exact value 1/6). Cross-check: exact enumeration through the closed form ways(s) = 6 - |s - 7| and a hand-written prime list, sharing no code with the simulation; they share only the parameters. Noise: 5 seeds x 200000 rolls = 1,000,000 rolls, standard error about 0.00037 for P(S >= 10) and 0.00049 for P(S prime); the H2 margin (about 0.083) is over 150 standard errors, the H3 gap (about 0.033) is about 90. Limit: a simulation can only show an estimate is consistent with 1/6 within about 0.0007, so 'supported' for H1 means consistent with 1/6, not proven exact; the exact value comes from the cross-check. Primes counted: 2, 3, 5, 7, 11. Interpretation of 'greater than 1/3' is strict.

## Hypotheses (preregistered)

| id | statement | falsifier | predicted | obtained | match |
|---|---|---|---|---|---|
| H1 | P(S >= 10) = 1/6 for two fair dice. | The pooled 95% interval for the estimated P(S >= 10) excludes 1/6. | supported | **supported** | yes |
| H2 | P(S is prime) > 1/3 for two fair dice. | The pooled 95% upper bound of the estimated P(S is prime) is at most 1/3. | supported | **supported** | yes |
| H3 | Negative control. P(S >= 10) = 1/5 for two fair dice. | The pooled 95% interval for the estimated P(S >= 10) excludes 1/5. The true value is 1/6, so this is expected to be refuted. | refuted | **refuted** | yes |

### Evaluation detail

**H1**

- 95% interval high: 0.167486
- 95% interval low: 0.166024
- P(S>=10) estimate: 0.166755
- claimed value 1/6: 0.166667
- rolls: 1000000
- standard error: 0.000372757

**H2**

- 95% lower bound: 0.415004
- 95% upper bound: 0.416936
- P(S prime) estimate: 0.41597
- standard error: 0.000492888
- threshold 1/3: 0.333333

**H3**

- P(S>=10) estimate: 0.166755
- claimed value 1/5: 0.2
- distance from 1/5 in standard errors: 89.1868

## Independent cross-checks

| check | observed | reference | tolerance | ok |
|---|---|---|---|---|
| closed-form outcome count is 36 | 36 | 36 | exact | yes |
| exact P(S>=10) = 6/36 = 1/6 | 6/36 | 6/36 | exact | yes |
| exact P(S prime) = 15/36 exceeds 1/3 | 15/36 | 15/36 | exact | yes |
| simulated P(S>=10) vs exact 1/6 | 0.166755 | 0.166667 | 4.0 standard errors | yes |
| simulated P(S prime) vs exact 15/36 | 0.41597 | 0.416667 | 4.0 standard errors | yes |
| negative control: exact P(S>=10) is not 1/5 | yes | yes | exact | yes |

## Provenance

- seeds: 11, 12, 13, 14, 15
- card sha256: `6dbbea3bbde7585813ef4453f5e65a158bd9cd7536cd3d07a1943669f03b5217`
- experiment sha256: `6f490083ca205a8aba5443194bdfc26e090a6dc34888bf8156083287e698f81e`
- results sha256: `1134dcc57a514db51880f9efcd91577e4cc9e89d44ab64fc9a2c0c38e90087de`
- ledger entry: seq 0, `c408c6427564c87f02e932469dfbfe188392e459e4a2d8332c93f6a67491a3f2`

## Interpretation (author prose, not covered by verification)

# Notes: dice-sum

## What was recorded

- H1 was supported: the estimate of P(S>=10) was 0.166755 over 1000000 rolls, and the 95% interval, from 0.166024 to 0.167486, contains 1/6 (0.166667).
- H2 was supported: the estimate of P(S prime) was 0.41597, and the 95% lower bound, 0.415004, is above 1/3 (0.333333).
- H3, the negative control, was refuted: the estimate of P(S>=10) is 89.1868 standard errors from 1/5 (0.2).
- All six cross-checks passed. The exact counts are 6/36 for a sum of at least 10 and 15/36 for a prime sum; the simulation agreed with them within 4.0 standard errors. Evidence level is L2.
- All three verdicts matched the predictions.

## What this does not show

- [conjecture] The simulation alone cannot establish that 1/6 is exact; it only fails to reject it. The exactness rests on the enumeration cross-check, which counts the 36 equally likely outcomes.
- [conjecture] The result assumes the dice are fair and independent, which is the premise of the question, not something the run tested.
- [conjecture] H2 depends on counting 2, 3, 5, 7 and 11 as the primes; the cross-check writes this list by hand, so a different convention would change the answer.

_notes sha256: `5dff8b543c8037eef336874155699e1340188d986b7e5fbddd98d6ece064cc83`_
