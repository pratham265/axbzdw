"""Thin client for the two Elexon BMRS stream endpoints used by the app."""
from datetime import date, datetime, time, timedelta, timezone

import requests

from .config import ELEXON_BASE_URL

TIMEOUT_S = 60
RETRIES = 3


def _get(dataset: str, params: dict) -> list[dict]:
    url = f"{ELEXON_BASE_URL}/{dataset}/stream"
    last_error = None
    for _ in range(RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT_S)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_error = exc
    raise RuntimeError(f"Elexon {dataset} request failed: {last_error}")


def _day_chunks(start: date, end: date, days: int = 7):
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=days - 1), end)
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


def fetch_wind_actuals(start: date, end: date) -> list[dict]:
    """FUELHH rows for fuelType WIND with settlement dates in [start, end]."""
    rows = []
    for a, b in _day_chunks(start, end):
        rows += _get("FUELHH", {
            "settlementDateFrom": a.isoformat(),
            "settlementDateTo": b.isoformat(),
            "fuelType": "WIND",
        })
    return [r for r in rows if r.get("fuelType") == "WIND"]


def fetch_wind_forecasts(start: date, end: date) -> list[dict]:
    """WINDFOR rows published on days [start, end] (UTC)."""
    rows = []
    for a, b in _day_chunks(start, end):
        frm = datetime.combine(a, time.min, timezone.utc)
        to = datetime.combine(b + timedelta(days=1), time.min, timezone.utc) - timedelta(seconds=1)
        rows += _get("WINDFOR", {
            "publishDateTimeFrom": frm.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return rows
