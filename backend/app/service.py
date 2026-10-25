"""Builds API responses from the cached January snapshot."""
from datetime import date
from functools import lru_cache

import numpy as np
import pandas as pd

from . import config, metrics
from .selection import (
    all_vintage_errors,
    build_decision_table,
    cutoff_for,
    load_actuals,
    load_forecasts,
)


@lru_cache(maxsize=1)
def _data():
    actuals = load_actuals()
    forecasts = load_forecasts()
    return {
        "actuals": actuals,
        "forecasts": forecasts,
        "table": build_decision_table(actuals, forecasts),
        "vintages": all_vintage_errors(actuals, forecasts),
    }


def _iso(t):
    return None if pd.isna(t) else t.strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(x, nd=1):
    return None if pd.isna(x) else round(float(x), nd)


def _window(start: date | None, end: date | None) -> pd.DataFrame:
    t = _data()["table"]
    day = t["delivery_day"].dt.date
    if start:
        t = t[day >= start]
        day = t["delivery_day"].dt.date
    if end:
        t = t[day <= end]
    return t


def meta() -> dict:
    d = _data()
    t = d["table"]
    expected = len(t)
    return {
        "decision_period": [config.DECISION_FIRST_DAY.isoformat(), config.DECISION_LAST_DAY.isoformat()],
        "delivery_period": [config.DELIVERY_FIRST_DAY.isoformat(), config.DELIVERY_LAST_DAY.isoformat()],
        "cutoff_rule": "Latest WINDFOR forecast published before 00:00 UTC (= UK time in January) "
                       "on the delivery day, i.e. published on D-1 or earlier.",
        "sources": {
            "actuals": "Elexon BMRS FUELHH, fuelType WIND (30-min)",
            "forecasts": "Elexon BMRS WINDFOR (hourly, multiple publishes per day)",
        },
        "completeness": {
            "expected_hours": expected,
            "hours_with_forecast": int(t["forecast"].notna().sum()),
            "hours_with_actual": int(t["actual"].notna().sum()),
            "hours_compared": int(t["error"].notna().sum()),
            "raw_actual_rows": int(len(d["actuals"])),
            "raw_forecast_rows": int(len(d["forecasts"])),
            "forecast_publishes": int(d["forecasts"]["publishTime"].nunique()),
        },
        "decision_publish_times": sorted(t["publishTime"].dropna().dt.strftime("%H:%M").unique().tolist()),
    }


def accuracy(start: date | None = None, end: date | None = None) -> dict:
    t = _window(start, end)
    return {
        "forecast": metrics.summary(t["error"], t["actual"]),
        "persistence": metrics.summary(t["persistence_error"], t["actual"]),
        "bias_corrected": metrics.summary(t["bias_corrected_error"], t["actual"]),
        "skill_vs_persistence": metrics.skill_score(t["error"], t["persistence_error"]),
        "bias_corrected_skill_vs_forecast": metrics.skill_score(t["bias_corrected_error"], t["error"]),
        "by_hour": metrics.by_hour_of_day(t),
        "by_forecast_level": metrics.by_forecast_level(t),
        "by_day": metrics.by_delivery_day(t),
        "histogram": metrics.histogram(t["error"]),
    }


def horizon() -> list[dict]:
    return metrics.by_horizon(_data()["vintages"])


def series(start: date | None = None, end: date | None = None) -> list[dict]:
    t = _window(start, end)
    return [{
        "startTime": _iso(r.startTime),
        "publishTime": _iso(r.publishTime),
        "horizon_h": _num(r.horizon_h),
        "forecast": _num(r.forecast),
        "actual": _num(r.actual),
        "error": _num(r.error),
        "bias_corrected": _num(r.bias_corrected),
        "persistence": _num(r.persistence),
    } for r in t.itertuples()]


def _band_by_level() -> dict:
    """P10/P90 error per forecast-level bucket over the whole month."""
    return {row["forecast_level"]: (row["p10_mw"], row["p90_mw"])
            for row in metrics.by_forecast_level(_data()["table"])}


def delivery_day(day: date) -> dict:
    """Everything a trader saw for one delivery day at decision time, plus the outcome."""
    d = _data()
    t = _window(day, day)
    if t.empty:
        raise KeyError(day)
    cutoff = cutoff_for(pd.Series([pd.Timestamp(day, tz="UTC")]))[0]

    f = d["forecasts"]
    f = f[(f["startTime"].dt.date == day) & (f["publishTime"] < cutoff)
          & (f["startTime"] >= f["publishTime"])]
    vintages = [{
        "publishTime": _iso(p),
        "points": [{"startTime": _iso(r.startTime), "forecast": _num(r.generation)}
                   for r in g.sort_values("startTime").itertuples()],
    } for p, g in f.groupby("publishTime")]

    bands = _band_by_level()
    levels = pd.cut(t["forecast"], metrics.FORECAST_LEVEL_BINS,
                    labels=metrics.FORECAST_LEVEL_LABELS, right=False)
    hours = []
    for r, level in zip(t.itertuples(), levels):
        p10, p90 = bands.get(level, (None, None)) if isinstance(level, str) else (None, None)
        hours.append({
            "startTime": _iso(r.startTime),
            "forecast": _num(r.forecast),
            "actual": _num(r.actual),
            "error": _num(r.error),
            # actual = forecast - error, so the error's P90 gives the low edge.
            "p90_low": _num(r.forecast - p90) if p90 is not None else None,
            "p10_high": _num(r.forecast - p10) if p10 is not None else None,
        })

    fc_energy = t["forecast"].sum(min_count=1)
    act_energy = t["actual"].sum(min_count=1)
    return {
        "day": day.isoformat(),
        "cutoff": _iso(cutoff),
        "decision_publish_time": _iso(t["publishTime"].max()),
        "forecast_mwh": _num(fc_energy, 0),
        "actual_mwh": _num(act_energy, 0),
        "shortfall_mwh": _num(fc_energy - act_energy, 0),
        "summary": metrics.summary(t["error"], t["actual"]),
        "hours": hours,
        "vintages": vintages,
    }
