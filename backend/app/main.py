"""MeghDrishti local demo API."""
import os
from threading import Lock
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .scenario import MAX_FRAME, build_state

def cors_origins(raw: str | None) -> list[str]:
    """Add configured frontend origins to the local development defaults."""
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    for value in (raw or "").split(","):
        parsed = urlsplit(value.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            continue
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if origin not in origins:
            origins.append(origin)
    return origins


app = FastAPI(title="MeghDrishti Nowcast API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=cors_origins(os.getenv("CORS_ORIGINS")),
                   allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["*"])
_lock = Lock()
_frame = 0


class SeekRequest(BaseModel):
    frame: int = Field(ge=0, le=MAX_FRAME)


def state() -> dict:
    with _lock:
        frame = _frame
    return build_state(frame)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "MeghDrishti", "scenario_ready": True}


@app.get("/api/scenario")
async def scenario() -> dict:
    return state()["scenario"]


@app.post("/api/scenario/reset")
async def reset() -> dict:
    global _frame
    with _lock:
        _frame = 0
    return state()


@app.post("/api/scenario/advance")
async def advance() -> dict:
    global _frame
    with _lock:
        _frame = min(MAX_FRAME, _frame + 1)
    return state()


@app.post("/api/scenario/seek")
async def seek(request: SeekRequest) -> dict:
    global _frame
    with _lock:
        _frame = request.frame
    return state()


@app.get("/api/state")
async def full_state() -> dict:
    return state()


@app.get("/api/weather/current")
async def weather() -> dict:
    return state()["weather"]


@app.get("/api/weather/radar")
async def radar() -> dict:
    return state()["weather"]["radar"]


@app.get("/api/weather/satellite")
async def satellite() -> dict:
    return state()["weather"]["satellite"]


@app.get("/api/weather/lightning")
async def lightning() -> dict:
    return state()["weather"]["lightning"]


@app.get("/api/weather/nwp")
async def nwp() -> dict:
    return state()["weather"]["nwp"]


@app.get("/api/storms")
async def storms() -> dict:
    return {"cells": state()["cells"]}


@app.get("/api/forecast")
async def forecast() -> dict:
    current = state()
    return {"time": current["scenario"]["time"], "horizons": current["forecast_horizons"],
            "cells": [{"id": cell["id"], "forecast": cell["forecast"]} for cell in current["cells"]]}


@app.get("/api/locations")
async def locations() -> dict:
    return {"localities": state()["localities"]}


@app.get("/api/alerts")
async def alerts() -> dict:
    return {"alerts": state()["alerts"]}
