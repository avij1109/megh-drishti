"""Deterministic, replaceable observation adapters and transparent demo nowcast.

All coordinates and calculations use a common geographic grid. This is a
teaching/demo model, not a validated meteorological forecast model.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import lru_cache
from math import atan2, cos, degrees, exp, hypot, radians, sin, sqrt

START = datetime(2026, 7, 18, 13, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
MAX_FRAME = 12
LAT0, LON0, DLAT, DLON, ROWS, COLS = 20.85, 80.90, 0.017, 0.020, 46, 66
HORIZONS = (15, 30, 60, 90, 120)
LOCALITIES = [
    {"id": "raipur", "name": "Raipur Central", "lat": 21.2514, "lon": 81.6296, "population": 1010087},
    {"id": "naya", "name": "Naya Raipur", "lat": 21.1598, "lon": 81.7787, "population": 85000},
    {"id": "abhanpur", "name": "Abhanpur", "lat": 21.0522, "lon": 81.7485, "population": 15000},
    {"id": "arang", "name": "Arang", "lat": 21.1964, "lon": 81.9669, "population": 20500},
]


def clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def level(value: float) -> str:
    return "SEVERE" if value >= 75 else "HIGH" if value >= 55 else "MODERATE" if value >= 30 else "LOW"


def distance_km(a: dict, b: dict) -> float:
    dy = (a["lat"] - b["lat"]) * 111.2
    dx = (a["lon"] - b["lon"]) * 111.2 * cos(radians((a["lat"] + b["lat"]) / 2))
    return hypot(dx, dy)


def circle(lat: float, lon: float, radius_km: float, count: int = 24) -> list[list[float]]:
    return [[round(lat + radius_km * sin(2 * 3.14159265 * i / count) / 111.2, 5),
             round(lon + radius_km * cos(2 * 3.14159265 * i / count) / (111.2 * cos(radians(lat))), 5)]
            for i in range(count)]


@lru_cache(maxsize=MAX_FRAME + 1)
def radar_adapter(frame: int) -> dict:
    """Two overlapping synthetic Doppler coverages on one fixed lat/lon grid."""
    lat = [round(LAT0 + i * DLAT, 5) for i in range(ROWS)]
    lon = [round(LON0 + j * DLON, 5) for j in range(COLS)]
    primary = (21.43 - .023 * frame, 81.12 + .083 * frame)
    secondary = (21.31 - .008 * max(0, frame - 3), 81.05 + .043 * max(0, frame - 3))
    peak = min(62, 29 + 3.5 * frame)
    grid = []
    for la in lat:
        row = []
        for lo in lon:
            d1 = ((la - primary[0]) / .105) ** 2 + ((lo - primary[1]) / .13) ** 2
            d2 = ((la - secondary[0]) / .065) ** 2 + ((lo - secondary[1]) / .075) ** 2
            v = peak * exp(-d1 / 2)
            if frame >= 4:
                v = max(v, min(43, 27 + 1.3 * (frame - 4)) * exp(-d2 / 2))
            row.append(round(v, 1) if v >= 5 else 0)
        grid.append(row)
    return {"timestamp": (START + timedelta(minutes=10 * frame)).isoformat(), "radars": [
        {"id": "DWR-RAIPUR", "name": "Raipur Doppler radar", "lat": 21.2514, "lon": 81.6296, "status": "ONLINE"},
        {"id": "DWR-NAGPUR", "name": "Nagpur Doppler radar", "lat": 21.1458, "lon": 79.0882, "status": "ONLINE"}],
        "grid": {"latitudes": lat, "longitudes": lon, "reflectivity_dbz": grid, "unit": "dBZ"}}


def satellite_adapter(frame: int) -> dict:
    top = round(-39 - min(frame, 9) * 2.7, 1)
    cooling = round(min(3.8, 1.1 + .34 * frame), 1)
    center = {"lat": round(21.43 - .023 * frame, 4), "lon": round(81.12 + .083 * frame, 4)}
    return {"timestamp": (START + timedelta(minutes=10 * frame)).isoformat(),
            "cloud_top_temperature_c": top, "cooling_rate_c_per_10min": cooling,
            "convective_signal": round(clamp((abs(top) - 35) * 2.2 + cooling * 9), 1),
            "cloud_polygon": circle(center["lat"], center["lon"], 16 + frame * .65)}


def lightning_adapter(frame: int) -> dict:
    center = {"lat": 21.43 - .023 * frame, "lon": 81.12 + .083 * frame}
    count = max(0, (frame - 1) * 3)
    strikes = []
    for i in range(count):
        angle = i * 2.39996 + frame * .22
        radius = 1.5 + ((i * 7 + frame * 3) % 15) * .62
        strikes.append({"id": f"L-{frame}-{i}",
                        "lat": round(center["lat"] + radius * sin(angle) / 111.2, 5),
                        "lon": round(center["lon"] + radius * cos(angle) / (111.2 * cos(radians(center["lat"]))), 5),
                        "intensity_ka": round(6 + (i * 11 + frame * 3) % 42, 1),
                        "polarity": "negative" if i % 3 else "positive",
                        "timestamp": (START + timedelta(minutes=10 * frame - (i % 9))).isoformat()})
    return {"timestamp": (START + timedelta(minutes=10 * frame)).isoformat(), "strikes": strikes,
            "recent_count": len(strikes)}


def nwp_adapter(frame: int) -> dict:
    return {"timestamp": (START + timedelta(minutes=10 * frame)).isoformat(),
            "cape_j_kg": 1850 + 52 * frame, "cin_j_kg": max(-95, -150 + frame * 8),
            "relative_humidity_pct": min(92, 68 + frame * 2), "temperature_c": round(32.4 - frame * .18, 1),
            "wind_u_ms": 7.7, "wind_v_ms": -2.5, "freezing_level_m": 4750}


def fuse(frame: int) -> dict:
    radar, satellite, lightning, nwp = (radar_adapter(frame), satellite_adapter(frame),
                                        lightning_adapter(frame), nwp_adapter(frame))
    return {"frame": frame, "time": radar["timestamp"], "radar": radar,
            "satellite": satellite, "lightning": lightning, "nwp": nwp,
            "grid_crs": "EPSG:4326", "synchronized": True,
            "source_age_minutes": {"radar": 0, "satellite": 0, "lightning": 0, "nwp": 0}}


def detect_cells(grid: dict) -> list[dict]:
    values = grid["reflectivity_dbz"]
    rows, cols = len(values), len(values[0])
    seen = set()
    cells = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) in seen or values[r][c] < 25:
                continue
            stack, pixels = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                pixels.append((y, x))
                for ny, nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                    if 0 <= ny < rows and 0 <= nx < cols and (ny, nx) not in seen and values[ny][nx] >= 25:
                        seen.add((ny, nx)); stack.append((ny, nx))
            if len(pixels) < 4:
                continue
            weight = sum(values[y][x] for y, x in pixels)
            la = sum(grid["latitudes"][y] * values[y][x] for y, x in pixels) / weight
            lo = sum(grid["longitudes"][x] * values[y][x] for y, x in pixels) / weight
            peak = max(values[y][x] for y, x in pixels)
            area = len(pixels) * DLAT * 111.2 * DLON * 111.2 * cos(radians(la))
            cells.append({"lat": round(la, 5), "lon": round(lo, 5), "peak_dbz": peak,
                          "area_km2": round(area, 1), "radius_km": round(sqrt(area / 3.14159265), 1)})
    return sorted(cells, key=lambda c: c["peak_dbz"], reverse=True)


def track_frames(frame: int) -> list[dict]:
    tracks: dict[str, dict] = {}
    next_id = 1
    for f in range(frame + 1):
        observations = detect_cells(radar_adapter(f)["grid"])
        assigned = set()
        new_tracks = {}
        for observation in observations:
            candidates = [(distance_km(observation, track), tid, track) for tid, track in tracks.items()
                          if tid not in assigned]
            nearest = min(candidates, default=None)
            if nearest and nearest[0] < 22:
                _, tid, old = nearest
                assigned.add(tid)
                history = old["history"] + [{"frame": f, "lat": observation["lat"], "lon": observation["lon"],
                                               "peak_dbz": observation["peak_dbz"]}]
                previous = old["history"][-1]
                dt = max(1, (f - previous["frame"]) * 10)
                dy = (observation["lat"] - previous["lat"]) * 111.2
                dx = (observation["lon"] - previous["lon"]) * 111.2 * cos(radians(observation["lat"]))
                velocity = {"east_km_min": round(dx / dt, 4), "north_km_min": round(dy / dt, 4)}
                speed = round(hypot(dx, dy) / dt * 60, 1)
                heading = round((degrees(atan2(dx, dy)) + 360) % 360)
                trend = round((observation["peak_dbz"] - previous["peak_dbz"]) / dt * 10, 1)
                first_frame = old["first_frame"]
            else:
                tid = f"MD-{next_id:02d}"; next_id += 1
                history = [{"frame": f, "lat": observation["lat"], "lon": observation["lon"],
                            "peak_dbz": observation["peak_dbz"]}]
                velocity = {"east_km_min": 0, "north_km_min": 0}
                speed, heading, trend, first_frame = 0, 0, 0, f
            new_tracks[tid] = {**observation, "id": tid, "history": history, "first_frame": first_frame,
                               "age_min": (f - first_frame) * 10, "velocity": velocity,
                               "speed_kmh": speed, "heading_deg": heading, "trend_dbz_per_10min": trend,
                               "severity": level(clamp((observation["peak_dbz"] - 20) * 2.4))}
        tracks = new_tracks
    return list(tracks.values())


def ci_score(cell: dict, weather: dict) -> float:
    s = weather["satellite"]
    n = weather["nwp"]
    l = weather["lightning"]
    return round(clamp(.33 * clamp(s["cooling_rate_c_per_10min"] / 4 * 100)
                       + .31 * clamp((cell["peak_dbz"] - 20) / 42 * 100)
                       + .22 * clamp((n["cape_j_kg"] - 800) / 2200 * 100)
                       + .14 * clamp(l["recent_count"] / 24 * 100)), 1)


def lightning_risk(cell: dict, weather: dict, ci: float) -> float:
    count = sum(distance_km(cell, strike) <= 18 for strike in weather["lightning"]["strikes"])
    return round(clamp(.32 * clamp(count / 18 * 100)
                       + .29 * clamp((cell["peak_dbz"] - 25) / 35 * 100)
                       + .19 * ci
                       + .12 * clamp((weather["nwp"]["cape_j_kg"] - 1000) / 2000 * 100)
                       + .08 * clamp(cell["trend_dbz_per_10min"] / 5 * 100)), 1)


def project(cell: dict, minutes: int) -> dict:
    east = cell["velocity"]["east_km_min"]
    north = cell["velocity"]["north_km_min"]
    # Initial wind steering is used until the detector has a motion vector.
    if cell["age_min"] == 0:
        east, north = .48, -.15
    lat = cell["lat"] + north * minutes / 111.2
    lon = cell["lon"] + east * minutes / (111.2 * cos(radians(cell["lat"])))
    peak = round(clamp(cell["peak_dbz"] + cell["trend_dbz_per_10min"] * minutes / 10 * .45, 0, 65), 1)
    return {"minutes": minutes, "lat": round(lat, 5), "lon": round(lon, 5),
            "peak_dbz": peak, "severity": level(clamp((peak - 20) * 2.4)),
            "radius_km": round(cell["radius_km"] + minutes * .035, 1)}


def locality_impact(locality: dict, cells: list[dict]) -> dict:
    best = None
    for cell in cells:
        east = cell["velocity"]["east_km_min"] if cell["age_min"] else .48
        north = cell["velocity"]["north_km_min"] if cell["age_min"] else -.15
        dx = (locality["lon"] - cell["lon"]) * 111.2 * cos(radians(cell["lat"]))
        dy = (locality["lat"] - cell["lat"]) * 111.2
        speed2 = east * east + north * north
        closest_min = clamp((dx * east + dy * north) / speed2, 0, 120) if speed2 > .0001 else 0
        separation = hypot(dx - east * closest_min, dy - north * closest_min)
        impact_radius = cell["radius_km"] + 9
        along_risk = clamp((impact_radius + 10 - separation) / (impact_radius + 10) * 100)
        urgency = clamp(100 - closest_min * .35)
        risk = round(clamp(along_risk * (.38 + cell["lightning_risk_pct"] * .0042) * urgency / 100), 1)
        eta = round(closest_min) if separation <= impact_radius and closest_min <= 120 else None
        candidate = {**locality, "source_cell_id": cell["id"], "distance_to_path_km": round(separation, 1),
                     "distance_km": round(hypot(dx, dy), 1), "eta_min": eta,
                     "risk_pct": risk, "risk_level": level(risk),
                     "lightning_risk_pct": round(clamp(cell["lightning_risk_pct"] * along_risk / 100), 1),
                     "storm_severity": cell["severity"]}
        if best is None or candidate["risk_pct"] > best["risk_pct"]:
            best = candidate
    return best or {**locality, "source_cell_id": None, "distance_to_path_km": None,
                    "distance_km": None, "eta_min": None, "risk_pct": 0, "risk_level": "LOW",
                    "lightning_risk_pct": 0, "storm_severity": "LOW"}


@lru_cache(maxsize=MAX_FRAME + 1)
def build_state(frame: int) -> dict:
    if not 0 <= frame <= MAX_FRAME:
        raise ValueError("frame out of range")
    weather = fuse(frame)
    cells = track_frames(frame)
    for cell in cells:
        ci = ci_score(cell, weather)
        risk = lightning_risk(cell, weather, ci)
        cell["ci_score"] = ci
        cell["ci_level"] = level(ci)
        cell["lightning_risk_pct"] = risk
        cell["lightning_level"] = level(risk)
        cell["forecast"] = [project(cell, h) for h in HORIZONS]
        cell["outline"] = circle(cell["lat"], cell["lon"], cell["radius_km"])
        cell["lightning_hazard_polygon"] = circle(cell["lat"], cell["lon"], cell["radius_km"] + 5 + risk * .12)
    localities = [locality_impact(loc, cells) for loc in LOCALITIES]
    alerts = []
    for loc in localities:
        if loc["eta_min"] is not None and loc["eta_min"] <= 65 and loc["lightning_risk_pct"] >= 55:
            severity = "SEVERE" if loc["lightning_risk_pct"] >= 75 or loc["risk_pct"] >= 65 else "HIGH"
            alerts.append({"id": f"ALERT-{loc['id']}-{frame}", "event": "Severe Thunderstorm and Lightning" if severity == "SEVERE" else "Thunderstorm and Lightning",
                           "severity": severity, "location_id": loc["id"], "location": loc["name"],
                           "eta_min": loc["eta_min"], "lightning_risk_pct": loc["lightning_risk_pct"],
                           "issued_at": weather["time"], "source_cell_id": loc["source_cell_id"],
                           "recommended_action": "Move indoors. Avoid open fields, trees and exposed structures. Suspend outdoor activity.",
                           "channels": ["Citizen SMS", "Panchayat", "District Administration", "Emergency Network"]})
    primary = cells[0] if cells else None
    explanations = []
    if primary:
        explanations = [f"Cloud tops cooling {weather['satellite']['cooling_rate_c_per_10min']}°C / 10 min",
                        f"Radar core {primary['peak_dbz']} dBZ; trend {primary['trend_dbz_per_10min']:+.1f} dBZ / 10 min",
                        f"{weather['lightning']['recent_count']} recent lightning observations",
                        f"CAPE {weather['nwp']['cape_j_kg']} J/kg supports convection"]
        nearest = min(localities, key=lambda l: l["distance_to_path_km"] if l["distance_to_path_km"] is not None else 999)
        explanations.append(f"Projected path passes {nearest['distance_to_path_km']} km from {nearest['name']}")
    return {"scenario": {"id": "raipur-severe-01", "name": "Raipur severe convection", "frame": frame,
                         "max_frame": MAX_FRAME, "step_minutes": 10, "time": weather["time"],
                         "elapsed_minutes": frame * 10, "complete": frame == MAX_FRAME},
            "weather": weather, "cells": cells, "localities": localities, "alerts": alerts,
            "explanations": explanations, "forecast_horizons": list(HORIZONS)}
