"""Draw the remaining README experiments from recorded results; no new scoring."""
import hashlib
import json

from plot_confirmations import ROOT, OUT, BLUE, ORANGE, GRAY, INK, clean, save, plt


def load(path):
    return json.loads((ROOT / path).read_text())


def panel(title, subtitle, two=False):
    fig, axes = plt.subplots(1, 2 if two else 1, figsize=(12, 5.6))
    fig.subplots_adjust(left=.1, right=.96, top=.72, bottom=.24, wspace=.45)
    fig.suptitle(title, x=.06, y=.96, ha="left", fontsize=17, weight="bold")
    fig.text(.06, .86, subtitle, fontsize=11)
    return fig, axes


def main():
    plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans", "text.color": INK,
                         "axes.labelcolor": INK, "svg.hashsalt": "aqua-research-overview"})
    sources = ["runs/8a7a3667c87d41e8.json", "research/results/crypto-v1/metrics.json",
               "runs/3dadd638fe75c9ca.json", "runs/e60e949f7ed4c1dc.json"]
    search, crypto, futures, equity = map(load, sources)
    gain = search["evaluation"]["H1"]["detail"]
    fig, (a, b) = panel("Restricted search improves toy utility; spot trading loses after costs",
                        "Two separate experiments: numerical auction utility is not investment return", True)
    value = gain["paired_mean_test_gain"]
    a.errorbar(value, 0, xerr=[[value - gain["normal_95_low"]], [gain["normal_95_high"] - value]],
               fmt="D", color=BLUE, capsize=6)
    a.axvline(0, color=INK, linewidth=.8)
    a.set_xlim(-.0004, .0035)
    a.set_xticks([0, .001, .002, .003], ["0.000", "0.001", "0.002", "0.003"])
    a.set_ylim(-.8, .8)
    a.set_yticks([])
    a.set_title("40 paired seeds; 12 calls per policy", fontsize=12)
    a.set_xlabel("Memory-guided minus IID test utility")
    a.text(.5, .2, f"Mean gain {value:.6f}\nNormal-approximation 95% interval above zero",
           transform=a.transAxes, ha="center", fontsize=10, linespacing=1.5)
    clean(a)
    factor = crypto["factors"]["memory"]
    ridge = crypto["ridge"]
    gross = [100 * next(r["net_return"] for r in rows if r["cost_bps_per_one_way_notional"] == 0) for rows in (factor, ridge)]
    net = [100 * next(r["net_return"] for r in rows if r["cost_bps_per_one_way_notional"] == 1) for rows in (factor, ridge)]
    b.bar([-.17, .83], gross, .32, label="Before costs", color=GRAY)
    b.bar([.17, 1.17], net, .32, label="1 bp per one-way turnover", color=ORANGE)
    for xs, values in (([-.17, .83], gross), ([.17, 1.17], net)):
        for x, v in zip(xs, values):
            b.annotate(f"{v:.2f}%", (x, v), xytext=(0, 5 if v >= 0 else -17), textcoords="offset points", ha="center", fontsize=10)
    b.axhline(0, color=INK, linewidth=.8)
    b.set_xticks([0, 1], ["Selected factor", "Ridge"])
    b.set_ylabel("Compounded spot-portfolio return (%)")
    b.set_ylim(-35, 10)
    b.set_title("BTC / ETH / BNB; May-Jun 2024 test", fontsize=12)
    b.legend(loc="upper right", fontsize=9, frameon=False)
    clean(b)
    fig.text(.06, .12, "Search uses numerical interval refinement, not LLM proposals. Random and no-memory are the same paired control.", fontsize=10)
    fig.text(.06, .055, "Spot search policies select the same factor. Positive Spearman IC does not establish profitable trading or memory benefit.", fontsize=10)
    save(fig, "aqua-search-spot-results")

    f = futures["evaluation"]
    fig, a = panel("OI / rebound / weak-flow filter fails its reserved-quarter target",
                   "BTC perpetual futures  /  Oct-Dec 2024 held out  /  validation-selected full filter")
    values = [100 * f["H3"]["detail"]["cost_1bp_pnl"], 100 * f["H3"]["detail"]["cost_5bp_pnl"], 0]
    a.bar(range(3), values, color=[BLUE, ORANGE, GRAY], width=.55)
    a.scatter([2], [0], marker="D", color=GRAY)
    for i, value in enumerate(values):
        a.annotate(f"{value:.2f}%", (i, value), xytext=(0, -20 if value < 0 else 8), textcoords="offset points", ha="center")
    a.set_xticks(range(3), ["Full filter: 1 bp / leg", "Same trades: 5 bp / leg", "Validation reference: cash"])
    a.set_ylabel("Arithmetic PNL / initial notional (%)")
    a.set_ylim(-5.5, 1.2)
    a.axhline(0, color=INK, linewidth=.8)
    clean(a)
    fig.text(.06, .12, "19 test trades; minimum activity requirement is 20. PNL and incremental-PNL hypotheses are inconclusive.", fontsize=10)
    fig.text(.06, .055, "The test does not establish profitability. Higher costs lower PNL, as expected by the negative control.", fontsize=10)
    save(fig, "aqua-futures-results")

    e = next(iter(equity["results"].values()))
    primary = e["results"][e["chosen_cnn"]]
    fig, (a, b) = panel("Four-stock equity proxy: held-out net returns are negative",
                        "Train 2010-2017  /  Validate 2018-2019  /  Embargo 2020  /  Test 2021-Jul 2025", True)
    lo, hi = e["primary_ic_ci"]
    ic = primary["ic"]
    a.errorbar(ic, 0, xerr=[[ic - lo], [hi - ic]], fmt="D", color=BLUE, capsize=6)
    a.axvline(0, color=INK, linewidth=.8)
    a.set_xlim(-.05, .03)
    a.set_ylim(-.8, .8)
    a.set_yticks([])
    a.set_title("Validation-selected CNN32 + IC loss", fontsize=12)
    a.set_xlabel("Mean per-stock test Pearson IC")
    a.text(.5, .2, f"IC {ic:.5f}; 95% interval includes zero\nNo supported IC improvement over GRU",
           transform=a.transAxes, ha="center", fontsize=10, linespacing=1.5)
    clean(a)
    years = list(primary["yearly_pnl"])
    values = [100 * v for v in primary["yearly_pnl"].values()]
    b.bar(range(len(years)), values, color=ORANGE, width=.6)
    for i, value in enumerate(values):
        b.annotate(f"{value:.2f}%", (i, value), xytext=(0, -18), textcoords="offset points", ha="center", fontsize=10)
    b.set_xticks(range(5), [*years[:-1], "2025*"])
    b.set_ylabel("Arithmetic PNL / initial notional (%)")
    b.set_ylim(-9.5, .8)
    b.axhline(0, color=INK, linewidth=.8)
    b.set_title("1 bp per absolute unit turnover", fontsize=12)
    clean(b)
    fig.text(.06, .12, f"1,613 active intervals; total arithmetic PNL {100 * primary['pnl']:.2f}%; daily Sharpe {primary['annualized_daily_sharpe']:.3f}.", fontsize=10)
    fig.text(.06, .055, "20-trading-day block intervals. *2025 ends in July. Fixed survivors and unresolved data adjustments limit interpretation.", fontsize=10)
    save(fig, "aqua-equity-results")
    (OUT / "aqua-overview-chart-data.json").write_text(json.dumps({
        "inputs": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
        "scope": "Different tasks and return conventions; no pooled cross-experiment performance ranking."}, indent=2) + "\n")


if __name__ == "__main__":
    main()
