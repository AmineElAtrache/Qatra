import type { Recommendation } from "./types";

/**
 * Copy of docs/contract.json (plot MA-001). Shown only in "exemple" mode,
 * always labelled as such — never as a measurement.
 */
export const CONTRACT_SAMPLE: Recommendation = {
  plot_id: "MA-001",
  crop: "citrus",
  stage: "fruit_growth",
  area_ha: 1.2,
  irrigation_method: "drip",
  et0_mm_day: 4.2,
  et0_source: "penman_monteith",
  kc: 0.75,
  etc_mm: 3.15,
  effective_rain_mm: 1.5,
  gross_irrigation_mm: 4.7,
  ndvi: 0.68,
  ndwi: 0.21,
  ndvi_observed_at: "2026-10-11",
  valid_pixel_pct: 86,
  satellite_source: "sentinel-2",
  wind_kmh: 9,
  spray_blocked: false,
  disease_risk: "low",
  fungal_risk: "low",
  status: "show_dose",
  reasons: ["fruit_growth", "rain_reduces_need"],
  engine_version: "0.1.0",
  texts: {
    fr: "Besoin estimé 3,15 mm (ETc). Pluie utile 1,5 mm. Dose brute indicative 4,7 mm en goutte-à-goutte.",
    darija: "L7aja dyal lma: 3.15 mm. Shta nafi3a: 1.5 mm. Doza ta9ribiya: 4.7 mm b drip.",
    ar: "الاحتياج التقديري 3.15 مم. مطر نافع 1.5 مم. جرعة خام إرشادية 4.7 مم بالتنقيط.",
  },
};

/** MA-001 ring from docs/samples/ma001.geojson, as [lon, lat]. */
export const MA001_RING: number[][] = [
  [-7.5898, 33.5731],
  [-7.5888, 33.5731],
  [-7.5888, 33.574],
  [-7.5898, 33.574],
  [-7.5898, 33.5731],
];
