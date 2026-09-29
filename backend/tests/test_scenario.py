import asyncio

import httpx

from app.main import app, cors_origins
from app.scenario import MAX_FRAME, build_state, detect_cells


def test_health_reset_and_deterministic_replay():
    async def flow():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/health")).json()["status"] == "ok"
            first = (await client.post("/api/scenario/reset")).json()
            for _ in range(7):
                await client.post("/api/scenario/advance")
            replay = (await client.post("/api/scenario/reset")).json()
            assert first == replay
            assert first["scenario"]["frame"] == 0
    asyncio.run(flow())


def test_sources_evolve_and_share_time():
    a, b = build_state(0), build_state(7)
    assert a["weather"]["radar"]["grid"] != b["weather"]["radar"]["grid"]
    assert a["weather"]["satellite"]["cloud_top_temperature_c"] > b["weather"]["satellite"]["cloud_top_temperature_c"]
    assert len(a["weather"]["lightning"]["strikes"]) < len(b["weather"]["lightning"]["strikes"])
    assert b["weather"]["nwp"]["cape_j_kg"] > a["weather"]["nwp"]["cape_j_kg"]
    assert len(b["weather"]["radar"]["radars"]) == 2
    assert len({b["weather"][source]["timestamp"] for source in ("radar", "satellite", "lightning", "nwp")}) == 1


def test_detection_tracking_forecast_and_hazard():
    early, late = build_state(2), build_state(7)
    assert detect_cells(early["weather"]["radar"]["grid"])
    ids = {c["id"] for c in early["cells"]} & {c["id"] for c in late["cells"]}
    assert ids
    cell = next(c for c in late["cells"] if c["id"] in ids)
    assert len(cell["history"]) >= 6
    assert cell["speed_kmh"] > 0
    assert [x["minutes"] for x in cell["forecast"]] == [15, 30, 60, 90, 120]
    assert cell["forecast"][0]["lon"] > cell["lon"]
    assert len(cell["lightning_hazard_polygon"]) >= 12


def test_lightning_risk_eta_and_alert_threshold():
    early, late = build_state(0), build_state(10)
    assert late["cells"][0]["lightning_risk_pct"] > early["cells"][0]["lightning_risk_pct"]
    assert 0 <= late["cells"][0]["lightning_risk_pct"] <= 100
    assert any(loc["eta_min"] is not None for loc in late["localities"])
    assert late["alerts"]
    assert not early["alerts"]
    assert all(a["lightning_risk_pct"] >= 55 for a in late["alerts"])


def test_api_seek_and_bounds():
    async def flow():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.post("/api/scenario/seek", json={"frame": 8})).json()["scenario"]["frame"] == 8
            assert (await client.get("/api/forecast")).json()["horizons"] == [15, 30, 60, 90, 120]
            assert (await client.post("/api/scenario/seek", json={"frame": MAX_FRAME + 1})).status_code == 422
            await client.post("/api/scenario/reset")
    asyncio.run(flow())


def test_cors_origins_keep_local_defaults_and_accept_configured_frontend():
    origins = cors_origins(" https://frontend.example.vercel.app/ , , *, https://frontend.example.vercel.app, https://example.com/path ")
    assert origins == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://frontend.example.vercel.app",
    ]
