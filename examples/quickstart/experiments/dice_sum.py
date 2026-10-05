"""Two fair six-sided dice: tail and prime-sum probabilities.

Claims under test (all about the sum S of two independent fair dice):
  H1  P(S >= 10) = 1/6
  H2  P(S is prime) > 1/3
  H3  negative control: P(S >= 10) = 1/5   (false; the true value is 1/6)

`run` simulates rolls with a seeded generator and a trial-division primality test.
`crosscheck` uses closed forms only: the number of ways to roll sum s is
6 - |s - 7| for s in 2..12, and the primes up to 12 are written out by hand.
They share only the parameters. Simulation can show consistency with an exact
value to within noise; it cannot prove exactness, which the cross-check supplies.
"""
from __future__ import annotations

import math
import random

Z95 = 1.96
SE_TOL = 4.0


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def run(params: dict, seed: int) -> dict:
    rng = random.Random(seed)
    n = params["n_rolls"]
    ge10 = prime = 0
    for _ in range(n):
        s = rng.randint(1, 6) + rng.randint(1, 6)
        if s >= 10:
            ge10 += 1
        if _is_prime(s):
            prime += 1
    return {"n": n, "ge10": ge10, "prime": prime}


def _pool(per_seed: dict, key: str):
    n = sum(per_seed[s]["n"] for s in per_seed)
    k = sum(per_seed[s][key] for s in per_seed)
    p = k / n
    se = math.sqrt(p * (1 - p) / n)
    return n, p, se


def evaluate(params: dict, per_seed: dict) -> dict:
    n, p10, se10 = _pool(per_seed, "ge10")
    _, pp, sep = _pool(per_seed, "prime")

    h1_ok = abs(p10 - 1 / 6) <= Z95 * se10
    h1 = {
        "verdict": "supported" if h1_ok else "refuted",
        "detail": {
            "rolls": n,
            "P(S>=10) estimate": p10,
            "standard error": se10,
            "95% interval low": p10 - Z95 * se10,
            "95% interval high": p10 + Z95 * se10,
            "claimed value 1/6": 1 / 6,
        },
    }

    low = pp - Z95 * sep
    high = pp + Z95 * sep
    if low > 1 / 3:
        v2 = "supported"
    elif high <= 1 / 3:
        v2 = "refuted"
    else:
        v2 = "inconclusive"
    h2 = {
        "verdict": v2,
        "detail": {
            "P(S prime) estimate": pp,
            "standard error": sep,
            "95% lower bound": low,
            "95% upper bound": high,
            "threshold 1/3": 1 / 3,
        },
    }

    h3_ok = abs(p10 - 0.2) <= Z95 * se10
    h3 = {
        "verdict": "supported" if h3_ok else "refuted",
        "detail": {
            "P(S>=10) estimate": p10,
            "distance from 1/5 in standard errors": abs(p10 - 0.2) / se10,
            "claimed value 1/5": 0.2,
        },
    }
    return {"H1": h1, "H2": h2, "H3": h3}


def _ways(s: int) -> int:
    return 6 - abs(s - 7)


def crosscheck(params: dict, per_seed: dict) -> list:
    sums = range(2, 13)
    total = sum(_ways(s) for s in sums)
    ge10_ways = sum(_ways(s) for s in sums if s >= 10)
    prime_ways = sum(_ways(s) for s in (2, 3, 5, 7, 11))
    n, p10, se10 = _pool(per_seed, "ge10")
    _, pp, sep = _pool(per_seed, "prime")
    ref10 = ge10_ways / total
    refp = prime_ways / total
    checks = [
        {
            "name": "closed-form outcome count is 36",
            "observed": total,
            "reference": 36,
            "tolerance": "exact",
            "ok": total == 36,
        },
        {
            "name": "exact P(S>=10) = 6/36 = 1/6",
            "observed": f"{ge10_ways}/{total}",
            "reference": "6/36",
            "tolerance": "exact",
            "ok": ge10_ways * 6 == total,
        },
        {
            "name": "exact P(S prime) = 15/36 exceeds 1/3",
            "observed": f"{prime_ways}/{total}",
            "reference": "15/36",
            "tolerance": "exact",
            "ok": prime_ways == 15 and prime_ways * 3 > total,
        },
        {
            "name": "simulated P(S>=10) vs exact 1/6",
            "observed": p10,
            "reference": ref10,
            "tolerance": f"{SE_TOL} standard errors",
            "ok": abs(p10 - ref10) <= SE_TOL * se10,
        },
        {
            "name": "simulated P(S prime) vs exact 15/36",
            "observed": pp,
            "reference": refp,
            "tolerance": f"{SE_TOL} standard errors",
            "ok": abs(pp - refp) <= SE_TOL * sep,
        },
        {
            "name": "negative control: exact P(S>=10) is not 1/5",
            "observed": ge10_ways * 5 != total,
            "reference": True,
            "tolerance": "exact",
            "ok": ge10_ways * 5 != total,
        },
    ]
    return checks
