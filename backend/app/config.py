"""Scope and business rules for the analysis, kept in one place."""
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ACTUALS_FILE = DATA_DIR / "actuals.csv"
FORECASTS_FILE = DATA_DIR / "forecasts.csv"

ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

# Purchase decisions are made during January 2026. A decision taken on day D-1
# is for delivery day D, so delivery runs 2 Jan - 1 Feb 2026.
DECISION_FIRST_DAY = date(2026, 1, 1)
DECISION_LAST_DAY = date(2026, 1, 31)
DELIVERY_FIRST_DAY = DECISION_FIRST_DAY + timedelta(days=1)
DELIVERY_LAST_DAY = DECISION_LAST_DAY + timedelta(days=1)

# Decisions are made "one day before the delivery day": the usable forecast for
# delivery day D is the latest one published before 00:00 on D. The UK is on
# GMT throughout January, so UTC midnight is UK midnight.
DECISION_CUTOFF_OFFSET = timedelta(0)

# Forecast vintages fetched for the horizon analysis (every forecast whose
# target falls in the delivery window was published within this range).
FORECAST_PUBLISH_FROM = DELIVERY_FIRST_DAY - timedelta(days=3)
FORECAST_PUBLISH_TO = DELIVERY_LAST_DAY + timedelta(days=1)

# Actuals: one extra day before delivery feeds the persistence baseline.
ACTUALS_FROM = DECISION_FIRST_DAY
ACTUALS_TO = DELIVERY_LAST_DAY
