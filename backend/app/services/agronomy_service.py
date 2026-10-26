"""Agronomy seat — FAO-56 engine. Deterministic. No LLM here."""

from __future__ import annotations

from dataclasses import dataclass


# Versioned Kc table (citrus, simplified MVP)
KC_TABLE: dict[str, float] = {
    "initial": 0.70,
    "flowering": 0.75,
    "fruit_growth": 0.75,
    "maturity": 0.70,
    "dormant": 0.65,
}

DRIP_EFFICIENCY = 0.90
SURFACE_EFFICIENCY = 0.70
WIND_BLOCK_KMH = 15.0


@dataclass
class AgronomyInput:
    et0_mm_day: float
    stage: str
    irrigation_method: str
    effective_rain_mm: float = 0.0
    wind_kmh: float = 0.0
    area_ha: float = 1.0


@dataclass
class AgronomyResult:
    kc: float
    etc_mm: float
    gross_irrigation_mm: float
    spray_blocked: bool
    fungal_risk: str
    disease_risk: str
    reasons: list[str]


def compute_etc(et0_mm_day: float, kc: float) -> float:
    """ETc = Kc × ET0. Locked unit test: 4.2 × 0.75 = 3.15."""
    return round(et0_mm_day * kc, 2)


def kc_for_stage(stage: str) -> float:
    return KC_TABLE.get(stage, KC_TABLE["fruit_growth"])


def efficiency(method: str) -> float:
    return DRIP_EFFICIENCY if method == "drip" else SURFACE_EFFICIENCY


def run_agronomy(inp: AgronomyInput) -> AgronomyResult:
    kc = kc_for_stage(inp.stage)
    etc = compute_etc(inp.et0_mm_day, kc)
    net = max(etc - inp.effective_rain_mm, 0.0)
    gross = round(net / efficiency(inp.irrigation_method), 2) if net > 0 else 0.0
    spray_blocked = inp.wind_kmh >= WIND_BLOCK_KMH
    fungal = "high" if inp.wind_kmh < 5 and inp.effective_rain_mm > 5 else "low"
    reasons = [inp.stage]
    if inp.effective_rain_mm > 0:
        reasons.append("rain_reduces_need")
    if spray_blocked:
        reasons.append("wind_blocks_spray")
    return AgronomyResult(
        kc=kc,
        etc_mm=etc,
        gross_irrigation_mm=gross,
        spray_blocked=spray_blocked,
        fungal_risk=fungal,
        disease_risk=fungal,
        reasons=reasons,
    )


def spray_volume_liters(area_ha: float, liters_per_ha: float = 400.0) -> float:
    return round(area_ha * liters_per_ha, 1)
