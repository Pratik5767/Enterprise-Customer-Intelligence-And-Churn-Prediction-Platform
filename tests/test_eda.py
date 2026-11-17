import pandas as pd
from src.analysis.stats import association_with_churn, churn_by, wilson_ci



def test_churn_by_computes_rates():
    df = pd.DataFrame({"g": ["a", "a", "b", "b"], "churn_flag": [1, 0, 0, 0]})
    t = churn_by(df, "g").set_index("g")
    assert t.loc["a", "churn_rate_pct"] == 50.0
    assert t.loc["b", "churn_rate_pct"] == 0.0
    assert t.loc["a", "customers"] == 2


def test_wilson_interval_contains_rate_and_stays_in_bounds():
    lo, hi = wilson_ci([30], [100])
    assert 0 <= lo[0] < 0.30 < hi[0] <= 1


def test_cramers_v_is_one_for_perfect_association():
    df = pd.DataFrame({"g": ["x"] * 50 + ["y"] * 50, "churn_flag": [1] * 50 + [0] * 50})
    assoc = association_with_churn(df, ["g"])
    assert assoc.loc[0, "cramers_v"] == 1.0

