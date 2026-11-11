"""Plots for the four key figures of the proposal, from the CSV files in results/<run>/.

    python -m pfair.analysis results/pilot

Needs pandas and matplotlib. Each function returns the figure so you can tweak it.
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _load(run_dir):
    return {n: pd.read_csv(os.path.join(run_dir, f"{n}.csv"))
            for n in ("exact", "dstar", "matches")
            if os.path.exists(os.path.join(run_dir, f"{n}.csv"))}


def plot1_winners(exact: pd.DataFrame, by: str):
    """Plot 1 (Q1): share of variants won by first / second player, grouped by one parameter."""
    solved = exact[exact["winner"].isin(["first", "second"])]
    share = solved.groupby(by)["winner"].value_counts(normalize=True).unstack(fill_value=0)
    ax = share.plot(kind="bar", stacked=True)
    ax.set_ylabel("share of solved variants")
    ax.set_title(f"Winner under perfect play, by {by}")
    return ax.figure


def plot2_dstar(dstar: pd.DataFrame, group: str = "eval"):
    """Plot 2 (Q2): share of variants with d* <= d, one line per group."""
    d = dstar[dstar["status"] == "ok"].copy()
    fig, ax = plt.subplots()
    for g, sub in d.groupby(group):
        xs = sorted(sub["d_star"].unique())
        ax.step(xs, [(sub["d_star"] <= x).mean() for x in xs], where="post", label=str(g))
    ax.set_xlabel("search depth d")
    ax.set_ylabel("share of variants with d* <= d")
    ax.legend(title=group)
    return fig


def plot2b_dstar_rel(dstar: pd.DataFrame, by: str):
    """Plot 2, second panel: d* relative to game length, by rule parameter (box plots)."""
    d = dstar[dstar["status"] == "ok"].copy()
    d["d_star_rel"] = pd.to_numeric(d["d_star_rel"])
    ax = d.boxplot(column="d_star_rel", by=by)
    ax.set_ylabel("d* / game length bound")
    return ax.figure


def plot3_cost(exact: pd.DataFrame, series: str = "memory"):
    """Plot 3 (Q1): nodes of the exact search against board size, one line per rule type."""
    d = exact[exact["solved"]].copy()
    d["cells"] = d["width"] * d["height"]
    fig, ax = plt.subplots()
    for g, sub in d.groupby(series):
        m = sub.groupby("cells")["nodes"].median()
        ax.plot(m.index, m.values, marker="o", label=str(g))
    ax.set_yscale("log")
    ax.set_xlabel("board cells")
    ax.set_ylabel("nodes (median)")
    ax.legend(title=series)
    return fig


def plot4_scatter(matches: pd.DataFrame, depth: int):
    """Plot 4 (Q2): exact winner vs practical first-player win rate, one dot per variant."""
    m = matches[matches["depth"] == depth]
    fig, ax = plt.subplots()
    ax.scatter(m["theory_first_wins"].astype(int), m["side0_rate"], alpha=0.6)
    ax.set_xticks([0, 1], ["second wins (exact)", "first wins (exact)"])
    ax.set_ylabel(f"first-player win rate at depth {depth}")
    return fig


def main(run_dir):
    data = _load(run_dir)
    out = os.path.join(run_dir, "plots")
    os.makedirs(out, exist_ok=True)
    if "exact" in data:
        plot1_winners(data["exact"], "memory").savefig(os.path.join(out, "plot1_winners.png"))
        plot3_cost(data["exact"]).savefig(os.path.join(out, "plot3_cost.png"))
    if "dstar" in data:
        plot2_dstar(data["dstar"]).savefig(os.path.join(out, "plot2_dstar.png"))
    if "matches" in data:
        depth = int(data["matches"]["depth"].max())
        plot4_scatter(data["matches"], depth).savefig(os.path.join(out, "plot4_scatter.png"))
    print("plots written to", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/pilot")
