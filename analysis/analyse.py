"""Summarise pairwise AI output ratings exported from tool/evaluate.html.

Usage:
    python analysis/analyse.py ratings/ratings.csv --out results

Produces:
    results/summary.md          headline findings and quality-control flags
    results/scores_by_dimension.png
    results/issue_frequency.png
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

DIMENSIONS = ["adherence", "quality", "realism"]
MIN_EXPLANATION_CHARS = 80


def load_ratings(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = ["pair_id", "preferred", "explanation"] + [f"{s}_{d}" for s in "ab" for d in DIMENSIONS]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"ratings file is missing columns: {missing}")
    for s in "ab":
        for d in DIMENSIONS:
            df[f"{s}_{d}"] = pd.to_numeric(df[f"{s}_{d}"], errors="coerce")
        df[f"{s}_issues"] = df.get(f"{s}_issues", "").fillna("").astype(str)
    df["explanation"] = df["explanation"].fillna("").astype(str)
    df["modality"] = df.get("modality", "unknown").fillna("unknown").replace("", "unknown")
    return df


def long_scores(df: pd.DataFrame) -> pd.DataFrame:
    """One row per output per dimension, marked as preferred or not."""
    rows = []
    for _, r in df.iterrows():
        for s in "ab":
            for d in DIMENSIONS:
                rows.append({
                    "pair_id": r["pair_id"], "modality": r["modality"], "side": s, "dimension": d,
                    "score": r[f"{s}_{d}"], "preferred": r["preferred"] == s,
                })
    return pd.DataFrame(rows)


def quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Flag ratings a reviewer would query: preference contradicts scores, thin explanations, ties."""
    flags = []
    for _, r in df.iterrows():
        mean_a = r[[f"a_{d}" for d in DIMENSIONS]].mean()
        mean_b = r[[f"b_{d}" for d in DIMENSIONS]].mean()
        pref_mean, other_mean = (mean_a, mean_b) if r["preferred"] == "a" else (mean_b, mean_a)
        if pref_mean < other_mean:
            flags.append((r["pair_id"], "preferred output has the lower average score"))
        if len(r["explanation"].strip()) < MIN_EXPLANATION_CHARS:
            flags.append((r["pair_id"], "explanation shorter than 80 characters"))
        if mean_a == mean_b:
            flags.append((r["pair_id"], "scores tied: explanation should state the deciding flaw"))
        issues = (r["a_issues"] + ";" + r["b_issues"]).lower()
        if issues.strip(";") == "" and min(mean_a, mean_b) <= 2:
            flags.append((r["pair_id"], "low score but no issue recorded"))
    return pd.DataFrame(flags, columns=["pair_id", "flag"])


def issue_counts(df: pd.DataFrame) -> pd.Series:
    items = []
    for s in "ab":
        for cell in df[f"{s}_issues"]:
            items += [x.strip() for x in cell.split(";") if x.strip()]
    return pd.Series(items, dtype="object").value_counts()


def plot_scores(scores: pd.DataFrame, out: Path) -> None:
    table = scores.groupby(["dimension", "preferred"])["score"].mean().unstack()
    table = table.reindex(DIMENSIONS)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    x = range(len(table))
    width = 0.38
    ax.bar([i - width / 2 for i in x], table.get(True), width, label="Preferred output", color="#2f5d50")
    ax.bar([i + width / 2 for i in x], table.get(False), width, label="Other output", color="#b8c4bf")
    ax.set_xticks(list(x), [d.title() for d in table.index])
    ax.set_ylim(0, 5)
    ax.set_ylabel("Mean score (1–5)")
    ax.set_title("Scores by dimension")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def plot_issues(counts: pd.Series, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 3.5))
    if counts.empty:
        ax.text(0.5, 0.5, "No issues recorded", ha="center", va="center")
        ax.axis("off")
    else:
        counts.sort_values().plot.barh(ax=ax, color="#2f5d50")
        ax.set_xlabel("Times recorded")
        ax.set_title("Most common problems spotted")
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def write_summary(df: pd.DataFrame, scores: pd.DataFrame, flags: pd.DataFrame, counts: pd.Series, out: Path) -> None:
    pref = scores[scores["preferred"]].groupby("dimension")["score"].mean().reindex(DIMENSIONS)
    other = scores[~scores["preferred"]].groupby("dimension")["score"].mean().reindex(DIMENSIONS)
    gap = (pref - other).sort_values(ascending=False)
    lines = [
        "# Evaluation summary",
        "",
        f"- Pairs rated: {len(df)}",
        f"- Modalities: {', '.join(f'{m} ({n})' for m, n in df['modality'].value_counts().items())}",
        f"- Median explanation length: {int(df['explanation'].str.len().median())} characters",
        f"- Dimension that most separated the preferred output: **{gap.index[0]}** "
        f"(+{gap.iloc[0]:.2f} points on average)",
        "",
        "| Dimension | Preferred output | Other output | Gap |",
        "|---|---|---|---|",
    ]
    for d in DIMENSIONS:
        lines.append(f"| {d.title()} | {pref[d]:.2f} | {other[d]:.2f} | {pref[d] - other[d]:+.2f} |")
    lines += ["", "## Most common problems", ""]
    lines += [f"- {k}: {v}" for k, v in counts.items()] or ["- none recorded"]
    lines += ["", "## Quality-control flags", ""]
    if flags.empty:
        lines.append("No ratings flagged.")
    else:
        lines += [f"- `{r.pair_id}`: {r.flag}" for r in flags.itertuples()]
    lines += ["", "![Scores by dimension](scores_by_dimension.png)", "", "![Issue frequency](issue_frequency.png)", ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ratings", type=Path)
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()

    df = load_ratings(args.ratings)
    if df.empty:
        raise SystemExit("No ratings yet: rate some pairs in tool/evaluate.html and export ratings.csv first.")
    args.out.mkdir(parents=True, exist_ok=True)
    scores = long_scores(df)
    flags = quality_flags(df)
    counts = issue_counts(df)
    plot_scores(scores, args.out / "scores_by_dimension.png")
    plot_issues(counts, args.out / "issue_frequency.png")
    write_summary(df, scores, flags, counts, args.out / "summary.md")
    print(f"Wrote summary for {len(df)} pairs to {args.out}/summary.md ({len(flags)} flags)")


if __name__ == "__main__":
    main()
