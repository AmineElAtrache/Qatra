/** French labels for codes coming from the API. Unknown codes are shown as-is. */

export const STAGES: { value: string; label: string; sensitive: boolean }[] = [
  { value: "initial", label: "Reprise végétative", sensitive: false },
  { value: "flowering", label: "Floraison", sensitive: true },
  { value: "fruit_growth", label: "Grossissement du fruit", sensitive: true },
  { value: "maturity", label: "Maturation", sensitive: false },
  { value: "dormant", label: "Repos", sensitive: false },
];

export const METHODS: { value: string; label: string }[] = [
  { value: "drip", label: "Goutte-à-goutte" },
  { value: "surface", label: "Gravitaire" },
];

export const stageLabel = (v?: string | null) => STAGES.find((s) => s.value === v)?.label ?? v ?? "Stade inconnu";
export const methodLabel = (v?: string | null) => METHODS.find((m) => m.value === v)?.label ?? v ?? "Méthode inconnue";
export const isSensitive = (v?: string | null) => STAGES.find((s) => s.value === v)?.sensitive ?? false;

const REASONS: Record<string, string> = {
  initial: "Reprise végétative",
  flowering: "Floraison, stade sensible",
  fruit_growth: "Grossissement du fruit, stade sensible",
  maturity: "Maturation",
  dormant: "Repos végétatif",
  rain_reduces_need: "La pluie réduit le besoin",
  wind_blocks_spray: "Vent trop fort pour traiter",
  wind_unknown: "Vent inconnu, traitement suspendu",
  fungal_risk_high: "Risque fongique élevé",
  deficit_above_raw: "Réserve du sol sous le seuil",
  soil_reserve_ok: "Réserve du sol suffisante",
  missing_stage: "Stade non renseigné",
  unknown_stage: "Stade non reconnu",
  missing_irrigation_method: "Méthode d'irrigation non renseignée",
  unknown_irrigation_method: "Méthode d'irrigation non reconnue",
  missing_weather: "Météo indisponible",
  missing_et0: "Évapotranspiration non calculée",
  weather_stale: "Météo de plus de 48 h",
  missing_ndvi: "Pas d'image satellite exploitable",
  satellite_stale: "Image satellite de plus de 10 jours",
  low_valid_pixels: "Image trop nuageuse",
  ok: "Données complètes",
};

/** Reasons that explain why a dose is hidden. */
export const BLOCKING = new Set([
  "missing_stage",
  "unknown_stage",
  "missing_irrigation_method",
  "unknown_irrigation_method",
  "missing_weather",
  "missing_et0",
  "weather_stale",
  "missing_ndvi",
  "satellite_stale",
  "low_valid_pixels",
]);

export const reasonLabel = (code: string) => REASONS[code] ?? code;

export const RISK_LABEL: Record<string, string> = { low: "Faible", medium: "Moyen", high: "Élevé" };

export function fmtMm(v?: number | null, digits = 2): string {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("fr-FR", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
}

export function fmtDateTime(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}

export function daysSince(iso?: string | null): number | null {
  if (!iso) return null;
  const d = new Date(iso.length === 10 ? iso + "T12:00:00" : iso);
  if (Number.isNaN(d.getTime())) return null;
  return Math.floor((Date.now() - d.getTime()) / 86_400_000);
}
