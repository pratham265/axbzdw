"""Smoke tests against the real January snapshot in backend/data."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_meta_reports_full_coverage():
    m = client.get("/api/meta").json()
    c = m["completeness"]
    assert c["expected_hours"] == 31 * 24
    assert c["hours_compared"] == c["expected_hours"]


def test_accuracy_shape():
    a = client.get("/api/accuracy").json()
    assert a["forecast"]["n_hours"] == 744
    assert len(a["by_hour"]) == 24
    assert len(a["by_day"]) == 31


def test_accuracy_range_filter():
    a = client.get("/api/accuracy", params={"start": "2026-01-10", "end": "2026-01-11"}).json()
    assert a["forecast"]["n_hours"] == 48


def test_rejects_dates_outside_scope():
    assert client.get("/api/accuracy", params={"start": "2025-12-01"}).status_code == 400
    assert client.get("/api/day/2026-03-01").status_code == 400


def test_day_view_uses_only_pre_cutoff_forecasts():
    d = client.get("/api/day/2026-01-15").json()
    assert len(d["hours"]) == 24
    assert all(v["publishTime"] < d["cutoff"] for v in d["vintages"])
    assert d["decision_publish_time"] < d["cutoff"]


def test_horizon_curve_present():
    h = client.get("/api/horizon").json()
    assert h[0]["horizon"] == "0-6h"
