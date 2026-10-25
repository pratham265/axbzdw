from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config, service

app = FastAPI(title="Wind Forecast Accuracy API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])


def _check_range(start: date | None, end: date | None):
    for d in (start, end):
        if d and not (config.DELIVERY_FIRST_DAY <= d <= config.DELIVERY_LAST_DAY):
            raise HTTPException(400, f"Dates must be within {config.DELIVERY_FIRST_DAY} "
                                     f"and {config.DELIVERY_LAST_DAY}")
    if start and end and start > end:
        raise HTTPException(400, "start must not be after end")


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta():
    return service.meta()


@app.get("/api/accuracy")
def accuracy(start: date | None = Query(None), end: date | None = Query(None)):
    _check_range(start, end)
    return service.accuracy(start, end)


@app.get("/api/horizon")
def horizon():
    return service.horizon()


@app.get("/api/series")
def series(start: date | None = Query(None), end: date | None = Query(None)):
    _check_range(start, end)
    return service.series(start, end)


@app.get("/api/day/{day}")
def delivery_day(day: date):
    _check_range(day, day)
    return service.delivery_day(day)
