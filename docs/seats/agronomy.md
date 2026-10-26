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
