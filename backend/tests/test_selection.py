from datetime import date

import numpy as np
import pandas as pd
import pytest

from app.selection import (
    build_decision_table,
    decision_forecasts,
    hourly_actuals,
    persistence_baseline,
    trailing_bias,
)


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def forecasts_df(rows):
    return pd.DataFrame([{"publishTime": ts(p), "startTime": ts(s), "generation": g}
                         for p, s, g in rows])


def actuals_df(rows):
    return pd.DataFrame([{"startTime": ts(s), "publishTime": ts(p), "generation": g}
                         for s, p, g in rows])


class TestDecisionForecasts:
    def test_picks_latest_forecast_published_before_cutoff(self):
        f = forecasts_df([
            ("2026-01-01T09:30Z", "2026-01-02T10:00Z", 100),
            ("2026-01-01T22:30Z", "2026-01-02T10:00Z", 200),
        ])
        out = decision_forecasts(f, date(2026, 1, 2), date(2026, 1, 2))
        assert out["forecast"].tolist() == [200]
        assert out["horizon_h"].tolist() == [11.5]

    def test_ignores_forecasts_published_on_or_after_delivery_day(self):
        f = forecasts_df([
            ("2026-01-01T22:30Z", "2026-01-02T10:00Z", 200),
            ("2026-01-02T00:00Z", "2026-01-02T10:00Z", 999),
            ("2026-01-02T02:30Z", "2026-01-02T10:00Z", 999),
        ])
        out = decision_forecasts(f, date(2026, 1, 2), date(2026, 1, 2))
        assert out["forecast"].tolist() == [200]

    def test_drops_rows_for_hours_already_past_at_publish(self):
        f = forecasts_df([("2026-01-02T02:30Z", "2026-01-02T01:00Z", 50)])
        out = decision_forecasts(f, date(2026, 1, 2), date(2026, 1, 2))
        assert out.empty

    def test_hour_with_no_eligible_forecast_is_absent(self):
        f = forecasts_df([("2026-01-02T01:30Z", "2026-01-02T10:00Z", 999)])
        out = decision_forecasts(f, date(2026, 1, 2), date(2026, 1, 2))
        assert out.empty


class TestHourlyActuals:
    def test_mean_of_two_half_hours(self):
        a = actuals_df([
            ("2026-01-02T10:00Z", "2026-01-02T10:30Z", 100),
            ("2026-01-02T10:30Z", "2026-01-02T11:00Z", 300),
        ])
        assert hourly_actuals(a)[ts("2026-01-02T10:00Z")] == 200

    def test_incomplete_hour_is_nan(self):
        a = actuals_df([("2026-01-02T10:00Z", "2026-01-02T10:30Z", 100)])
        assert np.isnan(hourly_actuals(a)[ts("2026-01-02T10:00Z")])


def test_persistence_uses_last_actual_published_before_cutoff():
    a = actuals_df([
        ("2026-01-01T22:30Z", "2026-01-01T23:00Z", 10),
        ("2026-01-01T23:00Z", "2026-01-01T23:30Z", 20),
        ("2026-01-01T23:30Z", "2026-01-02T00:00Z", 30),  # published at cutoff: not known yet
    ])
    out = persistence_baseline(a, pd.Series([ts("2026-01-02")]))
    assert out[ts("2026-01-02")] == 20


def test_trailing_bias_uses_only_days_d_minus_7_to_d_minus_2():
    days = pd.date_range("2026-01-01", periods=10, tz="UTC")
    table = pd.DataFrame({"delivery_day": days, "error": [float(i) for i in range(10)]})
    adj = trailing_bias(table)
    # Day index 9 -> window is days 2..7 -> mean of 2..7
    assert adj[days[9]] == pytest.approx(np.mean(range(2, 8)))
    # The first two days have no complete history
    assert adj[days[0]] == 0.0 and adj[days[1]] == 0.0
    assert adj[days[2]] == 0.0  # only day 0 available


def test_decision_table_end_to_end():
    f = forecasts_df([
        ("2026-01-01T22:30Z", "2026-01-02T00:00Z", 1000),
        ("2026-01-02T03:30Z", "2026-01-02T00:00Z", 5000),  # too late, ignored
    ])
    a = actuals_df([
        ("2026-01-01T23:00Z", "2026-01-01T23:30Z", 700),
        ("2026-01-02T00:00Z", "2026-01-02T00:30Z", 800),
        ("2026-01-02T00:30Z", "2026-01-02T01:00Z", 600),
    ])
    t = build_decision_table(a, f, date(2026, 1, 2), date(2026, 1, 2))
    assert len(t) == 24
    first = t.iloc[0]
    assert first["forecast"] == 1000
    assert first["actual"] == 700
    assert first["error"] == 300
    assert first["persistence"] == 700
    assert t["forecast"].iloc[1:].isna().all()
