"""Download the January 2026 snapshot from Elexon into backend/data/.

Usage: python -m app.ingest
"""
import pandas as pd

from . import config
from .elexon import fetch_wind_actuals, fetch_wind_forecasts


def build_actuals() -> pd.DataFrame:
    rows = fetch_wind_actuals(config.ACTUALS_FROM, config.ACTUALS_TO)
    df = pd.DataFrame(rows)[["startTime", "publishTime", "generation"]]
    # A settlement period can be republished; keep the most recent value.
    return (df.sort_values("publishTime")
              .drop_duplicates("startTime", keep="last")
              .sort_values("startTime")
              .reset_index(drop=True))


def build_forecasts() -> pd.DataFrame:
    rows = fetch_wind_forecasts(config.FORECAST_PUBLISH_FROM, config.FORECAST_PUBLISH_TO)
    df = pd.DataFrame(rows)[["publishTime", "startTime", "generation"]]
    return (df.drop_duplicates(["publishTime", "startTime"], keep="last")
              .sort_values(["publishTime", "startTime"])
              .reset_index(drop=True))


def main() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    actuals = build_actuals()
    forecasts = build_forecasts()
    actuals.to_csv(config.ACTUALS_FILE, index=False)
    forecasts.to_csv(config.FORECASTS_FILE, index=False)
    print(f"actuals: {len(actuals)} rows {actuals.startTime.min()} -> {actuals.startTime.max()}")
    print(f"forecasts: {len(forecasts)} rows, {forecasts.publishTime.nunique()} publishes "
          f"{forecasts.publishTime.min()} -> {forecasts.publishTime.max()}")


if __name__ == "__main__":
    main()
