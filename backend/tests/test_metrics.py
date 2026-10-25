import numpy as np
import pandas as pd
import pytest

from app import metrics


def test_summary_known_values():
    error = pd.Series([100.0, -100.0, 300.0, -300.0])
    actual = pd.Series([1000.0, 1000.0, 1000.0, 1000.0])
    s = metrics.summary(error, actual)
    assert s["n_hours"] == 4
    assert s["mae_mw"] == 200
    assert s["bias_mw"] == 0
    assert s["rmse_mw"] == pytest.approx(np.sqrt(50000), abs=0.1)
    assert s["nmae_pct"] == 20
    assert s["max_shortfall_mw"] == 300
    assert s["max_surplus_mw"] == 300
    assert s["share_over_forecast_pct"] == 50


def test_summary_skips_missing_rows():
    s = metrics.summary(pd.Series([100.0, np.nan]), pd.Series([1000.0, 1000.0]))
    assert s["n_hours"] == 1


def test_summary_empty():
    assert metrics.summary(pd.Series([], dtype=float), pd.Series([], dtype=float)) == {"n_hours": 0}


def test_skill_score():
    model = pd.Series([50.0, -50.0])
    base = pd.Series([100.0, -100.0])
    assert metrics.skill_score(model, base) == 0.5
    assert metrics.skill_score(base, base) == 0


def test_histogram_counts_everything():
    e = pd.Series([-600.0, -10.0, 0.0, 10.0, 499.0, 1200.0])
    h = metrics.histogram(e, width_mw=500)
    assert sum(b["count"] for b in h) == len(e)
    assert h[0]["from_mw"] == -1000
