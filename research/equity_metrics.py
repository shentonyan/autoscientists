"""Panel forecast statistics and netted, session-bounded portfolio accounting."""
import numpy as np


def mean_ic(prediction, target):
    return float(np.mean([np.corrcoef(prediction[:, s], target[:, s])[0, 1]
                          if np.std(prediction[:, s]) and np.std(target[:, s]) else 0.0
                          for s in range(target.shape[1])]))


def weights(prediction, cutoff):
    result = np.zeros_like(prediction)
    active = np.std(prediction, axis=1) >= cutoff
    for i in np.flatnonzero(active):
        order = np.argsort(prediction[i], kind="stable")
        if prediction[i, order[-1]] > prediction[i, order[0]]:
            result[i, order[0]], result[i, order[-1]] = -0.5, 0.5
    return result


def account(w, returns, entry, exit_, cost):
    """Fixed-notional arithmetic PnL, net positions at contiguous interval boundaries.

    Short proceeds do not earn cash interest. No overnight holdings; cost is per
    unit absolute notional traded. Borrow/spread beyond specified cost are unknown.
    """
    if w.shape != returns.shape or len(w) != len(entry) or len(w) != len(exit_):
        raise ValueError("incompatible portfolio dimensions")
    if np.any(exit_ <= entry) or np.any(entry[1:] < exit_[:-1]):
        raise ValueError("intervals overlap or are reversed")
    turnover = np.zeros(len(w))
    previous = np.zeros(w.shape[1])
    for i in range(len(w)):
        if i == 0 or entry[i] != exit_[i - 1]:
            previous = np.zeros(w.shape[1])
        turnover[i] += np.abs(w[i] - previous).sum()
        if i == len(w) - 1 or exit_[i] != entry[i + 1]:
            turnover[i] += np.abs(w[i]).sum()
        previous = w[i]
    return (w * returns).sum(axis=1) - cost * turnover, turnover


def select(prediction, target, entry, exit_):
    """Validation-only sign and threshold selection; cash if no positive net sum."""
    sign = 1 if mean_ic(prediction, target) >= 0 else -1
    p = sign * prediction
    dispersion = np.std(p, axis=1)
    candidates = []
    for quantile in (0.5, 0.75, 0.9):
        cutoff = float(np.quantile(dispersion, quantile))
        w = weights(p, cutoff)
        pnl, _ = account(w, target, entry, exit_, 0.0001)
        if np.count_nonzero(np.any(w != 0, axis=1)) >= 100:
            candidates.append((float(pnl.sum()), quantile, cutoff))
    best = max(candidates, default=(0, None, float("inf")))
    return {"sign": sign, "quantile": best[1] if best[0] > 0 else None,
            "cutoff": best[2] if best[0] > 0 else None,
            "validation_net_pnl": max(0.0, best[0])}


def moving_day_bootstrap(days, statistic, count=1000, seed=20261027):
    """Resample 20 observed trading-day blocks, preserving all intraday stocks."""
    unique = np.unique(days)
    groups = [np.flatnonzero(days == d) for d in unique]
    rng = np.random.default_rng(seed)
    result = []
    for _ in range(count):
        chosen = []
        while len(chosen) < len(groups):
            start = int(rng.integers(0, len(groups)))
            chosen.extend(range(start, min(start + 20, len(groups))))
        ids = np.concatenate([groups[i] for i in chosen[:len(groups)]])
        result.append(statistic(ids))
    return np.quantile(result, (0.025, 0.975)).tolist()
