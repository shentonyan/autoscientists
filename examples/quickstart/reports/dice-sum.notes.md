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
