"""Tests use a small hand-made fixture, not real ratings."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
import analyse  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "sample_ratings.csv"


def test_flags_catch_contradictions_and_thin_explanations():
    df = analyse.load_ratings(FIXTURE)
    flags = analyse.quality_flags(df)
    t3 = set(flags[flags.pair_id == "t3"].flag)
    assert "preferred output has the lower average score" in t3
    assert "explanation shorter than 80 characters" in t3
    assert "low score but no issue recorded" in t3
    assert flags[flags.pair_id == "t1"].empty


def test_issue_counts():
    counts = analyse.issue_counts(analyse.load_ratings(FIXTURE))
    assert counts["distorted anatomy"] == 1 and counts["flicker / unnatural motion"] == 1


def test_cli_writes_outputs(tmp_path):
    subprocess.run([sys.executable, str(ROOT / "analysis" / "analyse.py"), str(FIXTURE), "--out", str(tmp_path)], check=True)
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "scores_by_dimension.png").exists()
