"""Single frozen-test evaluation for the fixed four-stock proxy (optional NumPy)."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
from equity_metrics import account, mean_ic, moving_day_bootstrap, select, weights


def evaluate(directory):
    destination = directory / "evaluation.json"
    if destination.exists():
        raise ValueError("evaluation already exists; do not overwrite a test result")
    data = np.load(directory / "forecasts.npz", allow_pickle=False)
    names = ("cnn32", "cnn32_ic", "cnn64_ic", "gru32", "gru32_ic", "ridge")
    va, te = data["split"] == "validation", data["split"] == "test"
    y, entry, exit_, days = (data[k] for k in ("y", "entry", "exit", "day"))
    selections = {name: select(data[name][va], y[va], entry[va], exit_[va]) for name in names}
    signed_validation_ic = {name: abs(mean_ic(data[name][va], y[va])) for name in names}
    chosen = max(names[:3], key=lambda name: signed_validation_ic[name])
    reference = max(names[3:5], key=lambda name: signed_validation_ic[name])
    predictions = {name: selections[name]["sign"] * data[name][te] for name in names}
    target, test_days = y[te], days[te]
    results = {}
    for name in names:
        cutoff = selections[name]["cutoff"]
        w = weights(predictions[name], float("inf") if cutoff is None else cutoff)
        pnl, turnover = account(w, target, entry[te], exit_[te], .0001)
        stress, _ = account(w, target, entry[te], exit_[te], .0005)
        unique_days = np.unique(test_days)
        daily = np.array([pnl[test_days == day].sum() for day in unique_days])
        years = np.array([datetime.fromtimestamp(int(day) * 86400, timezone.utc).year for day in test_days])
        results[name] = {"ic": mean_ic(predictions[name], target),
                         "per_stock_ic": [float(np.corrcoef(predictions[name][:, i], target[:, i])[0, 1])
                                          if np.std(predictions[name][:, i]) else 0.0 for i in range(4)],
                         "pnl": float(pnl.sum()), "stress_pnl": float(stress.sum()),
                         "active_intervals": int(np.count_nonzero(np.any(w != 0, axis=1))),
                         "turnover": float(turnover.sum()),
                         "annualized_daily_sharpe": float(daily.mean() / daily.std(ddof=1) * np.sqrt(252))
                         if daily.std(ddof=1) > 0 else None,
                         "yearly_pnl": {str(year): float(pnl[years == year].sum()) for year in np.unique(years)}}
        if name == chosen:
            primary_pnl = pnl
    ic_ci = moving_day_bootstrap(test_days, lambda ids: mean_ic(predictions[chosen][ids], target[ids]))
    delta_ci = moving_day_bootstrap(test_days, lambda ids: mean_ic(predictions[chosen][ids], target[ids]) -
                                   mean_ic(predictions[reference][ids], target[ids]))
    # Equal-day mean, using resampled day blocks rather than unequal intraday counts.
    unique = np.unique(test_days)
    daily = np.array([primary_pnl[test_days == day].sum() for day in unique])
    pnl_ci = moving_day_bootstrap(unique, lambda ids: float(daily[ids].mean()))
    primary = results[chosen]
    verdicts = {"positive_ic": ic_ci[0] > 0, "incremental_ic": delta_ci[0] > 0,
                "positive_costed_pnl": pnl_ci[0] > 0 and primary["active_intervals"] >= 100,
                "positive_stress_pnl": primary["stress_pnl"] > 0,
                "nonnegative_each_year": all(v >= 0 for v in primary["yearly_pnl"].values())}
    output = {"chosen_cnn": chosen, "chosen_gru": reference, "validation_selections": selections,
              "absolute_validation_ic": signed_validation_ic, "results": results,
              "primary_ic_ci": ic_ci, "primary_minus_gru_ic_ci": delta_ci,
              "mean_daily_pnl_ci": pnl_ci, "success_components": verdicts,
              "joint_proxy_success": all(verdicts.values()),
              "scope": "four fixed survivors; unknown corporate-action adjustment; partial 2025; not original AQuA replication",
              "forecasts_sha256": hashlib.sha256((directory / "forecasts.npz").read_bytes()).hexdigest(),
              "evaluator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    destination.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, allow_nan=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    evaluate(parser.parse_args().directory)
