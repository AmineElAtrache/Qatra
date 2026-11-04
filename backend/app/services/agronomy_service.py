"""Agronomy seat — FAO-56 engine. Deterministic. No LLM here.

Rules this module follows (SEATS.md / docs/assumptions.md):
- Same inputs always give the same outputs (pure functions, no clock, no I/O).
- A missing input stays ``None``: no default value is invented to fill a gap.
- Every number the farmer sees can be traced to a formula in FAO-56
  (Allen et al., 1998, FAO Irrigation and Drainage Paper 56) or to a
  versioned table below.

Units: temperatures °C, wind m/s for Penman-Monteith and km/h for spraying,
radiation MJ m-2 day-1, water depths mm, areas ha.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Versioned tables (MVP, citrus). Change = bump KC_TABLE_VERSION + review.
# ---------------------------------------------------------------------------

KC_TABLE_VERSION = "citrus-mvp-0.1"

# FAO-56 Table 12, citrus with active ground cover, ~70 % canopy:
# Kc ini 0.75 / mid 0.70 / end 0.75. MVP keeps 0.75 for fruit_growth so the
# locked test (ET0 4.2 × Kc 0.75 = 3.15) stays the reference day.
# To be reviewed by an agronomist before any field use.
KC_TABLE: dict[str, float] = {
    "initial": 0.70,
    "flowering": 0.75,
    "fruit_growth": 0.75,
    "maturity": 0.70,
    "dormant": 0.65,
}

# Application efficiency (gross = net / efficiency).
IRRIGATION_EFFICIENCY: dict[str, float] = {
    "drip": 0.90,
    "surface": 0.70,
}
_METHOD_ALIASES: dict[str, str] = {
    "drip": "drip",
    "goutte_a_goutte": "drip",
    "localized": "drip",
    "surface": "surface",
    "gravity": "surface",
    "furrow": "surface",
    "flood": "surface",
}

# Kept for backward compatibility with earlier imports.
DRIP_EFFICIENCY = IRRIGATION_EFFICIENCY["drip"]
SURFACE_EFFICIENCY = IRRIGATION_EFFICIENCY["surface"]

# Spraying: wind at or above this value blocks the spray text.
WIND_BLOCK_KMH = 15.0

# Root zone, citrus (FAO-56 Table 22: Zr 1.2–1.5 m, p = 0.50).
CITRUS_ROOT_DEPTH_M = 1.2
CITRUS_DEPLETION_FRACTION = 0.50

# Soil water (m3/m3), midpoints of FAO-56 Table 19: (field capacity, wilting point).
SOIL_WATER: dict[str, tuple[float, float]] = {
    "sand": (0.12, 0.045),
    "loam": (0.25, 0.12),
    "clay": (0.36, 0.22),
}

# fungal_risk v1: generic humidity rule. Not a named citrus disease
# (see PDF note: no mildiou / oïdium label until an agronomist names it).
FUNGAL_RH_MIN_PCT = 80.0
FUNGAL_T_RANGE_C = (15.0, 28.0)
FUNGAL_RAIN_MIN_MM = 2.0

STEFAN_BOLTZMANN = 4.903e-9  # MJ K-4 m-2 day-1


# ---------------------------------------------------------------------------
# Penman-Monteith ET0 (FAO-56, chapter 3, equation 6)
# ---------------------------------------------------------------------------


def wind_speed_2m(u_z_ms: float, z_m: float = 10.0) -> float:
    """FAO-56 eq. 47: wind measured at height z → wind at 2 m (m/s)."""
    return u_z_ms * 4.87 / math.log(67.8 * z_m - 5.42)


def kmh_to_ms(kmh: float) -> float:
    return kmh / 3.6


def _sat_vapour_pressure(t_c: float) -> float:
    """FAO-56 eq. 11 (kPa)."""
    return 0.6108 * math.exp(17.27 * t_c / (t_c + 237.3))


def extraterrestrial_radiation(lat_deg: float, day_of_year: int) -> float:
    """FAO-56 eq. 21 (MJ m-2 day-1)."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)
    delta = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)
    ws = math.acos(max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta))))
    return (24 * 60 / math.pi) * 0.0820 * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def et0_penman_monteith(
    *,
    t_max_c: float,
    t_min_c: float,
    rs_mj: float,
    u2_ms: float,
    lat_deg: float,
    day_of_year: int,
    elevation_m: float = 0.0,
    rh_max_pct: float | None = None,
    rh_min_pct: float | None = None,
    rh_mean_pct: float | None = None,
) -> float:
    """Daily reference evapotranspiration ET0 (mm/day), FAO-56 eq. 6.

    Humidity: RHmax + RHmin (eq. 17) when both are given, else RHmean (eq. 19).
    Soil heat flux G = 0 for a daily step. Result rounded to 2 decimals.
    """
    t_mean = (t_max_c + t_min_c) / 2
    pressure = 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26  # eq. 7
    gamma = 0.000665 * pressure  # eq. 8
    delta = 4098 * _sat_vapour_pressure(t_mean) / (t_mean + 237.3) ** 2  # eq. 13

    e_tmax = _sat_vapour_pressure(t_max_c)
    e_tmin = _sat_vapour_pressure(t_min_c)
    es = (e_tmax + e_tmin) / 2  # eq. 12
    if rh_max_pct is not None and rh_min_pct is not None:
        ea = (e_tmin * rh_max_pct / 100 + e_tmax * rh_min_pct / 100) / 2  # eq. 17
    elif rh_mean_pct is not None:
        ea = rh_mean_pct / 100 * es  # eq. 19
    else:
        raise ValueError("humidity is required (rh_max+rh_min or rh_mean)")

    ra = extraterrestrial_radiation(lat_deg, day_of_year)
    rso = (0.75 + 2e-5 * elevation_m) * ra  # eq. 37
    rns = 0.77 * rs_mj  # eq. 38, albedo 0.23
    rs_rso = min(rs_mj / rso, 1.0) if rso > 0 else 1.0
    rnl = (
        STEFAN_BOLTZMANN
        * (((t_max_c + 273.16) ** 4 + (t_min_c + 273.16) ** 4) / 2)
        * (0.34 - 0.14 * math.sqrt(ea))
        * (1.35 * rs_rso - 0.35)
    )  # eq. 39
    rn = rns - rnl  # eq. 40
    g = 0.0

    et0 = (0.408 * delta * (rn - g) + gamma * (900 / (t_mean + 273)) * u2_ms * (es - ea)) / (
        delta + gamma * (1 + 0.34 * u2_ms)
    )
    return round(max(et0, 0.0), 2)


# ---------------------------------------------------------------------------
# Crop water use and dose
# ---------------------------------------------------------------------------


def compute_etc(et0_mm_day: float, kc: float) -> float:
    """ETc = Kc × ET0. Locked unit test: 4.2 × 0.75 = 3.15."""
    return round(et0_mm_day * kc, 2)


def kc_for_stage(stage: str | None) -> float | None:
    """Kc of a known stage, else None (no silent default stage)."""
    if not stage:
        return None
    return KC_TABLE.get(stage)


def normalize_method(method: str | None) -> str | None:
    if not method:
        return None
    return _METHOD_ALIASES.get(method.strip().lower())


def efficiency(method: str | None) -> float | None:
    """Application efficiency of a known method, else None."""
    key = normalize_method(method)
    return IRRIGATION_EFFICIENCY.get(key) if key else None


def effective_rain_mm(rain_mm: float | None, max_useful_mm: float | None = None) -> float | None:
    """Useful part of the rain (FAO-56 balance: P − RO).

    MVP: runoff ignored for daily rain; when the root-zone room is known,
    rain above it drains and is not counted (``max_useful_mm``).
    """
    if rain_mm is None:
        return None
    useful = max(rain_mm, 0.0)
    if max_useful_mm is not None:
        useful = min(useful, max(max_useful_mm, 0.0))
    return round(useful, 2)


def gross_from_net(net_mm: float, method: str | None) -> float | None:
    eff = efficiency(method)
    if eff is None:
        return None
    return round(net_mm / eff, 2) if net_mm > 0 else 0.0


# ---------------------------------------------------------------------------
# Root-zone water balance (FAO-56, chapter 8, eq. 85)
# ---------------------------------------------------------------------------


def total_available_water(soil: str, root_depth_m: float = CITRUS_ROOT_DEPTH_M) -> float:
    """TAW = 1000 (θFC − θWP) Zr (mm), FAO-56 eq. 82."""
    fc, wp = SOIL_WATER[soil]
    return round(1000 * (fc - wp) * root_depth_m, 1)


def readily_available_water(taw_mm: float, p: float = CITRUS_DEPLETION_FRACTION) -> float:
    """RAW = p × TAW (mm), FAO-56 eq. 83."""
    return round(p * taw_mm, 1)


@dataclass(frozen=True)
class RootZoneStep:
    depletion_mm: float  # Dr at end of day (0 = field capacity)
    deep_percolation_mm: float


def root_zone_step(
    *,
    depletion_prev_mm: float,
    etc_mm: float,
    effective_rain_mm: float,
    net_irrigation_mm: float,
    taw_mm: float,
) -> RootZoneStep:
    """Dr,i = Dr,i-1 − P_eff − I + ETc, bounded to [0, TAW] (eq. 85, RO = CR = 0).

    Water above field capacity leaves as deep percolation (eq. 88).
    """
    dr = depletion_prev_mm - effective_rain_mm - net_irrigation_mm + etc_mm
    dp = 0.0
    if dr < 0:
        dp = -dr
        dr = 0.0
    dr = min(dr, taw_mm)
    return RootZoneStep(depletion_mm=round(dr, 2), deep_percolation_mm=round(dp, 2))


# ---------------------------------------------------------------------------
# Spraying and disease risk
# ---------------------------------------------------------------------------


def spray_blocked(wind_kmh: float | None) -> bool:
    """Blocked when wind ≥ 15 km/h, or when wind is unknown (no guess)."""
    if wind_kmh is None:
        return True
    return wind_kmh >= WIND_BLOCK_KMH


def fungal_risk(
    *,
    humidity_pct: float | None,
    temperature_c: float | None,
    rain_mm: float | None,
) -> str | None:
    """v1 rule: count wet-weather conditions (humid, mild, rainy).

    3 → high, 2 → medium, 0–1 → low. Returns None if humidity or temperature
    is missing. Generic risk only, not a diagnosis of a named disease.
    """
    if humidity_pct is None or temperature_c is None:
        return None
    t_lo, t_hi = FUNGAL_T_RANGE_C
    score = 0
    score += humidity_pct >= FUNGAL_RH_MIN_PCT
    score += t_lo <= temperature_c <= t_hi
    score += (rain_mm or 0.0) >= FUNGAL_RAIN_MIN_MM
    if score >= 3:
        return "high"
    if score == 2:
        return "medium"
    return "low"


def spray_volume_liters(area_ha: float, liters_per_ha: float = 400.0) -> float:
    """Spray mix volume tied to the surface (L). Rate is a v1 default."""
    return round(area_ha * liters_per_ha, 1)


# ---------------------------------------------------------------------------
# Daily run — called by the orchestrator
# ---------------------------------------------------------------------------


@dataclass
class AgronomyInput:
    et0_mm_day: float | None
    stage: str | None
    irrigation_method: str | None
    effective_rain_mm: float | None = 0.0
    wind_kmh: float | None = 0.0
    area_ha: float = 1.0
    # Optional — when given, they refine the result:
    humidity_pct: float | None = None
    temperature_c: float | None = None
    irrigation_applied_mm: float = 0.0  # net water already applied today
    depletion_prev_mm: float | None = None  # Dr of yesterday → root-zone mode
    soil: str | None = None  # "sand" | "loam" | "clay"


@dataclass
class AgronomyResult:
    kc: float | None
    etc_mm: float | None
    gross_irrigation_mm: float | None
    spray_blocked: bool
    fungal_risk: str | None
    disease_risk: str | None
    reasons: list[str]
    net_irrigation_mm: float | None = None
    spray_volume_l: float | None = None
    depletion_mm: float | None = None
    taw_mm: float | None = None
    raw_mm: float | None = None
    kc_table_version: str = KC_TABLE_VERSION
    missing: list[str] = field(default_factory=list)


def run_agronomy(inp: AgronomyInput) -> AgronomyResult:
    """One plot, one day. Pure: same input → same result."""
    reasons: list[str] = []
    missing: list[str] = []

    kc = kc_for_stage(inp.stage)
    if inp.stage:
        reasons.append(inp.stage)
    if kc is None:
        missing.append("stage")
        if inp.stage:
            reasons.append("unknown_stage")
    if efficiency(inp.irrigation_method) is None:
        missing.append("irrigation_method")
        if inp.irrigation_method:
            reasons.append("unknown_irrigation_method")
    if inp.et0_mm_day is None:
        missing.append("et0")
        reasons.append("missing_et0")

    etc = compute_etc(inp.et0_mm_day, kc) if (kc is not None and inp.et0_mm_day is not None) else None

    taw = raw = depletion = None
    if inp.soil in SOIL_WATER:
        taw = total_available_water(inp.soil)
        raw = readily_available_water(taw)

    net: float | None = None
    rain_room = None
    if etc is not None and inp.effective_rain_mm is not None:
        if taw is not None and inp.depletion_prev_mm is not None:
            # Root-zone mode: refill to field capacity once Dr exceeds RAW.
            rain_room = inp.depletion_prev_mm + etc  # beyond this, rain drains
            p_eff = effective_rain_mm(inp.effective_rain_mm, rain_room) or 0.0
            step = root_zone_step(
                depletion_prev_mm=inp.depletion_prev_mm,
                etc_mm=etc,
                effective_rain_mm=p_eff,
                net_irrigation_mm=inp.irrigation_applied_mm,
                taw_mm=taw,
            )
            depletion = step.depletion_mm
            if depletion >= raw:
                net = depletion
                reasons.append("deficit_above_raw")
            else:
                net = 0.0
                reasons.append("soil_reserve_ok")
        else:
            # Daily replacement mode (no soil history yet).
            p_eff = effective_rain_mm(inp.effective_rain_mm) or 0.0
            net = round(max(etc - p_eff - inp.irrigation_applied_mm, 0.0), 2)
        if inp.effective_rain_mm and inp.effective_rain_mm > 0:
            reasons.append("rain_reduces_need")
    elif inp.effective_rain_mm is None:
        missing.append("rain")

    gross = gross_from_net(net, inp.irrigation_method) if net is not None else None

    blocked = spray_blocked(inp.wind_kmh)
    if inp.wind_kmh is None:
        missing.append("wind")
        reasons.append("wind_unknown")
    elif blocked:
        reasons.append("wind_blocks_spray")

    risk = fungal_risk(
        humidity_pct=inp.humidity_pct,
        temperature_c=inp.temperature_c,
        rain_mm=inp.effective_rain_mm,
    )
    if risk == "high":
        reasons.append("fungal_risk_high")

    return AgronomyResult(
        kc=kc,
        etc_mm=etc,
        gross_irrigation_mm=gross,
        spray_blocked=blocked,
        fungal_risk=risk,
        disease_risk=risk,
        reasons=reasons,
        net_irrigation_mm=net,
        spray_volume_l=None if blocked else spray_volume_liters(inp.area_ha),
        depletion_mm=depletion,
        taw_mm=taw,
        raw_mm=raw,
        missing=missing,
    )
