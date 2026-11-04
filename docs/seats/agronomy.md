# Seat · Agronomy

**Branch:** `seat/agronomy`

## Owns

- `weather_service.py` (Open-Meteo)
- `agronomy_service.py` (Penman-Monteith, ETc, root-zone balance, fungal_risk, spray volume)
- `tests/test_engine.py`

## First MVP tasks

1. [ ] Lock test: ET0=4.2, Kc=0.75 → **ETc=3.15** (must stay green)
2. [ ] Open-Meteo fetch with timestamp
3. [ ] Root-zone balance → gross irrigation mm
4. [ ] Wind ≥ 15 km/h → `spray_blocked`
5. [ ] `fungal_risk` rule (simple v1)

## Formula

`ETc = Kc × ET0`

## Week 5 — season totals, replay, explainable fungal risk

Branch: `seat/agronomy/week-5-season-totals`

1. [x] Season totals from **1 September** (Moroccan campaign), one value per day
   (last calculation of the day), `needs_check` days add no advised water,
   no stored day → all totals `null`.
   - Recommendation response: `season` object (not written into the stored payload).
   - `GET /api/v1/advisor/plots`: `season_start`, `season_days`, `season_etc_mm`,
     `season_rain_mm`, `season_water_mm`, `season_water_m3`.
2. [x] Replay: `replay_input(payload)` rebuilds the input; same inputs → same ETc,
   dose, spray and fungal results.
3. [x] `fungal_risk` explainable: orchestrator now passes `humidity_pct` and
   `temperature_c`; payload carries `fungal_factors`
   (`humid_air`, `mild_temperature`, `rain_wets_leaves`).
4. [x] ETc = 3.15 test still green.

Files touched outside this seat (review by Backend): `orchestrator.py`,
`api/v1/advisor.py`, `api/v1/recommendations.py`. Contract change: `docs/contract.json`.
