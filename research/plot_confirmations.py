"""Render README evidence figures from immutable recorded runs (optional matplotlib)."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/img"
RUNS = {"walk": "runs/9ad10ec0892047f6.json", "hybrid": "runs/55cf5d72f8ec4568.json"}
BLUE, ORANGE, GRAY, INK = "#176B9B", "#B65D25", "#727B86", "#243447"


def clean(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#B5BDC4")
    ax.tick_params(colors=INK)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(OUT / (name + ".png"), dpi=170, facecolor="white")
    fig.savefig(OUT / (name + ".svg"), facecolor="white")
    vector = OUT / (name + ".svg")
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    tree = ET.parse(vector)
    title = ET.Element("{http://www.w3.org/2000/svg}title")
    title.text = fig._suptitle.get_text()
    tree.getroot().insert(0, title)
    tree.write(vector, encoding="utf-8", xml_declaration=True)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 11, "font.family": "DejaVu Sans", "text.color": INK,
                         "axes.labelcolor": INK, "axes.titleweight": "bold", "svg.hashsalt": "aqua-confirmations"})
    recorded = {key: json.loads((ROOT / path).read_text()) for key, path in RUNS.items()}
    walk, hybrid = (next(iter(recorded[key]["results"].values())) for key in ("walk", "hybrid"))

    fig, ax = plt.subplots(figsize=(11, 5.6))
    fig.subplots_adjust(left=.09, right=.97, top=.76, bottom=.22)
    fig.suptitle("01  |  Walk-forward policy chooses cash in every quarter", x=.06, y=.97, ha="left", fontsize=17, weight="bold")
    fig.text(.06, .88, "BTC perpetual futures  /  2025 Q2-Q4  /  2 bp cost per leg", fontsize=11)
    fig.text(.06, .82, "Selected policy: 0 trades, 0.00% arithmetic PNL; profitability target not met", color=BLUE, weight="bold")
    series = (("selected", "Validation-selected policy (cash)", BLUE, -.24),
              ("oi_reference", "Fixed OI-only reference", ORANGE, 0),
              ("weak_reference", "Fixed weak-flow reference", GRAY, .24))
    for key, label, color, offset in series:
        values = [100 * fold[key]["arithmetic_pnl"] for fold in walk["folds"]]
        xs = [i + offset for i in range(3)]
        ax.bar(xs, values, width=.22, label=label, color=color)
        if key == "selected":
            ax.scatter(xs, values, marker="D", color=color, s=40, zorder=4)
        for x, value in zip(xs, values):
            ax.annotate(f"{value:.2f}%", (x, value), xytext=(0, 7 if value == 0 else -17),
                        textcoords="offset points", ha="center", fontsize=10, color=color)
    ax.axhline(0, color=INK, linewidth=.8)
    ax.set_xticks(range(3), ["2025 Q2", "2025 Q3", "2025 Q4"])
    ax.set_ylabel("Arithmetic PNL / initial notional (%)")
    ax.set_ylim(-4.8, 1.5)
    ax.grid(axis="y", color="#E2E6EA")
    ax.legend(loc="upper center", ncol=3, frameon=False, fontsize=10)
    clean(ax)
    fig.text(.06, .09, "All-period fixed references: OI-only -7.88%; weak-flow -5.45%. Cash has undefined conventional Sharpe.", fontsize=10)
    fig.text(.06, .045, "Zero-trade abstention is not evidence of profitable trading. References are fixed, not selected on these test results.", fontsize=10)
    save(fig, "aqua-walk-forward-results")

    fig, (ax, delta) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.3, 1]})
    fig.subplots_adjust(left=.18, right=.97, top=.71, bottom=.28, wspace=.65)
    fig.suptitle("02  |  CNN confirmation does not establish an edge", x=.055, y=.97, ha="left", fontsize=17, weight="bold")
    fig.text(.055, .89, "Train: Jul 2024-Sep 2025  /  Validate: Q4 2025  /  Test: Jan-Sep 2026 (13,103 samples)", fontsize=11)
    fig.text(.055, .82, "Nine neural training runs: CNN32, CNN64 and GRU32, each averaged over three seeds; ridge control", fontsize=11)
    names = ["cnn32", "cnn64", "gru32", "ridge"]
    labels = ["CNN32 (selected)", "CNN64 (descriptive)", "GRU32 (reference)", "Ridge (descriptive)"]
    values = [hybrid["outcomes"][name]["ic"] for name in names]
    ax.barh(range(4), values, color=[BLUE, GRAY, GRAY, GRAY], height=.52)
    lo, hi = hybrid["primary_ic_interval"]
    ax.errorbar(values[0], 0, xerr=[[values[0] - lo], [hi - values[0]]], fmt="o", color=BLUE, capsize=5, zorder=4)
    ax.set_yticks(range(4), labels)
    ax.invert_yaxis()
    ax.set_xlim(-.022, .045)
    ax.set_xlabel("Global test Pearson IC")
    ax.axvline(0, color=INK, linewidth=.9)
    ax.grid(axis="x", color="#E2E6EA")
    for i, value in enumerate(values):
        ax.text(.043, i, f"{value:.5f}", va="center", ha="right", fontsize=10)
    clean(ax)
    difference = values[0] - values[2]
    low, high = hybrid["ic_vs_gru_interval"]
    delta.errorbar(difference, 0, xerr=[[difference - low], [high - difference]], fmt="D", color=BLUE, capsize=6)
    delta.axvline(0, color=INK, linewidth=.9)
    delta.set_xlim(-.045, .025)
    delta.set_ylim(-.8, .8)
    delta.set_yticks([])
    delta.set_xlabel("Selected CNN IC minus GRU IC")
    delta.set_title("Paired difference", fontsize=12)
    delta.grid(axis="x", color="#E2E6EA")
    delta.text(.5, .23, f"95% interval [{low:.5f}, {high:.5f}]\nIncludes zero: no supported improvement",
               transform=delta.transAxes, ha="center", fontsize=10, linespacing=1.6)
    clean(delta)
    fig.text(.055, .16, f"Selected CNN 95% IC interval: [{lo:.5f}, {hi:.5f}]. Intervals use 14-day block bootstrap.", fontsize=10)
    fig.text(.055, .105, "All eligible validation trading thresholds lose after costs: selected policy abstains (0 test trades; 0 PNL).", fontsize=10)
    fig.text(.055, .05, "Only the selected CNN has an IC interval shown; other bars are point estimates. Test scores do not choose the winner.", fontsize=10)
    save(fig, "aqua-hybrid-confirmation-results")

    manifest = {"inputs": {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in RUNS.values()},
                "scope": "Recorded point estimates and intervals only; no new model training or test selection.",
                "walk_quarterly_arithmetic_pnl": [{key: fold[key]["arithmetic_pnl"] for key, *_ in series} for fold in walk["folds"]],
                "hybrid_point_ic": dict(zip(names, values)), "cnn_ic_interval": [lo, hi],
                "cnn_minus_gru_interval": [low, high]}
    (OUT / "aqua-confirmation-chart-data.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
