"use client";

import {
  CalendarClock,
  CircleX,
  CloudSun,
  Leaf,
  SatelliteDish,
  ShieldAlert,
  SprayCan,
  Sun,
  TriangleAlert,
  Wind,
} from "lucide-react";
import StatusBadge from "@/components/ui/StatusBadge";
import TextsPanel from "./TextsPanel";
import {
  BLOCKING,
  RISK_LABEL,
  daysSince,
  fmtDate,
  fmtDateTime,
  fmtMm,
  methodLabel,
  reasonLabel,
} from "@/lib/labels";
import type { Recommendation } from "@/lib/types";

/** Result card. Every number shown here comes from the recommendation JSON. */
export default function TodayCard({ rec, sample = false }: { rec: Recommendation; sample?: boolean }) {
  const dose = rec.status === "show_dose" ? (rec.display_dose ?? rec.gross_irrigation_mm ?? null) : null;
  const reasons = rec.reasons ?? [];
  const blocking = reasons.filter((r) => BLOCKING.has(r));
  const info = reasons.filter((r) => !BLOCKING.has(r) && r !== "ok");
  const satAge = daysSince(rec.ndvi_observed_at);
  const risk = rec.fungal_risk ?? rec.disease_risk ?? null;

  return (
    <section className="panel" aria-labelledby="today-title">
      <div className="today-head">
        <h2 id="today-title">Aujourd&apos;hui sur {rec.plot_id}</h2>
        <div className="chips">
          {sample && <span className="badge sample">Exemple du contrat</span>}
          <StatusBadge status={rec.status} />
        </div>
      </div>

      {dose !== null ? (
        <div className="dose">
          <p className="dose-caption">Dose à apporter</p>
          <p className="dose-value num">
            {fmtMm(dose)}
            <small>mm</small>
          </p>
          <p className="dose-caption">en {methodLabel(rec.irrigation_method).toLowerCase()}, efficience comprise</p>
          <Ledger rec={rec} />
        </div>
      ) : (
        <div className="dose hidden" role="status">
          <p className="dose-title">
            <TriangleAlert size={22} /> Besoin à vérifier
          </p>
          <p className="dose-caption">
            La dose précise n&apos;est pas affichée tant que ces points ne sont pas confirmés.
          </p>
          <ul className="checklist">
            {(blocking.length ? blocking : ["missing_weather"]).map((r) => (
              <li key={r}>
                <CircleX size={17} color="var(--amber)" /> {reasonLabel(r)}
              </li>
            ))}
          </ul>
          {rec.etc_mm != null && (
            <p className="small muted" style={{ margin: "12px 0 0" }}>
              Consommation estimée de la culture : <strong className="num">{fmtMm(rec.etc_mm)} mm</strong> (ETc).
            </p>
          )}
        </div>
      )}

      <div className="facts">
        <Fact
          icon={<CloudSun size={20} />}
          k="Météo"
          v={rec.weather_observed_at ? fmtDateTime(rec.weather_observed_at) : "Indisponible"}
        />
        <Fact
          icon={<SatelliteDish size={20} />}
          k="Image satellite"
          v={
            rec.ndvi_observed_at
              ? `${fmtDate(rec.ndvi_observed_at)}${satAge !== null ? ` (${satAge} j)` : ""}`
              : "Aucune image exploitable"
          }
        />
        <Fact
          icon={<Leaf size={20} />}
          k="Vigueur NDVI"
          v={
            rec.ndvi != null
              ? `${fmtMm(rec.ndvi)}${rec.valid_pixel_pct != null ? `, ${fmtMm(rec.valid_pixel_pct, 0)} % pixels valides` : ""}`
              : "Non mesurée"
          }
        />
        <Fact
          icon={<Sun size={20} />}
          k="Évapotranspiration ET0"
          v={rec.et0_mm_day != null ? `${fmtMm(rec.et0_mm_day)} mm/j` : "Non calculée"}
        />
        <Fact
          icon={rec.spray_blocked ? <Wind size={20} /> : <SprayCan size={20} />}
          k="Traitement"
          v={
            rec.spray_blocked
              ? `Bloqué${rec.wind_kmh != null ? `, vent ${fmtMm(rec.wind_kmh, 0)} km/h` : ""}`
              : `Possible${rec.wind_kmh != null ? `, vent ${fmtMm(rec.wind_kmh, 0)} km/h` : ""}${
                  rec.spray_volume_l != null ? `, ${fmtMm(rec.spray_volume_l, 0)} L de bouillie` : ""
                }`
          }
          tone={rec.spray_blocked ? "blocked" : "good"}
        />
        <Fact
          icon={<ShieldAlert size={20} />}
          k="Risque fongique"
          v={risk ? RISK_LABEL[risk] ?? risk : "Non évalué"}
          tone={risk === "high" ? "blocked" : undefined}
        />
      </div>

      {info.length > 0 && (
        <div className="chips" style={{ marginTop: 14 }} aria-label="Raisons">
          {info.map((r) => (
            <span key={r} className="chip">
              {reasonLabel(r)}
            </span>
          ))}
        </div>
      )}

      <TextsPanel rec={rec} />

      <p className="small muted" style={{ margin: "14px 0 0", display: "flex", alignItems: "center", gap: 6 }}>
        <CalendarClock size={14} />
        Moteur {rec.engine_version ?? "—"}. Aide à la décision : vérifiez le sol avant de changer un tour d&apos;eau.
      </p>
    </section>
  );
}

function Ledger({ rec }: { rec: Recommendation }) {
  const etc = rec.etc_mm;
  const rain = rec.effective_rain_mm ?? 0;
  if (etc == null || etc <= 0) return null;
  const rainShare = Math.min(rain / etc, 1) * 100;
  return (
    <div className="ledger">
      <div className="ledger-bar" aria-hidden="true">
        <div className="rain" style={{ width: `${rainShare}%` }} />
        <div className="need" style={{ width: `${100 - rainShare}%` }} />
      </div>
      <dl className="ledger-legend">
        <div>
          <dt>Besoin ETc</dt>
          <dd className="num">{fmtMm(etc)} mm</dd>
        </div>
        <div>
          <dt>
            <span className="swatch" style={{ background: "var(--water)" }} /> Pluie utile
          </dt>
          <dd className="num">{fmtMm(rec.effective_rain_mm)} mm</dd>
        </div>
        <div>
          <dt>
            <span className="swatch" style={{ background: "var(--drop)" }} /> Irrigation
          </dt>
          <dd className="num">{fmtMm(rec.gross_irrigation_mm)} mm brut</dd>
        </div>
      </dl>
      <p className="small muted num" style={{ margin: "10px 0 0" }}>
        ETc = Kc {fmtMm(rec.kc)} × ET0 {fmtMm(rec.et0_mm_day)} mm
      </p>
    </div>
  );
}

function Fact({
  icon,
  k,
  v,
  tone,
}: {
  icon: React.ReactNode;
  k: string;
  v: string;
  tone?: "blocked" | "good";
}) {
  return (
    <div className={`fact ${tone ?? ""}`}>
      {icon}
      <span className="k">{k}</span>
      <span className="v num">{v}</span>
    </div>
  );
}
