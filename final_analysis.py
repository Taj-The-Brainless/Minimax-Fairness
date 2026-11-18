"""Final analysis: readable figures, a per-variant fairness table and a text summary.

    python final_analysis.py                              # reads results/final, writes results/final/report/
    python final_analysis.py --dir results/final --depth 3 --eval mobility

Reads exact.csv, matches.csv, dstar.csv (written by collect_final.py). Pie variants are left out
(their exact result is the base game's). Every figure is made separately, so one failing figure does
not stop the others.

How "balanced" is decided: the 95% interval of the first player's win rate (from the matches at the
chosen depth) contains 0.5. "first-favoured" / "second-favoured" mean the interval lies above / below 0.5.
This says "balanced against depth-limited players", not "balanced against every player".
"""
import argparse
import os
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
import pandas as pd                                  # noqa: E402
from matplotlib.patches import Rectangle             # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("--dir", default=os.path.join("results", "final"))
p.add_argument("--out", default=None, help="default: <dir>/report")
p.add_argument("--depth", type=int, default=3,
               help="search depth of the matches used for fairness (3 exists for every tier)")
p.add_argument("--eval", default="mobility", help="evaluation function of the matches used")
args = p.parse_args()
OUT = args.out or os.path.join(args.dir, "report")
os.makedirs(OUT, exist_ok=True)


def as_bool(s):
    return s.map(lambda x: str(x).strip().lower() == "true")


def family(r):
    base = "plain" if r.memory == "off" else f"{r.memory}-{r.memory_stuck}"
    return ("misere, " if r.misere else "") + base


def prep_exact(exact):
    e = exact.copy()
    for c in ("partisan", "pie", "misere", "mirror_proved"):
        e[c] = as_bool(e[c]) if c in e else False
    e = e[~e["pie"]].copy()
    e["cells"] = e["width"] * e["height"]
    e["family"] = e.apply(family, axis=1)
    e["exact_winner"] = e["winner"].map(lambda w: w if w in ("first", "second", "timeout") else "unsolved")
    e["kind"] = e["partisan"].map({True: "Domineering-like", False: "Cram-like"})
    return e


def with_practical(e, matches, depth, ev):
    m = matches[(matches["depth"] == depth) & (matches["eval"] == ev)]
    cols = ["variant_id", "games", "side0_rate", "side0_ci_low", "side0_ci_high"]
    d = e.merge(m[cols], on="variant_id", how="left")

    def verdict(r):
        if pd.isna(r["side0_rate"]):
            return "no data"
        if r["side0_ci_low"] > 0.5:
            return "first-favoured"
        if r["side0_ci_high"] < 0.5:
            return "second-favoured"
        return "balanced"

    def relation(r):
        if r["exact_winner"] not in ("first", "second") or r["verdict"] == "no data":
            return "n/a"
        if r["verdict"] == "balanced":
            return "theory decides, practice balanced"
        agrees = (r["verdict"] == "first-favoured") == (r["exact_winner"] == "first")
        return "practice agrees with theory" if agrees else "practice contradicts theory"

    d["verdict"] = d.apply(verdict, axis=1)
    d["relation"] = d.apply(relation, axis=1)
    return d


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, name), dpi=150)
    plt.close(fig)


def _draw(ax, gg, kind):
    cmap = plt.get_cmap("coolwarm")
    for r in gg.itertuples():
        edge, lw, tcol = "white", 1, "black"
        if kind == "exact":
            col = {"first": "#4C78A8", "second": "#F58518",
                   "unsolved": "#BBBBBB", "timeout": "#777777"}[r.exact_winner]
            txt = {"first": "1", "second": "2", "unsolved": "?", "timeout": "T"}[r.exact_winner]
            txt += "*" if r.mirror_proved else ""
        elif r.verdict == "no data":
            col, txt = "#EEEEEE", ""
        else:
            col, txt = cmap(r.side0_rate), f"{r.side0_rate:.2f}"
            if r.verdict == "balanced":
                edge, lw = "black", 2.5
            if r.side0_rate < 0.15 or r.side0_rate > 0.85:
                tcol = "white"
        ax.add_patch(Rectangle((r.width - 0.5, r.height - 0.5), 1, 1,
                               facecolor=col, edgecolor=edge, linewidth=lw))
        ax.text(r.width, r.height, txt, ha="center", va="center", fontsize=8, color=tcol)
    ax.set_xlim(1.5, 6.5)
    ax.set_ylim(6.5, 1.5)
    ax.set_xticks(range(2, 7))
    ax.set_yticks(range(2, 7))
    ax.set_xlabel("width (columns)")
    ax.set_ylabel("height (rows)")
    ax.set_aspect("equal")


def board_pages(d, kind, depth, ev):
    """One image per rule family; one panel per (Cram/Domineering-like, shape set)."""
    for fam, g in d.groupby("family"):
        panels = sorted(g.groupby(["partisan", "shapes"]), key=lambda kv: (kv[0][0], kv[0][1]))
        cols = min(3, len(panels))
        rows = (len(panels) + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(4.4 * cols, 4.8 * rows), squeeze=False)
        for ax in axes.flat:
            ax.axis("off")
        for ax, ((par, shapes), gg) in zip(axes.flat, panels):
            ax.axis("on")
            _draw(ax, gg, kind)
            ax.set_title(f"{'Domineering' if par else 'Cram'}-like: {shapes}", fontsize=10)
        if kind == "exact":
            fig.suptitle(f"Exact winner under perfect play - rule family: {fam}\n"
                         "1 = first player, 2 = second, ? = unsolved, T = timeout, * = pairing strategy proved",
                         fontsize=10)
            prefix = "exact_winner"
        else:
            fig.suptitle(f"First player's win rate between depth-{depth} players ({ev} evaluation) - {fam}\n"
                         "red = first player wins more, blue = second; black border = balanced "
                         "(interval contains 0.5)", fontsize=10)
            prefix = "practical_balance"
        _save(fig, f"{prefix}_{re.sub('[^A-Za-z0-9]+', '_', fam).strip('_')}.png")


def theory_vs_practice(d, depth, ev):
    ok = d[d["exact_winner"].isin(["first", "second"]) & (d["verdict"] != "no data")]
    rows = ["first", "second"]
    cols = ["first-favoured", "balanced", "second-favoured"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, (flag, title) in zip(axes, [(False, "no pairing strategy proved"),
                                        (True, "pairing strategy proved (mirror)")]):
        sub = ok[ok["mirror_proved"] == flag]
        tab = pd.crosstab(sub["exact_winner"], sub["verdict"]).reindex(index=rows, columns=cols, fill_value=0)
        ax.imshow(tab.values, cmap="Blues")
        ax.set_xticks(range(3))
        ax.set_xticklabels([f"practice:\n{c}" for c in cols], fontsize=9)
        ax.set_yticks(range(2))
        ax.set_yticklabels([f"exact: {r} wins" for r in rows])
        for i in range(2):
            for j in range(3):
                ax.text(j, i, int(tab.values[i, j]), ha="center", va="center", fontsize=14)
        ax.set_title(f"{title} (n={len(sub)})", fontsize=10)
    fig.suptitle(f"Theory vs practice at depth {depth} ({ev}): diagonal-style cells = practice agrees; "
                 "middle column = theory decides but players look balanced", fontsize=9)
    _save(fig, "theory_vs_practice.png")


def size_trend(d, depth, ev):
    x = d[(d["verdict"] != "no data") & (~d["mirror_proved"])].copy()
    labels = ["4-9 cells", "10-16 cells", "17-25 cells", "26-36 cells"]
    x["bucket"] = pd.cut(x["cells"], bins=[0, 9, 16, 25, 40], labels=labels)
    x["is_balanced"] = (x["verdict"] == "balanced").astype(float)
    x["gap"] = (x["side0_rate"] - 0.5).abs()
    cnt = x.groupby(["bucket", "kind"], observed=False).size().unstack(fill_value=0)
    share = x.groupby(["bucket", "kind"], observed=False)["is_balanced"].mean().unstack()
    gap = x.groupby(["bucket", "kind"], observed=False)["gap"].mean().unstack()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    share.plot(kind="bar", ax=axes[0], rot=0)
    axes[0].set_ylabel("share of variants that look balanced")
    axes[0].set_ylim(0, 1)
    gap.plot(kind="bar", ax=axes[1], rot=0)
    axes[1].set_ylabel("mean |first-player win rate - 0.5|")
    for ax in axes:
        ax.set_xlabel("board size")
        ax.set_xticklabels([f"{b}\n(n={int(cnt.loc[b].sum())})" for b in cnt.index], fontsize=8)
    fig.suptitle(f"Does play get closer to fair on bigger boards? depth {depth}, {ev}, "
                 "variants without a proved pairing strategy", fontsize=9)
    _save(fig, "balance_vs_board_size.png")


def dstar_curves(dstar, e):
    ds = dstar.copy()
    ds = ds[ds["status"] == "ok"]
    ds["d_star"] = pd.to_numeric(ds["d_star"], errors="coerce")
    ds = ds.dropna(subset=["d_star"])
    ds = ds.drop(columns=[c for c in ("kind",) if c in ds.columns]).merge(
        e[["variant_id", "kind"]], on="variant_id", how="inner")
    ds = ds[~((ds["kind"] == "Cram-like") & (ds["eval"] != "zero"))]   # impartial: mobility == zero
    maxd = int(ds["d_star"].max())
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for (ev, kind), g in ds.groupby(["eval", "kind"]):
        xs = list(range(1, maxd + 1))
        ax.step(xs, [(g["d_star"] <= k).mean() for k in xs], where="post", label=f"{kind}, {ev} (n={len(g)})")
    ax.set_xlabel("search depth d (plies)")
    ax.set_ylabel("share of solved variants with settling depth d* <= d")
    ax.set_ylim(0, 1.02)
    ax.legend(fontsize=8)
    ax.set_title("How deep must depth-limited search look to predict the exact winner?", fontsize=10)
    _save(fig, "settling_depth.png")
    return ds


def fairness_table(d, ds):
    t = d.copy()
    t["board"] = t["width"].astype(str) + "x" + t["height"].astype(str)
    if ds is not None and len(ds):
        piv = ds.pivot_table(index="variant_id", columns="eval", values="d_star", aggfunc="first")
        piv.columns = [f"d_star_{c}" for c in piv.columns]
        t = t.merge(piv, left_on="variant_id", right_index=True, how="left")
    keep = ["variant_id", "board", "cells", "kind", "shapes", "family", "exact_winner", "mirror_proved",
            "mirror_winner", "nodes"] + [c for c in t.columns if c.startswith("d_star_")] + [
            "games", "side0_rate", "side0_ci_low", "side0_ci_high", "verdict", "relation"]
    keep = [c for c in keep if c in t.columns]
    t = t[keep].sort_values(["family", "kind", "shapes", "cells", "board"])
    t.to_csv(os.path.join(OUT, "fairness_table.csv"), index=False)
    return t


def summary(d, t):
    lines = []
    n = len(d)
    lines.append(f"variants (without pie): {n}")
    lines.append("exact result: " + ", ".join(f"{k}={v}" for k, v in d["exact_winner"].value_counts().items()))
    lines.append(f"pairing strategy proved for {int(d['mirror_proved'].sum())} variants")
    nm = d[~d["mirror_proved"] & d["exact_winner"].isin(["first", "second"])]
    lines.append("without pairing strategy, solved: " +
                 ", ".join(f"{k}={v}" for k, v in nm["exact_winner"].value_counts().items()))
    lines.append(f"\nmatches used: depth {args.depth}, eval {args.eval}; "
                 f"variants with match data: {int((d['verdict'] != 'no data').sum())}")
    lines.append("verdicts: " + ", ".join(f"{k}={v}" for k, v in d["verdict"].value_counts().items()))
    lines.append("relation to theory: " + ", ".join(f"{k}={v}" for k, v in d["relation"].value_counts().items()))
    sub = d[(d["relation"] == "theory decides, practice balanced") & (~d["mirror_proved"])]
    lines.append(f"\n'theory decides but practice looks balanced' without a proved pairing strategy: {len(sub)}")
    for r in sub.sort_values("cells", ascending=False).head(15).itertuples():
        lines.append(f"  {r.variant_id}: exact {r.exact_winner}, first-player rate {r.side0_rate:.2f} "
                     f"[{r.side0_ci_low:.2f}, {r.side0_ci_high:.2f}]")
    text = "\n".join(lines)
    with open(os.path.join(OUT, "summary.txt"), "w") as f:
        f.write(text + "\n")
    print(text)


def safe(name, fn, *a):
    try:
        return fn(*a)
    except Exception as exc:                # keep going: the other outputs are independent
        print(f"[skipped] {name}: {exc!r}")
        return None


exact = pd.read_csv(os.path.join(args.dir, "exact.csv"))
matches = pd.read_csv(os.path.join(args.dir, "matches.csv"))
dstar_raw = pd.read_csv(os.path.join(args.dir, "dstar.csv"))
e = prep_exact(exact)
d = with_practical(e, matches, args.depth, args.eval)

safe("exact winner pages", board_pages, d, "exact", args.depth, args.eval)
safe("practical balance pages", board_pages, d, "practical", args.depth, args.eval)
safe("theory vs practice", theory_vs_practice, d, args.depth, args.eval)
safe("balance vs size", size_trend, d, args.depth, args.eval)
ds = safe("settling depth", dstar_curves, dstar_raw, e)
table = safe("fairness table", fairness_table, d, ds)
safe("summary", summary, d, table)
print(f"\nfigures, fairness_table.csv and summary.txt are in {OUT}")
