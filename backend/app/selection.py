"""Turn raw Elexon rows into the hourly table a trader would have worked from.

Conventions
-----------
* All timestamps are tz-aware UTC (GMT == UTC in January).
* WINDFOR is hourly, FUELHH is half-hourly. The actual for hour H is the mean of
  the two settlement periods starting at H and H+30min; an hour with a missing
  half is left empty rather than guessed.
* error = forecast - actual. Positive error means wind under-delivered against
  the forecast, i.e. the shortfall the team would have had to buy in.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import config

BIAS_WINDOW_DAYS = 6


def _utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def load_actuals(path=config.ACTUALS_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["startTime"] = _utc(df["startTime"])
    df["publishTime"] = _utc(df["publishTime"])
    return df


def load_forecasts(path=config.FORECASTS_FILE) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["startTime"] = _utc(df["startTime"])
    df["publishTime"] = _utc(df["publishTime"])
    return df


def hourly_actuals(actuals: pd.DataFrame) -> pd.Series:
    """Hourly mean wind generation (MW), NaN where a half-hour is missing."""
    hour = actuals["startTime"].dt.floor("h")
    agg = actuals.groupby(hour)["generation"].agg(["mean", "count"])
    return agg["mean"].where(agg["count"] == 2).rename("actual")


def cutoff_for(delivery_day: pd.Series) -> pd.Series:
    return delivery_day + config.DECISION_CUTOFF_OFFSET


def decision_forecasts(forecasts: pd.DataFrame, first_day: date, last_day: date) -> pd.DataFrame:
    """Latest forecast for each delivery hour that was published before the cutoff.

    Forecasts published after the cutoff are dropped so the evaluation never
    uses information the trader did not have (no look-ahead).
    """
    f = forecasts.copy()
    f["delivery_day"] = f["startTime"].dt.floor("D")
    f = f[(f["delivery_day"].dt.date >= first_day) & (f["delivery_day"].dt.date <= last_day)]
    f = f[f["publishTime"] < cutoff_for(f["delivery_day"])]
    f = f[f["startTime"] >= f["publishTime"]]
    latest = f.sort_values("publishTime").groupby("startTime").tail(1)
    latest = latest.rename(columns={"generation": "forecast"})
    latest["horizon_h"] = (latest["startTime"] - latest["publishTime"]).dt.total_seconds() / 3600
    return latest.sort_values("startTime").reset_index(drop=True)


def persistence_baseline(actuals: pd.DataFrame, delivery_days: pd.Series) -> pd.Series:
    """Naive benchmark: the last actual published before the cutoff, held flat
    for the whole delivery day. Returns a value per delivery day."""
    a = actuals.sort_values("publishTime")
    values = {}
    for day in pd.Series(delivery_days.unique()):
        known = a[a["publishTime"] < cutoff_for(pd.Series([day]))[0]]
        values[day] = known["generation"].iloc[-1] if len(known) else np.nan
    return pd.Series(values, name="persistence")


def build_decision_table(actuals: pd.DataFrame, forecasts: pd.DataFrame,
                         first_day: date = config.DELIVERY_FIRST_DAY,
                         last_day: date = config.DELIVERY_LAST_DAY) -> pd.DataFrame:
    """One row per delivery hour: decision forecast, actual, baseline, errors."""
    hours = pd.date_range(pd.Timestamp(first_day, tz="UTC"),
                          pd.Timestamp(last_day + timedelta(days=1), tz="UTC"),
                          freq="h", inclusive="left", name="startTime")
    table = pd.DataFrame(index=hours).reset_index()
    table["delivery_day"] = table["startTime"].dt.floor("D")

    fc = decision_forecasts(forecasts, first_day, last_day)
    table = table.merge(fc[["startTime", "publishTime", "forecast", "horizon_h"]],
                        on="startTime", how="left")
    table = table.merge(hourly_actuals(actuals), left_on="startTime",
                        right_index=True, how="left")
    table["persistence"] = table["delivery_day"].map(
        persistence_baseline(actuals, table["delivery_day"]))

    table["error"] = table["forecast"] - table["actual"]
    table["persistence_error"] = table["persistence"] - table["actual"]

    table["bias_adjustment"] = table["delivery_day"].map(trailing_bias(table))
    table["bias_corrected"] = table["forecast"] - table["bias_adjustment"]
    table["bias_corrected_error"] = table["bias_corrected"] - table["actual"]
    return table


def trailing_bias(table: pd.DataFrame) -> pd.Series:
    """Mean decision-forecast error over delivery days D-7..D-2 for each day D.

    D-1 is excluded because its final settlement period is only published at
    the cutoff itself, so it is not fully known when the decision is made.
    Days without any history get no adjustment.
    """
    daily = table.groupby("delivery_day")["error"].mean()
    adj = {}
    for day in daily.index:
        window = daily[(daily.index >= day - pd.Timedelta(days=BIAS_WINDOW_DAYS + 1))
                       & (daily.index <= day - pd.Timedelta(days=2))]
        adj[day] = window.mean() if window.notna().any() else 0.0
    return pd.Series(adj)


def all_vintage_errors(actuals: pd.DataFrame, forecasts: pd.DataFrame,
                       first_day: date = config.DELIVERY_FIRST_DAY,
                       last_day: date = config.DELIVERY_LAST_DAY) -> pd.DataFrame:
    """Every forecast vintage (not just the decision one) against the actual,
    used to show how accuracy depends on how far ahead the forecast is made."""
    f = forecasts[forecasts["startTime"] >= forecasts["publishTime"]].copy()
    day = f["startTime"].dt.date
    f = f[(day >= first_day) & (day <= last_day)]
    f["horizon_h"] = (f["startTime"] - f["publishTime"]).dt.total_seconds() / 3600
    f = f.merge(hourly_actuals(actuals), left_on="startTime", right_index=True, how="inner")
    f["error"] = f["generation"] - f["actual"]
    return f.dropna(subset=["error"])
