"""Accuracy statistics on forecast errors (error = forecast - actual, in MW)."""
import numpy as np
import pandas as pd

QUANTILES = (0.05, 0.10, 0.50, 0.90, 0.95)

FORECAST_LEVEL_BINS = [0, 5000, 10000, 15000, np.inf]
FORECAST_LEVEL_LABELS = ["< 5 GW", "5-10 GW", "10-15 GW", "> 15 GW"]

HORIZON_BINS = [0, 6, 12, 18, 24, 36, 48, 72]


def _r(x, nd=1):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def summary(error: pd.Series, actual: pd.Series) -> dict:
    """Headline accuracy for a set of hourly errors.

    MAPE is deliberately not reported: it explodes when wind output is near
    zero. nMAE (MAE / mean actual) is used as the relative measure instead.
    """
    mask = error.notna() & actual.notna()
    e, a = error[mask], actual[mask]
    if e.empty:
        return {"n_hours": 0}
    mae = e.abs().mean()
    return {
        "n_hours": int(len(e)),
        "mae_mw": _r(mae),
        "rmse_mw": _r(np.sqrt((e ** 2).mean())),
        "bias_mw": _r(e.mean()),
        "nmae_pct": _r(100 * mae / a.mean(), 2),
        "max_shortfall_mw": _r(e.max()),
        "max_surplus_mw": _r(max(0.0, -e.min())),
        "quantiles_mw": {f"p{int(q * 100)}": _r(e.quantile(q)) for q in QUANTILES},
        "share_over_forecast_pct": _r(100 * (e > 0).mean(), 1),
    }


def skill_score(model_error: pd.Series, baseline_error: pd.Series) -> float | None:
    """1 - MAE_model / MAE_baseline on hours where both exist. >0 means better."""
    mask = model_error.notna() & baseline_error.notna()
    base = baseline_error[mask].abs().mean()
    if not mask.any() or base == 0:
        return None
    return _r(1 - model_error[mask].abs().mean() / base, 3)


def _grouped(df: pd.DataFrame, key, label_name: str) -> list[dict]:
    rows = []
    for k, g in df.groupby(key, observed=True):
        e = g["error"]
        rows.append({
            label_name: k if not isinstance(k, pd.Timestamp) else k.strftime("%Y-%m-%d"),
            "n_hours": int(e.notna().sum()),
            "mae_mw": _r(e.abs().mean()),
            "bias_mw": _r(e.mean()),
            "p10_mw": _r(e.quantile(0.10)),
            "p90_mw": _r(e.quantile(0.90)),
        })
    return rows


def by_hour_of_day(table: pd.DataFrame) -> list[dict]:
    return _grouped(table, table["startTime"].dt.hour, "hour")


def by_forecast_level(table: pd.DataFrame) -> list[dict]:
    """Errors grouped by the *forecast* level, which is what the trader knows
    at decision time, so the bands can be applied to tomorrow's forecast."""
    bins = pd.cut(table["forecast"], FORECAST_LEVEL_BINS, labels=FORECAST_LEVEL_LABELS, right=False)
    return _grouped(table, bins, "forecast_level")


def by_delivery_day(table: pd.DataFrame) -> list[dict]:
    rows = _grouped(table, table["delivery_day"], "day")
    energy = table.groupby("delivery_day")[["forecast", "actual"]].sum(min_count=1)
    for row, (_, en) in zip(rows, energy.iterrows()):
        # Hourly MW summed over the day == MWh for the day.
        row["forecast_mwh"] = _r(en["forecast"], 0)
        row["actual_mwh"] = _r(en["actual"], 0)
    return rows


def by_horizon(vintages: pd.DataFrame) -> list[dict]:
    bins = pd.cut(vintages["horizon_h"], HORIZON_BINS, right=False)
    rows = []
    for interval, g in vintages.groupby(bins, observed=True):
        e = g["error"]
        rows.append({
            "horizon": f"{int(interval.left)}-{int(interval.right)}h",
            "n": int(len(e)),
            "mae_mw": _r(e.abs().mean()),
            "bias_mw": _r(e.mean()),
            "rmse_mw": _r(np.sqrt((e ** 2).mean())),
        })
    return rows


def histogram(error: pd.Series, width_mw: int = 500) -> list[dict]:
    e = error.dropna()
    if e.empty:
        return []
    lo = int(np.floor(e.min() / width_mw) * width_mw)
    hi = int(np.ceil(e.max() / width_mw) * width_mw) + width_mw
    counts, edges = np.histogram(e, bins=np.arange(lo, hi + 1, width_mw))
    return [{"from_mw": int(edges[i]), "to_mw": int(edges[i + 1]), "count": int(c)}
            for i, c in enumerate(counts)]
