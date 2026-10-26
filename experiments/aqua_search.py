"""Self-contained, locked auction search experiment; standard library only.

Candidate interface: {"operator": "scaled_value", "alpha": finite [0,1]}.
This is an application interface, not an OS sandbox. The experiment owns data
and scoring. No candidate source is imported, evaluated or executed.
"""
import math
import random
import statistics


def candidate(spec):
    if not isinstance(spec, dict) or set(spec) != {"operator", "alpha"}:
        raise ValueError("candidate must contain only operator and alpha")
    a = spec["alpha"]
    if spec["operator"] != "scaled_value" or type(a) not in (int, float):
        raise ValueError("unregistered operator or nonnumeric alpha")
    if not math.isfinite(a) or not 0 <= a <= 1:
        raise ValueError("alpha outside finite [0,1]")
    return float(a)


def utility(alpha, values, opponents):
    return sum((v - alpha * v) if alpha * v > o else 0.0
               for v, o in zip(values, opponents)) / len(values)


def search(mode, budget, values, opponents, seed):
    rng = random.Random(seed)
    history = []
    # Memory-guided interval refinement; the optimum is not supplied.
    lo, hi = 0.0, 1.0
    for iteration in range(budget):
        if mode == "memory":
            if iteration >= 2 and iteration % 2 == 0:
                left, right = history[-2:]
                if left["score"] < right["score"]:
                    lo = min(left["alpha"], right["alpha"])
                else:
                    hi = max(left["alpha"], right["alpha"])
            # Re-evaluate both interior points per round; every call counts.
            alpha = lo + (hi - lo) * (1 if iteration % 2 == 0 else 2) / 3
        else:
            # Paired IID baseline; memory-disabled and random are intentionally
            # identical controls, rather than inventing a distinct algorithm.
            alpha = rng.random()
        spec = {"operator": "scaled_value", "alpha": alpha}
        score = utility(candidate(spec), values, opponents)
        history.append({"alpha": alpha, "score": score})
    selected = max(history, key=lambda x: x["score"])
    return {"alpha": selected["alpha"], "validation": selected["score"],
            "evaluations": len(history), "history": history}


def run(params, seed):
    rng = random.Random(seed)
    exponent = rng.choice([0.7, 1.3, 2.0, 3.1])
    validation_values = [rng.uniform(0.2, 0.9) for _ in range(params["validation_n"])]
    validation_opponents = [0.5 * rng.random() ** exponent for _ in validation_values]
    # Independent test samples are never passed to search().
    test_values = [rng.uniform(0.2, 0.9) for _ in range(params["test_n"])]
    test_opponents = [0.5 * rng.random() ** exponent for _ in test_values]
    result = {"exponent": exponent, "modes": {}}
    for mode in ("random", "no_memory", "memory"):
        selected = search(mode, params["budget"], validation_values,
                          validation_opponents, seed + 100000)
        selected["test"] = utility(selected["alpha"], test_values, test_opponents)
        # Independent analytic reference, evaluated only after search finishes.
        selected["analytic_test"] = sum(
            (v - selected["alpha"] * v) * min(2 * selected["alpha"] * v, 1) ** (1 / exponent)
            for v in test_values) / len(test_values)
        result["modes"][mode] = selected
    result["truthful_test"] = utility(1.0, test_values, test_opponents)
    attacks = [None, {}, {"operator": "exec", "alpha": 0.5},
               {"operator": "scaled_value", "alpha": float("nan")},
               {"operator": "scaled_value", "alpha": True},
               {"operator": "scaled_value", "alpha": -0.1},
               {"operator": "scaled_value", "alpha": 0.5, "evaluator": "replace"}]
    rejected = 0
    for attack in attacks:
        try:
            candidate(attack)
        except ValueError:
            rejected += 1
    result["rejected"] = rejected
    result["attacks"] = len(attacks)
    return result


def evaluate(params, per_seed):
    differences = [r["modes"]["memory"]["test"] - r["modes"]["random"]["test"]
                   for r in per_seed.values()]
    mean = statistics.mean(differences)
    se = statistics.stdev(differences) / math.sqrt(len(differences))
    # Normal-approximation paired interval; a finite benchmark, not a theorem.
    low, high = mean - 1.96 * se, mean + 1.96 * se
    controls = all(r["modes"]["random"] == r["modes"]["no_memory"]
                   for r in per_seed.values())
    equal_budget = all(x["evaluations"] == params["budget"]
                       for r in per_seed.values() for x in r["modes"].values())
    attacks_rejected = all(r["rejected"] == r["attacks"] for r in per_seed.values())
    return {
        "H1": {"verdict": "supported" if low > 0 else "refuted" if high < 0 else "inconclusive",
               "detail": {"paired_mean_test_gain": mean, "paired_se": se,
                          "normal_95_low": low, "normal_95_high": high}},
        "H2": {"verdict": "supported" if controls and equal_budget and attacks_rejected else "refuted",
               "detail": {"controls_identical": controls, "equal_budget": equal_budget,
                          "rejected": sum(r["rejected"] for r in per_seed.values()),
                          "attacks": sum(r["attacks"] for r in per_seed.values())}},
        "H3": {"verdict": "supported" if any(r["truthful_test"] > 0 for r in per_seed.values()) else "refuted",
               "detail": {"truthful_max": max(r["truthful_test"] for r in per_seed.values())}},
    }


def crosscheck(params, per_seed):
    # Direct comparison to the closed-form CDF reference recorded by run().
    # The reference shares the auction distribution and sampled private values,
    # but no winner simulation. Hoeffding bound + union bound over all checks.
    count = len(per_seed) * 3
    tol = math.sqrt(math.log(2 * count / 0.001) / (2 * params["test_n"]))
    worst = max(abs(x["test"] - x["analytic_test"])
                for r in per_seed.values() for x in r["modes"].values())
    return [{"name": "test utilities vs analytic opponent CDF (familywise bound)",
             "observed": worst, "reference": 0, "tolerance": tol, "ok": worst <= tol}]
