/** Shapes from docs/contract.json and backend/app/api/v1. Never invent fields. */

export type Status = "show_dose" | "needs_check";
export type Risk = "low" | "medium" | "high";

export interface Recommendation {
  plot_id: string;
  crop?: string;
  stage?: string | null;
  area_ha?: number | null;
  irrigation_method?: string | null;
  et0_mm_day?: number | null;
  et0_source?: string | null;
  kc?: number | null;
  etc_mm?: number | null;
  effective_rain_mm?: number | null;
  gross_irrigation_mm?: number | null;
  display_dose?: number | null;
  ndvi?: number | null;
  ndwi?: number | null;
  ndvi_observed_at?: string | null;
  valid_pixel_pct?: number | null;
  satellite_source?: string | null;
  satellite_quality?: string | null;
  wind_kmh?: number | null;
  spray_blocked?: boolean;
  spray_volume_l?: number | null;
  disease_risk?: Risk | null;
  fungal_risk?: Risk | null;
  status: Status;
  reasons?: string[];
  engine_version?: string;
  weather_observed_at?: string | null;
  weather_quality?: string | null;
  texts?: { fr?: string; darija?: string; ar?: string };
  text_fr?: string;
  text_ary?: string;
  text_ar?: string;
}

export interface Plot {
  id: number;
  public_id: string;
  crop: string;
  stage: string;
  irrigation_method: string;
  area_ha: number;
  /** Optional until the Backend seat returns geometry. [[lon, lat], ...] */
  coordinates?: number[][][] | null;
}

export interface PlotCreate {
  public_id: string;
  crop: string;
  stage: string;
  irrigation_method: string;
  area_ha: number;
  last_irrigation_on?: string | null;
  coordinates?: number[][][] | null;
}

export interface AdvisorPlot {
  public_id: string;
  stage: string | null;
  status: Status | null;
  etc_mm: number | null;
  gross_irrigation_mm: number | null;
  /** Optional fields the Backend seat can add later. */
  coordinates?: number[][][] | null;
  lat?: number | null;
  lon?: number | null;
  ndvi_observed_at?: string | null;
  season_water_mm?: number | null;
}

export interface Session {
  token: string;
  role: "farmer" | "advisor";
  email: string;
}

export interface AskAnswer {
  answer: { fr?: string; darija?: string; ar?: string; note?: string };
  from_recommendation_id: number;
}
