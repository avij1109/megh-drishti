# MeghDrishti — SIH26072

An offline-first Smart India Hackathon 2026 demonstration of thunderstorm and lightning nowcasting around Raipur, Chhattisgarh. It combines four synchronized observation types, identifies and tracks convective cells, projects their path, estimates lightning risk and locality arrival, and issues threshold-based local warnings. The weather inputs and scoring coefficients are deterministic **demo simulation**, not official IMD observations or scientifically validated forecasts.

## Architecture

```text
Synthetic feed adapters (2 radar coverages, satellite IR, lightning, NWP)
  -> timestamped EPSG:4326 fused weather state
  -> threshold/connected-component radar cell detector (>=25 dBZ)
  -> nearest-neighbor cell tracker (stable IDs, motion, growth)
  -> weighted convective-initiation and lightning-risk scores
  -> 15/30/60/90/120-minute motion and intensity forecasts
  -> projected-path locality ETA/risk and threshold alert engine
  -> FastAPI JSON -> React/Vite dashboard with offline SVG map
```

The four adapter functions in `backend/app/scenario.py` are the replacement boundary for actual INSAT, Doppler radar, lightning-network and NWP feeds. Radar fields are mapped to a common geographic grid; all data share an observation timestamp. Frontend visualizations use backend state only. The SVG map does not request map tiles or external fonts.

## Repository

```text
backend/app/scenario.py       deterministic feeds, fusion, detection, tracking, risk and alerts
backend/app/main.py           FastAPI scenario controls and read APIs
backend/tests/               behavioral tests for replay and nowcast pipeline
backend/requirements.txt      Python dependencies
frontend/src/App.tsx          dashboard, controls, offline geospatial visualization
frontend/src/style.css        responsive operator styling
frontend/package.json         Vite/React build and type check commands
```

## Setup and start

Use Python 3.10+ and Node.js 20+. Install packages once; the running demonstration needs no external data or API keys.

**Terminal 1 — backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite server proxies `/api` and `/health` to port 8000. The API documentation is at `http://127.0.0.1:8000/docs`. A development server can be stopped with Ctrl+C. For a production asset check, run `npm run build` in `frontend`.

## Presenter flow (2–3 minutes)

1. **Reset demo**. At T+0, point out synchronized radar, satellite, lightning and environmental inputs, the radar field, and the nascent `MD-01` cell.
2. **Start scenario** or press **Next step** to T+30–40. Show cloud-top cooling, increasing radar dBZ and CI score. Toggle observation layers to show their separate contribution.
3. At T+50–70, select `MD-01`. Show stable track history, movement vector, future positions and the `+15` to `+120` minute horizon selector. Point out rising strike count and lightning-risk polygon.
4. Select Raipur Central or Naya Raipur. Show calculated arrival minutes and risk. At T+50, the first threshold-based warning appears; at T+70, Naya Raipur is warned. Read the localized action and dissemination channels.
5. Press **Reset demo**, then advance again. The same observations, scores and alerts recur exactly.

Play advances one 10-minute frame every 1.8 seconds. The slider can seek any frame; Pause freezes the scenario. Scenario time is fixed to 18 July 2026, 13:00–15:00 IST.

## API

`GET /health`, `GET /api/state`, `GET /api/scenario`, `POST /api/scenario/reset`, `POST /api/scenario/advance`, `POST /api/scenario/seek` with `{"frame": 7}`. Read-specific endpoints: `/api/weather/current`, `/api/weather/radar`, `/api/weather/satellite`, `/api/weather/lightning`, `/api/weather/nwp`, `/api/storms`, `/api/forecast`, `/api/locations`, `/api/alerts`.

The state includes a frame index, all synchronized source payloads, tracked cells, forecasts, locality impacts, active alerts and human-readable score explanations. `advance` stops at frame 12. `reset` returns frame 0. Each frame is a pure deterministic calculation, cached for responsive replay.

## Checks

```bash
cd backend
PYTHONPATH=. python -m pytest -q

cd ../frontend
npm run typecheck
npm run build
```

## Model scope and next integration points

- The current feed adapters generate a realistic-style radar reflectivity field (dBZ), cloud-top cooling, strike points and CAPE/CIN/humidity/wind. They are repeatable synthetic observations.
- Cell detection uses a 25 dBZ grid threshold and connected components. Tracking matches nearby centroids within 22 km. The CI and lightning probabilities are transparent weighted scores for the demo; they have **not** been calibrated against observed outcomes.
- Motion extrapolation and measured intensity trend produce short-range forecasts. Locality ETA comes from the closest point on the projected path; alerts require both arrival and lightning-risk thresholds. This is not a CAP XML feed or operational dissemination service.
- To advance beyond the demo, replace the adapters with licensed data readers, calibrate scores on held-out events, add uncertainty and radar quality control, validate warnings with meteorologists, and connect approved dissemination systems.
# megh-drishti
