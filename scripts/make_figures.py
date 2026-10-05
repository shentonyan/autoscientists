"""Generate the SVG figures in docs/img from repository data (standard library only).

    python scripts/make_figures.py          # write docs/img/*.svg
    python scripts/make_figures.py --check  # exit 1 if the committed SVGs are stale

Data-driven figures (calibration, selftest) are recomputed from the code and the
calibration card, not typed in. Every figure has an explicit light background so it
reads the same in GitHub's light and dark themes.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "img"

SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#dcdad2"
BLUE, ORANGE = "#2a78d6", "#eb6834"  # validated pair (ΔE 24.7 CVD, 33.6 normal)
FONT = "system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


class Svg:
    def __init__(self, w, h, title, desc):
        self.w, self.h = w, h
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-labelledby="t d" font-family="{FONT}">',
            f"<title id=\"t\">{escape(title)}</title><desc id=\"d\">{escape(desc)}</desc>",
            '<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>',
            f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>',
        ]

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=13, fill=INK, anchor="start", weight="400", rotate=None):
        s = str(s).replace("`", "")
        tr = f' transform="rotate({rotate} {x:.1f} {y:.1f})"' if rotate else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}"{tr}>{escape(s)}</text>')

    def rect(self, x, y, w, h, fill="none", stroke=INK, sw=1.5, rx=6):
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def line(self, x1, y1, x2, y2, stroke=MUTED, sw=1.5, arrow=False, dash=None):
        extra = ' marker-end="url(#ar)"' if arrow else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d}{extra}/>')

    def box(self, x, y, w, h, lines, fill=SURFACE, stroke=INK, title_size=14):
        self.rect(x, y, w, h, fill=fill, stroke=stroke)
        n = len(lines)
        y0 = y + h / 2 - (n - 1) * 9 + 4
        for i, ln in enumerate(lines):
            self.text(x + w / 2, y0 + i * 18, ln, size=title_size if i == 0 else 12,
                      fill=INK if i == 0 else MUTED, anchor="middle", weight="600" if i == 0 else "400")

    def render(self):
        return "\n".join(self.parts + ["</svg>"]) + "\n"


# ---------------------------------------------------------------- static diagrams

def workflow():
    s = Svg(900, 330, "The research loop", "Eight steps from idea to draft pull request; verification failure stops the loop.")
    s.text(450, 28, "One card per wake-up, in this order", 16, anchor="middle", weight="600")
    row1 = [("1 Idea", "from the queue"), ("2 Design review", "refuters, control,", "cross-check"),
            ("3 Pre-register", "card + experiment", "SHA-256 locked"), ("4 Run", "ledger entry,", "hash-chained")]
    row2 = [("5 Verify", "re-execute, compare", "with cross-check"), ("6 Report", "generated from", "recorded data"),
            ("7 Notes + lint", "numbers grounded,", "opinion tagged"), ("8 Review + draft PR", "fresh read-only agent,", "maintainer merges")]
    xs = [30, 250, 470, 690]
    for row, y in ((row1, 55), (row2, 185)):
        for i, (t, *rest) in enumerate(row):
            s.box(xs[i], y, 180, 80, [t] + rest)
            if i < 3:
                s.line(xs[i] + 180, y + 40, xs[i + 1], y + 40, arrow=True)
    s.line(780, 135, 780, 160, arrow=False)
    s.line(780, 160, 120, 160, arrow=False)
    s.line(120, 160, 120, 185, arrow=True)
    s.rect(250, 285, 400, 34, fill="#fdeee8", stroke=ORANGE)
    s.text(450, 307, "verify fails: stop, journal, never edit locked files", 13, anchor="middle", weight="600")
    s.line(120, 265, 120, 302, stroke=ORANGE, arrow=False, dash="4 3")
    s.line(120, 302, 250, 302, stroke=ORANGE, arrow=True, dash="4 3")
    return s


def tiers():
    s = Svg(900, 365, "Trust tiers", "Three tiers of files: frozen core, gated, free.")
    s.text(450, 28, "Who may change what", 16, anchor="middle", weight="600")
    rows = [
        ("Tier 0  frozen core", "maintainer only", "autosci/*.py, calibration card, tests, PROTOCOL.md,",
         "governor limits, CI and settings files. Checked by `guard`.", "#fdeee8", ORANGE),
        ("Tier 1  gated", "loop proposes, maintainer merges", "skills, loop/AGENT.md, new experiments, docs.",
         "Recorded with `evolve propose`; the gate must pass; draft PR.", "#e8f0fb", BLUE),
        ("Tier 2  free", "the loop", "notes, queue, journal, runs, reports, source registry.",
         "Normal work, still verified by `verify` and `lint`.", SURFACE, MUTED),
    ]
    y = 50
    for title, who, l1, l2, fill, stroke in rows:
        s.rect(30, y, 840, 80, fill=fill, stroke=stroke, sw=2)
        s.text(50, y + 30, title, 16, weight="700")
        s.text(50, y + 54, who, 13, MUTED)
        s.text(330, y + 34, l1, 13)
        s.text(330, y + 56, l2, 13, MUTED)
        y += 95
    s.text(450, 350, "The evaluator is not edited by the thing it evaluates.", 13, MUTED, anchor="middle")
    return s


def evidence():
    s = Svg(900, 300, "Evidence ladder", "Four evidence levels, L0 to L3, each requiring the one below.")
    s.text(450, 28, "Evidence level of a result", 16, anchor="middle", weight="600")
    levels = [("L0", "unverified", "a check failed or is missing"),
              ("L1", "reproducible", "fresh re-execution is byte-identical"),
              ("L2", "cross-checked", "L1, and every independent cross-check passed"),
              ("L3", "sourced", "L2, and every cited source is recorded as verified")]
    for i, (lv, name, crit) in enumerate(levels):
        x, h = 40 + i * 210, 100 + i * 34
        y = 268 - h
        s.rect(x, y, 190, h, fill="#e8f0fb" if i else "#fdeee8", stroke=BLUE if i else ORANGE, sw=2)
        s.text(x + 14, y + 26, f"{lv}  {name}", 15, weight="700")
        words, lines, cur = crit.split(" "), [], ""
        for w in words:
            if len(cur) + len(w) + 1 > 27:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        lines.append(cur)
        for j, ln in enumerate(lines):
            s.text(x + 14, y + 48 + j * 16, ln, 12, MUTED)
    s.text(450, 292, "Source evidence is primary-text or tool-summary; a hash proves identity, not truth.", 12, MUTED, anchor="middle")
    return s


def ledger():
    s = Svg(900, 230, "Hash-chained ledger", "Each ledger entry stores the hash of the previous entry.")
    s.text(450, 28, "Append-only ledger: editing any entry breaks every hash after it", 16, anchor="middle", weight="600")
    for i in range(4):
        x = 30 + i * 220
        s.rect(x, 55, 190, 120, fill=SURFACE)
        s.text(x + 12, 78, f"entry {i}", 14, weight="700")
        s.text(x + 12, 102, "card + experiment hashes", 11, MUTED)
        s.text(x + 12, 120, "results hash", 11, MUTED)
        s.text(x + 12, 138, "prev = hash of entry %d" % (i - 1) if i else "prev = 000…0", 11)
        s.text(x + 12, 160, "entry hash", 11, weight="700")
        if i < 3:
            s.line(x + 190, 115, x + 220, 115, arrow=True)
    s.text(450, 208, "`python -m autosci status` recomputes the chain; `verify` also re-executes the run.", 12, MUTED, anchor="middle")
    return s


# ---------------------------------------------------------------- data-driven

def calibration():
    import importlib
    from autosci.paths import Layout
    card = json.loads((ROOT / "cards" / "auction-calibration.json").read_text())
    mod = importlib.import_module("experiments." + card["experiment"])
    params = card["params"]
    per_seed = {s: mod.run(params, s) for s in card["seeds"]}
    n_steps, bids = mod._grid(params)
    v = mod._values(params)[1]  # second tested value
    W, H = 900, 430
    s = Svg(W, H, "Calibration: simulation against closed form",
            f"Expected utility versus bid at value {v} in two auctions: simulated mean with two standard errors and the closed-form curve.")
    s.text(450, 26, f"Calibration card: simulated vs closed-form expected utility (value v = {v})", 15, anchor="middle", weight="600")
    panels = [("second_price", "Second-price: best bid = v (truthful)"), ("first_price", "First-price vs opponent bidding x/2: best bid = v/2")]
    worst = 0.0
    for p, (mech, title) in enumerate(panels):
        x0, y0, pw, ph = 80 + p * 430, 70, 340, 260
        means, ses = mod._pool(per_seed, mech, v)
        ref = [mod._analytic(mech, v, b) for b in bids]
        lo = min(min(ref), min(m - 2 * e for m, e in zip(means, ses)))
        hi = max(max(ref), max(m + 2 * e for m, e in zip(means, ses)))
        pad = (hi - lo) * 0.08
        lo, hi = lo - pad, hi + pad
        X = lambda b: x0 + b * pw
        Y = lambda u: y0 + ph - (u - lo) / (hi - lo) * ph
        s.text(x0, y0 - 14, title, 13, weight="600")
        for k in range(5):
            u = lo + (hi - lo) * k / 4
            s.line(x0, Y(u), x0 + pw, Y(u), stroke=GRID, sw=1)
            s.text(x0 - 6, Y(u) + 4, f"{u:.3f}", 10, MUTED, anchor="end")
        for k in range(0, 5):
            b = k / 4
            s.text(X(b), y0 + ph + 16, f"{b:.2f}", 10, MUTED, anchor="middle")
        s.text(x0 + pw / 2, y0 + ph + 34, "bid", 11, MUTED, anchor="middle")
        if p == 0:
            s.text(14, y0 + ph / 2, "expected utility", 11, MUTED, anchor="middle", rotate=-90)
        pts = " ".join(f"{X(b):.1f},{Y(u):.1f}" for b, u in zip(bids, ref))
        s.add(f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="2"/>')
        for b, m, e, r in zip(bids, means, ses, ref):
            worst = max(worst, abs(m - r) / e if e else 0)
            s.line(X(b), Y(m - 2 * e), X(b), Y(m + 2 * e), stroke=ORANGE, sw=1.5)
            s.add(f'<circle cx="{X(b):.1f}" cy="{Y(m):.1f}" r="3.5" fill="{ORANGE}" stroke="{SURFACE}" stroke-width="1.5"/>')
        best = max(range(len(bids)), key=lambda j: ref[j])
        s.text(X(bids[best]), Y(ref[best]) - 12, f"max at {bids[best]:.2f}", 11, INK, anchor="middle", weight="600")
    s.line(70, 402, 100, 402, stroke=BLUE, sw=2)
    s.text(106, 406, "closed form", 12)
    s.add(f'<circle cx="215" cy="402" r="3.5" fill="{ORANGE}"/>')
    s.line(215, 394, 215, 410, stroke=ORANGE)
    s.text(226, 406, f"simulated mean ± 2 pooled SE ({len(card['seeds'])} seeds × {params['n_samples']} draws); error bars are drawn but smaller than the markers", 12)
    s.text(850, 424, f"largest gap between simulation and closed form: {worst:.1f} SE", 11, MUTED, anchor="end")
    return s


def selftest():
    from autosci import selftest as st
    result = st.run_selftest(ROOT, "auction-calibration")
    missed = set(result["missed"]) if result["missed"] else set()
    rows = st.MUTATIONS
    W = 900
    H = 90 + 30 * len(rows)
    s = Svg(W, H, "Self-test matrix", f"{result['caught']} of {result['total']} deliberate corruptions are caught by the check meant to catch them.")
    s.text(450, 26, f"Self-test: {result['caught']} of {result['total']} deliberate corruptions caught", 16, anchor="middle", weight="600")
    s.text(40, 56, "corruption applied to a copy", 11, MUTED, weight="600")
    s.text(430, 56, "must be reported with this text", 11, MUTED, weight="600")
    s.text(850, 56, "result", 11, MUTED, anchor="end", weight="600")
    for i, (desc, _fn, expect) in enumerate(rows):
        y = 66 + i * 30
        ok = desc not in missed and not any(desc in str(m) for m in missed)
        if i % 2 == 0:
            s.add(f'<rect x="30" y="{y}" width="840" height="30" fill="#f3f2ee"/>')
        s.text(40, y + 20, desc, 12)
        s.text(430, y + 20, f"“{expect}”", 12, MUTED)
        col = BLUE if ok else ORANGE
        s.add(f'<circle cx="{790}" cy="{y + 15}" r="6" fill="{col}"/>')
        s.text(850, y + 20, "caught" if ok else "MISSED", 12, anchor="end", weight="600")
    s.text(450, H - 12, "A high score is not a safety result: blind spots are printed by `python -m autosci selftest`.", 12, MUTED, anchor="middle")
    return s


FIGURES = {"workflow.svg": workflow, "tiers.svg": tiers, "evidence.svg": evidence,
           "ledger.svg": ledger, "calibration.svg": calibration, "selftest.svg": selftest}


def main(argv):
    check = "--check" in argv
    OUT.mkdir(parents=True, exist_ok=True)
    stale = []
    for name, fn in FIGURES.items():
        text = fn().render()
        path = OUT / name
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(name)
        else:
            path.write_text(text, encoding="utf-8")
            print("wrote", path.relative_to(ROOT))
    if stale:
        print("stale figures:", ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
