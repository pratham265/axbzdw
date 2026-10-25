# Wind Forecast Monitor

A web app for a UK utility's day-ahead power purchasing team. It shows:

1. **The wind forecast that was available when each purchase decision was made**, next to what actually happened.
2. **How accurate that forecast is, in numbers**, so the size of the error can be built into buying decisions.

Scope: national GB wind generation, purchase decisions made in **January 2026**. The only data used is Elexon
BMRS [FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream) (actuals, `fuelType = WIND`)
and [WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) (forecasts).

**Live app:** `<VERCEL_URL>`

---

## Key results (delivery days 2 Jan – 1 Feb 2026, 744 hours)

| Method | MAE | RMSE | Bias | nMAE | P90 error |
|---|---|---|---|---|---|
| Decision forecast (WINDFOR, published D-1) | 1.82 GW | 2.28 GW | **+1.60 GW** | 16.2% | 3.61 GW |
| Naive baseline (last known actual) | 2.54 GW | 3.36 GW | +0.59 GW | 22.5% | 5.00 GW |
| Bias-corrected forecast (past errors only) | **1.56 GW** | 2.05 GW | +0.02 GW | 13.8% | 3.03 GW |

* The forecast **over-predicted wind in 88% of hours**. Taken at face value, it would have led to consistent under-buying.
* In 9 out of 10 hours, actual wind was no more than **3.6 GW below the forecast**. That is the buffer needed for 90% cover.
* The over-forecast grows with wind level. Above 15 GW forecast, the average bias is **+2.7 GW** and the P90 error is 4.5 GW.
* The forecast beats a naive baseline by **28%** (skill score on MAE).
* Subtracting the mean error of earlier days (which is known at decision time) cuts MAE by **14%**.
* Error grows with lead time: MAE is 1.66 GW at 0–6 h ahead and 2.32 GW at 48–72 h ahead.
* The hardest day was 11 Jan: the forecast was 446 GWh and the actual was 325 GWh, a **121 GWh** shortfall.

---

## Methodology

### Which forecast counts as "available at decision time"
The brief says purchase decisions are made **one day before the delivery day**. For delivery day D, the app
therefore uses, for each hour, the **latest WINDFOR forecast published before 00:00 on D** (i.e. on D-1 or
earlier). The UK is on GMT in January, so UTC equals UK local time and no timezone conversion is needed.

* Forecasts published on D itself are excluded. Including them would credit the forecast with information the
  trader did not have (look-ahead bias).
* WINDFOR rows whose `startTime` is earlier than their `publishTime` are dropped, because they are not forecasts.
* In January this always picked the 22:30 UTC publication on D-1, giving lead times of 1.5–24.5 h.
* The rule lives in one place: `DECISION_CUTOFF_OFFSET` in [backend/app/config.py](backend/app/config.py).

### Matching hourly forecasts to half-hourly actuals
WINDFOR is hourly and FUELHH is half-hourly. The actual for hour H is the **mean of the two settlement
periods** starting at H and H+30 min. An hour with a missing half is excluded, not filled in. Where a
settlement period was published more than once, the latest value is used.

### Metrics
`error = forecast − actual` (MW). A positive error is a shortfall the team has to buy in.

| Metric | Why |
|---|---|
| MAE, RMSE | Typical and large-miss-weighted error size |
| Bias (mean error) | Shows whether the forecast is systematically high or low |
| nMAE = MAE / mean actual | Relative error. MAPE is not used because it blows up when wind output is near zero |
| P10 / P90 error | Empirical error bands. P90 = buffer that covers 90% of hours |
| Error by forecast level | Grouped by the *forecast*, which is known at decision time, so the bands can be applied to tomorrow |
| Error by lead time | Uses every WINDFOR vintage, to show how accuracy depends on how far ahead the forecast is made |
| Skill = 1 − MAE / MAE_baseline | Compares against a naive baseline: last actual published before the cutoff, held flat for the day |

**Bias-corrected forecast:** the decision forecast minus the mean error over delivery days D-7 to D-2. D-1 is
excluded because its last settlement period is only published at the cutoff. This is a walk-forward
correction that uses only information available at decision time. It is shown as an indication of value,
not as a production model.

### Limitations
* One month of data, so all statistics are estimated from 744 hours.
* The likely-range band on the day view uses January's error quantiles per forecast level (in-sample). It
  illustrates the idea and is not a back-tested interval.
* The cause of the over-forecast at high wind cannot be determined from these two datasets alone.

---

## Repository layout

```
.
├── backend/                 Python (FastAPI) API and analysis
│   ├── app/
│   │   ├── config.py        Scope (Jan 2026), decision cutoff rule, file paths
│   │   ├── elexon.py        Elexon BMRS client (chunked requests, retries)
│   │   ├── ingest.py        Downloads FUELHH/WINDFOR into backend/data/ (python -m app.ingest)
│   │   ├── selection.py     Decision-forecast selection, half-hour→hour alignment, baselines
│   │   ├── metrics.py       Accuracy statistics (MAE, RMSE, bias, quantiles, breakdowns)
│   │   ├── service.py       Builds API responses from the cached snapshot
│   │   └── main.py          FastAPI routes
│   ├── data/                January 2026 snapshot (actuals.csv, forecasts.csv)
│   ├── tests/               pytest: selection rules, metrics, API smoke tests
│   ├── requirements*.txt
│   └── Dockerfile
├── frontend/                React (Vite) + Recharts
│   ├── src/pages/           Overview, Day-ahead view, Accuracy analysis, Methodology
│   ├── src/components/      Small shared UI pieces
│   ├── src/api.js           Fetch helper and useApi hook
│   ├── nginx.conf           Serves the build and proxies /api in Docker
│   └── Dockerfile
├── api/index.py             Vercel serverless entry point (wraps backend/app/main.py)
├── vercel.json              Vercel build and routing
├── requirements.txt         Python dependencies for the Vercel function
└── docker-compose.yml       Runs backend + frontend locally
```

### API
| Endpoint | Returns |
|---|---|
| `GET /api/meta` | Scope, cutoff rule, data completeness |
| `GET /api/accuracy?start=&end=` | Summary vs baselines, breakdowns by hour / forecast level / day, histogram |
| `GET /api/series?start=&end=` | Hourly decision forecast, actual, error |
| `GET /api/day/{YYYY-MM-DD}` | Everything known at decision time for one delivery day, plus the outcome |
| `GET /api/horizon` | Error by forecast lead time across all WINDFOR vintages |

---

## Running the app

### Docker
```bash
docker compose up --build
# app: http://localhost:3000   API: http://localhost:8000/api/meta
```

### Without Docker
```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev            # http://localhost:5173, proxies /api to :8000
```

### Tests
```bash
cd backend && pytest
```

### Refreshing the data
The app reads a committed snapshot, so it does not depend on Elexon being up. To rebuild it from the API:
```bash
cd backend && python -m app.ingest
```

### Deploying to Vercel
```bash
vercel --prod
```
`vercel.json` builds the React app as static files and serves the FastAPI app as a Python function under `/api`.

---

## Design decisions
* **Snapshot instead of live calls.** January 2026 is historical. Fetching it once makes the app fast and
  reproducible, and keeps the demo independent of Elexon's availability. `app.ingest` regenerates it.
* **Analysis code is pure functions** (`selection.py`, `metrics.py`) that take and return DataFrames. They are
  tested with small hand-built datasets that pin down the business rules (cutoff, alignment, baselines).
* **The API does the analysis and the frontend only displays it.** The numbers are computed in one place and
  can be checked directly through the API.

---

## Use of AI tools
This project was built with the help of an AI coding assistant (Claude Code by Anthropic). It was used for
scaffolding, code generation, and drafting documentation. The analysis approach, the decision rules, and the
results were reviewed and checked against the data.
